"""
nodes/mask_prep.py
ノード: ✂️ Cloth Decorator - Mask Prep

SAM やクリック選択ノードなどから受け取った標準 MASK 型を、
装飾処理（Direct Paint / Prompt Composer）に渡す前に整形する。

処理順序: shrink → grow → (他マスクとcombine) → invert → feather
"""

from __future__ import annotations

from typing import Any

from . import mask_utils
from .node_base import ClothDecoratorNodeBase, mask_to_numpy, numpy_to_mask_tensor, numpy_to_tensor


class ClothMaskPrepNode(ClothDecoratorNodeBase):
    """MASK の膨張/収縮/ぼかし/反転/合成を行い、下流ノードに渡すための整形マスクを作る。"""

    RETURN_TYPES = ("MASK", "IMAGE")
    RETURN_NAMES = ("mask", "mask_preview")
    FUNCTION = "prep"
    CATEGORY = "ClothDecorator"

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "mask": ("MASK", {"tooltip": "SAM等から接続する対象領域マスク"}),
                "shrink_px": (
                    "INT",
                    {"default": 0, "min": 0, "max": 200, "tooltip": "先に収縮させるピクセル数"},
                ),
                "grow_px": (
                    "INT",
                    {"default": 0, "min": 0, "max": 200, "tooltip": "収縮後に膨張させるピクセル数"},
                ),
                "feather_px": (
                    "FLOAT",
                    {
                        "default": 4.0,
                        "min": 0.0,
                        "max": 100.0,
                        "step": 0.5,
                        "tooltip": "境界をぼかす量（合成時の継ぎ目を目立たなくする）",
                    },
                ),
                "invert": ("BOOLEAN", {"default": False}),
                "combine_mode": (
                    ["none", "union", "intersect", "subtract", "xor"],
                    {"default": "none", "tooltip": "combine_mask を指定した場合の合成方法"},
                ),
            },
            "optional": {
                "combine_mask": ("MASK", {"tooltip": "combine_mode が none 以外のとき使用する第2マスク"}),
            },
        }

    def prep(
        self,
        mask: Any,
        shrink_px: int,
        grow_px: int,
        feather_px: float,
        invert: bool,
        combine_mode: str,
        combine_mask: Any = None,
    ) -> tuple[Any, Any]:
        m = mask_to_numpy(mask)

        if shrink_px > 0:
            m = mask_utils.shrink_mask(m, shrink_px)
        if grow_px > 0:
            m = mask_utils.grow_mask(m, grow_px)

        if combine_mode != "none" and combine_mask is not None:
            cm = mask_to_numpy(combine_mask)
            if cm.shape != m.shape:
                # サイズが違う場合は最近傍でリサイズして合わせる
                from PIL import Image
                import numpy as np

                cm_img = Image.fromarray((cm * 255).astype("uint8"), mode="L")
                cm_img = cm_img.resize((m.shape[1], m.shape[0]), resample=Image.NEAREST)
                cm = np.asarray(cm_img, dtype="float32") / 255.0
            m = mask_utils.combine_masks(m, cm, mode=combine_mode)  # type: ignore[arg-type]

        if invert:
            m = mask_utils.invert_mask(m)

        if feather_px > 0:
            m = mask_utils.feather_mask(m, feather_px)

        preview = (m[..., None].repeat(3, axis=-1) * 255).astype("uint8")
        return numpy_to_mask_tensor(m), numpy_to_tensor(preview)
