"""
nodes/color_analysis.py — マスク領域の色解析コアロジック

torch / ComfyUI に依存しない純粋関数群。マスクされた画素集合から
代表色（クラスタ中心）を抽出し、vocabulary の色語彙（日本の伝統色 +
BASE_COLORS）の中から最も近い色を探す。単体テスト可能。

外部依存: numpy のみ（scikit-learn 等は使わない軽量k-means実装）。
"""

from __future__ import annotations

import math

import numpy as np

from . import vocabulary

# k-means のクラスタ数・反復回数の上限。代表色抽出は本来少数（数個〜十数個）で
# 十分な用途のため、上限を超える指定は「意味がない」として安全にクランプする。
# これが無いと、例えば num_colors に極端に大きい値を渡された場合、
# 距離行列 (N, k, 3) の N・k がどちらも大きくなり、数十GB規模のメモリ確保で
# クラッシュしうる（k は事実上 N に近づくほど危険）。
_MAX_K = 16
_MAX_ITERS = 50


def _sanitize_int(value: float, default: int, lo: int, hi: int) -> int:
    """NaN/Inf/変換不能な値を default に丸め、[lo, hi] にクランプする。"""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(v):
        return default
    return max(lo, min(hi, int(round(v))))


def extract_masked_pixels(
    image: np.ndarray, mask: np.ndarray, threshold: float = 0.5
) -> np.ndarray:
    """
    image: (H,W,3) uint8, mask: (H,W) float32 0-1
    mask > threshold の画素だけを (N,3) uint8 で返す。該当画素が無ければ
    画像全体の画素を返す（フォールバック）。
    """
    sel = mask > threshold
    pixels = image[sel]
    if pixels.size == 0:
        return image.reshape(-1, 3)
    return pixels


def kmeans_colors(
    pixels: np.ndarray, k: int = 3, iters: int = 8, seed: int = 0
) -> list[tuple[tuple[int, int, int], float]]:
    """
    pixels: (N,3) uint8 の画素集合。
    軽量な k-means（numpyのみ、外部ライブラリ不要）でk個の代表色を求める。
    戻り値: [((r,g,b), 割合0-1), ...] をクラスタサイズの大きい順で返す。
    """
    if pixels.shape[0] == 0:
        return []

    data = pixels.astype("float64")
    n = data.shape[0]
    k = _sanitize_int(k, default=3, lo=1, hi=min(_MAX_K, n))
    iters = _sanitize_int(iters, default=8, lo=1, hi=_MAX_ITERS)

    rng = np.random.default_rng(seed)
    # k-means++ 風の初期化（単純化: ランダムサンプルから重複無しで選ぶ）
    init_idx = rng.choice(n, size=k, replace=False)
    centers = data[init_idx].copy()

    for _ in range(max(1, iters)):
        dists = ((data[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = dists.argmin(axis=1)
        new_centers = centers.copy()
        for i in range(k):
            members = data[labels == i]
            if members.shape[0] > 0:
                new_centers[i] = members.mean(axis=0)
        if np.allclose(new_centers, centers, atol=1e-3):
            centers = new_centers
            break
        centers = new_centers

    dists = ((data[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    labels = dists.argmin(axis=1)
    counts = np.bincount(labels, minlength=k)
    order = np.argsort(-counts)

    result = []
    for i in order:
        if counts[i] == 0:
            continue
        rgb = tuple(int(round(c)) for c in centers[i])
        weight = float(counts[i]) / float(n)
        result.append((rgb, weight))
    return result


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.strip().lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return float(sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5)


def _named_color_candidates() -> dict[str, dict[str, str]]:
    """
    色マッチング候補プールを作る。
    キー: 表示名（日本語伝統色は漢字名、BASE_COLORSは英語名）
    値: {"hex":..., "en":..., "ja":...}
    """
    pool: dict[str, dict[str, str]] = {}
    for kanji, entry in vocabulary.TRADITIONAL_COLORS_JA.items():
        pool[kanji] = {"hex": entry["hex"], "en": entry["en"], "ja": kanji}
    for name, hex_code in vocabulary.BASE_COLOR_HEX.items():
        ja = vocabulary.BASE_COLOR_EN_TO_JA.get(name, name)
        pool[name] = {"hex": hex_code, "en": name, "ja": ja}
    return pool


def nearest_named_color(rgb: tuple[int, int, int]) -> dict[str, str | float]:
    """
    rgb に最も近い語彙上の色（日本の伝統色 or BASE_COLORS）を探す。
    戻り値: {"name_en":..., "name_ja":..., "hex":..., "distance":...}
    """
    pool = _named_color_candidates()
    best_name = None
    best_entry = None
    best_dist = float("inf")
    for name, entry in pool.items():
        cand_rgb = _hex_to_rgb(entry["hex"])
        d = _color_distance(rgb, cand_rgb)
        if d < best_dist:
            best_dist = d
            best_name = name
            best_entry = entry
    assert best_entry is not None
    return {
        "matched_key": best_name,
        "name_en": best_entry["en"],
        "name_ja": best_entry["ja"],
        "hex": best_entry["hex"],
        "distance": best_dist,
    }


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*[max(0, min(255, c)) for c in rgb])


def analyze_masked_region(
    image: np.ndarray,
    mask: np.ndarray,
    num_colors: int = 3,
    mask_threshold: float = 0.5,
    match_distance_threshold: float = 60.0,
) -> dict:
    """
    マスク領域の代表色を抽出し、語彙上の最寄り色とマッチングする。

    Returns:
        {
          "dominant_colors": [{"hex":..., "weight":...}, ...],
          "best_match": {"name_en":..., "name_ja":..., "hex":..., "distance":..., "is_close_match": bool},
          "all_matches": [同形式のリスト（各代表色に対応）],
        }
    """
    pixels = extract_masked_pixels(image, mask, threshold=mask_threshold)
    clusters = kmeans_colors(pixels, k=num_colors)

    dominant_colors = [{"hex": rgb_to_hex(rgb), "weight": round(w, 4)} for rgb, w in clusters]

    all_matches = []
    for rgb, weight in clusters:
        match = nearest_named_color(rgb)
        match["source_hex"] = rgb_to_hex(rgb)
        match["weight"] = round(weight, 4)
        match["is_close_match"] = match["distance"] <= match_distance_threshold
        all_matches.append(match)

    best_match = all_matches[0] if all_matches else None

    return {
        "dominant_colors": dominant_colors,
        "best_match": best_match,
        "all_matches": all_matches,
    }
