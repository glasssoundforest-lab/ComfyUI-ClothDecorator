"""
nodes/model_adapter.py
ノード: 🧠 Cloth Decorator - Model Prompt Adapter

🧵 Prompt Composer / 🧩 Auto に限らず、任意のプロンプト文字列
（タグ列 or 自然文）を対象モデル系統（SD1.5アニメ系/Pony/Illustrious/
NoobAI/SDXL/FLUX/SD3 等）の慣習に合わせて変換・拡張する単体ノード。
既存ワークフローの CLIP Text Encode の直前に挟むだけで使える。

接続例:
  [任意のプロンプト文字列] ── prompt ──┐
                                          ├→ [🧠 Model Prompt Adapter] → model_prompt ──→ [CLIP Text Encode]
                          (target_model)─┘                              → model_negative_prompt → [CLIP Text Encode]
"""

from __future__ import annotations

from typing import Any

from . import model_profiles
from .node_base import ClothDecoratorNodeBase


class ClothPromptModelAdapterNode(ClothDecoratorNodeBase):
    """任意のプロンプトを対象モデル系統向けの書式に変換・拡張する。"""

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("model_prompt", "model_negative_prompt", "style_used")
    FUNCTION = "adapt"
    CATEGORY = "ClothDecorator"

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "forceInput": True,
                        "tooltip": "変換元プロンプト。tags系モデルへはカンマ区切りタグ列として解釈される",
                    },
                ),
                "target_model": (
                    [
                        f"{k} | {v.label_ja}" if v.label_ja else k
                        for k, v in model_profiles.MODEL_PROFILES.items()
                    ],
                    {
                        "default": f"generic | {model_profiles.MODEL_PROFILES['generic'].label_ja}",
                    },
                ),
            },
            "optional": {
                "subject_hint": (
                    "STRING",
                    {"default": "", "tooltip": "対象語（任意。指定するとプロンプト先頭に補われる）"},
                ),
                "negative_extra": (
                    "STRING",
                    {"default": "", "tooltip": "追加のネガティブ要素（カンマ区切り）"},
                ),
            },
        }

    def adapt(
        self,
        prompt: str,
        target_model: str,
        subject_hint: str = "",
        negative_extra: str = "",
    ) -> tuple[str, str, str]:
        model_key = target_model.split(" | ", 1)[0].strip()
        positive, negative, style_used = model_profiles.adapt_freeform_prompt(
            prompt=prompt,
            subject=subject_hint,
            negative_extra=negative_extra,
            target_model=model_key,
        )
        return positive, negative, style_used
