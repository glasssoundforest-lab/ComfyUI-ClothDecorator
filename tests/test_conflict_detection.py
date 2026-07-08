"""
tests/test_conflict_detection.py — タグ衝突検出・confirm_continue の動作検証

color / free_text / subject_hint の間で、同じカテゴリ（色・対象の服/部位）に
属する異なる語彙が複数指定された場合の検出ロジックと、
🧵 Prompt Composer / 🧩 Auto の confirm_continue ゲートの挙動をテストする。
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


def test_color_conflict_between_color_field_and_free_text():
    conflicts = vocabulary.detect_tag_conflicts(color="red", free_text="blue accents")
    assert len(conflicts) == 1
    assert conflicts[0].category == "color"
    assert set(conflicts[0].values) == {"red", "blue"}


def test_color_conflict_within_free_text_alone():
    conflicts = vocabulary.detect_tag_conflicts(free_text="red and blue stripes")
    assert any(c.category == "color" for c in conflicts)


def test_subject_conflict_between_subject_hint_and_free_text():
    conflicts = vocabulary.detect_tag_conflicts(subject_hint="dress", free_text="with a jacket on top")
    subject_conflicts = [c for c in conflicts if c.category == "subject"]
    assert len(subject_conflicts) == 1
    assert set(subject_conflicts[0].values) == {"dress", "jacket"}


def test_no_subject_conflict_for_single_garment_mentioned_twice():
    """同じ服が2回言及されても（同義語ではなく同一語）衝突扱いにしない。"""
    conflicts = vocabulary.detect_tag_conflicts(subject_hint="dress", free_text="a beautiful dress")
    assert not any(c.category == "subject" for c in conflicts)


def test_japanese_color_conflict_detection():
    conflicts = vocabulary.detect_tag_conflicts(color="藍色", free_text="朱色のアクセント")
    assert any(c.category == "color" and set(c.values) == {"藍色", "朱色"} for c in conflicts)


def test_format_conflict_message_empty():
    assert vocabulary.format_conflict_message([]) == ""


def test_format_conflict_message_joins_multiple():
    conflicts = vocabulary.detect_tag_conflicts(color="red", free_text="blue, with a jacket", subject_hint="dress")
    msg = vocabulary.format_conflict_message(conflicts)
    assert "色" in msg
    assert "部位" in msg


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
            color="red", free_text="blue accents",
        )


def test_prompt_composer_continues_when_confirmed():
    node = NODE_CLASS_MAPPINGS["ClothPromptComposer"]()
    preset_raw = cat.grouped_default_decoration("none")
    target_raw = f"generic | {mp.MODEL_PROFILES['generic'].label_ja}"
    out = node.compose(
        _mask(), decoration_preset=preset_raw, pattern="none", material="none",
        target_model=target_raw, output_language="en", subject_hint="dress",
        grow_px=0, feather_px=0.0, confirm_continue=True,
        color="red", free_text="blue accents",
    )
    prompt, neg, merged, model_prompt, model_neg, prep_mask, conflict_warning, dbg = out
    assert "red" in prompt and "blue accents" in prompt
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


def test_auto_node_raises_on_conflict_in_generative_mode():
    node = NODE_CLASS_MAPPINGS["ClothDecoratorAuto"]()
    preset_raw = cat.grouped_default_decoration("embroidery")
    target_raw = f"generic | {mp.MODEL_PROFILES['generic'].label_ja}"
    img = torch.rand(1, 32, 32, 3)
    with pytest.raises(ValueError, match="競合"):
        node.run(
            mode="generative_prompt", image=img, mask=_mask(), decoration_type="solid_color",
            decoration_preset=preset_raw, target_model=target_raw, color="red", opacity=1.0,
            feather_px=3.0, output_language="en", confirm_continue=False, free_text="blue sparkles",
        )


def test_auto_node_continues_when_confirmed():
    node = NODE_CLASS_MAPPINGS["ClothDecoratorAuto"]()
    preset_raw = cat.grouped_default_decoration("embroidery")
    target_raw = f"generic | {mp.MODEL_PROFILES['generic'].label_ja}"
    img = torch.rand(1, 32, 32, 3)
    out = node.run(
        mode="generative_prompt", image=img, mask=_mask(), decoration_type="solid_color",
        decoration_preset=preset_raw, target_model=target_raw, color="red", opacity=1.0,
        feather_px=3.0, output_language="en", confirm_continue=True, free_text="blue sparkles",
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
