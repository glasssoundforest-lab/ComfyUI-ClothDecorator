"""
nodes/tag_mapping.py — タガー出力タグ → 語彙辞書キー のマッピング

外部の WD14/Florence2 系タガー（HTTPサーバー経由、nodes/image_analyzer.py
から呼び出される）が返す英語タグ列を、nodes/vocabulary.py の
DECORATION_PRESETS / PATTERN_VOCAB / MATERIAL_VOCAB のキーへベストエフォートで
マッピングする。厳密な分類器ではなく、キーワード重なりに基づく単純な
スコアリングであることに注意（0件マッチなら空文字を返す＝無理に決め打ちしない）。

torch / ComfyUI に依存しない純粋関数のため、単体テスト可能。
"""

from __future__ import annotations

from . import vocabulary


def _normalize(s: str) -> str:
    return s.lower().replace("_", " ").strip()


def _best_match(tags_norm: list[str], vocab: dict) -> tuple[str, int]:
    best_key = ""
    best_score = 0
    for key, val in vocab.items():
        if key in ("none", "custom"):
            continue
        phrases = val if isinstance(val, list) else [val]
        # フレーズ数が多いキー（複数の言い換えを持つプリセット）が単純合計だと
        # 有利になりすぎるため、全フレーズ×全タグの中で最良の一致強度のみを採用する
        # （同義語の重複ヒットで加点され続けることを防ぐ）。
        key_score = 0
        for phrase in phrases:
            if not phrase:
                continue
            phrase_norm = phrase.lower()
            phrase_words = set(phrase_norm.split())
            for tag in tags_norm:
                if not tag:
                    continue
                if tag in phrase_norm or phrase_norm in tag:
                    key_score = max(key_score, 2)
                    continue
                tag_words = set(tag.split())
                key_score = max(key_score, len(tag_words & phrase_words))
        if key_score > best_score:
            best_score = key_score
            best_key = key
    return best_key, best_score


def map_tags_to_vocab(tags: list[str]) -> dict:
    """
    タガーが返した英語タグ列から、decoration_preset / pattern / material の
    最有力候補キーを推定する。マッチが無いカテゴリは空文字を返す。

    Args:
        tags: タグ文字列のリスト（例: ["red_dress", "lace_trim", "floral_print"]）

    Returns:
        {
          "decoration_preset": "lace_trim" | "",
          "pattern": "floral" | "",
          "material": "" ,
          "scores": {"decoration_preset": int, "pattern": int, "material": int},
        }
    """
    tags_norm = [_normalize(t) for t in tags if t and t.strip()]
    dec_key, dec_score = _best_match(tags_norm, vocabulary.DECORATION_PRESETS)
    pat_key, pat_score = _best_match(tags_norm, vocabulary.PATTERN_VOCAB)
    mat_key, mat_score = _best_match(tags_norm, vocabulary.MATERIAL_VOCAB)
    return {
        "decoration_preset": dec_key if dec_score > 0 else "",
        "pattern": pat_key if pat_score > 0 else "",
        "material": mat_key if mat_score > 0 else "",
        "scores": {
            "decoration_preset": dec_score,
            "pattern": pat_score,
            "material": mat_score,
        },
    }
