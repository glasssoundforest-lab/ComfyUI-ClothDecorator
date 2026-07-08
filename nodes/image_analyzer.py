"""
nodes/image_analyzer.py
ノード: 🔍 Cloth Decorator - Image Analyzer

マスク領域の画像を解析し、装飾内容の初期値を自動提案する。
これまでは「ユーザーが語彙から選んでプロンプトを組み立てる」だけだったが、
このノードにより「画像から読み取って提案する」経路が加わる。

analysis_source:
  color_only   — マスク領域の代表色を軽量k-meansで抽出し、語彙上の最寄り色
                （日本の伝統色 / BASE_COLORS）とマッチングする。
                外部通信・追加モデル不要（常に使える）。
  http_tagger  — マスク領域を切り出し、ユーザーが指定した tagger_url
                （WD14/Florence2等のタグ推定を行うHTTPサーバー）に送信し、
                返ってきたタグを decoration_preset/pattern/material の
                語彙キーへベストエフォートでマッピングする。
                tagger_url は各自で用意する必要がある（本リポジトリは
                サーバー自体は同梱しない）。プロトコルは README を参照。
                通信に失敗した場合は color_only の結果のみで続行する。

出力の suggested_* は STRING のため、🧵 Prompt Composer / 🧩 Auto の
*_override 入力（color はそのまま、decoration_preset/pattern/material は
override 系）に直接ワイヤーできる。
"""

from __future__ import annotations

import json
import math
import urllib.error
import urllib.request
from typing import Any

from . import color_analysis, tag_mapping, vocabulary
from .node_base import ClothDecoratorNodeBase, mask_to_numpy, numpy_to_tensor, tensor_to_numpy_uint8


