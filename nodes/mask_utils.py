"""
nodes/mask_utils.py — マスク処理コアロジック

torch / ComfyUI に依存しない純粋関数群。numpy + PIL のみに依存するため、
ノード本体（node_base の torch 変換）とは独立して pytest で単体テスト可能。

すべてのマスクは numpy.float32, shape (H, W), 値域 0.0-1.0（1.0=対象領域）で表現する。
すべての画像は numpy.uint8, shape (H, W, 3) で表現する。
"""

from __future__ import annotations

from typing import Literal

import numpy as np

CombineMode = Literal["union", "intersect", "subtract", "xor"]


# ── マスク整形 ────────────────────────────────────────────────────────

def feather_mask(mask: np.ndarray, feather_px: float) -> np.ndarray:
    """マスクの境界をガウスぼかしで滑らかにする（合成時の境目を目立たなくする）。"""
    if feather_px <= 0:
        return mask.astype("float32")
    from PIL import Image, ImageFilter

    img = Image.fromarray((np.clip(mask, 0, 1) * 255).astype("uint8"), mode="L")
    blurred = img.filter(ImageFilter.GaussianBlur(radius=float(feather_px)))
    return np.asarray(blurred, dtype="float32") / 255.0


def grow_mask(mask: np.ndarray, px: int) -> np.ndarray:
    """マスク領域を px ピクセル分だけ膨張させる（MaxFilter による近似dilate）。"""
    if px <= 0:
        return mask.astype("float32")
    from PIL import Image, ImageFilter

    size = _odd_kernel_size(px)
    img = Image.fromarray((np.clip(mask, 0, 1) * 255).astype("uint8"), mode="L")
    grown = img.filter(ImageFilter.MaxFilter(size=size))
    return np.asarray(grown, dtype="float32") / 255.0


def shrink_mask(mask: np.ndarray, px: int) -> np.ndarray:
    """マスク領域を px ピクセル分だけ収縮させる（MinFilter による近似erode）。"""
    if px <= 0:
        return mask.astype("float32")
    from PIL import Image, ImageFilter

    size = _odd_kernel_size(px)
    img = Image.fromarray((np.clip(mask, 0, 1) * 255).astype("uint8"), mode="L")
    shrunk = img.filter(ImageFilter.MinFilter(size=size))
    return np.asarray(shrunk, dtype="float32") / 255.0


def invert_mask(mask: np.ndarray) -> np.ndarray:
    return (1.0 - np.clip(mask, 0, 1)).astype("float32")


def _odd_kernel_size(px: int) -> int:
    """PIL の MaxFilter/MinFilter は奇数サイズのみ受け付けるため丸める。"""
    size = max(1, int(px) * 2 + 1)
    return size if size % 2 == 1 else size + 1


def combine_masks(a: np.ndarray, b: np.ndarray, mode: CombineMode = "union") -> np.ndarray:
    """2つのマスクを合成する。union=和集合 / intersect=積集合 / subtract=a-b / xor=排他的論理和"""
    a = np.clip(a, 0, 1)
    b = np.clip(b, 0, 1)
    if a.shape != b.shape:
        raise ValueError(f"mask shape mismatch: {a.shape} vs {b.shape}")
    if mode == "union":
        out = np.maximum(a, b)
    elif mode == "intersect":
        out = np.minimum(a, b)
    elif mode == "subtract":
        out = np.clip(a - b, 0, 1)
    elif mode == "xor":
        out = np.clip(np.abs(a - b), 0, 1)
    else:
        raise ValueError(f"unknown combine mode: {mode}")
    return out.astype("float32")


# ── バウンディングボックス抽出・クロップ・貼り戻し ────────────────────

def mask_bbox(mask: np.ndarray, threshold: float = 0.02) -> tuple[int, int, int, int] | None:
    """マスクの非ゼロ領域を囲む (x0, y0, x1, y1)（x1/y1は排他的）を返す。空マスクなら None。"""
    ys, xs = np.where(mask > threshold)
    if ys.size == 0 or xs.size == 0:
        return None
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    return x0, y0, x1, y1


def pad_bbox(
    bbox: tuple[int, int, int, int],
    pad: int,
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    """bbox を pad ピクセル分拡張し、画像範囲内に収める。"""
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(width, x1 + pad)
    y1 = min(height, y1 + pad)
    return x0, y0, x1, y1


def crop_to_bbox(image: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = bbox
    return image[y0:y1, x0:x1, ...].copy()


def paste_back(
    original: np.ndarray,
    patch: np.ndarray,
    bbox: tuple[int, int, int, int],
    patch_mask: np.ndarray | None = None,
    feather_px: float = 0.0,
) -> np.ndarray:
    """
    加工済みの patch（bbox サイズの画像）を original の bbox 位置に貼り戻す。

    patch_mask（bbox と同サイズ、0-1）が与えられた場合、そのマスクで
    アルファブレンドする。feather_px > 0 の場合は貼り戻し境界を
    ガウスぼかしして継ぎ目を目立たなくする。patch_mask が None の場合は
    bbox 全域を単純に上書きする。
    """
    x0, y0, x1, y1 = bbox
    out = original.copy()
    region_h, region_w = y1 - y0, x1 - x0
    if patch.shape[0] != region_h or patch.shape[1] != region_w:
        raise ValueError(
            f"patch size {patch.shape[:2]} does not match bbox size {(region_h, region_w)}"
        )

    if patch_mask is None:
        out[y0:y1, x0:x1, ...] = patch
        return out

    m = patch_mask.astype("float32")
    if feather_px > 0:
        m = feather_mask(m, feather_px)
    m3 = m[..., None] if out.ndim == 3 else m

    region = out[y0:y1, x0:x1, ...].astype("float32")
    blended = region * (1.0 - m3) + patch.astype("float32") * m3
    out[y0:y1, x0:x1, ...] = np.clip(blended, 0, 255).astype(original.dtype)
    return out
