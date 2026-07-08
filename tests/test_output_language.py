from nodes import vocabulary


def test_output_language_default_is_english():
    result = vocabulary.build_decoration_prompt(
        decoration_preset="embroidery", color="red", subject_hint="dress"
    )
    assert result.resolved["output_language"] == "en"
    assert "intricate embroidery" in result.decoration_prompt


def test_output_language_japanese_uses_ja_labels():
    result = vocabulary.build_decoration_prompt(
        decoration_preset="embroidery",
        pattern="floral",
        material="silk",
        color="red",
        subject_hint="dress",
        output_language="ja",
    )
    assert result.resolved["output_language"] == "ja"
    assert "刺繍" in result.decoration_prompt
    assert "花柄" in result.decoration_prompt
    assert "シルク" in result.decoration_prompt
    assert "赤" in result.decoration_prompt
    assert "ワンピース" in result.inpaint_prompt


def test_output_language_japanese_negative_prompt():
    result = vocabulary.build_decoration_prompt(output_language="ja")
    assert "ブレ" in result.negative_prompt
    assert "低品質" in result.negative_prompt


def test_output_language_ja_with_japanese_input_stays_japanese():
    result = vocabulary.build_decoration_prompt(
        decoration_preset="刺繍",
        pattern="青海波",
        material="ちりめん",
        color="藍色",
        subject_hint="着物",
        output_language="ja",
    )
    assert result.decoration_prompt == "藍色, 刺繍, 青海波, ちりめん"
    assert result.inpaint_prompt.startswith("着物")


def test_output_language_none_preset_produces_no_stray_label():
    """decoration_preset='none' の場合、JA出力でも「なし」というテキストが紛れ込まない。"""
    result = vocabulary.build_decoration_prompt(
        decoration_preset="none", pattern="none", material="none", output_language="ja"
    )
    assert "なし" not in result.decoration_prompt


def test_output_language_invalid_value_falls_back_to_english():
    result = vocabulary.build_decoration_prompt(decoration_preset="embroidery", output_language="fr")
    assert result.resolved["output_language"] == "en"
    assert "intricate embroidery" in result.decoration_prompt


def test_resolve_color_bilingual_traditional():
    en, ja = vocabulary.resolve_color_bilingual("藍色")
    assert en == "deep indigo blue"
    assert ja == "藍色"


def test_resolve_color_bilingual_base_color():
    en, ja = vocabulary.resolve_color_bilingual("red")
    assert en == "red"
    assert ja == "赤"


def test_resolve_color_bilingual_unknown_passthrough():
    en, ja = vocabulary.resolve_color_bilingual("cerulean")
    assert en == "cerulean"
    assert ja == "cerulean"


def test_resolve_subject_bilingual_japanese_input():
    en, ja = vocabulary.resolve_subject_bilingual("着物")
    assert en == "kimono"
    assert ja == "着物"


def test_resolve_subject_bilingual_english_input():
    en, ja = vocabulary.resolve_subject_bilingual("dress")
    assert en == "dress"
    # SUBJECT_HINT_JA_TO_EN には "ドレス"→dress と "ワンピース"→dress の両方があり、
    # 逆引きは辞書定義順で後勝ち（"ワンピース"）になる仕様
    assert ja == "ワンピース"


def test_resolve_subject_bilingual_empty_defaults():
    en, ja = vocabulary.resolve_subject_bilingual("")
    assert en == "clothing"
    assert ja == "服"


# ── プロンプト整形（空白・改行の正規化） ─────────────────────────────

def test_free_text_internal_whitespace_and_newlines_are_normalized():
    result = vocabulary.build_decoration_prompt(
        decoration_preset="none", free_text="  lots of   extra   spaces  \n\n and a newline "
    )
    assert result.decoration_prompt == "lots of extra spaces and a newline"


def test_negative_extra_internal_whitespace_is_normalized():
    result = vocabulary.build_decoration_prompt(
        decoration_preset="none", negative_extra="watermark,   text  with   spaces \n"
    )
    assert "text with spaces" in result.negative_prompt
    assert "  " not in result.negative_prompt


