"""
nodes/model_profiles.py — 生成モデルに応じたプロンプト適応・拡張ロジック

同じ装飾内容（terms）でも、対象モデルの系統によって最適なプロンプト書式は
大きく異なる:

  - booru タグ系（SD1.5アニメ系, Pony Diffusion, Illustrious, NoobAI 等）:
      カンマ区切りタグ、単語はアンダースコア表記が慣習。モデルごとに
      決まった quality/negative タグの接頭辞がある（例: Pony の
      "score_9, score_8_up..." や Illustrious の "masterpiece, best quality"）。
  - 自然文系（SDXL Base, SD3/3.5, FLUX.1 等）:
      カンマ区切りタグ列より、流暢な英語の説明文の方が指示に忠実に
      従う傾向がある。FLUX.1 系は基本的に negative prompt を使わない
      （CFG/ガイダンス機構が異なるため）。

build_decoration_prompt() が返す語彙（terms_used / resolved など）を
受け取り、target_model に応じてプロンプトを組み立てる（tags）か、
自然文へ拡張する（natural）。

torch / ComfyUI に依存しない純粋データ + 関数のため、単体テスト可能。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ModelProfile:
    key: str
    label_ja: str
    style: str  # "tags" | "natural" | "natural_sentence"
    quality_prefix: list[str] = field(default_factory=list)
    negative_prefix: list[str] = field(default_factory=list)
    supports_negative: bool = True
    underscore_tags: bool = False
    notes: str = ""


MODEL_PROFILES: dict[str, ModelProfile] = {
    "generic": ModelProfile(
        key="generic",
        label_ja="汎用（無加工のタグ列）",
        style="tags",
        quality_prefix=[],
        negative_prefix=[],
        supports_negative=True,
        underscore_tags=False,
        notes="quality/negativeタグの自動付与や語形変換を行わない、そのままのタグ列。",
    ),
    "sd15_anime": ModelProfile(
        key="sd15_anime",
        label_ja="SD1.5系アニメモデル（Danbooruタグ形式）",
        style="tags",
        quality_prefix=["masterpiece", "best quality", "highres"],
        negative_prefix=[
            "worst quality",
            "low quality",
            "normal quality",
            "jpeg artifacts",
            "signature",
            "watermark",
        ],
        supports_negative=True,
        underscore_tags=True,
        notes="NAI系/Anything系などDanbooruタグ学習モデル向け。単語はアンダースコア区切り。",
    ),
    "sdxl_base": ModelProfile(
        key="sdxl_base",
        label_ja="SDXL Base（自然文寄り）",
        style="natural",
        quality_prefix=["high quality", "highly detailed"],
        negative_prefix=["blurry", "low quality", "deformed", "disfigured"],
        supports_negative=True,
        underscore_tags=False,
        notes="SDXL Base/RefinerはCLIP-Gの自然文理解が強いため、説明文形式を推奨。",
    ),
    "pony_v6": ModelProfile(
        key="pony_v6",
        label_ja="Pony Diffusion V6 XL",
        style="tags",
        quality_prefix=["score_9", "score_8_up", "score_7_up"],
        negative_prefix=["score_6", "score_5", "score_4", "worst quality", "low quality"],
        supports_negative=True,
        underscore_tags=True,
        notes="Pony系はscore_9等のqualityタグ、ネガティブ側にscore_6以下を入れるのが慣習。",
    ),
    "illustrious": ModelProfile(
        key="illustrious",
        label_ja="Illustrious XL",
        style="tags",
        quality_prefix=["masterpiece", "best quality", "very aesthetic", "absurdres"],
        negative_prefix=["worst quality", "low quality", "bad anatomy"],
        supports_negative=True,
        underscore_tags=True,
        notes="Danbooruタグ学習のXLモデル。",
    ),
    "noobai": ModelProfile(
        key="noobai",
        label_ja="NoobAI XL",
        style="tags",
        quality_prefix=["masterpiece", "best quality", "newest"],
        negative_prefix=["worst quality", "old", "early", "low quality"],
        supports_negative=True,
        underscore_tags=True,
        notes="年代タグ（newest/old等）を持つ学習慣習に合わせている。",
    ),
    "flux": ModelProfile(
        key="flux",
        label_ja="FLUX.1（自然文・ネガティブ非対応）",
        style="natural_sentence",
        quality_prefix=[],
        negative_prefix=[],
        supports_negative=False,
        underscore_tags=False,
        notes="FLUX.1はnegative promptを基本的に使わないアーキテクチャのため、"
        "model_negative_prompt は空文字を返す。",
    ),
    "sd3": ModelProfile(
        key="sd3",
        label_ja="Stable Diffusion 3 / 3.5",
        style="natural_sentence",
        quality_prefix=[],
        negative_prefix=["blurry", "low quality"],
        supports_negative=True,
        underscore_tags=False,
        notes="T5+CLIPのハイブリッドエンコーダのため自然文推奨。",
    ),
}


def model_choices() -> list[str]:
    return list(MODEL_PROFILES.keys())


def _tagify(term: str, underscore: bool) -> str:
    t = term.strip()
    if not t:
        return ""
    if underscore:
        t = t.replace(" ", "_")
    return t


def _dedupe_join(parts: list[str], sep: str = ", ") -> str:
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return sep.join(out)


def _join_natural(terms: list[str]) -> str:
    terms = [t.strip() for t in terms if t.strip()]
    if not terms:
        return ""
    if len(terms) == 1:
        return terms[0]
    return ", ".join(terms[:-1]) + f", and {terms[-1]}"


def _build_natural_sentence(subject: str, terms: list[str], profile: ModelProfile) -> str:
    """
    タグの羅列ではなく、流暢な英語の説明文へと「拡張」する。
    自然文系モデル（SDXL/SD3/FLUX等）はこの形式の方が指示追従性が高い。
    """
    subj = subject.strip() if subject and subject.strip() else "the garment"
    if not terms:
        sentence = f"A finely detailed, high quality photo of {subj}."
    else:
        joined = _join_natural(terms)
        sentence = (
            f"A {subj} elaborately decorated with {joined}, "
            f"rendered with fine, photorealistic fabric detail and natural draping."
        )
    if profile.quality_prefix:
        prefix = " ".join(profile.quality_prefix).capitalize()
        sentence = f"{prefix}. {sentence}"
    return sentence


def adapt_prompt(
    terms: list[str],
    subject: str,
    negative_terms: list[str],
    target_model: str = "generic",
) -> tuple[str, str, str]:
    """
    装飾語彙（terms）を target_model に応じたプロンプトへ変換・拡張する。

    Args:
        terms:            装飾語彙のリスト（vocabulary.build_decoration_prompt の
                          terms_used。英語）
        subject:            対象語（英語。resolved["subject_hint"] 等）
        negative_terms:     ベースのネガティブ語彙リスト（英語）
        target_model:        MODEL_PROFILES のキー

    Returns:
        (positive_prompt, negative_prompt, style_used)
        style_used は "tags" | "natural" | "natural_sentence"
    """
    profile = MODEL_PROFILES.get(target_model, MODEL_PROFILES["generic"])

    if profile.style == "tags":
        subj_tag = _tagify(subject, profile.underscore_tags) if subject else ""
        tag_terms = [_tagify(t, profile.underscore_tags) for t in terms]
        pos_parts = list(profile.quality_prefix) + ([subj_tag] if subj_tag else []) + tag_terms
        positive = _dedupe_join(pos_parts)
    else:
        positive = _build_natural_sentence(subject, terms, profile)

    if not profile.supports_negative:
        negative = ""
    else:
        if profile.style == "tags":
            neg_parts = [
                _tagify(t, profile.underscore_tags)
                for t in (list(profile.negative_prefix) + list(negative_terms))
            ]
        else:
            neg_parts = list(profile.negative_prefix) + list(negative_terms)
        negative = _dedupe_join(neg_parts)

    return positive, negative, profile.style


def adapt_freeform_prompt(
    prompt: str,
    subject: str = "",
    negative_extra: str = "",
    target_model: str = "generic",
) -> tuple[str, str, str]:
    """
    任意のプロンプト文字列（タグ列 or 自然文）を target_model に適応・拡張する。
    🧵 Prompt Composer / 🧩 Auto の内部語彙に限らず、既存のプロンプトを
    別のモデル系統向けに変換したい場合に単体で使う（🧠 Model Prompt Adapter ノード用）。

    style="tags" 系モデルへは prompt をカンマ区切りタグ列として解釈し、
    quality タグの付与・アンダースコア化を行う。
    style="natural"系モデルへは prompt をほぼそのまま自然文として扱い、
    quality の前置き文と subject の導入句のみを付加する（拡張）。

    Args:
        prompt:           変換元プロンプト（タグ列 or 自然文、英語推奨）
        subject:            対象語（任意。指定すると先頭に補われる）
        negative_extra:      追加のネガティブ要素（カンマ区切り）
        target_model:         MODEL_PROFILES のキー

    Returns:
        (positive_prompt, negative_prompt, style_used)
    """
    profile = MODEL_PROFILES.get(target_model, MODEL_PROFILES["generic"])
    prompt = (prompt or "").strip()
    subject = (subject or "").strip()

    if profile.style == "tags":
        terms = [t.strip() for t in prompt.split(",") if t.strip()]
        tag_terms = [_tagify(t, profile.underscore_tags) for t in terms]
        subj_tag = _tagify(subject, profile.underscore_tags) if subject else ""
        pos_parts = list(profile.quality_prefix) + ([subj_tag] if subj_tag else []) + tag_terms
        positive = _dedupe_join(pos_parts)
    else:
        body = prompt
        if subject and subject.lower() not in body.lower():
            body = f"{subject}. {body}" if body else subject
        if profile.quality_prefix:
            prefix = " ".join(profile.quality_prefix).capitalize()
            body = f"{prefix}. {body}" if body else f"{prefix}."
        positive = body.strip()

    if not profile.supports_negative:
        negative = ""
    else:
        neg_terms = [t.strip() for t in negative_extra.split(",") if t.strip()]
        if profile.style == "tags":
            neg_parts = [
                _tagify(t, profile.underscore_tags)
                for t in (list(profile.negative_prefix) + neg_terms)
            ]
        else:
            neg_parts = list(profile.negative_prefix) + neg_terms
        negative = _dedupe_join(neg_parts)

    return positive, negative, profile.style
