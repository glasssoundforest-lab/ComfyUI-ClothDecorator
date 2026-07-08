"""
tests/test_vocab_data_modules.py — 語彙データモジュール（*_data.py）の整合性検証

- 各辞書が目標件数（200件程度）に達しているか
- 生データ内にキーの重複が無いか
- vocabulary.py のフラット辞書が生データの件数と一致しているか
  （一致しない場合、キーの重複によって静かに上書きされたことを意味する）
"""

from nodes import color_data, decoration_data, material_data, pattern_data, subject_data, vocabulary


def test_decoration_data_reaches_200_with_no_duplicates():
    keys = [
        key
        for _major, _major_ja, mids in decoration_data.DECORATION_GROUPS
        for _mid, _mid_ja, entries in mids
        for key, _phrases, _ja in entries
    ]
    assert len(keys) >= 200
    assert len(keys) == len(set(keys))
    # vocabulary.DECORATION_PRESETS には none/custom の2件が追加される
    assert len(vocabulary.DECORATION_PRESETS) == len(keys) + 2


def test_pattern_data_reaches_200_with_no_duplicates():
    keys = [key for _major, _major_ja, entries in pattern_data.PATTERN_GROUPS for key, _p, _ja in entries]
    assert len(keys) >= 200
    assert len(keys) == len(set(keys))
    assert len(vocabulary.PATTERN_VOCAB) == len(keys) + 2


def test_material_data_reaches_200_with_no_duplicates():
    keys = [key for _major, _major_ja, entries in material_data.MATERIAL_GROUPS for key, _p, _ja in entries]
    assert len(keys) >= 200
    assert len(keys) == len(set(keys))
    assert len(vocabulary.MATERIAL_VOCAB) == len(keys) + 2


def test_color_data_reaches_200_with_no_duplicate_kanji_or_romaji():
    kanji_list = [kanji for _fam, _fam_ja, entries in color_data.COLOR_GROUPS for kanji, *_ in entries]
    romaji_list = [
        romaji.lower() for _fam, _fam_ja, entries in color_data.COLOR_GROUPS for _k, romaji, _e, _h in entries
    ]
    assert len(kanji_list) >= 200
    assert len(kanji_list) == len(set(kanji_list))
    assert len(romaji_list) == len(set(romaji_list))
    assert len(vocabulary.TRADITIONAL_COLORS_JA) == len(kanji_list)


def test_subject_data_reaches_200_with_no_duplicate_japanese_terms():
    ja_list = [ja for _major, _major_ja, entries in subject_data.SUBJECT_GROUPS for ja, _en in entries]
    assert len(ja_list) >= 200
    assert len(ja_list) == len(set(ja_list))
    assert len(vocabulary.SUBJECT_HINT_JA_TO_EN) == len(ja_list)


def test_all_color_hex_codes_are_valid_format():
    for _fam, _fam_ja, entries in color_data.COLOR_GROUPS:
        for kanji, _romaji, _en, hex_code in entries:
            assert hex_code.startswith("#"), f"{kanji}: invalid hex {hex_code!r}"
            assert len(hex_code) == 7, f"{kanji}: invalid hex length {hex_code!r}"
            int(hex_code[1:], 16)  # 16進として解釈できることを確認（例外なければOK）


def test_all_decoration_entries_have_at_least_one_phrase_or_are_meta():
    for _major, _major_ja, mids in decoration_data.DECORATION_GROUPS:
        for _mid, _mid_ja, entries in mids:
            for key, phrases, ja in entries:
                assert phrases, f"{key} has empty phrase list"
                assert ja, f"{key} has empty Japanese label"


def test_random_new_entries_resolve_correctly_end_to_end():
    """第5弾以降に追加された新語彙が build_decoration_prompt を通しで動くことを確認。"""
    result = vocabulary.build_decoration_prompt(
        decoration_preset="adire_resist_dye",
        pattern="huipil_pattern",
        material="pina_fiber",
        color="蒲公英色",
        subject_hint="ハンボク",
        output_language="ja",
    )
    assert result.resolved["decoration_preset"] == "adire_resist_dye"
    assert result.resolved["pattern"] == "huipil_pattern"
    assert result.resolved["material"] == "pina_fiber"
    assert "蒲公英色" in result.decoration_prompt
    assert result.inpaint_prompt.startswith("ハンボク")
