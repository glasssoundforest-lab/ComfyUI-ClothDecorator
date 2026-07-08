import pytest

from nodes import model_profiles as mp


def test_all_profiles_have_required_fields():
    for key, profile in mp.MODEL_PROFILES.items():
        assert profile.key == key
        assert profile.style in ("tags", "natural", "natural_sentence")
        assert profile.label_ja


def test_generic_profile_passthrough():
    positive, negative, style = mp.adapt_prompt(
        terms=["red", "embroidery"], subject="dress", negative_terms=["blurry"], target_model="generic"
    )
    assert style == "tags"
    assert positive == "dress, red, embroidery"
    assert negative == "blurry"


def test_sd15_anime_adds_quality_tags_and_underscores():
    positive, negative, style = mp.adapt_prompt(
        terms=["lace trim", "gold"], subject="school uniform", negative_terms=[], target_model="sd15_anime"
    )
    assert style == "tags"
    assert positive.startswith("masterpiece, best quality, highres, school_uniform")
    assert "lace_trim" in positive
    assert "worst_quality" in negative  # negative_prefix もアンダースコア化される


def test_pony_v6_score_tags():
    positive, negative, style = mp.adapt_prompt(
        terms=["sequins"], subject="dress", negative_terms=[], target_model="pony_v6"
    )
    assert positive.startswith("score_9, score_8_up, score_7_up, dress, sequins")
    assert "score_6" in negative and "score_5" in negative and "score_4" in negative


def test_sdxl_base_natural_style():
    positive, negative, style = mp.adapt_prompt(
        terms=["red embroidery", "gold trim"],
        subject="a dress",
        negative_terms=["watermark"],
        target_model="sdxl_base",
    )
    assert style == "natural"
    assert "a dress" in positive
    assert "red embroidery" in positive
    assert "and gold trim" in positive
    assert "watermark" in negative
    assert "blurry" in negative


def test_flux_has_no_negative_prompt():
    positive, negative, style = mp.adapt_prompt(
        terms=["floral pattern"], subject="jacket", negative_terms=["blurry"], target_model="flux"
    )
    assert style == "natural_sentence"
    assert negative == ""
    assert "jacket" in positive
    assert "floral pattern" in positive


def test_sd3_natural_sentence_with_negative():
    positive, negative, style = mp.adapt_prompt(
        terms=[], subject="coat", negative_terms=["extra limbs"], target_model="sd3"
    )
    assert style == "natural_sentence"
    assert "coat" in positive
    assert "blurry" in negative
    assert "extra limbs" in negative


def test_unknown_model_falls_back_to_generic():
    positive, negative, style = mp.adapt_prompt(
        terms=["red"], subject="shirt", negative_terms=[], target_model="totally_unknown_model"
    )
    assert style == "tags"
    assert positive == "shirt, red"


def test_empty_terms_natural_sentence_still_produces_output():
    positive, _, _ = mp.adapt_prompt(terms=[], subject="", negative_terms=[], target_model="flux")
    assert "the garment" in positive


@pytest.mark.parametrize("key", list(mp.MODEL_PROFILES.keys()))
def test_model_choices_contains_all_keys(key):
    assert key in mp.model_choices()


# ── adapt_freeform_prompt（🧠 Model Prompt Adapter ノード用） ───────────

def test_freeform_tags_style_splits_and_tagifies():
    positive, negative, style = mp.adapt_freeform_prompt(
        prompt="red dress, lace trim, gold buttons",
        subject="1girl",
        negative_extra="watermark",
        target_model="sd15_anime",
    )
    assert style == "tags"
    assert positive.startswith("masterpiece, best quality, highres, 1girl")
    assert "red_dress" in positive
    assert "lace_trim" in positive
    assert "watermark" in negative


def test_freeform_natural_style_prepends_subject_and_quality():
    positive, negative, style = mp.adapt_freeform_prompt(
        prompt="wearing an elegant red dress with lace trim.",
        subject="A young woman",
        negative_extra="",
        target_model="sdxl_base",
    )
    assert style == "natural"
    assert positive.startswith("High quality")
    assert "A young woman" in positive
    assert "elegant red dress" in positive


def test_freeform_flux_no_negative():
    positive, negative, style = mp.adapt_freeform_prompt(
        prompt="a red silk dress", target_model="flux"
    )
    assert negative == ""
    assert "red silk dress" in positive


def test_freeform_empty_prompt_tags_style():
    positive, negative, style = mp.adapt_freeform_prompt(
        prompt="", subject="dress", target_model="generic"
    )
    assert positive == "dress"
