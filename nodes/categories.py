"""
nodes/categories.py — 語彙辞書の大項目・中項目カテゴリ分類

nodes/decoration_data.py / pattern_data.py / material_data.py /
color_data.py / subject_data.py の「大項目・中項目でグループ化された
生データ」から、キー→カテゴリの対応表と大項目/中項目の日本語ラベルを
自動的に構築する。手動で2箇所に同じキーを書いてズレる、という事故を
防ぐための設計（vocabulary.py 側のフラット辞書も同じ生データから
構築されているため、両者は常に一致する）。

分類階層:
  - decoration_preset: 大項目 × 中項目（2階層）
  - pattern / material / color(TRADITIONAL_COLORS_JA) / subject_hint:
    大項目のみ（1階層）。項目数は多いが、中項目まで分割せず
    大項目のみで分類する。

ComfyUI のドロップダウンではこの分類を使って
"[大項目 > 中項目] english_key | 日本語ラベル" の形式でグルーピング表示する。

torch / ComfyUI に依存しない純粋データ + 関数のため、単体テスト可能。
"""

from __future__ import annotations

from . import color_data, decoration_data, material_data, pattern_data, subject_data, vocabulary

# ═══════════════════════════════════════════════════════════════════
# 装飾技法プリセット（decoration_preset）— 大項目 × 中項目
# ═══════════════════════════════════════════════════════════════════


def _build_decoration_categories():
    major_labels: dict[str, str] = {}
    mid_labels: dict[tuple[str, str], str] = {("none_custom", "none_custom"): "（分類なし）"}
    category_of: dict[str, tuple[str, str]] = {}
    for major, major_ja, mids in decoration_data.DECORATION_GROUPS:
        major_labels[major] = major_ja
        for mid, mid_ja, entries in mids:
            mid_labels[(major, mid)] = mid_ja
            for key, _phrases, _ja in entries:
                category_of[key] = (major, mid)
    return major_labels, mid_labels, category_of


DECORATION_MAJOR_LABELS_JA, DECORATION_MID_LABELS_JA, DECORATION_CATEGORY_OF = (
    _build_decoration_categories()
)


# ═══════════════════════════════════════════════════════════════════
# 単一階層カテゴリの共通ビルダー（pattern/material/color/subject用）
# ═══════════════════════════════════════════════════════════════════


def _build_single_level_categories(groups, key_index: int = 0):
    """
    groups: list[(major_key, major_ja, list[entry])]
    entry の先頭要素（key_index）をカテゴリ対象のキーとして使う。
    Returns: (major_labels: dict[str,str], category_of: dict[str,str])
    """
    major_labels: dict[str, str] = {}
    category_of: dict[str, str] = {}
    for major, major_ja, entries in groups:
        major_labels[major] = major_ja
        for entry in entries:
            key = entry[key_index]
            category_of[key] = major
    return major_labels, category_of


# ── 柄（pattern）— 大項目のみ ─────────────────────────────────────────
PATTERN_MAJOR_LABELS_JA, PATTERN_CATEGORY_OF = _build_single_level_categories(
    pattern_data.PATTERN_GROUPS
)

# ── 素材（material）— 大項目のみ ───────────────────────────────────────
MATERIAL_MAJOR_LABELS_JA, MATERIAL_CATEGORY_OF = _build_single_level_categories(
    material_data.MATERIAL_GROUPS
)

# ── 伝統色（TRADITIONAL_COLORS_JA）— 大項目のみ（色系統） ───────────────
COLOR_MAJOR_LABELS_JA, COLOR_CATEGORY_OF = _build_single_level_categories(
    color_data.COLOR_GROUPS
)

# ── 対象語（SUBJECT_HINT_JA_TO_EN）— 大項目のみ ─────────────────────────
SUBJECT_MAJOR_LABELS_JA, SUBJECT_CATEGORY_OF = _build_single_level_categories(
    subject_data.SUBJECT_GROUPS
)


# ═══════════════════════════════════════════════════════════════════
# 共通ヘルパー
# ═══════════════════════════════════════════════════════════════════

def grouped_decoration_options() -> list[str]:
    """
    decoration_preset を大項目→中項目の順でグルーピングし、
    "[大項目 > 中項目] english_key | 日本語ラベル" 形式のリストを返す。
    ComfyUI のドロップダウンにそのまま渡せる。
    """
    keys = list(vocabulary.DECORATION_PRESETS.keys())

    def sort_key(k: str) -> tuple[str, str, str]:
        major, mid = DECORATION_CATEGORY_OF.get(k, ("none_custom", "none_custom"))
        return (major, mid, k)

    ordered = sorted(keys, key=sort_key)
    out = []
    for k in ordered:
        major, mid = DECORATION_CATEGORY_OF.get(k, ("none_custom", "none_custom"))
        ja = vocabulary.DECORATION_LABELS_JA.get(k, "")
        if major == "none_custom":
            out.append(f"{k} | {ja}" if ja else k)
        else:
            major_ja = DECORATION_MAJOR_LABELS_JA.get(major, major)
            mid_ja = DECORATION_MID_LABELS_JA.get((major, mid), mid)
            out.append(f"[{major_ja} > {mid_ja}] {k} | {ja}")
    return out


def grouped_default_decoration(key: str) -> str:
    """grouped_decoration_options() と同じ形式でデフォルト値の文字列を作る。"""
    for opt in grouped_decoration_options():
        body = opt.split("] ", 1)[-1]
        if body.split(" | ", 1)[0] == key:
            return opt
    return key


def resolve_grouped_key(raw: str) -> str:
    """
    "[大項目 > 中項目] key | ja" / "key | ja" / "key" / 日本語ラベル の
    いずれからも英語キーを取り出す（先頭のグループラベルだけを取り除く）。
    残りは vocabulary.resolve_key 側でさらに解決される。
    """
    if raw is None:
        return ""
    raw = raw.strip()
    if "] " in raw:
        raw = raw.split("] ", 1)[1]
    return raw


def grouped_single_level_options(
    keys: list[str],
    labels_ja: dict[str, str],
    category_of: dict[str, str],
    major_labels: dict[str, str],
) -> list[str]:
    """pattern/material/color/subject_hint 用: 大項目のみでグルーピングした選択肢を返す。"""

    def sort_key(k: str) -> tuple[str, str]:
        return (category_of.get(k, "zzz_other"), k)

    ordered = sorted(keys, key=sort_key)
    out = []
    for k in ordered:
        major = category_of.get(k)
        ja = labels_ja.get(k, "")
        label = f"{k} | {ja}" if ja else k
        if major:
            out.append(f"[{major_labels.get(major, major)}] {label}")
        else:
            out.append(label)
    return out


def category_map_summary() -> dict[str, dict[str, list[str]]]:
    """decoration_preset の大項目→中項目→キー一覧をネスト辞書で返す（デバッグ/テスト用）。"""
    summary: dict[str, dict[str, list[str]]] = {}
    for key, (major, mid) in DECORATION_CATEGORY_OF.items():
        summary.setdefault(major, {}).setdefault(mid, []).append(key)
    return summary
