"""
ClothDecorator — ComfyUI カスタムノード エントリポイント

マスクで切り取った服の領域を、プロンプト（生成AI連携）または
直接画像処理（拡散モデル不要）で装飾するノード集。

インストール:
    cd ComfyUI/custom_nodes
    git clone <このリポジトリのURL> ClothDecorator
    pip install -r ClothDecorator/requirements.txt
    # ComfyUI 再起動 → "ClothDecorator" カテゴリにノードが出現
"""

from __future__ import annotations

import logging

logger = logging.getLogger("ClothDecorator")

try:
    # 通常経路: ComfyUI/pip がこのフォルダを真のパッケージとしてロードする場合
    from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS  # noqa: E402
except ImportError:
    # フォールバック: 相対importの親パッケージ文脈が無い状態で
    # このファイル単体がロードされた場合（一部のツールが __init__.py を
    # 直接importするケース。例: pytest の Package コレクタ）。
    import sys
    from pathlib import Path

    _here = str(Path(__file__).resolve().parent)
    if _here not in sys.path:
        sys.path.insert(0, _here)
    from nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS  # noqa: E402

WEB_DIRECTORY = None  # 現時点でカスタムJS/CSSは無し

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
