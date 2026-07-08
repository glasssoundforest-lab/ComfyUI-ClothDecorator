"""
tests/test_conflict_detection.py — タグ衝突検出・confirm_continue の動作検証

color / free_text / subject_hint の間で、同じカテゴリ（色・対象の服/部位）に
属する異なる語彙が複数指定された場合の検出ロジックと、
🧵 Prompt Composer / 🧩 Auto の confirm_continue ゲートの挙動をテストする。

重要な仕様: 衝突検出は「タグ全体が丸ごと語彙上の色名/対象語と一致する」
場合のみ発動する（完全一致）。"red and blue striped skirt" のような、
色の単語が長い説明文の一部として含まれているだけの複合フレーズは
誤って衝突扱いにしない（過去に実際に発生した誤検出バグの回帰テストを含む）。
"""

import pytest
import torch

from nodes import vocabulary


# ── vocabulary.detect_tag_conflicts（純粋ロジック） ─────────────────────

def test_no_conflict_when_everything_consistent():
    conflicts = vocabulary.detect_tag_conflicts(
        color="red", free_text="sparkly embroidery", subject_hint="dress"
    )
    assert conflicts == []


def test_color_conflict_between_color_field_and_standalone_free_text_tag():
    conflicts = vocabulary.detect_tag_conflicts(color="red", free_text="blue")
    assert len(conflicts) == 1
    assert conflicts[0].category == "color"
    assert set(conflicts[0].values) == {"red", "blue"}


def test_color_conflict_between_two_standalone_free_text_tags():
    conflicts = vocabulary.detect_tag_conflicts(free_text="red, blue")
    assert any(c.category == "color" and set(c.values) == {"red", "blue"} for c in conflicts)


def test_subject_conflict_between_subject_hint_and_standalone_free_text_tag():
    conflicts = vocabulary.detect_tag_conflicts(subject_hint="dress", free_text="jacket")
    subject_conflicts = [c for c in conflicts if c.category == "subject"]
    assert len(subject_conflicts) == 1
    assert set(subject_conflicts[0].values) == {"dress", "jacket"}


def test_no_subject_conflict_for_single_garment_mentioned_twice():
    """同じ服が2回言及されても（同義語ではなく同一語）衝突扱いにしない。"""
    conflicts = vocabulary.detect_tag_conflicts(subject_hint="dress", free_text="dress")
    assert not any(c.category == "subject" for c in conflicts)


def test_japanese_color_conflict_detection_standalone_tags():
    conflicts = vocabulary.detect_tag_conflicts(color="藍色", free_text="朱色")
    assert any(c.category == "color" and set(c.values) == {"藍色", "朱色"} for c in conflicts)


def test_format_conflict_message_empty():
    assert vocabulary.format_conflict_message([]) == ""


def test_format_conflict_message_joins_multiple():
    conflicts = vocabulary.detect_tag_conflicts(color="red", free_text="blue, jacket", subject_hint="dress")
    msg = vocabulary.format_conflict_message(conflicts)
    assert "色" in msg
    assert "部位" in msg


# ── 誤検出防止（複合フレーズは衝突扱いにしない） ─────────────────────────

def test_no_false_positive_for_compound_color_pattern_phrase():
    """「赤と青のストライプ柄のスカート」のような複合フレーズを誤って色の衝突にしない。"""
    conflicts = vocabulary.detect_tag_conflicts(free_text="red and blue striped skirt")
    assert conflicts == []


def test_no_false_positive_when_subject_hint_and_descriptive_phrase_share_a_word():
    """subject_hint="dress" で free_text 中にたまたま別の服の単語が混じっていても、
    それが長い説明文の一部なら誤検出しない。"""
    conflicts = vocabulary.detect_tag_conflicts(
        subject_hint="dress", free_text="with a beautiful pleated skirt pattern printed on it"
    )
    assert not any(c.category == "subject" for c in conflicts)


def test_no_false_positive_for_color_word_inside_decoration_phrase():
    conflicts = vocabulary.detect_tag_conflicts(free_text="yellow embroidery")
    assert conflicts == []


def test_categorize_term_compound_phrase_is_other_not_color():
    """categorize_term も同じ理由で複合フレーズを安易に color 扱いしない。"""
    assert vocabulary.categorize_term("yellow embroidery") == "other"
    assert vocabulary.categorize_term("red and blue striped skirt") == "other"
    assert vocabulary.categorize_term("red") == "color"  # 単独タグは引き続き検出される


