"""
nodes/region_extract.py
ノード: 🖼️ Cloth Decorator - Region Extract

マスク領域のバウンディングボックス（+パディング）で画像とマスクを
切り出す。切り出した領域だけを Direct Paint / インペイントに通すことで、
処理対象を服の領域に絞り込み、無駄な計算とサイズ起因の破綻を減らす。
bbox_json は 🔀 Paste Back ノードに渡して元画像へ貼り戻す際に使う。
"""

from __future__ import annotations

import json
from typing import Any

from . import mask_utils
from .node_base import (
    ClothDecoratorNodeBase,
    mask_to_numpy,
    numpy_to_mask_tensor,
    numpy_to_tensor,
    tensor_to_numpy_uint8,
)


class ClothRegionExtractNode(ClothDecoratorNodeBase):
    """マスク領域のバウンディングボックスで image/mask を切り出す。"""

    RETURN_TYPES = ("IMAGE", "MASK", "IMAGE", "STRING")
    RETURN_NAMES = ("cropped_image", "cropped_mask", "original_image", "bbox_json")
    FUNCTION = "extract"
    CATEGORY = "ClothDecorator"

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "image": ("IMAGE",),
                "mask": ("MASK",),
                "padding": (
                    "INT",
                    {
                        "default": 24,
                        "min": 0,
                        "max": 512,
                        "tooltip": "マスクのbboxから何ピクセル余分に切り出すか",
                    },
                ),
                "min_size": (
                    "INT",
                    {
                        "default": 64,
                        "min": 8,
                        "max": 2048,
                        "tooltip": "切り出し領域の最小辺長。bboxがこれより小さければ中心基準で拡張する",
                    },
                ),
            },
        }

    def extract(
        self, image: Any, mask: Any, padding: int, min_size: int
    ) -> tuple[Any, Any, Any, str]:
        img_np = tensor_to_numpy_uint8(image)
        mask_np = mask_to_numpy(mask)
        h, w = img_np.shape[:2]

        bbox = mask_utils.mask_bbox(mask_np)
        if bbox is None:
            # マスクが空の場合は画像全体を返す（下流でのエラーを避けるフォールバック）
            bbox = (0, 0, w, h)
        else:
            bbox = mask_utils.pad_bbox(bbox, padding, w, h)
            bbox = _enforce_min_size(bbox, min_size, w, h)

        cropped_img = mask_utils.crop_to_bbox(img_np, bbox)
        cropped_mask = mask_utils.crop_to_bbox(mask_np, bbox)

        bbox_json = json.dumps(
            {"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3], "orig_w": w, "orig_h": h}
        )

        return (
            numpy_to_tensor(cropped_img),
            numpy_to_mask_tensor(cropped_mask),
            image,
            bbox_json,
        )


def _enforce_min_size(
    bbox: tuple[int, int, int, int], min_size: int, width: int, height: int
) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = bbox
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bw, bh = max(x1 - x0, min_size), max(y1 - y0, min_size)
    nx0 = int(max(0, cx - bw / 2))
    ny0 = int(max(0, cy - bh / 2))
    nx1 = int(min(width, nx0 + bw))
    ny1 = int(min(height, ny0 + bh))
    # 右/下端でクリップされた分を左/上に押し戻す
    nx0 = int(max(0, nx1 - bw))
    ny0 = int(max(0, ny1 - bh))
    return nx0, ny0, nx1, ny1
