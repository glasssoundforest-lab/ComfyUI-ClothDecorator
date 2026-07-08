import pytest

torch = pytest.importorskip("torch")

from nodes import NODE_CLASS_MAPPINGS  # noqa: E402


def _solid_color_image_and_mask(rgb, size=48, box=(8, 8, 40, 40)):
    img = torch.zeros(1, size, size, 3)
    img[0, :, :, 0] = rgb[0] / 255
    img[0, :, :, 1] = rgb[1] / 255
    img[0, :, :, 2] = rgb[2] / 255
    mask = torch.zeros(1, size, size)
    x0, y0, x1, y1 = box
    mask[0, y0:y1, x0:x1] = 1.0
    return img, mask


def test_image_analyzer_registered():
    assert "ClothImageAnalyzer" in NODE_CLASS_MAPPINGS


def test_color_only_analysis_suggests_indigo():
    img, mask = _solid_color_image_and_mask((0x1E, 0x50, 0xA2))
    node = NODE_CLASS_MAPPINGS["ClothImageAnalyzer"]()
    out = node.analyze(img, mask, analysis_source="color_only", num_dominant_colors=2)
    suggested_color_en, suggested_color_ja, dec, pat, mat, preview, debug = out
    assert suggested_color_en == "deep indigo blue"
    assert suggested_color_ja == "藍色"
    assert dec == ""  # color_only モードでは装飾候補は出さない
    assert preview.shape[0] == 1
    assert preview.shape[-1] == 3


def test_http_tagger_without_url_falls_back_gracefully():
    img, mask = _solid_color_image_and_mask((200, 50, 50))
    node = NODE_CLASS_MAPPINGS["ClothImageAnalyzer"]()
    out = node.analyze(img, mask, analysis_source="http_tagger", num_dominant_colors=1, tagger_url="")
    *_, debug = out
    assert "tagger_error" in debug


def test_suggested_color_wires_into_prompt_composer():
    """Analyzerの出力を Prompt Composer の color / override 入力にそのまま渡せる。"""
    img, mask = _solid_color_image_and_mask((0x1E, 0x50, 0xA2))
    analyzer = NODE_CLASS_MAPPINGS["ClothImageAnalyzer"]()
    _, suggested_color_ja, *_ = analyzer.analyze(img, mask, analysis_source="color_only", num_dominant_colors=1)

    composer = NODE_CLASS_MAPPINGS["ClothPromptComposer"]()
    from nodes import categories, model_profiles, vocabulary

    target_raw = f"generic | {model_profiles.MODEL_PROFILES['generic'].label_ja}"
    preset_raw = categories.grouped_default_decoration("none")
    pattern_raw = vocabulary.bilingual_default("none", vocabulary.PATTERN_LABELS_JA)
    material_raw = vocabulary.bilingual_default("none", vocabulary.MATERIAL_LABELS_JA)

    prompt, *_rest = composer.compose(
        mask,
        decoration_preset=preset_raw,
        pattern=pattern_raw,
        material=material_raw,
        target_model=target_raw,
        output_language="ja",
        subject_hint="着物",
        grow_px=0,
        feather_px=0.0,
        color=suggested_color_ja,
    )
    assert "藍色" in prompt
    assert "着物" in prompt
