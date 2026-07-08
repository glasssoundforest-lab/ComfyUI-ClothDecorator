from nodes import vocabulary


# ── resolve_key（バイリンガルドロップダウン解決） ───────────────────

def test_resolve_key_plain_english_key():
    assert vocabulary.resolve_key("embroidery", vocabulary.DECORATION_PRESETS, {}) == "embroidery"


def test_resolve_key_bilingual_dropdown_format():
    raw = vocabulary.bilingual_default("embroidery", vocabulary.DECORATION_LABELS_JA)
    assert raw == "embroidery | 刺繍"
    resolved = vocabulary.resolve_key(raw, vocabulary.DECORATION_PRESETS, vocabulary.DECORATION_LABELS_JA)
    assert resolved == "embroidery"


def test_resolve_key_japanese_label_only():
    resolved = vocabulary.resolve_key(
        "刺繍", vocabulary.DECORATION_PRESETS, vocabulary.DECORATION_LABELS_JA
    )
    assert resolved == "embroidery"


def test_resolve_key_unknown_passthrough():
    resolved = vocabulary.resolve_key(
        "totally_unknown_xyz", vocabulary.DECORATION_PRESETS, vocabulary.DECORATION_LABELS_JA
    )
    assert resolved == "totally_unknown_xyz"


def test_bilingual_options_matches_labels():
    options = vocabulary.bilingual_options(["embroidery", "none"], vocabulary.DECORATION_LABELS_JA)
    assert "embroidery | 刺繍" in options
    assert "none | なし" in options


# ── 色（日本の伝統色） ─────────────────────────────────────────────

def test_resolve_color_term_kanji():
    assert vocabulary.resolve_color_term("藍色") == "deep indigo blue"


def test_resolve_color_term_romaji():
    assert vocabulary.resolve_color_term("ai-iro") == "deep indigo blue"


def test_resolve_color_term_romaji_case_insensitive():
    assert vocabulary.resolve_color_term("AI-IRO") == "deep indigo blue"


def test_resolve_color_term_passthrough_for_unknown():
    assert vocabulary.resolve_color_term("cerulean") == "cerulean"
    assert vocabulary.resolve_color_term("#ff0000") == "#ff0000"


def test_resolve_color_to_hex_kanji():
    assert vocabulary.resolve_color_to_hex("藍色") == "#1e50a2"


def test_resolve_color_to_hex_passthrough_for_hex_input():
    assert vocabulary.resolve_color_to_hex("#00ff00") == "#00ff00"


def test_resolve_color_to_hex_passthrough_for_rgb_string():
    assert vocabulary.resolve_color_to_hex("10,20,30") == "10,20,30"


# ── 対象語（subject_hint） ─────────────────────────────────────────

def test_resolve_subject_hint_japanese():
    assert vocabulary.resolve_subject_hint("着物") == "kimono"
    assert vocabulary.resolve_subject_hint("ドレス") == "dress"


def test_resolve_subject_hint_english_passthrough():
    assert vocabulary.resolve_subject_hint("jacket") == "jacket"


def test_resolve_subject_hint_empty_defaults_to_clothing():
    assert vocabulary.resolve_subject_hint("") == "clothing"


# ── build_decoration_prompt 全体としての日本語対応 ───────────────────

def test_build_decoration_prompt_fully_japanese_input():
    result = vocabulary.build_decoration_prompt(
        decoration_preset="刺繍",
        pattern="青海波",
        material="ちりめん",
        color="藍色",
        subject_hint="着物",
    )
    assert result.resolved["decoration_preset"] == "embroidery"
    assert result.resolved["pattern"] == "seigaiha"
    assert result.resolved["material"] == "chirimen"
    assert result.resolved["color"] == "deep indigo blue"
    assert result.resolved["subject_hint"] == "kimono"
    assert "deep indigo blue" in result.decoration_prompt
    assert "seigaiha" in result.decoration_prompt
    assert "chirimen" in result.decoration_prompt
    assert result.inpaint_prompt.startswith("kimono")


def test_build_decoration_prompt_bilingual_dropdown_input():
    preset_raw = vocabulary.bilingual_default("lace_trim", vocabulary.DECORATION_LABELS_JA)
    result = vocabulary.build_decoration_prompt(decoration_preset=preset_raw)
    assert result.resolved["decoration_preset"] == "lace_trim"
    assert "lace trim" in result.decoration_prompt


