"""
nodes/mask_utils.py — マスク処理コアロジック

torch / ComfyUI に依存しない純粋関数群。numpy + PIL のみに依存するため、
ノード本体（node_base の torch 変換）とは独立して pytest で単体テスト可能。

すべてのマスクは numpy.float32, shape (H, W), 値域 0.0-1.0（1.0=対象領域）で表現する。
すべての画像は numpy.uint8, shape (H, W, 3) で表現する。
"""

from __future__ import annotations

import math
from typing import Literal

import numpy as np

CombineMode = Literal["union", "intersect", "subtract", "xor"]

# 巨大値・NaN・Infなどの異常入力からPIL呼び出しを守るための上限値。
# これらを超える値は「効果が飽和する」とみなして上限にクランプする
# （エラーにせず、常に有限時間で完了することを優先する）。
_FEATHER_MAX_PX = 500.0
_GROW_SHRINK_MAX_PX = 300.0


def _sanitize_amount(value: float, cap: float) -> float:
    """
    NaN/Inf/文字列型・負値などの異常な値を 0（無処理）に丸め、
    有効な正の値は cap を超えないようクランプする。
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(v) or v <= 0:
        return 0.0
    return min(v, cap)


# ── マスク整形 ────────────────────────────────────────────────────────

def feather_mask(mask: np.ndarray, feather_px: float) -> np.ndarray:
    """マスクの境界をガウスぼかしで滑らかにする（合成時の境目を目立たなくする）。"""
    amount = _sanitize_amount(feather_px, _FEATHER_MAX_PX)
    if amount <= 0:
        return mask.astype("float32")
    from PIL import Image, ImageFilter

    img = Image.fromarray((np.clip(mask, 0, 1) * 255).astype("uint8"), mode="L")
    blurred = img.filter(ImageFilter.GaussianBlur(radius=amount))
    return np.asarray(blurred, dtype="float32") / 255.0


def grow_mask(mask: np.ndarray, px: int) -> np.ndarray:
    """
    マスク領域を px ピクセル分だけ膨張させる（近似dilate）。

    実装メモ: PIL の ImageFilter.MaxFilter(size=2N+1) を1回呼ぶ方式は
    カーネルが大きくなるほど極端に遅くなる（512x512画像でN=50でも3秒超、
    N=100以上は事実上停止する）。3x3 の MaxFilter を N 回繰り返す方式は
    数学的に同一の結果（maxは冪等・結合的な演算のため）を、大幅に高速かつ
    Nに対して線形の時間で計算できるため、この実装を採用している。
    """
    amount = _sanitize_amount(px, _GROW_SHRINK_MAX_PX)
    if amount <= 0:
        return mask.astype("float32")
    from PIL import Image, ImageFilter

    n = int(round(amount))
    img = Image.fromarray((np.clip(mask, 0, 1) * 255).astype("uint8"), mode="L")
    for _ in range(n):
        img = img.filter(ImageFilter.MaxFilter(3))
    return np.asarray(img, dtype="float32") / 255.0


def shrink_mask(mask: np.ndarray, px: int) -> np.ndarray:
    """マスク領域を px ピクセル分だけ収縮させる（近似erode）。grow_mask と同じ理由で反復方式を採用。"""
    amount = _sanitize_amount(px, _GROW_SHRINK_MAX_PX)
    if amount <= 0:
        return mask.astype("float32")
    from PIL import Image, ImageFilter

    n = int(round(amount))
    img = Image.fromarray((np.clip(mask, 0, 1) * 255).astype("uint8"), mode="L")
    for _ in range(n):
        img = img.filter(ImageFilter.MinFilter(3))
    return np.asarray(img, dtype="float32") / 255.0


def invert_mask(mask: np.ndarray) -> np.ndarray:
    return (1.0 - np.clip(mask, 0, 1)).astype("float32")


def combine_masks(a: np.ndarray, b: np.ndarray, mode: CombineMode = "union") -> np.ndarray:
    """2つのマスクを合成する。union=和集合 / intersect=積集合 / subtract=a-b / xor=排他的論理和"""
    a = np.clip(a, 0, 1)
    b = np.clip(b, 0, 1)
    if a.shape != b.shape:
        raise ValueError(f"mask shape mismatch: {a.shape} vs {b.shape}")
    if mode == "union":
        out = np.maximum(a, b)
    elif mode == "intersect":
        out = np.minimum(a, b)
    elif mode == "subtract":
        out = np.clip(a - b, 0, 1)
    elif mode == "xor":
        out = np.clip(np.abs(a - b), 0, 1)
    else:
        raise ValueError(f"unknown combine mode: {mode}")
    return out.astype("float32")


# ── バウンディングボックス抽出・クロップ・貼り戻し ────────────────────

def mask_bbox(mask: np.ndarray, threshold: float = 0.02) -> tuple[int, int, int, int] | None:
    """マスクの非ゼロ領域を囲む (x0, y0, x1, y1)（x1/y1は排他的）を返す。空マスクなら None。"""
    ys, xs = np.where(mask > threshold)
    if ys.size == 0 or xs.size == 0:
        return None
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    return x0, y0, x1, y1


def _sanitize_signed(value: float) -> float:
    """NaN/Inf/変換不能な値のみ 0 に丸め、符号・大きさはそのまま保つ（pad等の収縮/拡張両対応値用）。"""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return v if math.isfinite(v) else 0.0


def pad_bbox(
    bbox: tuple[int, int, int, int],
    pad: int,
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    """
    bbox を pad ピクセル分拡張（負値なら収縮）し、画像範囲内に収める。
    NaN/Inf な pad は 0（無処理）として扱う。収縮方向に極端な pad が
    渡されても、x0<=x1・y0<=y1 が破綻しない（bboxが反転しない）ことを保証する。
    """
    x0, y0, x1, y1 = bbox
    pad = int(round(_sanitize_signed(pad)))

    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(width, x1 + pad)
    y1 = min(height, y1 + pad)

    # 収縮しすぎて反転した場合は、中心点で1pxの矩形に潰して安全側に倒す
    if x0 > x1:
        cx = (x0 + x1) // 2
        x0 = x1 = max(0, min(width, cx))
    if y0 > y1:
        cy = (y0 + y1) // 2
        y0 = y1 = max(0, min(height, cy))
    return x0, y0, x1, y1


def crop_to_bbox(image: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = bbox
    return image[y0:y1, x0:x1, ...].copy()


def paste_back(
    original: np.ndarray,
    patch: np.ndarray,
    bbox: tuple[int, int, int, int],
    patch_mask: np.ndarray | None = None,
    feather_px: float = 0.0,
) -> np.ndarray:
    """
    加工済みの patch（bbox サイズの画像）を original の bbox 位置に貼り戻す。

    patch_mask（bbox と同サイズ、0-1）が与えられた場合、そのマスクで
    アルファブレンドする。feather_px > 0 の場合は貼り戻し境界を
    ガウスぼかしして継ぎ目を目立たなくする。patch_mask が None の場合は
    bbox 全域を単純に上書きする。
    """
    x0, y0, x1, y1 = bbox
    out = original.copy()
    region_h, region_w = y1 - y0, x1 - x0
    if patch.shape[0] != region_h or patch.shape[1] != region_w:
        raise ValueError(
            f"patch size {patch.shape[:2]} does not match bbox size {(region_h, region_w)}"
        )

    if patch_mask is None:
        out[y0:y1, x0:x1, ...] = patch
        return out

    m = patch_mask.astype("float32")
    if feather_px > 0:
        m = feather_mask(m, feather_px)
    m3 = m[..., None] if out.ndim == 3 else m

    region = out[y0:y1, x0:x1, ...].astype("float32")
    blended = region * (1.0 - m3) + patch.astype("float32") * m3
    out[y0:y1, x0:x1, ...] = np.clip(blended, 0, 255).astype(original.dtype)
    return out
