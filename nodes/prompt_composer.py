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

from . import categories, mask_utils, model_profiles, vocabulary
from .node_base import ClothDecoratorNodeBase, mask_to_numpy, numpy_to_mask_tensor


class ClothPromptComposerNode(ClothDecoratorNodeBase):
    """マスク＋語彙選択から、生成系インペイントノード向けのプロンプトとマスクを組み立てる。"""

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "MASK", "STRING", "STRING")
    RETURN_NAMES = (
        "prompt",
        "negative_prompt",
        "merged_prompt",
        "model_prompt",
        "model_negative_prompt",
        "prepared_mask",
        "conflict_warning",
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
                    categories.grouped_decoration_options(),
                    {"default": categories.grouped_default_decoration("embroidery")},
                ),
                "pattern": (
                    categories.grouped_single_level_options(
                        list(vocabulary.PATTERN_VOCAB.keys()),
                        vocabulary.PATTERN_LABELS_JA,
                        categories.PATTERN_CATEGORY_OF,
                        categories.PATTERN_MAJOR_LABELS_JA,
                    ),
                    {"default": vocabulary.bilingual_default("none", vocabulary.PATTERN_LABELS_JA)},
                ),
                "material": (
                    categories.grouped_single_level_options(
                        list(vocabulary.MATERIAL_VOCAB.keys()),
                        vocabulary.MATERIAL_LABELS_JA,
                        categories.MATERIAL_CATEGORY_OF,
                        categories.MATERIAL_MAJOR_LABELS_JA,
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
                "output_language": (
                    ["en", "ja"],
                    {
                        "default": "en",
                        "tooltip": (
                            "prompt/merged_prompt/model_prompt を英語(en)か日本語(ja)で組み立てるか。"
                            "free_text/base_prompt は自動翻訳されない。"
                        ),
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
                "confirm_continue": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "color/free_text/subject_hint の間で色や対象の服/部位が"
                            "複数競合している場合、既定ではエラーで停止して内容を確認できるようにする。"
                            "内容を確認した上で意図通りであれば ON にして再実行すると続行する。"
                        ),
                    },
                ),
                "group_by_category": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "ON にすると、color/decoration_preset/pattern/material/free_text から"
                            "集めたタグを、色→装飾技法→柄→素材→その他の順でカテゴリごとに"
                            "ブロックにまとめて並べ替える（各カテゴリ内の相対順序は保つ）。"
                        ),
                    },
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
                "decoration_preset_override": (
                    "STRING",
                    {
                        "default": "",
                        "forceInput": True,
                        "tooltip": (
                            "指定するとdecoration_presetドロップダウンより優先される。"
                            "🔍 Image Analyzer の suggested_decoration_preset を接続する用途。"
                        ),
                    },
                ),
                "pattern_override": (
                    "STRING",
                    {
                        "default": "",
                        "forceInput": True,
                        "tooltip": "指定するとpatternドロップダウンより優先される（🔍 Image Analyzer 用）。",
                    },
                ),
                "material_override": (
                    "STRING",
                    {
                        "default": "",
                        "forceInput": True,
                        "tooltip": "指定するとmaterialドロップダウンより優先される（🔍 Image Analyzer 用）。",
                    },
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
        output_language: str,
        subject_hint: str,
        grow_px: int,
        feather_px: float,
        confirm_continue: bool = False,
        group_by_category: bool = False,
        color: str = "",
        free_text: str = "",
        base_prompt: str = "",
        negative_extra: str = "",
        decoration_preset_override: str = "",
        pattern_override: str = "",
        material_override: str = "",
    ) -> tuple[str, str, str, str, str, Any, str, str]:
        decoration_preset = categories.resolve_grouped_key(decoration_preset)
        pattern = categories.resolve_grouped_key(pattern)
        material = categories.resolve_grouped_key(material)

        if decoration_preset_override.strip():
            decoration_preset = categories.resolve_grouped_key(decoration_preset_override.strip())
        if pattern_override.strip():
            pattern = categories.resolve_grouped_key(pattern_override.strip())
        if material_override.strip():
            material = categories.resolve_grouped_key(material_override.strip())

        # タグの衝突検出（同じカテゴリに異なる値が複数指定されていないか）。
        # 検出された場合、confirm_continue=False（既定）なら処理を中断してエラーで
        # 知らせる（ComfyUI上でノードが赤くハイライトされ、内容を確認できる）。
        # 内容を確認した上で意図通りなら confirm_continue=True で再実行すれば続行する。
        conflicts = vocabulary.detect_tag_conflicts(
            color=color, free_text=free_text, subject_hint=subject_hint
        )
        conflict_warning = vocabulary.format_conflict_message(conflicts)
        if conflicts and not confirm_continue:
            details = "\n".join(f"  - {c.message}" for c in conflicts)
            raise ValueError(
                "⚠ タグの競合が検出されました。内容を確認してください:\n"
                f"{details}\n"
                "意図した内容であれば confirm_continue を ON にして再実行すると続行します。"
            )

        result = vocabulary.build_decoration_prompt(
            decoration_preset=decoration_preset,
            pattern=pattern,
            material=material,
            color=color,
            free_text=free_text,
            subject_hint=subject_hint,
            base_prompt=base_prompt,
            negative_extra=negative_extra,
            output_language=output_language,
            group_by_category=group_by_category,
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
        debug["output_language"] = output_language
        debug["overrides_applied"] = {
            "decoration_preset": bool(decoration_preset_override.strip()),
            "pattern": bool(pattern_override.strip()),
            "material": bool(material_override.strip()),
        }
        debug["conflicts"] = [
            {"category": c.category, "values": c.values, "message": c.message} for c in conflicts
        ]
        debug["confirm_continue"] = confirm_continue
        debug["group_by_category"] = group_by_category

        return (
            result.inpaint_prompt,
            result.negative_prompt,
            result.merged_prompt,
            model_prompt,
            model_negative_prompt,
            numpy_to_mask_tensor(m),
            conflict_warning,
            json.dumps(debug, ensure_ascii=False, indent=2),
        )
