from nodes import categories, vocabulary


def _non_meta_keys(d: dict) -> set:
    return set(d.keys()) - {"none", "custom"}


def test_all_decoration_presets_categorized():
    missing = _non_meta_keys(vocabulary.DECORATION_PRESETS) - set(categories.DECORATION_CATEGORY_OF)
    assert not missing


def test_all_patterns_categorized():
    missing = _non_meta_keys(vocabulary.PATTERN_VOCAB) - set(categories.PATTERN_CATEGORY_OF)
    assert not missing


def test_all_materials_categorized():
    missing = _non_meta_keys(vocabulary.MATERIAL_VOCAB) - set(categories.MATERIAL_CATEGORY_OF)
    assert not missing


def test_all_colors_categorized():
    missing = _non_meta_keys(vocabulary.TRADITIONAL_COLORS_JA) - set(categories.COLOR_CATEGORY_OF)
    assert not missing


def test_all_subject_hints_categorized():
    missing = _non_meta_keys(vocabulary.SUBJECT_HINT_JA_TO_EN) - set(categories.SUBJECT_CATEGORY_OF)
    assert not missing


def test_no_stale_category_entries():
    """カテゴリ辞書側に、実際の語彙辞書に存在しないキーが残っていないか。"""
    assert set(categories.DECORATION_CATEGORY_OF) <= set(vocabulary.DECORATION_PRESETS)
    assert set(categories.PATTERN_CATEGORY_OF) <= set(vocabulary.PATTERN_VOCAB)
    assert set(categories.MATERIAL_CATEGORY_OF) <= set(vocabulary.MATERIAL_VOCAB)
    assert set(categories.COLOR_CATEGORY_OF) <= set(vocabulary.TRADITIONAL_COLORS_JA)
    assert set(categories.SUBJECT_CATEGORY_OF) <= set(vocabulary.SUBJECT_HINT_JA_TO_EN)


def test_every_mid_category_has_a_label():
    used_pairs = set(categories.DECORATION_CATEGORY_OF.values())
    missing = used_pairs - set(categories.DECORATION_MID_LABELS_JA)
    assert not missing


def test_every_major_category_used_and_labeled():
    used_majors = {major for major, _ in categories.DECORATION_CATEGORY_OF.values()}
    missing = used_majors - set(categories.DECORATION_MAJOR_LABELS_JA)
    assert not missing


def test_grouped_decoration_options_format():
    options = categories.grouped_decoration_options()
    assert any(opt.startswith("[刺繍・ビーズ手芸 > 刺繍技法] embroidery | 刺繍") for opt in options)
    # "none"/"custom" は分類が無いため角括弧プレフィックスが付かない
    assert "none | なし" in options
    assert "custom | 自由入力" in options


def test_grouped_default_decoration_matches_options():
    default = categories.grouped_default_decoration("embroidery")
    assert default in categories.grouped_decoration_options()
    assert default.startswith("[")


def test_resolve_grouped_key_strips_prefix():
    raw = "[刺繍・ビーズ手芸 > 刺繍技法] embroidery | 刺繍"
    assert categories.resolve_grouped_key(raw) == "embroidery | 刺繍"


def test_resolve_grouped_key_passthrough_without_prefix():
    assert categories.resolve_grouped_key("none | なし") == "none | なし"
    assert categories.resolve_grouped_key("embroidery") == "embroidery"


def test_resolve_grouped_key_then_vocabulary_resolve_key_roundtrip():
    raw = categories.grouped_default_decoration("kintsugi_seam")
    stripped = categories.resolve_grouped_key(raw)
    resolved = vocabulary.resolve_key(stripped, vocabulary.DECORATION_PRESETS, vocabulary.DECORATION_LABELS_JA)
    assert resolved == "kintsugi_seam"


def test_grouped_single_level_options_for_pattern():
    options = categories.grouped_single_level_options(
        list(vocabulary.PATTERN_VOCAB.keys()),
        vocabulary.PATTERN_LABELS_JA,
        categories.PATTERN_CATEGORY_OF,
        categories.PATTERN_MAJOR_LABELS_JA,
    )
    assert any(opt.startswith("[和柄] seigaiha | 青海波") for opt in options)


def test_category_map_summary_structure():
    summary = categories.category_map_summary()
    assert "embroidery_beadwork" in summary
    assert "embroidery" in summary["embroidery_beadwork"]
    assert "embroidery" in summary["embroidery_beadwork"]["embroidery"]


def test_full_compose_pipeline_with_grouped_dropdown_value():
    """実際のノードが渡すであろうグループ付きドロップダウン文字列で通しで動く。"""
    raw = categories.grouped_default_decoration("sashiko_stitch")
    stripped = categories.resolve_grouped_key(raw)
    result = vocabulary.build_decoration_prompt(decoration_preset=stripped, subject_hint="kimono")
    assert result.resolved["decoration_preset"] == "sashiko_stitch"
    assert "sashiko stitching" in result.decoration_prompt