def test_base_prompt_internal_whitespace_is_normalized():
    result = vocabulary.build_decoration_prompt(
        decoration_preset="embroidery", base_prompt="masterpiece,   best  quality \n , 1girl"
    )
    assert "best quality" in result.merged_prompt
    assert "  " not in result.merged_prompt


# ── タグの統合（順不同・重複タグの一本化） ─────────────────────────────

def test_free_text_duplicate_tags_are_consolidated_regardless_of_order():
    r1 = vocabulary.build_decoration_prompt(decoration_preset="none", free_text="dress, jacket, dress, Jacket")
    r2 = vocabulary.build_decoration_prompt(decoration_preset="none", free_text="Jacket, dress, jacket, dress")
    terms1 = {t.lower() for t in r1.decoration_prompt.split(", ")}
    terms2 = {t.lower() for t in r2.decoration_prompt.split(", ")}
    assert terms1 == terms2 == {"dress", "jacket"}


def test_free_text_tags_dedupe_against_color_and_preset_terms():
    result = vocabulary.build_decoration_prompt(
        decoration_preset="embroidery", color="red", free_text="red, sparkly, intricate embroidery"
    )
    terms = result.decoration_prompt.split(", ")
    assert terms.count("red") == 1
    assert terms.count("intricate embroidery") == 1
    assert "sparkly" in terms


def test_free_text_single_phrase_without_comma_is_unaffected():
    """カンマを含まない一続きのフレーズは、これまで通り1つの語として扱われる。"""
    result = vocabulary.build_decoration_prompt(decoration_preset="none", free_text="a delicate hand-stitched look")
    assert result.decoration_prompt == "a delicate hand-stitched look"


# ── カテゴリ別ブロック整形（group_by_category） ─────────────────────────

def test_categorize_term_basic():
    assert vocabulary.categorize_term("red") == "color"
    assert vocabulary.categorize_term("intricate embroidery") == "decoration"
    assert vocabulary.categorize_term("floral pattern") == "pattern"
    assert vocabulary.categorize_term("silk fabric") == "material"
    assert vocabulary.categorize_term("sparkly") == "other"


def test_group_terms_by_category_reorders_into_blocks():
    terms = ["blue", "lace trim", "red", "floral pattern", "silk fabric", "gold", "sparkly"]
    grouped = vocabulary.group_terms_by_category(terms)
    categories = [vocabulary.categorize_term(t) for t in grouped]
    # 一度出現したカテゴリの後に別カテゴリへ戻ることが無い＝ブロック化されている
    seen = []
    for c in categories:
        if not seen or seen[-1] != c:
            seen.append(c)
    assert len(seen) == len(set(categories))


def test_group_terms_by_category_preserves_intra_category_order():
    terms = ["blue", "red", "gold"]
    grouped = vocabulary.group_terms_by_category(terms)
    assert grouped == ["blue", "red", "gold"]  # 色カテゴリのみなので入力順のまま


def test_build_decoration_prompt_group_by_category_true():
    result = vocabulary.build_decoration_prompt(
        decoration_preset="embroidery",
        color="red",
        free_text="blue, lace trim, floral pattern, gold, silk fabric, sparkly",
        group_by_category=True,
    )
    terms = result.decoration_prompt.split(", ")
    color_positions = [i for i, t in enumerate(terms) if vocabulary.categorize_term(t) == "color"]
    # 色タグ（red, blue, gold）が連続したブロックになっている
    assert color_positions == list(range(color_positions[0], color_positions[0] + len(color_positions)))
    assert set(terms[: len(color_positions)]) == {"red", "blue", "gold"}


def test_build_decoration_prompt_group_by_category_false_preserves_order():
    result = vocabulary.build_decoration_prompt(
        decoration_preset="embroidery",
        color="red",
        free_text="blue, lace trim, floral pattern, gold, silk fabric, sparkly",
        group_by_category=False,
    )
    # 既定では従来通り入力順（colorが先頭、以降はpreset→free_textの出現順）
    assert result.decoration_prompt.startswith("red, intricate embroidery, embroidered pattern, blue")
