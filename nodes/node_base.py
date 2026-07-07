"""
nodes/node_base.py — ClothDecorator ノード共通基底

ComfyUI の IMAGE / MASK テンソル形式:
  IMAGE: torch.Tensor, shape (B, H, W, C=3), float32, 値域 0.0-1.0
  MASK : torch.Tensor, shape (B, H, W),      float32, 値域 0.0-1.0（1.0=対象領域）

このモジュールはノード本体からテンソル変換ロジックを分離し、
torch 非依存のコアロジック（mask_utils / vocabulary）と、
torch/PIL 依存の I/O 変換を明確に分ける。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("ClothDecorator")

CATEGORY_ROOT = "ClothDecorator"


class ClothDecoratorNodeBase:
    """全 ClothDecorator ノードの共通基底クラス"""

    CATEGORY = CATEGORY_ROOT

    @classmethod
    def IS_CHANGED(cls, **kwargs: Any) -> float:
        # デフォルトではキャッシュを許可する（決定的なノードのため）。
        # キャッシュを無効化したいノードは個別にオーバーライドする。
        return 0.0


# ── IMAGE テンソル ⇔ numpy/PIL 変換 ─────────────────────────────────

def tensor_to_numpy_uint8(image: Any) -> "Any":
    """IMAGE テンソル（B,H,W,C float0-1）→ numpy uint8 (H,W,C)。バッチの先頭のみ。"""
    import numpy as np

    arr = image
    if hasattr(arr, "detach"):
        arr = arr.detach().cpu().numpy()
    arr = np.asarray(arr)
    if arr.ndim == 4:
        arr = arr[0]
    return np.clip(arr * 255.0, 0, 255).astype(np.uint8)


def tensor_to_pil(image: Any) -> "Any":
    from PIL import Image

    return Image.fromarray(tensor_to_numpy_uint8(image))


def pil_to_tensor(pil_image: Any) -> Any:
    """PIL.Image (RGB) → IMAGE テンソル（B=1,H,W,C float0-1）"""
    import numpy as np
    import torch

    arr = np.array(pil_image.convert("RGB")).astype("float32") / 255.0
    return torch.from_numpy(arr)[None, ...]


def numpy_to_tensor(arr: Any) -> Any:
    """numpy (H,W,C) uint8 or float0-1 → IMAGE テンソル (B=1,H,W,C)"""
    import numpy as np
    import torch

    a = np.asarray(arr)
    if a.dtype == np.uint8:
        a = a.astype("float32") / 255.0
    else:
        a = a.astype("float32")
    return torch.from_numpy(a)[None, ...]


# ── MASK テンソル ⇔ numpy 変換 ───────────────────────────────────────

def mask_to_numpy(mask: Any) -> "Any":
    """MASK テンソル（B,H,W float0-1 または H,W）→ numpy float32 (H,W) 0-1。バッチの先頭のみ。"""
    import numpy as np

    arr = mask
    if hasattr(arr, "detach"):
        arr = arr.detach().cpu().numpy()
    arr = np.asarray(arr, dtype="float32")
    if arr.ndim == 3:
        arr = arr[0]
    return np.clip(arr, 0.0, 1.0)


def numpy_to_mask_tensor(arr: Any) -> Any:
    """numpy float32 (H,W) 0-1 → MASK テンソル (B=1,H,W)"""
    import numpy as np
    import torch

    a = np.asarray(arr, dtype="float32")
    a = np.clip(a, 0.0, 1.0)
    return torch.from_numpy(a)[None, ...]
