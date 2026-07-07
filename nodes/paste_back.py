"""
nodes/paste_back.py
ノード: 🔀 Cloth Decorator - Paste Back

🖼️ Region Extract で切り出し、Direct Paint や外部のインペイント系ノードで
加工した patch_image を、bbox_json の位置に元画像へフェザー付きで
貼り戻す。patch_mask を指定すると、bbox全域ではなくマスク形状に沿って
自然に合成する（未指定時は bbox 全域を上書き）。
"""

from __future__ import annotations

import json
from typing import Any

from . import mask_utils
from .node_base import (
    ClothDecoratorNodeBase,
    mask_to_numpy,
    numpy_to_tensor,
    tensor_to_numpy_uint8,
)


class ClothPasteBackNode(ClothDecoratorNodeBase):
    """加工済みパッチ画像を元画像の指定位置へフェザー合成で貼り戻す。"""

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "paste"
    CATEGORY = "ClothDecorator"

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "original_image": ("IMAGE",),
                "patch_image": ("IMAGE", {"tooltip": "🖼️ Region Extract で切り出し加工した画像"}),
                "bbox_json": ("STRING", {"forceInput": True}),
                "feather_px": (
                    "FLOAT",
                    {"default": 6.0, "min": 0.0, "max": 100.0, "step": 0.5},
                ),
            },
            "optional": {
                "patch_mask": (
                    "MASK",
                    {"tooltip": "指定するとこの形状に沿って合成する（未指定=bbox全域を上書き）"},
                ),
            },
        }

    def paste(
        self,
        original_image: Any,
        patch_image: Any,
        bbox_json: str,
        feather_px: float,
        patch_mask: Any = None,
    ) -> tuple[Any]:
        orig_np = tensor_to_numpy_uint8(original_image)
        patch_np = tensor_to_numpy_uint8(patch_image)

        info = json.loads(bbox_json)
        bbox = (int(info["x0"]), int(info["y0"]), int(info["x1"]), int(info["y1"]))

        expected_h, expected_w = bbox[3] - bbox[1], bbox[2] - bbox[0]
        if patch_np.shape[0] != expected_h or patch_np.shape[1] != expected_w:
            from PIL import Image

            patch_np = _resize_np(patch_np, (expected_w, expected_h))

        pmask_np = None
        if patch_mask is not None:
            pmask_np = mask_to_numpy(patch_mask)
            if pmask_np.shape[0] != expected_h or pmask_np.shape[1] != expected_w:
                pmask_np = _resize_mask_np(pmask_np, (expected_w, expected_h))

        result = mask_utils.paste_back(
            orig_np, patch_np, bbox, patch_mask=pmask_np, feather_px=feather_px
        )
        return (numpy_to_tensor(result),)


def _resize_np(arr, size_wh):
    from PIL import Image

    img = Image.fromarray(arr).resize(size_wh, resample=Image.LANCZOS)
    import numpy as np

    return np.asarray(img)


def _resize_mask_np(arr, size_wh):
    from PIL import Image
    import numpy as np

    img = Image.fromarray((arr * 255).astype("uint8"), mode="L").resize(
        size_wh, resample=Image.NEAREST
    )
    return np.asarray(img, dtype="float32") / 255.0
