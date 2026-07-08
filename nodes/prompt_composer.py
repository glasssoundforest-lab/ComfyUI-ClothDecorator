"""
nodes/prompt_composer.py
ノード: 🧵 Cloth Decorator - Prompt Composer  （生成AI連携モード）

マスク領域を「どう装飾したいか」を語彙プリセット＋自由記述で組み立て、
下流の VAE Encode (for Inpainting) / SetLatentNoiseMask / KSampler などの
標準ComfyUIノードにそのまま接続できる prompt / negative_prompt /
prepared_mask を出力する。実際のピクセル生成はここでは行わない。

target_model を指定すると、装飾語彙を対象モデル系統（SD1.5アニメ系/
Pony/Illustrious/SDXL/FLUX/SD3 等）に適したタグ書式・自然文へ
自動的に変換・拡張した model_prompt / model_negative_prompt も出力する
（詳細は nodes/model_profiles.py を参照）。

接続例:
  [SAM等] ── mask ──┐
                      ├→ [🧵 Prompt Composer] → model_prompt ──→ [CLIP Text Encode]
  [既存プロンプト] ─┘                        → model_negative_prompt → [CLIP Text Encode]
                                              → prepared_mask → [SetLatentNoiseMask] / [VAE Encode (for Inpainting)]
"""

from __future__ import annotations

import json
from typing import Any

from . import mask_utils, model_profiles, vocabulary
from .node_base import ClothDecoratorNodeBase, mask_to_numpy, numpy_to_mask_tensor


class ClothPromptComposerNode(ClothDecoratorNodeBase):
    """マスク＋語彙選択から、生成系インペイントノード向けのプロンプトとマスクを組み立てる。"""

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "MASK", "STRING")
    RETURN_NAMES = (
        "prompt",
        "negative_prompt",
        "merged_prompt",
        "model_prompt",
        "model_negative_prompt",
        "prepared_mask",
        "debug_json",
    )
    FUNCTION = "compose"
    CATEGORY = "ClothDecorator"

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "mask": ("MASK", {"tooltip": "装飾対象の服領域マスク（SAM等から接続）"}),
                "decoration_preset": (
                    vocabulary.bilingual_options(
                        list(vocabulary.DECORATION_PRESETS.keys()), vocabulary.DECORATION_LABELS_JA
                    ),
                    {"default": vocabulary.bilingual_default("embroidery", vocabulary.DECORATION_LABELS_JA)},
                ),
                "pattern": (
                    vocabulary.bilingual_options(
                        list(vocabulary.PATTERN_VOCAB.keys()), vocabulary.PATTERN_LABELS_JA
                    ),
                    {"default": vocabulary.bilingual_default("none", vocabulary.PATTERN_LABELS_JA)},
                ),
                "material": (
                    vocabulary.bilingual_options(
                        list(vocabulary.MATERIAL_VOCAB.keys()), vocabulary.MATERIAL_LABELS_JA
                    ),
                    {"default": vocabulary.bilingual_default("none", vocabulary.MATERIAL_LABELS_JA)},
                ),
                "target_model": (
                    [
                        f"{k} | {v.label_ja}" if v.label_ja else k
                        for k, v in model_profiles.MODEL_PROFILES.items()
                    ],
                    {
                        "default": f"generic | {model_profiles.MODEL_PROFILES['generic'].label_ja}",
                        "tooltip": "model_prompt/model_negative_prompt の書式を合わせる対象モデル系統",
                    },
                ),
                "subject_hint": (
                    "STRING",
                    {
                        "default": "clothing",
                        "tooltip": "対象の呼称（dress, jacket 等。日本語も可: 'ドレス', '着物' など）",
                    },
                ),
                "grow_px": (
                    "INT",
                    {
                        "default": 8,
                        "min": 0,
                        "max": 200,
                        "tooltip": "インペイント時に境界を自然にするためマスクを膨張させる量",
                    },
                ),
                "feather_px": (
                    "FLOAT",
                    {"default": 6.0, "min": 0.0, "max": 100.0, "step": 0.5},
                ),
            },
            "optional": {
                "color": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "色（自由入力。例: 'red', '#ff0000', '藍色', 'ai-iro'）",
                    },
                ),
                "free_text": (
                    "STRING",
                    {"multiline": True, "default": "", "tooltip": "追加の自由記述プロンプト"},
                ),
                "base_prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "forceInput": True,
                        "tooltip": "既存プロンプト。指定すると末尾にマージした merged_prompt を出力",
                    },
                ),
                "negative_extra": (
                    "STRING",
                    {"default": "", "tooltip": "追加のネガティブプロンプト（カンマ区切り）"},
                ),
            },
        }

    def compose(
        self,
        mask: Any,
        decoration_preset: str,
        pattern: str,
        material: str,
        target_model: str,
        subject_hint: str,
        grow_px: int,
        feather_px: float,
        color: str = "",
        free_text: str = "",
        base_prompt: str = "",
        negative_extra: str = "",
    ) -> tuple[str, str, str, str, str, Any, str]:
        result = vocabulary.build_decoration_prompt(
            decoration_preset=decoration_preset,
            pattern=pattern,
            material=material,
            color=color,
            free_text=free_text,
            subject_hint=subject_hint,
            base_prompt=base_prompt,
            negative_extra=negative_extra,
        )

        model_key = target_model.split(" | ", 1)[0].strip()
        model_prompt, model_negative_prompt, style_used = model_profiles.adapt_prompt(
            terms=result.terms_used,
            subject=result.resolved.get("subject_hint", ""),
            negative_terms=result.negative_terms_used,
            target_model=model_key,
        )

        m = mask_to_numpy(mask)
        if grow_px > 0:
            m = mask_utils.grow_mask(m, grow_px)
        if feather_px > 0:
            m = mask_utils.feather_mask(m, feather_px)

        debug = result.to_dict()  # "resolved" キーに解決済みの英語キーが入る
        debug["grow_px"] = grow_px
        debug["feather_px"] = feather_px
        debug["raw_decoration_preset"] = decoration_preset
        debug["raw_pattern"] = pattern
        debug["raw_material"] = material
        debug["target_model"] = model_key
        debug["prompt_style_used"] = style_used

        return (
            result.inpaint_prompt,
            result.negative_prompt,
            result.merged_prompt,
            model_prompt,
            model_negative_prompt,
            numpy_to_mask_tensor(m),
            json.dumps(debug, ensure_ascii=False, indent=2),
        )
