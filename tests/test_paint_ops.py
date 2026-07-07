import numpy as np
import pytest

from nodes import paint_ops


def test_solid_color_fill_hex():
    img = paint_ops.solid_color_fill((10, 10), "#ff0000")
    assert img.shape == (10, 10, 3)
    assert (img == [255, 0, 0]).all()


def test_solid_color_fill_rgb_string():
    img = paint_ops.solid_color_fill((4, 4), "0,128,255")
    assert (img == [0, 128, 255]).all()


def test_solid_color_fill_invalid_raises():
    with pytest.raises(ValueError):
        paint_ops.solid_color_fill((4, 4), "not-a-color")


def test_gradient_fill_endpoints():
    img = paint_ops.gradient_fill((1, 100), "#000000", "#ffffff", angle_deg=0.0)
    # 左端は黒に近く、右端は白に近い
    assert img[0, 0].mean() < 40
    assert img[0, -1].mean() > 215


def test_pattern_tile_covers_full_shape():
    pattern = np.zeros((4, 4, 3), dtype="uint8")
    pattern[..., 0] = 200
    tiled = paint_ops.pattern_tile((10, 13), pattern)
    assert tiled.shape == (10, 13, 3)
    assert (tiled[..., 0] == 200).all()


def test_pattern_tile_empty_pattern_raises():
    with pytest.raises(ValueError):
        paint_ops.pattern_tile((10, 10), np.zeros((0, 0, 3), dtype="uint8"))


def test_brightness_contrast_no_change_when_zero():
    img = np.full((5, 5, 3), 128, dtype="uint8")
    out = paint_ops.brightness_contrast(img, brightness=0.0, contrast=0.0)
    assert (out == img).all()


def test_brightness_increase():
    img = np.full((5, 5, 3), 100, dtype="uint8")
    out = paint_ops.brightness_contrast(img, brightness=0.2, contrast=0.0)
    assert out.mean() > img.mean()


def test_hue_shift_changes_pixels():
    img = np.zeros((4, 4, 3), dtype="uint8")
    img[..., 0] = 255  # 純赤
    shifted = paint_ops.hue_shift(img, 120.0)
    assert not (shifted == img).all()


def test_apply_within_mask_only_affects_masked_area():
    img = np.zeros((20, 20, 3), dtype="uint8")
    effect = np.full((20, 20, 3), 255, dtype="uint8")
    mask = np.zeros((20, 20), dtype="float32")
    mask[5:10, 5:10] = 1.0

    result = paint_ops.apply_within_mask(img, mask, effect, feather_px=0.0, opacity=1.0)
    assert (result[7, 7] == [255, 255, 255]).all()
    assert (result[0, 0] == [0, 0, 0]).all()


def test_apply_within_mask_shape_mismatch_raises():
    img = np.zeros((10, 10, 3), dtype="uint8")
    effect = np.zeros((5, 5, 3), dtype="uint8")
    mask = np.zeros((10, 10), dtype="float32")
    with pytest.raises(ValueError):
        paint_ops.apply_within_mask(img, mask, effect)
