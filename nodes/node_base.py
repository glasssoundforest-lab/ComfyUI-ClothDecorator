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
    """IMAGE テンソル（B,H,W,C float0-1）→ numpy uint8 (H,W,3)。バッチの先頭のみ。"""
    import numpy as np

    if image is None:
        raise ValueError("image が None です。IMAGE 型の入力が接続されているか確認してください。")

    arr = image
    if hasattr(arr, "detach"):
        arr = arr.detach().cpu().numpy()
    try:
        arr = np.asarray(arr)
    except (TypeError, ValueError) as e:
        raise ValueError(
            f"image を数値配列に変換できません（{type(image).__name__} が渡されています）。"
            f"IMAGE 型のテンソルが正しく接続されているか確認してください: {e}"
        ) from e
    if arr.dtype == object or arr.ndim not in (2, 3, 4):
        raise ValueError(
            f"image の形式が不正です（shape={arr.shape}, dtype={arr.dtype}）。"
            "画像ではないデータが接続されている可能性があります。"
        )
    if arr.ndim == 4:
        arr = arr[0]
    if arr.ndim == 2:
        # (H,W) のグレースケール（チャンネル軸が無い）も許容する
        arr = arr[..., None]
    arr = _normalize_channels(arr)
    # 上流ノードから NaN/Inf が混入した場合でも uint8 キャスト時に未定義値に
    # ならないよう、ここで安全な値に丸めておく（0=NaN, 1.0=+Inf, 0.0=-Inf）。
    arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(arr * 255.0, 0, 255).astype(np.uint8)


def _normalize_channels(arr: Any) -> Any:
    """
    (H,W,C) の C を常に3（RGB）へ正規化する。
    - C==1（グレースケール）: 3チャンネルへ複製
    - C==3（RGB）: そのまま
    - C==4（RGBA等）: 先頭3チャンネルのみ使用（アルファは破棄）
    - それ以外: どう解釈すべきか不明なため、明確なエラーとして知らせる
      （黙って壊れたデータのまま処理を続けるより安全）
    """
    import numpy as np

    c = arr.shape[-1] if arr.ndim == 3 else 1
    if c == 3:
        return arr
    if c == 1:
        return np.repeat(arr, 3, axis=-1)
    if c == 4:
        return arr[..., :3]
    raise ValueError(
        f"IMAGE テンソルのチャンネル数が不正です（想定: 1/3/4, 実際: {c}）。"
        "画像ではないデータが接続されている可能性があります。"
    )


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

    if mask is None:
        raise ValueError("mask が None です。MASK 型の入力が接続されているか確認してください。")

    arr = mask
    if hasattr(arr, "detach"):
        arr = arr.detach().cpu().numpy()
    try:
        arr = np.asarray(arr, dtype="float32")
    except (TypeError, ValueError) as e:
        raise ValueError(
            f"mask を数値配列に変換できません（{type(mask).__name__} が渡されています）。"
            f"MASK 型のテンソルが正しく接続されているか確認してください: {e}"
        ) from e
    if arr.ndim not in (2, 3):
        raise ValueError(f"mask の形式が不正です（shape={arr.shape}）。MASK型ではないデータの可能性があります。")
    if arr.ndim == 3:
        arr = arr[0]
    # NaN/Inf が混入していても後続処理が未定義動作にならないよう安全な値に丸める。
    arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(arr, 0.0, 1.0)


def numpy_to_mask_tensor(arr: Any) -> Any:
    """numpy float32 (H,W) 0-1 → MASK テンソル (B=1,H,W)"""
    import numpy as np
    import torch

    a = np.asarray(arr, dtype="float32")
    a = np.clip(a, 0.0, 1.0)
    return torch.from_numpy(a)[None, ...]
