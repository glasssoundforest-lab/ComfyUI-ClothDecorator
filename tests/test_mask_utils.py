import numpy as np
import pytest

from nodes import mask_utils


def _square_mask(size=64, box=(16, 16, 48, 48)):
    m = np.zeros((size, size), dtype="float32")
    x0, y0, x1, y1 = box
    m[y0:y1, x0:x1] = 1.0
    return m


def test_mask_bbox_basic():
    m = _square_mask()
    bbox = mask_utils.mask_bbox(m)
    assert bbox == (16, 16, 48, 48)


def test_mask_bbox_empty_returns_none():
    m = np.zeros((32, 32), dtype="float32")
    assert mask_utils.mask_bbox(m) is None


def test_pad_bbox_clips_to_bounds():
    bbox = (5, 5, 10, 10)
    padded = mask_utils.pad_bbox(bbox, pad=10, width=12, height=12)
    assert padded == (0, 0, 12, 12)


def test_grow_mask_increases_area():
    m = _square_mask()
    grown = mask_utils.grow_mask(m, 4)
    assert grown.sum() > m.sum()


def test_shrink_mask_decreases_area():
    m = _square_mask()
    shrunk = mask_utils.shrink_mask(m, 4)
    assert shrunk.sum() < m.sum()


def test_invert_mask():
    m = _square_mask()
    inv = mask_utils.invert_mask(m)
    assert np.allclose(inv, 1.0 - m)


def test_feather_mask_smooths_edges_without_changing_shape():
    m = _square_mask()
    feathered = mask_utils.feather_mask(m, 3.0)
    assert feathered.shape == m.shape
    # 境界付近は中間値になっているはず（0か1だけではない）
    assert ((feathered > 0.01) & (feathered < 0.99)).any()


@pytest.mark.parametrize(
    "mode,expected_fn",
    [
        ("union", lambda a, b: np.maximum(a, b)),
        ("intersect", lambda a, b: np.minimum(a, b)),
        ("subtract", lambda a, b: np.clip(a - b, 0, 1)),
        ("xor", lambda a, b: np.abs(a - b)),
    ],
)
def test_combine_masks(mode, expected_fn):
    a = _square_mask(box=(0, 0, 32, 32))
    b = _square_mask(box=(16, 16, 48, 48))
    result = mask_utils.combine_masks(a, b, mode=mode)
    assert np.allclose(result, expected_fn(a, b))


def test_combine_masks_shape_mismatch_raises():
    a = np.zeros((32, 32), dtype="float32")
    b = np.zeros((16, 16), dtype="float32")
    with pytest.raises(ValueError):
        mask_utils.combine_masks(a, b)


def test_crop_to_bbox_and_paste_back_roundtrip():
    img = np.zeros((64, 64, 3), dtype="uint8")
    img[..., 0] = 100  # 元画像は赤成分100の一様色
    bbox = (16, 16, 48, 48)

    cropped = mask_utils.crop_to_bbox(img, bbox)
    assert cropped.shape == (32, 32, 3)

    patch = np.zeros_like(cropped)
    patch[..., 1] = 200  # 緑成分200のパッチに置き換える

    pasted = mask_utils.paste_back(img, patch, bbox)
    # bbox内は緑200になっている
    assert (pasted[20, 20] == [0, 200, 0]).all()
    # bbox外は元のまま
    assert (pasted[0, 0] == [100, 0, 0]).all()


def test_paste_back_with_mask_blends_only_masked_region():
    img = np.zeros((32, 32, 3), dtype="uint8")
    bbox = (0, 0, 32, 32)
    patch = np.full((32, 32, 3), 255, dtype="uint8")
    patch_mask = np.zeros((32, 32), dtype="float32")
    patch_mask[10:20, 10:20] = 1.0

    result = mask_utils.paste_back(img, patch, bbox, patch_mask=patch_mask, feather_px=0.0)
    assert (result[15, 15] == [255, 255, 255]).all()
    assert (result[0, 0] == [0, 0, 0]).all()


def test_paste_back_size_mismatch_raises():
    img = np.zeros((32, 32, 3), dtype="uint8")
    patch = np.zeros((10, 10, 3), dtype="uint8")
    with pytest.raises(ValueError):
        mask_utils.paste_back(img, patch, (0, 0, 20, 20))
