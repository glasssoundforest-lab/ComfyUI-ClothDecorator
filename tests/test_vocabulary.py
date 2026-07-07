from nodes import vocabulary


def test_build_decoration_prompt_basic():
    result = vocabulary.build_decoration_prompt(
        decoration_preset="embroidery",
        pattern="floral",
        material="silk",
        color="red",
        subject_hint="dress",
    )
    assert "red" in result.decoration_prompt
    assert "embroidery" in result.decoration_prompt or "embroidered" in result.decoration_prompt
    assert "floral pattern" in result.decoration_prompt
    assert "silk fabric" in result.decoration_prompt
    assert result.inpaint_prompt.startswith("dress")


def test_build_decoration_prompt_dedupes_terms():
    result = vocabulary.build_decoration_prompt(
        decoration_preset="none",
        color="red",
        free_text="red accents",
    )
    # "red" と "red accents" は別語句として扱われるが、同一語の重複は除かれる
    result2 = vocabulary.build_decoration_prompt(color="red", free_text="red")
    terms_lower = [t.lower() for t in result2.terms_used]
    assert terms_lower.count("red") == 1


def test_build_decoration_prompt_merges_with_base():
    result = vocabulary.build_decoration_prompt(
        decoration_preset="lace_trim",
        base_prompt="masterpiece, best quality, 1girl",
    )
    assert result.merged_prompt.startswith("masterpiece, best quality, 1girl")
    assert "lace trim" in result.merged_prompt


def test_build_decoration_prompt_negative_includes_defaults_and_extra():
    result = vocabulary.build_decoration_prompt(negative_extra="watermark, text")
    assert "blurry" in result.negative_prompt
    assert "watermark" in result.negative_prompt
    assert "text" in result.negative_prompt


def test_empty_input_produces_empty_decoration_prompt():
    result = vocabulary.build_decoration_prompt()
    assert result.decoration_prompt == ""
    assert result.inpaint_prompt == "clothing"