# ── 一般的な日本語の色名（黄色・黒など）の認識 ───────────────────────────

def test_generic_japanese_base_color_words_are_recognized():
    """「黄色」「黒」のような基本的な日本語色名（伝統色ではない）も色として認識する。"""
    assert vocabulary.categorize_term("黄色") == "color"
    assert vocabulary.categorize_term("黒") == "color"


def test_color_conflict_with_generic_japanese_color_words():
    conflicts = vocabulary.detect_tag_conflicts(free_text="黄色, 黒")
    color_conflicts = [c for c in conflicts if c.category == "color"]
    assert len(color_conflicts) == 1
    assert set(color_conflicts[0].values) == {"yellow", "black"}


def test_compound_japanese_sentence_still_not_falsely_flagged():
    """「黄色のワンピースと黒のロングスカート」のような1つの文は、
    タグ分割されていないため衝突として検出されない（既存の複合フレーズ仕様通り）。"""
    conflicts = vocabulary.detect_tag_conflicts(free_text="黄色のワンピースと黒のロングスカート")
    assert conflicts == []


def test_dress_and_skirt_detected_as_subject_conflict_when_using_dictionary_terms():
    """辞書に完全一致する語（"スカート"）を使えば、ワンピースとの対象語衝突は検出される。"""
    conflicts_matched = vocabulary.detect_tag_conflicts(free_text="ワンピース, スカート")
    assert any(c.category == "subject" and set(c.values) == {"dress", "skirt"} for c in conflicts_matched)


def test_skirt_length_variants_are_registered_and_conflict_with_each_other():
    """
    「ミニスカート」「マキシスカート」「ロングスカート」等の丈違いスカートは、
    それぞれ別の服として区別され、互いに衝突として検知される（意図的な仕様）。
    """
    conflicts = vocabulary.detect_tag_conflicts(free_text="ロングスカート, スカート")
    assert any(c.category == "subject" and set(c.values) == {"long skirt", "skirt"} for c in conflicts)

    conflicts2 = vocabulary.detect_tag_conflicts(free_text="ロングスカート, ミニスカート")
    assert any(
        c.category == "subject" and set(c.values) == {"long skirt", "mini skirt"} for c in conflicts2
    )


def test_dress_length_variants_are_registered_and_conflict_with_each_other():
    """
    スカートと同じ理由で見つかった同種のギャップ: 「ミニドレス」「マキシドレス」
    「ロングドレス」も丈違いスカートと同様に登録し、互いに衝突として検知する。
    """
    conflicts = vocabulary.detect_tag_conflicts(free_text="ワンピース, ミニドレス")
    assert any(c.category == "subject" and set(c.values) == {"dress", "mini dress"} for c in conflicts)

    conflicts2 = vocabulary.detect_tag_conflicts(free_text="ミニドレス, マキシドレス")
    assert any(
        c.category == "subject" and set(c.values) == {"mini dress", "maxi dress"} for c in conflicts2
    )

    conflicts3 = vocabulary.detect_tag_conflicts(free_text="ロングドレス, マキシドレス")
    assert any(
        c.category == "subject" and set(c.values) == {"long dress", "maxi dress"} for c in conflicts3
    )


# ── Prompt Composer / Auto の confirm_continue ゲート ────────────────────

from nodes import NODE_CLASS_MAPPINGS  # noqa: E402
from nodes import categories as cat  # noqa: E402
from nodes import model_profiles as mp  # noqa: E402


def _mask():
    m = torch.zeros(1, 32, 32)
    m[0, 4:28, 4:28] = 1.0
    return m


def test_prompt_composer_raises_on_conflict_by_default():
    node = NODE_CLASS_MAPPINGS["ClothPromptComposer"]()
    preset_raw = cat.grouped_default_decoration("none")
    target_raw = f"generic | {mp.MODEL_PROFILES['generic'].label_ja}"
    with pytest.raises(ValueError, match="競合"):
        node.compose(
            _mask(), decoration_preset=preset_raw, pattern="none", material="none",
            target_model=target_raw, output_language="en", subject_hint="dress",
            grow_px=0, feather_px=0.0, confirm_continue=False,
            color="red", free_text="blue",
        )


