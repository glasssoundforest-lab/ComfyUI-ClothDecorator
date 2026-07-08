"""
tests/test_robustness.py — 異常入力（負値・空データ・巨大値・NaN/Inf）に対する堅牢性の回帰テスト

過去に発見・修正したクラッシュ/ハング/未定義動作を再発防止するためのテスト群:
  - mask_utils.grow_mask/shrink_mask: 巨大なpxでOOM/ハングしていた
    （PILのMaxFilter/MinFilterは大きいカーネルで極端に遅い）
  - mask_utils.feather_mask: NaNでセグメンテーションフォルトしていた
  - mask_utils.pad_bbox: 極端な負のpadでbboxが反転（x0>x1）していた
  - paint_ops: 範囲外RGB文字列でOverflowError、hue_shiftの巨大角度で
    OverflowErrorしていた
  - color_analysis.kmeans_colors: kが画素数に近づくと数十GB規模のメモリ確保
    でクラッシュしていた
  - tag_mapping.map_tags_to_vocab: 巨大なタグ列で処理時間が爆発していた
  - node_base: NaN/Infを含むテンソルがuint8への未定義キャストを起こしていた
  - paste_back: 範囲外・反転したbboxで例外や不正な貼り戻しが起きていた
"""

import time

import numpy as np
import pytest

from nodes import color_analysis, mask_utils, model_profiles, paint_ops, tag_mapping, vocabulary

TIME_LIMIT = 5.0  # このスイートで許容する1操作あたりの最大実行時間（秒）


# ── mask_utils ───────────────────────────────────────────────────────

def test_grow_mask_huge_px_completes_quickly_and_correctly():
    mask = np.zeros((256, 256), dtype="float32")
    mask[100:150, 100:150] = 1.0
    t0 = time.time()
    result = mask_utils.grow_mask(mask, 100000)
    assert time.time() - t0 < TIME_LIMIT
    assert result.shape == mask.shape
    assert result.sum() >= mask.sum()


def test_shrink_mask_huge_px_completes_quickly():
    mask = np.ones((256, 256), dtype="float32")
    t0 = time.time()
    result = mask_utils.shrink_mask(mask, 100000)
    assert time.time() - t0 < TIME_LIMIT
    assert result.shape == mask.shape


@pytest.mark.parametrize("px", [-100, 0, float("nan"), float("inf"), float("-inf")])
def test_grow_shrink_mask_invalid_px_are_no_ops(px):
    mask = np.zeros((32, 32), dtype="float32")
    mask[8:24, 8:24] = 1.0
    grown = mask_utils.grow_mask(mask, px)
    shrunk = mask_utils.shrink_mask(mask, px)
    assert np.array_equal(grown, mask)
    assert np.array_equal(shrunk, mask)


def test_feather_mask_nan_does_not_crash():
    """回帰テスト: feather_px=NaN が PIL 内でセグメンテーションフォルトしていた。"""
    mask = np.zeros((32, 32), dtype="float32")
    mask[8:24, 8:24] = 1.0
    result = mask_utils.feather_mask(mask, float("nan"))
    assert result.shape == mask.shape
    assert not np.isnan(result).any()


def test_feather_mask_huge_value_completes_quickly():
    mask = np.zeros((64, 64), dtype="float32")
    mask[16:48, 16:48] = 1.0
    t0 = time.time()
    result = mask_utils.feather_mask(mask, 1e9)
    assert time.time() - t0 < TIME_LIMIT
    assert result.shape == mask.shape


@pytest.mark.parametrize(
    "pad", [-10**9, 10**9, float("nan"), float("inf"), float("-inf"), -5, 5, 0]
)
def test_pad_bbox_never_inverts(pad):
    result = mask_utils.pad_bbox((10, 10, 50, 50), pad, 64, 64)
    x0, y0, x1, y1 = result
    assert x0 <= x1
    assert y0 <= y1
    assert 0 <= x0 <= 64
    assert 0 <= x1 <= 64
    assert 0 <= y0 <= 64
    assert 0 <= y1 <= 64


def test_mask_bbox_empty_and_full_masks():
    assert mask_utils.mask_bbox(np.zeros((16, 16), dtype="float32")) is None
    bbox = mask_utils.mask_bbox(np.ones((16, 16), dtype="float32"))
    assert bbox == (0, 0, 16, 16)


# ── paint_ops ─────────────────────────────────────────────────────────

def test_parse_color_clamps_out_of_range_rgb():
    rgb = paint_ops._parse_color("-10,-20,-30")
    assert all(0 <= c <= 255 for c in rgb)
    rgb2 = paint_ops._parse_color("99999,99999,99999")
    assert rgb2 == (255, 255, 255)


def test_hue_shift_huge_degrees_does_not_overflow():
    img = np.zeros((16, 16, 3), dtype="uint8")
    img[..., 0] = 255
    result = paint_ops.hue_shift(img, 1e15)
    assert result.shape == img.shape


def test_hue_shift_nan_degrees_is_safe_noop_like():
    img = np.zeros((16, 16, 3), dtype="uint8")
    result = paint_ops.hue_shift(img, float("nan"))
    assert result.shape == img.shape


def test_gradient_fill_nan_angle_does_not_crash():
    result = paint_ops.gradient_fill((16, 16), "#ff0000", "#00ff00", float("nan"))
    assert result.shape == (16, 16, 3)


def test_brightness_contrast_extreme_and_nan_values():
    img = np.full((16, 16, 3), 128, dtype="uint8")
    for brightness, contrast in [(1e10, 0), (0, 1e10), (float("nan"), 0), (0, float("nan"))]:
        result = paint_ops.brightness_contrast(img, brightness, contrast)
        assert result.shape == img.shape
        assert result.dtype == np.uint8


