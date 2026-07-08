from nodes import tag_mapping


def test_map_tags_finds_lace_trim_decoration():
    result = tag_mapping.map_tags_to_vocab(["lace_trim", "red_dress"])
    assert result["decoration_preset"] == "lace_trim"
    assert result["scores"]["decoration_preset"] > 0


def test_map_tags_finds_floral_pattern():
    result = tag_mapping.map_tags_to_vocab(["floral_pattern", "1girl"])
    assert result["pattern"] == "floral"


def test_map_tags_finds_silk_material():
    result = tag_mapping.map_tags_to_vocab(["silk_fabric", "shiny"])
    assert result["material"] == "silk"


def test_map_tags_no_match_returns_empty():
    result = tag_mapping.map_tags_to_vocab(["1girl", "smile", "looking_at_viewer"])
    assert result["decoration_preset"] == ""
    assert result["pattern"] == ""
    assert result["material"] == ""


def test_map_tags_empty_input():
    result = tag_mapping.map_tags_to_vocab([])
    assert result["decoration_preset"] == ""
    assert result["pattern"] == ""
    assert result["material"] == ""


def test_map_tags_combined_multi_category():
    result = tag_mapping.map_tags_to_vocab(["embroidery", "striped_pattern", "denim_fabric"])
    assert result["decoration_preset"] == "embroidery"
    assert result["pattern"] == "striped"
    assert result["material"] == "denim"