def test_wagara_patterns_present():
    for key in ["seigaiha", "asanoha", "ichimatsu", "karakusa", "kikkou", "shippou", "raimon"]:
        assert key in vocabulary.PATTERN_VOCAB
        assert key in vocabulary.PATTERN_LABELS_JA


def test_japanese_materials_present():
    for key in ["washi", "chirimen", "kinran", "nishijin_ori", "tsumugi"]:
        assert key in vocabulary.MATERIAL_VOCAB
        assert key in vocabulary.MATERIAL_LABELS_JA


def test_new_decoration_presets_present():
    for key in [
        "sashiko_stitch",
        "indigo_dye",
        "kintsugi_seam",
        "origami_applique",
        "kamon_emblem",
        "rhinestone",
        "hand_painted",
    ]:
        assert key in vocabulary.DECORATION_PRESETS
        assert key in vocabulary.DECORATION_LABELS_JA


def test_all_decoration_presets_have_ja_labels():
    missing = set(vocabulary.DECORATION_PRESETS) - set(vocabulary.DECORATION_LABELS_JA)
    assert not missing


def test_all_patterns_have_ja_labels():
    missing = set(vocabulary.PATTERN_VOCAB) - set(vocabulary.PATTERN_LABELS_JA)
    assert not missing


def test_all_materials_have_ja_labels():
    missing = set(vocabulary.MATERIAL_VOCAB) - set(vocabulary.MATERIAL_LABELS_JA)
    assert not missing


# ── 第3/4弾拡充分のスポットチェック ─────────────────────────────────

def test_world_textile_decoration_presets_present():
    for key in [
        "zari_embroidery",
        "mirror_work",
        "block_print",
        "ikat_weave",
        "kente_pattern",
        "fair_isle_knit",
        "damask_weave",
        "toile_print",
        "frog_buttons",
        "laser_cut_pattern",
    ]:
        assert key in vocabulary.DECORATION_PRESETS
        assert key in vocabulary.DECORATION_LABELS_JA


def test_world_patterns_present():
    for key in ["damask", "toile", "ikat", "kente", "fair_isle", "tartan", "arabesque_tile", "mandala"]:
        assert key in vocabulary.PATTERN_VOCAB
        assert key in vocabulary.PATTERN_LABELS_JA


def test_new_wagara_present():
    for key in ["hishi", "kumo"]:
        assert key in vocabulary.PATTERN_VOCAB
        assert key in vocabulary.PATTERN_LABELS_JA


def test_western_materials_present():
    for key in ["organza", "tulle", "brocade_western", "tweed", "corduroy", "faux_fur", "neoprene"]:
        assert key in vocabulary.MATERIAL_VOCAB
        assert key in vocabulary.MATERIAL_LABELS_JA


def test_additional_traditional_colors_resolve():
    assert vocabulary.resolve_color_term("江戸紫") == "edo purple"
    assert vocabulary.resolve_color_term("kikyou-iro") == "bellflower purple-blue"
    assert vocabulary.resolve_color_to_hex("銀鼠") == "#91989f"


def test_additional_subject_hints_resolve():
    assert vocabulary.resolve_subject_hint("花嫁衣装") == "wedding dress"
    assert vocabulary.resolve_subject_hint("軍服") == "military uniform"
    assert vocabulary.resolve_subject_hint("白衣") == "lab coat"


def test_dictionary_sizes_grew_as_expected():
    assert len(vocabulary.DECORATION_PRESETS) >= 70
    assert len(vocabulary.PATTERN_VOCAB) >= 35
    assert len(vocabulary.MATERIAL_VOCAB) >= 30
    assert len(vocabulary.TRADITIONAL_COLORS_JA) >= 35
    assert len(vocabulary.SUBJECT_HINT_JA_TO_EN) >= 35


def test_no_duplicate_romaji_in_traditional_colors():
    romaji_list = [e["romaji"] for e in vocabulary.TRADITIONAL_COLORS_JA.values()]
    assert len(romaji_list) == len(set(romaji_list))