def test_apply_within_mask_nan_and_extreme_opacity():
    img = np.zeros((16, 16, 3), dtype="uint8")
    mask = np.ones((16, 16), dtype="float32")
    effect = np.full((16, 16, 3), 255, dtype="uint8")
    for opacity in [float("nan"), -100, 1e10]:
        result = paint_ops.apply_within_mask(img, mask, effect, feather_px=2.0, opacity=opacity)
        assert result.shape == img.shape
        assert not np.isnan(result.astype("float64")).any()


# ── color_analysis ────────────────────────────────────────────────────

def test_kmeans_colors_huge_k_does_not_blow_memory():
    pixels = np.random.randint(0, 255, (10000, 3), dtype="uint8")
    t0 = time.time()
    result = color_analysis.kmeans_colors(pixels, k=1_000_000)
    assert time.time() - t0 < TIME_LIMIT
    assert len(result) <= color_analysis._MAX_K


def test_kmeans_colors_huge_iters_does_not_hang():
    pixels = np.random.randint(0, 255, (1000, 3), dtype="uint8")
    t0 = time.time()
    color_analysis.kmeans_colors(pixels, k=3, iters=10**9)
    assert time.time() - t0 < TIME_LIMIT


def test_analyze_masked_region_huge_num_colors():
    img = np.random.randint(0, 255, (64, 64, 3), dtype="uint8")
    mask = np.ones((64, 64), dtype="float32")
    t0 = time.time()
    result = color_analysis.analyze_masked_region(img, mask, num_colors=1_000_000)
    assert time.time() - t0 < TIME_LIMIT
    assert result["best_match"] is not None


# ── tag_mapping ───────────────────────────────────────────────────────

def test_map_tags_to_vocab_huge_list_completes_quickly():
    t0 = time.time()
    result = tag_mapping.map_tags_to_vocab(["embroidery"] * 200000)
    assert time.time() - t0 < TIME_LIMIT
    assert result["decoration_preset"] == "embroidery"


def test_map_tags_to_vocab_handles_non_string_entries():
    result = tag_mapping.map_tags_to_vocab(["", None, "embroidery", 123, 45.6])
    assert result["decoration_preset"] == "embroidery"


# ── vocabulary / model_profiles ────────────────────────────────────────

def test_build_decoration_prompt_empty_everything():
    result = vocabulary.build_decoration_prompt()
    assert result.decoration_prompt == ""
    assert result.negative_prompt


def test_build_decoration_prompt_huge_free_text_completes_quickly():
    t0 = time.time()
    vocabulary.build_decoration_prompt(free_text="x" * 1_000_000)
    assert time.time() - t0 < TIME_LIMIT


def test_adapt_prompt_huge_terms_list_completes_quickly():
    t0 = time.time()
    model_profiles.adapt_prompt(["tag"] * 100000, "dress", [], "sd15_anime")
    assert time.time() - t0 < TIME_LIMIT


def test_adapt_prompt_unknown_model_falls_back_safely():
    positive, negative, style = model_profiles.adapt_prompt(["red"], "dress", [], "no_such_model")
    assert style == "tags"


# ── node_base（テンソル変換境界でのNaN/Infサニタイズ） ───────────────────

torch = pytest.importorskip("torch")

from nodes.node_base import mask_to_numpy, tensor_to_numpy_uint8  # noqa: E402


def test_tensor_to_numpy_uint8_sanitizes_nan_and_inf():
    img = torch.rand(1, 8, 8, 3)
    img[0, 0, 0, 0] = float("nan")
    img[0, 1, 1, 1] = float("inf")
    img[0, 2, 2, 2] = float("-inf")
    arr = tensor_to_numpy_uint8(img)
    assert arr.dtype == np.uint8
    assert not np.isnan(arr.astype("float64")).any()


def test_mask_to_numpy_sanitizes_nan_and_inf():
    mask = torch.zeros(1, 8, 8)
    mask[0, 0, 0] = float("nan")
    mask[0, 1, 1] = float("inf")
    mask[0, 2, 2] = float("-inf")
    arr = mask_to_numpy(mask)
    assert not np.isnan(arr).any()
    assert (arr >= 0).all() and (arr <= 1).all()


# ── Paste Back ノード（bbox_json の頑健性） ─────────────────────────────

from nodes import NODE_CLASS_MAPPINGS  # noqa: E402
import json as _json  # noqa: E402


def test_paste_back_malformed_json_raises_clear_error():
    node = NODE_CLASS_MAPPINGS["ClothPasteBack"]()
    orig = torch.rand(1, 32, 32, 3)
    patch = torch.rand(1, 16, 16, 3)
    with pytest.raises(ValueError):
        node.paste(orig, patch, "not valid json", feather_px=2.0)


def test_paste_back_out_of_range_bbox_is_clamped_not_crashed():
    node = NODE_CLASS_MAPPINGS["ClothPasteBack"]()
    orig = torch.rand(1, 32, 32, 3)
    patch = torch.rand(1, 16, 16, 3)
    bbox_json = _json.dumps({"x0": -1000, "y0": -1000, "x1": 2000, "y1": 2000, "orig_w": 32, "orig_h": 32})
    (result,) = node.paste(orig, patch, bbox_json, feather_px=2.0)
    assert result.shape == orig.shape


def test_paste_back_inverted_bbox_is_handled_gracefully():
    node = NODE_CLASS_MAPPINGS["ClothPasteBack"]()
    orig = torch.rand(1, 32, 32, 3)
    patch = torch.rand(1, 16, 16, 3)
    bbox_json = _json.dumps({"x0": 20, "y0": 20, "x1": 5, "y1": 5, "orig_w": 32, "orig_h": 32})
    (result,) = node.paste(orig, patch, bbox_json, feather_px=2.0)
    assert result.shape == orig.shape