class ClothImageAnalyzerNode(ClothDecoratorNodeBase):
    """マスク領域の画像を解析し、色・装飾候補を自動提案する。"""

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "IMAGE", "STRING")
    RETURN_NAMES = (
        "suggested_color_en",
        "suggested_color_ja",
        "suggested_decoration_preset",
        "suggested_pattern",
        "suggested_material",
        "color_preview",
        "debug_json",
    )
    FUNCTION = "analyze"
    CATEGORY = "ClothDecorator"

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "image": ("IMAGE",),
                "mask": ("MASK", {"tooltip": "解析する領域（服の部分）のマスク"}),
                "analysis_source": (
                    ["color_only", "http_tagger"],
                    {
                        "default": "color_only",
                        "tooltip": (
                            "color_only: マスク領域の代表色を抽出し語彙上の最寄り色を提案"
                            "（外部通信不要）。\n"
                            "http_tagger: tagger_url で指定したHTTPタガーにも問い合わせ、"
                            "装飾/柄/素材の候補も提案（要: 自前のタガーサーバー）。"
                        ),
                    },
                ),
                "num_dominant_colors": (
                    "INT",
                    {"default": 3, "min": 1, "max": 8, "tooltip": "抽出する代表色の数"},
                ),
            },
            "optional": {
                "tagger_url": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": (
                            "http_tagger モードで使用するHTTPエンドポイント。"
                            "POST {\"image\": \"data:image/png;base64,...\"} を受け取り、"
                            "{\"tags\": [{\"tag\": \"...\", \"score\": 0.9}, ...]} を返す"
                            "サーバーを自前で用意する（README参照）。"
                        ),
                    },
                ),
                "confidence_threshold": (
                    "FLOAT",
                    {"default": 0.35, "min": 0.0, "max": 1.0, "step": 0.05},
                ),
            },
        }

    def analyze(
        self,
        image: Any,
        mask: Any,
        analysis_source: str,
        num_dominant_colors: int,
        tagger_url: str = "",
        confidence_threshold: float = 0.35,
    ) -> tuple[str, str, str, str, str, Any, str]:
        img_np = tensor_to_numpy_uint8(image)
        mask_np = mask_to_numpy(mask)

        color_result = color_analysis.analyze_masked_region(
            img_np, mask_np, num_colors=num_dominant_colors
        )
        best = color_result.get("best_match")
        suggested_color_en = best["name_en"] if best else ""
        suggested_color_ja = best["name_ja"] if best else ""

        debug: dict[str, Any] = {
            "analysis_source": analysis_source,
            "color_analysis": color_result,
        }

        suggested_decoration_preset = ""
        suggested_pattern = ""
        suggested_material = ""

        if analysis_source == "http_tagger":
            if not tagger_url.strip():
                debug["tagger_error"] = "tagger_url が指定されていません。color_only の結果のみ返します。"
            else:
                try:
                    tags = self._call_http_tagger(
                        img_np, mask_np, tagger_url.strip(), confidence_threshold
                    )
                    debug["tagger_tags"] = tags
                    mapping = tag_mapping.map_tags_to_vocab(tags)
                    suggested_decoration_preset = mapping["decoration_preset"]
                    suggested_pattern = mapping["pattern"]
                    suggested_material = mapping["material"]
                    debug["tag_mapping"] = mapping
                except Exception as e:  # noqa: BLE001 — 外部通信の失敗は致命的にせずフォールバック
                    debug["tagger_error"] = f"{type(e).__name__}: {e}"

        preview = self._build_color_preview(color_result.get("dominant_colors", []))

        return (
            suggested_color_en,
            suggested_color_ja,
            suggested_decoration_preset,
            suggested_pattern,
            suggested_material,
            numpy_to_tensor(preview),
            json.dumps(debug, ensure_ascii=False, indent=2),
        )

    # ── HTTP タガー呼び出し ─────────────────────────────────────────

    @staticmethod
    def _call_http_tagger(
        img_np: Any, mask_np: Any, tagger_url: str, threshold: float, timeout: float = 15.0
    ) -> list[str]:
        """
        マスク領域を切り出して tagger_url にPOSTし、タグ文字列リストを返す。
        期待するレスポンス形式: {"tags": [{"tag": "...", "score": 0.9}, ...]}
        """
        import base64
        import io

        import numpy as np
        from PIL import Image

        from . import mask_utils

        bbox = mask_utils.mask_bbox(mask_np)
        if bbox is not None:
            bbox = mask_utils.pad_bbox(bbox, 16, img_np.shape[1], img_np.shape[0])
            crop = mask_utils.crop_to_bbox(img_np, bbox)
        else:
            crop = img_np

        pil_img = Image.fromarray(crop.astype(np.uint8))
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        data_url = f"data:image/png;base64,{b64}"

        payload = json.dumps({"image": data_url}).encode("utf-8")
        req = urllib.request.Request(
            tagger_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = json.loads(resp.read().decode("utf-8"))

        tags_field = body.get("tags", [])
        if not isinstance(tags_field, list):
            tags_field = []

        tags: list[str] = []
        for t in tags_field[:500]:  # 応答が異常に長い場合の性能保護（実用上十分な上限）
            try:
                if isinstance(t, dict):
                    score = float(t.get("score", 1.0))
                    if not math.isfinite(score) or score < threshold:
                        continue
                    tag_str = str(t.get("tag", "")).strip()
                else:
                    tag_str = str(t).strip()
            except (TypeError, ValueError):
                # 個々のタグエントリが壊れていても、他の正常なタグは活かす
                continue
            if tag_str:
                tags.append(tag_str)
        return tags

    # ── 色プレビュー画像生成 ─────────────────────────────────────────

    @staticmethod
    def _build_color_preview(dominant_colors: list[dict], width: int = 256, height: int = 64):
        import numpy as np

        if not dominant_colors:
            return np.zeros((height, width, 3), dtype="uint8")

        canvas = np.zeros((height, width, 3), dtype="uint8")
        x = 0
        total_weight = sum(c.get("weight", 0) for c in dominant_colors) or 1.0
        for c in dominant_colors:
            hex_color = c.get("hex", "#000000").lstrip("#")
            rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
            w = int(round(width * (c.get("weight", 0) / total_weight)))
            w = max(1, w)
            end = min(width, x + w)
            if end > x:
                canvas[:, x:end] = rgb
            x = end
            if x >= width:
                break
        return canvas
