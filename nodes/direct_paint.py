"""
nodes/direct_paint.py
ノード: 🎨 Cloth Decorator - Direct Paint （直接画像処理モード）

拡散モデルを使わず、PIL/numpy でマスク領域に直接:
  - 単色塗り (solid_color)
  - グラデーション (gradient_fill)
  - 柄タイリング (pattern_tile: pattern_image を敷き詰め)
  - テクスチャ合成 (texture_blend: texture_image をブレンド)
  - 明るさ/コントラスト調整 (brightness_contrast)
  - 色相シフト (hue_shift)
を適用する。軽量・決定的・GPU/拡散モデル不要。
"""

from __future__ import annotations

from typing import Any

from . import paint_ops
from .node_base import (
    ClothDecoratorNodeBase,
    mask_to_numpy,
    numpy_to_tensor,
    tensor_to_numpy_uint8,
)


class ClothDirectPaintNode(ClothDecoratorNodeBase):
    """マスク領域に直接ピクセル加工を適用する（拡散モデル不要）。"""

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "paint"
    CATEGORY = "ClothDecorator"

    @classmethod
    def IS_CHANGED(cls, **kwargs: Any) -> float:
        return float("nan")  # 決定的だが image/mask 入力の変化を確実に反映するため毎回実行

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "image": ("IMAGE",),
                "mask": ("MASK",),
                "decoration_type": (
                    [
                        "solid_color",
                        "gradient_fill",
                        "pattern_tile",
                        "texture_blend",
                        "brightness_contrast",
                        "hue_shift",
                    ],
                    {"default": "solid_color"},
                ),
                "color": ("STRING", {"default": "#c0392b", "tooltip": "'#rrggbb' または 'r,g,b'"}),
                "color_b": (
                    "STRING",
                    {"default": "#f1c40f", "tooltip": "gradient_fill の第2色"},
                ),
                "angle": (
                    "FLOAT",
                    {"default": 0.0, "min": -360.0, "max": 360.0, "step": 1.0, "tooltip": "gradient_fill の角度(度)"},
                ),
                "opacity": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.05}),
                "blend_mode": (
                    ["normal", "multiply", "overlay", "screen"],
                    {"default": "normal"},
                ),
                "feather_px": (
                    "FLOAT",
                    {
                        "default": 4.0,
                        "min": 0.0,
                        "max": 100.0,
                        "step": 0.5,
                        "tooltip": "マスク境界のぼかし量（自然な馴染ませ）",
                    },
                ),
                "brightness": (
                    "FLOAT",
                    {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05, "tooltip": "brightness_contrast 用"},
                ),
                "contrast": (
                    "FLOAT",
                    {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.05, "tooltip": "brightness_contrast 用"},
                ),
                "hue_degrees": (
                    "FLOAT",
                    {"default": 30.0, "min": -180.0, "max": 180.0, "step": 1.0, "tooltip": "hue_shift 用"},
                ),
            },
            "optional": {
                "pattern_image": ("IMAGE", {"tooltip": "pattern_tile で敷き詰める柄画像"}),
                "texture_image": ("IMAGE", {"tooltip": "texture_blend で合成するテクスチャ画像"}),
            },
        }

    def paint(
        self,
        image: Any,
        mask: Any,
        decoration_type: str,
        color: str,
        color_b: str,
        angle: float,
        opacity: float,
        blend_mode: str,
        feather_px: float,
        brightness: float,
        contrast: float,
        hue_degrees: float,
        pattern_image: Any = None,
        texture_image: Any = None,
    ) -> tuple[Any]:
        img_np = tensor_to_numpy_uint8(image)
        mask_np = mask_to_numpy(mask)
        shape = img_np.shape[:2]

        if decoration_type == "solid_color":
            effect = paint_ops.solid_color_fill(shape, color)
        elif decoration_type == "gradient_fill":
            effect = paint_ops.gradient_fill(shape, color, color_b, angle)
        elif decoration_type == "pattern_tile":
            if pattern_image is None:
                raise ValueError("pattern_tile には pattern_image の接続が必要です")
            pattern_np = tensor_to_numpy_uint8(pattern_image)
            effect = paint_ops.pattern_tile(shape, pattern_np)
        elif decoration_type == "texture_blend":
            if texture_image is None:
                raise ValueError("texture_blend には texture_image の接続が必要です")
            texture_np = tensor_to_numpy_uint8(texture_image)
            effect = paint_ops.texture_blend(img_np, texture_np, opacity=1.0, mode="normal")
        elif decoration_type == "brightness_contrast":
            effect = paint_ops.brightness_contrast(img_np, brightness, contrast)
        elif decoration_type == "hue_shift":
            effect = paint_ops.hue_shift(img_np, hue_degrees)
        else:
            raise ValueError(f"unknown decoration_type: {decoration_type}")

        result = paint_ops.apply_within_mask(
            img_np,
            mask_np,
            effect,
            feather_px=feather_px,
            opacity=opacity,
            blend_mode=blend_mode,
        )
        return (numpy_to_tensor(result),)