def test_prompt_composer_continues_when_confirmed():
    node = NODE_CLASS_MAPPINGS["ClothPromptComposer"]()
    preset_raw = cat.grouped_default_decoration("none")
    target_raw = f"generic | {mp.MODEL_PROFILES['generic'].label_ja}"
    out = node.compose(
        _mask(), decoration_preset=preset_raw, pattern="none", material="none",
        target_model=target_raw, output_language="en", subject_hint="dress",
        grow_px=0, feather_px=0.0, confirm_continue=True,
        color="red", free_text="blue",
    )
    prompt, neg, merged, model_prompt, model_neg, prep_mask, conflict_warning, dbg = out
    assert "red" in prompt and "blue" in prompt
    assert conflict_warning != ""


def test_prompt_composer_no_conflict_runs_normally_without_confirm():
    node = NODE_CLASS_MAPPINGS["ClothPromptComposer"]()
    preset_raw = cat.grouped_default_decoration("none")
    target_raw = f"generic | {mp.MODEL_PROFILES['generic'].label_ja}"
    out = node.compose(
        _mask(), decoration_preset=preset_raw, pattern="none", material="none",
        target_model=target_raw, output_language="en", subject_hint="dress",
        grow_px=0, feather_px=0.0, confirm_continue=False,
        color="red", free_text="sparkly embroidery",
    )
    assert out[6] == ""  # conflict_warning


def test_prompt_composer_compound_phrase_does_not_falsely_block_execution():
    """回帰テスト: 複合フレーズが誤って処理をブロックしないことを、ノード経由でも確認する。"""
    node = NODE_CLASS_MAPPINGS["ClothPromptComposer"]()
    preset_raw = cat.grouped_default_decoration("none")
    target_raw = f"generic | {mp.MODEL_PROFILES['generic'].label_ja}"
    out = node.compose(
        _mask(), decoration_preset=preset_raw, pattern="none", material="none",
        target_model=target_raw, output_language="en", subject_hint="dress",
        grow_px=0, feather_px=0.0, confirm_continue=False,
        free_text="a skirt with red and blue striped pattern",
    )
    assert out[6] == ""  # conflict_warning


def test_auto_node_raises_on_conflict_in_generative_mode():
    node = NODE_CLASS_MAPPINGS["ClothDecoratorAuto"]()
    preset_raw = cat.grouped_default_decoration("embroidery")
    target_raw = f"generic | {mp.MODEL_PROFILES['generic'].label_ja}"
    img = torch.rand(1, 32, 32, 3)
    with pytest.raises(ValueError, match="競合"):
        node.run(
            mode="generative_prompt", image=img, mask=_mask(), decoration_type="solid_color",
            decoration_preset=preset_raw, target_model=target_raw, color="red", opacity=1.0,
            feather_px=3.0, output_language="en", confirm_continue=False, free_text="blue",
        )


def test_auto_node_continues_when_confirmed():
    node = NODE_CLASS_MAPPINGS["ClothDecoratorAuto"]()
    preset_raw = cat.grouped_default_decoration("embroidery")
    target_raw = f"generic | {mp.MODEL_PROFILES['generic'].label_ja}"
    img = torch.rand(1, 32, 32, 3)
    out = node.run(
        mode="generative_prompt", image=img, mask=_mask(), decoration_type="solid_color",
        decoration_preset=preset_raw, target_model=target_raw, color="red", opacity=1.0,
        feather_px=3.0, output_language="en", confirm_continue=True, free_text="blue",
    )
    assert "red" in out[1]
    assert out[7] != ""  # conflict_warning


def test_auto_node_direct_paint_mode_unaffected_by_conflict_gate():
    """direct_paintモードは色の衝突検出（generative向け機能）の影響を受けない。"""
    node = NODE_CLASS_MAPPINGS["ClothDecoratorAuto"]()
    preset_raw = cat.grouped_default_decoration("embroidery")
    target_raw = f"generic | {mp.MODEL_PROFILES['generic'].label_ja}"
    img = torch.rand(1, 32, 32, 3)
    out = node.run(
        mode="direct_paint", image=img, mask=_mask(), decoration_type="solid_color",
        decoration_preset=preset_raw, target_model=target_raw, color="#ff0000", opacity=1.0,
        feather_px=3.0, confirm_continue=False, free_text="blue sparkles",
    )
    assert out[0].shape == img.shape
    assert out[7] == ""
