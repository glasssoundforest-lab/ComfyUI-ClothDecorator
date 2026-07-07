"""
nodes/prompt_composer.py
ノード: 🧵 Cloth Decorator - Prompt Composer  （生成AI連携モード）

マスク領域を「どう装飾したいか」を語彙プリセット＋自由記述で組み立て、
下流の VAE Encode (for Inpainting) / SetLatentNoiseMask / KSampler などの
標準ComfyUIノードにそのまま接続できる prompt / negative_prompt /
prepared_mask を出力する。実際のピクセル生成はここでは行わない。

接続例:
  [SAM等] ── mask ──┐
                      ├→ [🧵 Prompt Composer] → prompt ──→ [CLIP Text Encode]
  [既存プロンプト] ─┘                        → negative_prompt → [CLIP Text Encode]
                                              → prepared_mask → [SetLatentNoiseMask] / [VAE Encode (for Inpainting)]
"""

from __future__ import annotations

import json
from typing import Any

from . import mask_utils, vocabulary
from .node_base import ClothDecoratorNodeBase, mask_to_numpy, numpy_to_mask_tensor


class ClothPromptComposerNode(ClothDecoratorNodeBase):
    """マスク＋語彙選択から、生成系インペイントノード向けのプロンプトとマスクを組み立てる。"""

    RETURN_TYPES = ("STRING", "STRING", "STRING", "MASK", "STRING")
    RETURN_NAMES = ("prompt", "negative_prompt", "merged_prompt", "prepared_mask", "debug_json")
    FUNCTION = "compose"
    CATEGORY = "ClothDecorator"

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "mask": ("MASK", {"tooltip": "装飾対象の服領域マスク（SAM等から接続）"}),
                "decoration_preset": (
                    list(vocabulary.DECORATION_PRESETS.keys()),
                    {"default": "embroidery"},
                ),
                "pattern": (list(vocabulary.PATTERN_VOCAB.keys()), {"default": "none"}),
                "material": (list(vocabulary.MATERIAL_VOCAB.keys()), {"default": "none"}),
                "subject_hint": (
                    "STRING",
                    {"default": "clothing", "tooltip": "対象の呼称（dress, jacket 等に変更可）"},
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
                "color": ("STRING", {"default": "", "tooltip": "色（自由入力。例: 'red', '#ff0000'）"}),
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
        subject_hint: str,
        grow_px: int,
        feather_px: float,
        color: str = "",
        free_text: str = "",
        base_prompt: str = "",
        negative_extra: str = "",
    ) -> tuple[str, str, str, Any, str]:
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

        m = mask_to_numpy(mask)
        if grow_px > 0:
            m = mask_utils.grow_mask(m, grow_px)
        if feather_px > 0:
            m = mask_utils.feather_mask(m, feather_px)

        debug = result.to_dict()
        debug["grow_px"] = grow_px
        debug["feather_px"] = feather_px
        debug["decoration_preset"] = decoration_preset
        debug["pattern"] = pattern
        debug["material"] = material

        return (
            result.inpaint_prompt,
            result.negative_prompt,
            result.merged_prompt,
            numpy_to_mask_tensor(m),
            json.dumps(debug, ensure_ascii=False, indent=2),
        )
