"""
nodes/auto_mode.py
ノード: 🧩 Cloth Decorator - Auto （両対応統合ノード）

🎨 Direct Paint と 🧵 Prompt Composer の機能を1ノードにまとめ、
mode 選択で切り替えられるようにしたもの。ワークフローを組み替えずに
「その場でどちらの装飾方式を使うか」を切り替えたい場合に使う。
個別に細かく制御したい場合は 🎨 / 🧵 の専用ノードを直接使うことを推奨する。

mode = "direct_paint":       image を直接加工して返す（generative_* 出力は空）
mode = "generative_prompt":  プロンプト一式とマスクを返す（image はパススルー）。
                              target_model を指定すると model_prompt /
                              model_negative_prompt も対象モデル系統に
                              合わせて生成・拡張される（詳細は
                              nodes/model_profiles.py を参照）。
"""

from __future__ import annotations

import json
from typing import Any

from . import mask_utils, model_profiles, paint_ops, vocabulary
from .node_base import (
    ClothDecoratorNodeBase,
    mask_to_numpy,
    numpy_to_mask_tensor,
    numpy_to_tensor,
    tensor_to_numpy_uint8,
)


class ClothDecoratorAutoNode(ClothDecoratorNodeBase):
    """mode で Direct Paint / Prompt Composer を切り替える統合ノード。"""

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING", "STRING", "STRING", "MASK", "STRING")
    RETURN_NAMES = (
        "image",
        "prompt",
        "negative_prompt",
        "merged_prompt",
        "model_prompt",
        "model_negative_prompt",
        "prepared_mask",
        "debug_json",
    )
    FUNCTION = "run"
    CATEGORY = "ClothDecorator"

    @classmethod
    def IS_CHANGED(cls, **kwargs: Any) -> float:
        return float("nan")

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "mode": (["direct_paint", "generative_prompt"], {"default": "generative_prompt"}),
                "image": ("IMAGE",),
                "mask": ("MASK",),
                "decoration_type": (
                    ["solid_color", "gradient_fill", "pattern_tile", "texture_blend"],
                    {"default": "solid_color", "tooltip": "mode=direct_paint のとき使用"},
                ),
                "decoration_preset": (
                    vocabulary.bilingual_options(
                        list(vocabulary.DECORATION_PRESETS.keys()), vocabulary.DECORATION_LABELS_JA
                    ),
                    {
                        "default": vocabulary.bilingual_default(
                            "embroidery", vocabulary.DECORATION_LABELS_JA
                        ),
                        "tooltip": "mode=generative_prompt のとき使用",
                    },
                ),
                "target_model": (
                    [
                        f"{k} | {v.label_ja}" if v.label_ja else k
                        for k, v in model_profiles.MODEL_PROFILES.items()
                    ],
                    {
                        "default": f"generic | {model_profiles.MODEL_PROFILES['generic'].label_ja}",
                        "tooltip": "mode=generative_prompt のとき model_prompt の書式を合わせる対象モデル系統",
                    },
                ),
                "color": (
                    "STRING",
                    {
                        "default": "#c0392b",
                        "tooltip": "'#rrggbb' / 'r,g,b' / 日本語伝統色（例: '藍色', 'ai-iro'）",
                    },
                ),
                "opacity": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.05}),
                "feather_px": ("FLOAT", {"default": 5.0, "min": 0.0, "max": 100.0, "step": 0.5}),
            },
            "optional": {
                "color_b": ("STRING", {"default": "#f1c40f"}),
                "pattern_image": ("IMAGE",),
                "texture_image": ("IMAGE",),
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
                "free_text": ("STRING", {"multiline": True, "default": ""}),
                "subject_hint": ("STRING", {"default": "clothing"}),
                "base_prompt": ("STRING", {"multiline": True, "default": "", "forceInput": True}),
                "grow_px": ("INT", {"default": 8, "min": 0, "max": 200}),
            },
        }

    def run(
        self,
        mode: str,
        image: Any,
        mask: Any,
        decoration_type: str,
        decoration_preset: str,
        target_model: str,
        color: str,
        opacity: float,
        feather_px: float,
        color_b: str = "#f1c40f",
        pattern_image: Any = None,
        texture_image: Any = None,
        pattern: str = "none",
        material: str = "none",
        free_text: str = "",
        subject_hint: str = "clothing",
        base_prompt: str = "",
        grow_px: int = 8,
    ) -> tuple[Any, str, str, str, str, str, Any, str]:
        mask_np = mask_to_numpy(mask)

        if mode == "direct_paint":
            img_np = tensor_to_numpy_uint8(image)
            shape = img_np.shape[:2]
            color_hex = vocabulary.resolve_color_to_hex(color)
            color_b_hex = vocabulary.resolve_color_to_hex(color_b)

            if decoration_type == "solid_color":
                effect = paint_ops.solid_color_fill(shape, color_hex)
            elif decoration_type == "gradient_fill":
                effect = paint_ops.gradient_fill(shape, color_hex, color_b_hex, 0.0)
            elif decoration_type == "pattern_tile":
                if pattern_image is None:
                    raise ValueError("pattern_tile には pattern_image の接続が必要です")
                effect = paint_ops.pattern_tile(shape, tensor_to_numpy_uint8(pattern_image))
            elif decoration_type == "texture_blend":
                if texture_image is None:
                    raise ValueError("texture_blend には texture_image の接続が必要です")
                effect = paint_ops.texture_blend(
                    img_np, tensor_to_numpy_uint8(texture_image), opacity=1.0, mode="normal"
                )
            else:
                raise ValueError(f"unknown decoration_type: {decoration_type}")

            result = paint_ops.apply_within_mask(
                img_np, mask_np, effect, feather_px=feather_px, opacity=opacity, blend_mode="normal"
            )
            debug = {"mode": mode, "decoration_type": decoration_type}
            return (
                numpy_to_tensor(result),
                "",
                "",
                "",
                "",
                "",
                numpy_to_mask_tensor(mask_np),
                json.dumps(debug, ensure_ascii=False),
            )

        # mode == "generative_prompt"
        result = vocabulary.build_decoration_prompt(
            decoration_preset=decoration_preset,
            pattern=pattern,
            material=material,
            color=color,
            free_text=free_text,
            subject_hint=subject_hint,
            base_prompt=base_prompt,
        )

        model_key = target_model.split(" | ", 1)[0].strip()
        model_prompt, model_negative_prompt, style_used = model_profiles.adapt_prompt(
            terms=result.terms_used,
            subject=result.resolved.get("subject_hint", ""),
            negative_terms=result.negative_terms_used,
            target_model=model_key,
        )

        prepared = mask_np
        if grow_px > 0:
            prepared = mask_utils.grow_mask(prepared, grow_px)
        if feather_px > 0:
            prepared = mask_utils.feather_mask(prepared, feather_px)

        debug = result.to_dict()
        debug["mode"] = mode
        debug["target_model"] = model_key
        debug["prompt_style_used"] = style_used
        return (
            image,
            result.inpaint_prompt,
            result.negative_prompt,
            result.merged_prompt,
            model_prompt,
            model_negative_prompt,
            numpy_to_mask_tensor(prepared),
            json.dumps(debug, ensure_ascii=False),
        )
