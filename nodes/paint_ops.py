"""
nodes/paint_ops.py — 直接画像処理による装飾コアロジック（拡散モデル不要）

torch / ComfyUI に依存しない純粋関数群。マスク領域に対して色変更・
グラデーション・柄タイリング・テクスチャ合成などを直接適用する。
すべて numpy.uint8 (H,W,3) の画像 / numpy.float32 (H,W) 0-1 のマスクを扱う。
"""

from __future__ import annotations

from typing import Literal

import numpy as np

from .mask_utils import feather_mask

BlendMode = Literal["normal", "multiply", "overlay", "screen"]


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"invalid hex color: {hex_color!r}")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _blend(base: np.ndarray, effect: np.ndarray, mode: BlendMode, opacity: float) -> np.ndarray:
    base_f = base.astype("float32") / 255.0
    eff_f = effect.astype("float32") / 255.0

    if mode == "normal":
        blended = eff_f
    elif mode == "multiply":
        blended = base_f * eff_f
    elif mode == "screen":
        blended = 1.0 - (1.0 - base_f) * (1.0 - eff_f)
    elif mode == "overlay":
        low = 2 * base_f * eff_f
        high = 1.0 - 2 * (1.0 - base_f) * (1.0 - eff_f)
        blended = np.where(base_f <= 0.5, low, high)
    else:
        raise ValueError(f"unknown blend mode: {mode}")

    opacity = float(np.clip(opacity, 0.0, 1.0))
    out = base_f * (1.0 - opacity) + blended * opacity
    return np.clip(out * 255.0, 0, 255).astype("uint8")


def solid_color_fill(shape: tuple[int, int], color: str) -> np.ndarray:
    """shape=(H,W) の単色 (H,W,3) uint8 画像を作る。color は '#rrggbb' か 'r,g,b'。"""
    rgb = _parse_color(color)
    h, w = shape
    return np.tile(np.array(rgb, dtype="uint8"), (h, w, 1))


def gradient_fill(
    shape: tuple[int, int], color_a: str, color_b: str, angle_deg: float = 0.0
) -> np.ndarray:
    """2色間の線形グラデーション画像 (H,W,3) uint8 を生成する。angle_deg=0 で左→右。"""
    h, w = shape
    rgb_a = np.array(_parse_color(color_a), dtype="float32")
    rgb_b = np.array(_parse_color(color_b), dtype="float32")

    theta = np.deg2rad(angle_deg)
    xs, ys = np.meshgrid(np.linspace(0, 1, w), np.linspace(0, 1, h))
    proj = xs * np.cos(theta) + ys * np.sin(theta)
    proj = (proj - proj.min()) / max(1e-6, (proj.max() - proj.min()))

    out = rgb_a[None, None, :] * (1 - proj[..., None]) + rgb_b[None, None, :] * proj[..., None]
    return np.clip(out, 0, 255).astype("uint8")


def pattern_tile(shape: tuple[int, int], pattern: np.ndarray) -> np.ndarray:
    """pattern 画像 (h,w,3) を shape=(H,W) 全面に敷き詰めてタイル化する。"""
    h, w = shape
    ph, pw = pattern.shape[:2]
    if ph == 0 or pw == 0:
        raise ValueError("pattern image is empty")
    reps_y = -(-h // ph)  # ceil division
    reps_x = -(-w // pw)
    tiled = np.tile(pattern, (reps_y, reps_x, 1))
    return tiled[:h, :w, :].astype("uint8")


def texture_blend(
    base: np.ndarray, texture: np.ndarray, opacity: float = 0.6, mode: BlendMode = "overlay"
) -> np.ndarray:
    """base (H,W,3) にリサイズ済み texture (H,W,3) を合成する。"""
    if base.shape[:2] != texture.shape[:2]:
        from PIL import Image

        tex_img = Image.fromarray(texture).resize(
            (base.shape[1], base.shape[0]), resample=Image.LANCZOS
        )
        texture = np.asarray(tex_img)
    return _blend(base, texture, mode, opacity)


def brightness_contrast(
    image: np.ndarray, brightness: float = 0.0, contrast: float = 0.0
) -> np.ndarray:
    """brightness/contrast は -1.0〜1.0。0.0=無変化。"""
    img = image.astype("float32")
    img = img + brightness * 255.0
    factor = 1.0 + float(np.clip(contrast, -1.0, 1.0))
    img = (img - 127.5) * factor + 127.5
    return np.clip(img, 0, 255).astype("uint8")


def hue_shift(image: np.ndarray, degrees: float) -> np.ndarray:
    """HSV色空間で色相を degrees(°) だけ回転させる。"""
    from PIL import Image

    pil_img = Image.fromarray(image).convert("HSV")
    arr = np.array(pil_img).astype("int32")
    shift = int(round((degrees / 360.0) * 255.0))
    arr[..., 0] = (arr[..., 0] + shift) % 256
    out = Image.fromarray(arr.astype("uint8"), mode="HSV").convert("RGB")
    return np.array(out)


def _parse_color(color: str) -> tuple[int, int, int]:
    color = color.strip()
    if color.startswith("#") or (len(color) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in color)):
        return _hex_to_rgb(color)
    if "," in color:
        parts = [int(p.strip()) for p in color.split(",")]
        if len(parts) == 3:
            return parts[0], parts[1], parts[2]
    raise ValueError(f"unrecognized color format: {color!r} (use '#rrggbb' or 'r,g,b')")


def apply_within_mask(
    image: np.ndarray,
    mask: np.ndarray,
    effect: np.ndarray,
    feather_px: float = 4.0,
    opacity: float = 1.0,
    blend_mode: BlendMode = "normal",
) -> np.ndarray:
    """
    effect（image と同サイズの加工結果）を mask 領域だけに opacity/blend_mode で
    合成し、feather_px で境界をぼかして自然に馴染ませる。
    """
    if image.shape != effect.shape:
        raise ValueError(f"image/effect shape mismatch: {image.shape} vs {effect.shape}")
    m = feather_mask(mask, feather_px) if feather_px > 0 else mask.astype("float32")
    m = np.clip(m, 0.0, 1.0) * float(np.clip(opacity, 0.0, 1.0))

    blended_full = _blend(image, effect, blend_mode, 1.0)
    m3 = m[..., None]
    out = image.astype("float32") * (1 - m3) + blended_full.astype("float32") * m3
    return np.clip(out, 0, 255).astype("uint8")
