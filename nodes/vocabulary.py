"""
nodes/vocabulary.py — 服飾「装飾」プロンプト語彙ライブラリ

Face-Prompt-Studio の fps-core/clothing_refiner が持つ服飾カテゴリ
（服の種類そのもの: tops/bottoms/dress...）とは目的が異なり、
こちらは「既存の服の上に何を足す/どう加工するか」という
装飾（デコレーション）語彙に特化している。

torch / ComfyUI に依存しない純粋データ + 関数のため、単体テスト可能。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── 装飾技法プリセット ────────────────────────────────────────────────
# キー: UI（ComfyUIのドロップダウン）に出す短い識別子
# 値:   実際にプロンプトへ展開する語句（複数可）
DECORATION_PRESETS: dict[str, list[str]] = {
    "none": [],
    "embroidery": ["intricate embroidery", "embroidered pattern"],
    "lace_trim": ["lace trim", "delicate lace edging"],
    "sequins": ["sequined", "sparkling sequins"],
    "beading": ["beaded detail", "hand-beaded"],
    "ribbon_bow": ["ribbon bow accent", "satin ribbon"],
    "floral_applique": ["floral applique", "fabric flower decoration"],
    "gradient_dye": ["gradient dye", "ombre coloring"],
    "tie_dye": ["tie-dye pattern"],
    "patchwork": ["patchwork design", "mixed fabric patches"],
    "glitter": ["glitter accents", "shimmering glitter"],
    "holographic": ["holographic finish", "iridescent sheen"],
    "metallic_foil": ["metallic foil print", "metallic accents"],
    "fringe": ["fringe trim", "swaying fringe"],
    "tassel": ["tassel details"],
    "pearl_trim": ["pearl trim", "pearl embellishment"],
    "jewel_encrusted": ["jewel-encrusted", "gemstone embellishments"],
    "studs": ["metal studs", "studded detail"],
    "printed_pattern": ["printed graphic pattern"],
    "custom": [],  # free_text のみで構成
}

# ── 柄・模様（pattern）語彙 ──────────────────────────────────────────
PATTERN_VOCAB: dict[str, str] = {
    "none": "",
    "striped": "striped pattern",
    "polka_dot": "polka dot pattern",
    "floral": "floral pattern",
    "plaid": "plaid pattern",
    "checkered": "checkered pattern",
    "geometric": "geometric pattern",
    "animal_print": "animal print pattern",
    "camouflage": "camouflage pattern",
    "paisley": "paisley pattern",
    "houndstooth": "houndstooth pattern",
    "custom": "",
}

# ── 素材・質感（material）語彙 ────────────────────────────────────────
MATERIAL_VOCAB: dict[str, str] = {
    "none": "",
    "silk": "silk fabric",
    "leather": "leather texture",
    "denim": "denim fabric",
    "velvet": "velvet texture",
    "satin": "satin sheen",
    "lace": "lace fabric",
    "wool": "wool texture",
    "cotton": "cotton fabric",
    "chiffon": "sheer chiffon",
    "vinyl": "glossy vinyl",
    "custom": "",
}

# ── 基本色パレット（自由入力の補助用） ────────────────────────────────
BASE_COLORS: list[str] = [
    "black",
    "white",
    "red",
    "blue",
    "navy",
    "green",
    "yellow",
    "pink",
    "purple",
    "brown",
    "gray",
    "orange",
    "gold",
    "silver",
    "pastel",
    "custom",
]

DEFAULT_NEGATIVE_TERMS: list[str] = [
    "blurry",
    "low quality",
    "distorted fabric",
    "extra clothing layers",
    "mismatched pattern",
    "seam artifacts",
    "unnatural texture",
]


@dataclass
class DecorationPromptResult:
    """Prompt Composer ノードの整形結果。"""

    decoration_prompt: str
    inpaint_prompt: str
    negative_prompt: str
    merged_prompt: str
    terms_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "decoration_prompt": self.decoration_prompt,
            "inpaint_prompt": self.inpaint_prompt,
            "negative_prompt": self.negative_prompt,
            "merged_prompt": self.merged_prompt,
            "terms_used": self.terms_used,
        }


def _dedupe_list(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for t in terms:
        t = t.strip()
        if not t:
            continue
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def _dedupe_join(terms: list[str], sep: str = ", ") -> str:
    return sep.join(_dedupe_list(terms))


def build_decoration_prompt(
    decoration_preset: str = "none",
    pattern: str = "none",
    material: str = "none",
    color: str = "",
    free_text: str = "",
    subject_hint: str = "clothing",
    base_prompt: str = "",
    negative_extra: str = "",
) -> DecorationPromptResult:
    """
    プリセット選択＋自由入力から、装飾用プロンプト一式を組み立てる。

    Args:
        decoration_preset: DECORATION_PRESETS のキー
        pattern:            PATTERN_VOCAB のキー
        material:           MATERIAL_VOCAB のキー
        color:               色（自由入力可。"custom" プリセット時などに使用）
        free_text:            追加の自由記述プロンプト
        subject_hint:          対象の呼称（既定 "clothing"。"dress" 等に変更可）
        base_prompt:            既存プロンプト。指定すると末尾にマージした
                                merged_prompt を生成する
        negative_extra:          追加のネガティブプロンプト（カンマ区切り）

    Returns:
        DecorationPromptResult
    """
    terms: list[str] = []

    if color.strip():
        terms.append(color.strip())

    terms.extend(DECORATION_PRESETS.get(decoration_preset, []))

    pattern_term = PATTERN_VOCAB.get(pattern, "")
    if pattern_term:
        terms.append(pattern_term)

    material_term = MATERIAL_VOCAB.get(material, "")
    if material_term:
        terms.append(material_term)

    if free_text.strip():
        terms.append(free_text.strip())

    terms = _dedupe_list(terms)
    decoration_prompt = _dedupe_join(terms)

    # inpaint_prompt: 対象語＋装飾語（インペイント系ノードにそのまま渡す想定）
    inpaint_terms = [subject_hint.strip()] if subject_hint.strip() else []
    inpaint_terms.extend(terms)
    inpaint_prompt = _dedupe_join(inpaint_terms)

    negative_terms = list(DEFAULT_NEGATIVE_TERMS)
    if negative_extra.strip():
        negative_terms.extend(t.strip() for t in negative_extra.split(",") if t.strip())
    negative_prompt = _dedupe_join(negative_terms)

    if base_prompt.strip():
        # base_prompt はカンマ区切りの既存タグ列として扱い、装飾語との重複を除く
        base_terms = [t.strip() for t in base_prompt.split(",") if t.strip()]
        merged_prompt = _dedupe_join(base_terms + terms)
    else:
        merged_prompt = decoration_prompt

    return DecorationPromptResult(
        decoration_prompt=decoration_prompt,
        inpaint_prompt=inpaint_prompt,
        negative_prompt=negative_prompt,
        merged_prompt=merged_prompt,
        terms_used=terms,
    )
