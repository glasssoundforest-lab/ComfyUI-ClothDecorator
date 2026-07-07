"""
nodes/__init__.py — ClothDecorator ノード登録

個別ノードのロード失敗が他ノードに波及しないよう、_safe() で
1つずつ import する（Face-Prompt-Studio と同じ方式）。
"""

from __future__ import annotations

import logging

logger = logging.getLogger("ClothDecorator.nodes")


def _safe(mod_name: str, cls_name: str):
    try:
        from importlib import import_module

        mod = import_module(f".{mod_name}", package=__name__)
        return getattr(mod, cls_name)
    except Exception as e:
        logger.warning("ClothDecorator: ノード %s をスキップ: %s", cls_name, e)
        return None


ClothMaskPrepNode = _safe("mask_prep", "ClothMaskPrepNode")
ClothRegionExtractNode = _safe("region_extract", "ClothRegionExtractNode")
ClothPasteBackNode = _safe("paste_back", "ClothPasteBackNode")
ClothPromptComposerNode = _safe("prompt_composer", "ClothPromptComposerNode")
ClothDirectPaintNode = _safe("direct_paint", "ClothDirectPaintNode")
ClothDecoratorAutoNode = _safe("auto_mode", "ClothDecoratorAutoNode")

_all = {
    "ClothMaskPrep": ClothMaskPrepNode,
    "ClothRegionExtract": ClothRegionExtractNode,
    "ClothPasteBack": ClothPasteBackNode,
    "ClothPromptComposer": ClothPromptComposerNode,
    "ClothDirectPaint": ClothDirectPaintNode,
    "ClothDecoratorAuto": ClothDecoratorAutoNode,
}

NODE_CLASS_MAPPINGS = {k: v for k, v in _all.items() if v is not None}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ClothMaskPrep": "✂️ Cloth Decorator - Mask Prep",
    "ClothRegionExtract": "🖼️ Cloth Decorator - Region Extract",
    "ClothPasteBack": "🔀 Cloth Decorator - Paste Back",
    "ClothPromptComposer": "🧵 Cloth Decorator - Prompt Composer",
    "ClothDirectPaint": "🎨 Cloth Decorator - Direct Paint",
    "ClothDecoratorAuto": "🧩 Cloth Decorator - Auto",
}
NODE_DISPLAY_NAME_MAPPINGS = {
    k: v for k, v in NODE_DISPLAY_NAME_MAPPINGS.items() if k in NODE_CLASS_MAPPINGS
}

logger.info("ClothDecorator: %d ノード登録完了", len(NODE_CLASS_MAPPINGS))

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
