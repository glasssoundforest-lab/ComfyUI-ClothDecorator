"""
nodes/vocabulary.py — 服飾「装飾」プロンプト語彙ライブラリ（日本語対応）

Face-Prompt-Studio の fps-core/clothing_refiner が持つ服飾カテゴリ
（服の種類そのもの: tops/bottoms/dress...）とは目的が異なり、
こちらは「既存の服の上に何を足す/どう加工するか」という
装飾（デコレーション）語彙に特化している。

torch / ComfyUI に依存しない純粋データ + 関数のため、単体テスト可能。

── 日本語対応方針 ──────────────────────────────────────────────────
Stable Diffusion 系モデルは基本的に英語プロンプトの方が精度が高いため、
辞書のキー・実際にプロンプトへ展開される語句は英語のまま維持する。
その上で:
  1. 各キーに日本語ラベル（*_LABELS_JA）を対応付け、ComfyUI の
     ドロップダウンに "english_key | 日本語ラベル" の形式で表示する。
  2. resolve_key() が "english_key"・"english_key | 日本語ラベル"・
     日本語ラベルそのもの のどれを渡されても正しいキーへ解決する。
  3. 色・対象語（subject_hint）は自由入力のため、日本語の伝統色名や
     服飾用語を英語のプロンプト語へ変換する辞書（TRADITIONAL_COLORS_JA /
     SUBJECT_HINT_JA_TO_EN）を用意し、resolve_color_term() /
     resolve_subject_hint() で変換する。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ═══════════════════════════════════════════════════════════════════
# 装飾技法プリセット
# ═══════════════════════════════════════════════════════════════════
# キー: UI（ComfyUIのドロップダウン）に出す短い識別子（英語・不変）
# 値:   実際にプロンプトへ展開する語句（複数可、英語）
from . import color_data, decoration_data, material_data, pattern_data, subject_data

# ═══════════════════════════════════════════════════════════════════
# 装飾技法プリセット（decoration_preset）
# ═══════════════════════════════════════════════════════════════════
# 実体データは nodes/decoration_data.py（大項目・中項目でグループ化）に
# 集約されており、ここではそれを展開してフラットな辞書を作るだけ。
# categories.py 側もこの同じ decoration_data モジュールから
# 大項目/中項目の対応表を作るため、二重管理によるズレが発生しない。


def _build_decoration_vocab() -> tuple[dict[str, list[str]], dict[str, str]]:
    presets: dict[str, list[str]] = {"none": [], "custom": []}
    labels_ja: dict[str, str] = {"none": "なし", "custom": "自由入力"}
    for _major, _major_ja, mids in decoration_data.DECORATION_GROUPS:
        for _mid, _mid_ja, entries in mids:
            for key, phrases, ja in entries:
                presets[key] = phrases
                labels_ja[key] = ja
    return presets, labels_ja


DECORATION_PRESETS, DECORATION_LABELS_JA = _build_decoration_vocab()

# ═══════════════════════════════════════════════════════════════════
# 柄（pattern）語彙
# ═══════════════════════════════════════════════════════════════════


def _build_pattern_vocab() -> tuple[dict[str, str], dict[str, str]]:
    vocab: dict[str, str] = {"none": "", "custom": ""}
    labels_ja: dict[str, str] = {"none": "なし", "custom": "自由入力"}
    for _major, _major_ja, entries in pattern_data.PATTERN_GROUPS:
        for key, phrase, ja in entries:
            vocab[key] = phrase
            labels_ja[key] = ja
    return vocab, labels_ja


PATTERN_VOCAB, PATTERN_LABELS_JA = _build_pattern_vocab()

# ═══════════════════════════════════════════════════════════════════
# 素材・質感（material）語彙
# ═══════════════════════════════════════════════════════════════════


def _build_material_vocab() -> tuple[dict[str, str], dict[str, str]]:
    vocab: dict[str, str] = {"none": "", "custom": ""}
    labels_ja: dict[str, str] = {"none": "なし", "custom": "自由入力"}
    for _major, _major_ja, entries in material_data.MATERIAL_GROUPS:
        for key, phrase, ja in entries:
            vocab[key] = phrase
            labels_ja[key] = ja
    return vocab, labels_ja


MATERIAL_VOCAB, MATERIAL_LABELS_JA = _build_material_vocab()

# ═══════════════════════════════════════════════════════════════════
# 色
# ═══════════════════════════════════════════════════════════════════
# 基本色パレット（自由入力の補助用。英語のまま）
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
    "beige",
    "cream",
    "burgundy",
    "teal",
    "custom",
]

# BASE_COLORS の代表hexコード（画像解析ノードの色マッチング用）。"pastel"/"custom" は
# 具体色ではないため対象外。
BASE_COLOR_HEX: dict[str, str] = {
    "black": "#0a0a0a",
    "white": "#f5f5f5",
    "red": "#e63946",
    "blue": "#1d4ed8",
    "navy": "#1e293b",
    "green": "#16a34a",
    "yellow": "#eab308",
    "pink": "#ec4899",
    "purple": "#7c3aed",
    "brown": "#7c4a25",
    "gray": "#6b7280",
    "orange": "#f97316",
    "gold": "#d4af37",
    "silver": "#c0c0c0",
    "beige": "#d9c8a9",
    "cream": "#fdf6e3",
    "burgundy": "#6d071a",
    "teal": "#147a72",
}

# BASE_COLORS の日本語訳（output_language="ja" 時の色語彙として使用）
BASE_COLOR_EN_TO_JA: dict[str, str] = {
    "black": "黒",
    "white": "白",
    "red": "赤",
    "blue": "青",
    "navy": "紺",
    "green": "緑",
    "yellow": "黄色",
    "pink": "ピンク",
    "purple": "紫",
    "brown": "茶色",
    "gray": "グレー",
    "orange": "オレンジ",
    "gold": "金色",
    "silver": "銀色",
    "pastel": "パステルカラー",
    "beige": "ベージュ",
    "cream": "クリーム色",
    "burgundy": "えんじ色",
    "teal": "ティール",
}


# 日本の伝統色名 → {ローマ字読み, CLIPプロンプト向け英語表現, 16進カラーコード}
# color フィールドに「藍色」「ai-iro」のいずれを入力しても解決できるようにする。
# 実体データは nodes/color_data.py（色系統でグループ化）に集約されている。
def _build_traditional_colors() -> dict[str, dict[str, str]]:
    colors: dict[str, dict[str, str]] = {}
    for _family, _family_ja, entries in color_data.COLOR_GROUPS:
        for kanji, romaji, en, hex_code in entries:
            colors[kanji] = {"romaji": romaji, "en": en, "hex": hex_code}
    return colors


TRADITIONAL_COLORS_JA: dict[str, dict[str, str]] = _build_traditional_colors()


# ── 服飾対象語（subject_hint）日本語→英語 ─────────────────────────────
# 実体データは nodes/subject_data.py（大項目でグループ化）に集約されている。
def _build_subject_hints() -> dict[str, str]:
    hints: dict[str, str] = {}
    for _major, _major_ja, entries in subject_data.SUBJECT_GROUPS:
        for ja, en in entries:
            hints[ja] = en
    return hints


SUBJECT_HINT_JA_TO_EN: dict[str, str] = _build_subject_hints()

# SUBJECT_HINT_JA_TO_EN の逆引き（英語→日本語）。output_language="ja" 時に、
# ユーザーが英語で subject_hint を入力した場合でも日本語表現へ変換するために使う。
# 複数の日本語表記が同じ英語に対応する場合（例: スカーフ/マフラー→scarf）は
# 辞書定義順で後勝ちになる（scarf → "マフラー"）。
SUBJECT_HINT_EN_TO_JA: dict[str, str] = {v: k for k, v in SUBJECT_HINT_JA_TO_EN.items()}

DEFAULT_NEGATIVE_TERMS: list[str] = [
    "blurry",
    "low quality",
    "distorted fabric",
    "extra clothing layers",
    "mismatched pattern",
    "seam artifacts",
    "unnatural texture",
]

# DEFAULT_NEGATIVE_TERMS の日本語版（output_language="ja" 時に使用）
DEFAULT_NEGATIVE_TERMS_JA: list[str] = [
    "ブレ",
    "低品質",
    "不自然な生地",
    "余分な衣服レイヤー",
    "柄の不一致",
    "縫い目の乱れ",
    "不自然な質感",
]


@dataclass
class DecorationPromptResult:
    """Prompt Composer ノードの整形結果。"""

    decoration_prompt: str
    inpaint_prompt: str
    negative_prompt: str
    merged_prompt: str
    terms_used: list[str] = field(default_factory=list)
    negative_terms_used: list[str] = field(default_factory=list)
    resolved: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "decoration_prompt": self.decoration_prompt,
            "inpaint_prompt": self.inpaint_prompt,
            "negative_prompt": self.negative_prompt,
            "merged_prompt": self.merged_prompt,
            "terms_used": self.terms_used,
            "negative_terms_used": self.negative_terms_used,
            "resolved": self.resolved,
        }


# ═══════════════════════════════════════════════════════════════════
# 内部ヘルパー
# ═══════════════════════════════════════════════════════════════════

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


def bilingual_options(keys: list[str], labels_ja: dict[str, str]) -> list[str]:
    """ComfyUI ドロップダウン用に "english_key | 日本語ラベル" 形式のリストを作る。"""
    out = []
    for k in keys:
        ja = labels_ja.get(k)
        out.append(f"{k} | {ja}" if ja else k)
    return out


def bilingual_default(key: str, labels_ja: dict[str, str]) -> str:
    """bilingual_options() と同じ形式でデフォルト値の文字列を作る。"""
    ja = labels_ja.get(key)
    return f"{key} | {ja}" if ja else key


def resolve_key(raw: str, valid_keys: set[str] | dict, labels_ja: dict[str, str]) -> str:
    """
    "english_key"・"english_key | 日本語ラベル"・日本語ラベルそのもの の
    いずれを渡されても、辞書の正しい英語キーへ解決する。
    どれにも一致しない場合は raw をそのまま返す（未知値のフォールバック）。
    """
    if isinstance(valid_keys, dict):
        valid_keys = set(valid_keys.keys())
    if raw is None:
        return "none" if "none" in valid_keys else ""
    raw = raw.strip()
    if not raw:
        return "none" if "none" in valid_keys else raw
    if raw in valid_keys:
        return raw
    if " | " in raw:
        candidate = raw.split(" | ", 1)[0].strip()
        if candidate in valid_keys:
            return candidate
    for k, v in labels_ja.items():
        if v == raw:
            return k
    return raw


def _match_traditional_color(raw: str) -> tuple[str, dict[str, str]] | None:
    """入力文字列を日本の伝統色辞書（漢字名 or ローマ字）から検索する。(漢字キー, エントリ) を返す。"""
    if not raw or not raw.strip():
        return None
    raw_stripped = raw.strip()
    if raw_stripped in TRADITIONAL_COLORS_JA:
        return raw_stripped, TRADITIONAL_COLORS_JA[raw_stripped]
    lower = raw_stripped.lower()
    for kanji, entry in TRADITIONAL_COLORS_JA.items():
        if entry["romaji"].lower() == lower:
            return kanji, entry
    return None


def resolve_color_term(raw: str) -> str:
    """
    色名を CLIP プロンプト向けの英語表現に変換する。
    日本の伝統色名（漢字/ローマ字）に一致すればその英語表現を返し、
    一致しなければ入力をそのまま返す（"red" や "#ff0000" 等はそのまま通す）。
    """
    if not raw or not raw.strip():
        return ""
    match = _match_traditional_color(raw)
    return match[1]["en"] if match else raw.strip()


def resolve_color_to_hex(raw: str) -> str:
    """
    色名を直接画像処理（Direct Paint）向けの16進カラーコードに変換する。
    日本の伝統色名に一致すればその hex を返し、一致しなければ入力を
    そのまま返す（'#rrggbb' や 'r,g,b' 形式はそのまま paint_ops 側で解釈される）。
    """
    if not raw or not raw.strip():
        return raw
    match = _match_traditional_color(raw)
    return match[1]["hex"] if match else raw


def resolve_color_bilingual(raw: str) -> tuple[str, str]:
    """
    色名を (英語表現, 日本語表現) のペアに変換する。output_language の切り替えに使う。
    日本の伝統色名に一致すればその漢字名を、BASE_COLORS の英語色名に一致すれば
    対応する日本語訳を、どちらにも一致しなければ入力をそのまま両方に使う
    （翻訳できない自由記述はベストエフォートで素通しする）。
    """
    if not raw or not raw.strip():
        return "", ""
    raw_stripped = raw.strip()
    match = _match_traditional_color(raw_stripped)
    if match:
        kanji, entry = match
        return entry["en"], kanji
    ja = BASE_COLOR_EN_TO_JA.get(raw_stripped.lower())
    if ja:
        return raw_stripped, ja
    return raw_stripped, raw_stripped


def resolve_subject_hint(raw: str) -> str:
    """対象語（subject_hint）の日本語表記を英語のプロンプト語へ変換する。"""
    if not raw or not raw.strip():
        return "clothing"
    raw = raw.strip()
    return SUBJECT_HINT_JA_TO_EN.get(raw, raw)


def resolve_subject_bilingual(raw: str) -> tuple[str, str]:
    """
    対象語を (英語表現, 日本語表現) のペアに変換する。output_language の切り替えに使う。
    日本語入力ならその英訳を、英語入力なら SUBJECT_HINT_EN_TO_JA から日本語訳を探す。
    どちらの辞書にも無い場合は入力をそのまま両方に使う。
    """
    if not raw or not raw.strip():
        return "clothing", "服"
    raw = raw.strip()
    if raw in SUBJECT_HINT_JA_TO_EN:
        return SUBJECT_HINT_JA_TO_EN[raw], raw
    ja = SUBJECT_HINT_EN_TO_JA.get(raw.lower())
    if ja:
        return raw, ja
    return raw, raw


# ═══════════════════════════════════════════════════════════════════
# メイン関数
# ═══════════════════════════════════════════════════════════════════

def build_decoration_prompt(
    decoration_preset: str = "none",
    pattern: str = "none",
    material: str = "none",
    color: str = "",
    free_text: str = "",
    subject_hint: str = "clothing",
    base_prompt: str = "",
    negative_extra: str = "",
    output_language: str = "en",
) -> DecorationPromptResult:
    """
    プリセット選択＋自由入力から、装飾用プロンプト一式を組み立てる。

    decoration_preset / pattern / material は、英語キー・
    "english_key | 日本語ラベル"（ComfyUIドロップダウンの表示形式）・
    日本語ラベルそのもの のいずれでも指定できる。
    color / subject_hint は日本語の伝統色名・服飾用語にも対応する
    （例: color="藍色" や "ai-iro" → "deep indigo blue" に変換される）。

    output_language="ja" を指定すると、decoration_prompt / inpaint_prompt /
    merged_prompt / negative_prompt を日本語語彙で組み立てる（各キーに
    対応する日本語ラベル・伝統色名・和訳ネガティブ語を使用）。
    free_text / base_prompt はユーザーの生入力のため自動翻訳はされず、
    そのまま両言語で使われる点に注意。

    Args:
        decoration_preset: DECORATION_PRESETS のキー（日本語ラベルも可）
        pattern:            PATTERN_VOCAB のキー（日本語ラベルも可）
        material:           MATERIAL_VOCAB のキー（日本語ラベルも可）
        color:               色（自由入力可。日本語の伝統色名にも対応）
        free_text:            追加の自由記述プロンプト（翻訳されない）
        subject_hint:          対象の呼称（既定 "clothing"。日本語も可）
        base_prompt:            既存プロンプト。指定すると末尾にマージした
                                merged_prompt を生成する（翻訳されない）
        negative_extra:          追加のネガティブプロンプト（カンマ区切り、翻訳されない）
        output_language:          "en"（既定）または "ja"

    Returns:
        DecorationPromptResult
    """
    lang = output_language if output_language in ("en", "ja") else "en"

    preset_key = resolve_key(decoration_preset, DECORATION_PRESETS, DECORATION_LABELS_JA)
    pattern_key = resolve_key(pattern, PATTERN_VOCAB, PATTERN_LABELS_JA)
    material_key = resolve_key(material, MATERIAL_VOCAB, MATERIAL_LABELS_JA)
    color_en, color_ja = resolve_color_bilingual(color)
    subject_en, subject_ja = resolve_subject_bilingual(subject_hint)

    if lang == "ja":
        color_term = color_ja
        subject_term = subject_ja
        preset_terms = (
            [DECORATION_LABELS_JA[preset_key]] if preset_key not in ("none", "custom") else []
        )
        pattern_term = PATTERN_LABELS_JA.get(pattern_key, "") if pattern_key not in ("none", "custom") else ""
        material_term = (
            MATERIAL_LABELS_JA.get(material_key, "") if material_key not in ("none", "custom") else ""
        )
        negative_base = DEFAULT_NEGATIVE_TERMS_JA
    else:
        color_term = color_en
        subject_term = subject_en
        preset_terms = DECORATION_PRESETS.get(preset_key, [])
        pattern_term = PATTERN_VOCAB.get(pattern_key, "")
        material_term = MATERIAL_VOCAB.get(material_key, "")
        negative_base = DEFAULT_NEGATIVE_TERMS

    terms: list[str] = []

    if color_term:
        terms.append(color_term)

    terms.extend(preset_terms)

    if pattern_term:
        terms.append(pattern_term)

    if material_term:
        terms.append(material_term)

    if free_text.strip():
        terms.append(free_text.strip())

    terms = _dedupe_list(terms)
    decoration_prompt = _dedupe_join(terms)

    # inpaint_prompt: 対象語＋装飾語（インペイント系ノードにそのまま渡す想定）
    inpaint_terms = [subject_term] if subject_term else []
    inpaint_terms.extend(terms)
    inpaint_prompt = _dedupe_join(inpaint_terms)

    negative_terms = list(negative_base)
    if negative_extra.strip():
        negative_terms.extend(t.strip() for t in negative_extra.split(",") if t.strip())
    negative_terms = _dedupe_list(negative_terms)
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
        negative_terms_used=negative_terms,
        resolved={
            "decoration_preset": preset_key,
            "pattern": pattern_key,
            "material": material_key,
            "color": color_term,
            "subject_hint": subject_term,
            "output_language": lang,
            "color_en": color_en,
            "color_ja": color_ja,
            "subject_hint_en": subject_en,
            "subject_hint_ja": subject_ja,
        },
    )
