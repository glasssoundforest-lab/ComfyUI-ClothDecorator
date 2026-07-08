import numpy as np

from nodes import color_analysis as ca


def test_extract_masked_pixels_basic():
    img = np.zeros((10, 10, 3), dtype="uint8")
    img[:, :5] = [255, 0, 0]
    img[:, 5:] = [0, 255, 0]
    mask = np.zeros((10, 10), dtype="float32")
    mask[:, :5] = 1.0

    pixels = ca.extract_masked_pixels(img, mask)
    assert pixels.shape[1] == 3
    assert (pixels == [255, 0, 0]).all()


def test_extract_masked_pixels_empty_mask_falls_back_to_full_image():
    img = np.ones((4, 4, 3), dtype="uint8") * 7
    mask = np.zeros((4, 4), dtype="float32")
    pixels = ca.extract_masked_pixels(img, mask)
    assert pixels.shape[0] == 16


def test_kmeans_colors_two_clear_clusters():
    red = np.tile(np.array([200, 10, 10], dtype="uint8"), (50, 1))
    blue = np.tile(np.array([10, 10, 200], dtype="uint8"), (50, 1))
    pixels = np.vstack([red, blue])

    clusters = ca.kmeans_colors(pixels, k=2, iters=10)
    assert len(clusters) == 2
    colors = [c[0] for c in clusters]
    # どちらのクラスタも概ね赤系/青系に収束しているはず
    assert any(c[0] > 150 and c[2] < 60 for c in colors)  # 赤寄り
    assert any(c[2] > 150 and c[0] < 60 for c in colors)  # 青寄り
    # 重みの合計はほぼ1
    assert abs(sum(c[1] for c in clusters) - 1.0) < 1e-6


def test_kmeans_colors_single_pixel_value():
    pixels = np.tile(np.array([100, 100, 100], dtype="uint8"), (20, 1))
    clusters = ca.kmeans_colors(pixels, k=3)
    assert len(clusters) >= 1
    assert clusters[0][1] == 1.0 or sum(c[1] for c in clusters) == 1.0


def test_kmeans_colors_empty_input():
    pixels = np.zeros((0, 3), dtype="uint8")
    assert ca.kmeans_colors(pixels, k=3) == []


def test_nearest_named_color_exact_match():
    # 藍色の hex は #1e50a2
    rgb = (0x1E, 0x50, 0xA2)
    result = ca.nearest_named_color(rgb)
    assert result["distance"] < 1.0
    assert result["name_ja"] == "藍色"
    assert result["name_en"] == "deep indigo blue"


def test_nearest_named_color_base_color_match():
    # 赤 (BASE_COLOR_HEX["red"] = #e63946) に近い色
    rgb = (0xE6, 0x39, 0x46)
    result = ca.nearest_named_color(rgb)
    assert result["name_en"] == "red"
    assert result["name_ja"] == "赤"


def test_rgb_to_hex():
    assert ca.rgb_to_hex((255, 0, 0)) == "#ff0000"
    assert ca.rgb_to_hex((0, 0, 0)) == "#000000"
    assert ca.rgb_to_hex((300, -10, 128)) == "#ff0080"  # クリップされる


def test_analyze_masked_region_structure():
    img = np.zeros((20, 20, 3), dtype="uint8")
    img[:, :] = [0x1E, 0x50, 0xA2]  # 藍色一色
    mask = np.ones((20, 20), dtype="float32")

    result = ca.analyze_masked_region(img, mask, num_colors=2)
    assert "dominant_colors" in result
    assert "best_match" in result
    assert "all_matches" in result
    assert result["best_match"]["name_ja"] == "藍色"
    assert result["best_match"]["is_close_match"] is True


def test_analyze_masked_region_far_color_not_close_match():
    # 語彙のどの色からも遠い、彩度の高い中間的な色を使う
    img = np.zeros((10, 10, 3), dtype="uint8")
    img[:, :] = [128, 255, 0]  # 強い黄緑
    mask = np.ones((10, 10), dtype="float32")

    result = ca.analyze_masked_region(img, mask, num_colors=1, match_distance_threshold=5.0)
    # 距離5以内に収まる語彙色はまず無いはず
    assert result["best_match"]["is_close_match"] is False
