#!/usr/bin/env python3
"""
examples/wd14_tagger_server.py — WD14 Tagger を使った本番向けタガーサーバー例

🔍 Image Analyzer の http_tagger モード（README / docs/TAGGER_SERVER.md）が
期待するHTTP契約を実装した、実際に動作するタガーサーバーの実装例。
SmilingWolf 氏の WD14 (wd-v1-4 / wd-swinv2 等) ONNXタガーモデルを想定している。

事前準備:
  1. Hugging Face から WD14 タガーモデルを入手し、以下の2ファイルを
     同じディレクトリに置く（例: models/wd14/ 配下）:
       - model.onnx        （例: wd-v1-4-swinv2-tagger-v2 の model.onnx）
       - selected_tags.csv  （同モデル配布元の tag_name 一覧CSV）
     入手先の例: https://huggingface.co/SmilingWolf/wd-v1-4-swinv2-tagger-v2
     （本ファイルはモデルを同梱しない。ライセンス・配布条件は配布元に従うこと）
  2. 依存ライブラリをインストール:
       pip install -r examples/requirements-tagger.txt

起動:
    python3 examples/wd14_tagger_server.py \\
        --model-dir models/wd14 \\
        --port 8765

ComfyUI 側の 🔍 Image Analyzer ノードで:
    analysis_source = http_tagger
    tagger_url       = http://127.0.0.1:8765/tag
"""

from __future__ import annotations

import argparse
import base64
import csv
import io
from pathlib import Path

import numpy as np
import onnxruntime as ort
import uvicorn
from fastapi import FastAPI, HTTPException
from PIL import Image
from pydantic import BaseModel

app = FastAPI(title="WD14 Tagger Server (ClothDecorator-compatible)")

_session: ort.InferenceSession | None = None
_tag_names: list[str] = []
_rating_tag_indices: set[int] = set()
_input_size: int = 448


class TagRequest(BaseModel):
    image: str  # "data:image/png;base64,...."


class TagItem(BaseModel):
    tag: str
    score: float


class TagResponse(BaseModel):
    tags: list[TagItem]


def load_model(model_dir: Path) -> None:
    """model.onnx + selected_tags.csv をロードしてグローバル状態にセットする。"""
    global _session, _tag_names, _rating_tag_indices, _input_size

    model_path = model_dir / "model.onnx"
    tags_path = model_dir / "selected_tags.csv"
    if not model_path.exists() or not tags_path.exists():
        raise FileNotFoundError(
            f"model.onnx / selected_tags.csv が見つかりません: {model_dir}\n"
            "ファイル冒頭のコメントを参照してモデルを配置してください。"
        )

    _session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    _input_size = _session.get_inputs()[0].shape[1] or 448

    _tag_names = []
    _rating_tag_indices = set()
    with open(tags_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            _tag_names.append(row["name"])
            # category==9 は rating（general/sensitive/questionable/explicit）タグの慣習
            if row.get("category") == "9":
                _rating_tag_indices.add(i)

    print(f"[wd14_tagger_server] loaded {len(_tag_names)} tags, input_size={_input_size}")


def preprocess(pil_img: Image.Image, size: int) -> np.ndarray:
    """WD14系モデルの慣習: 正方形にパディングしてリサイズ、BGR、float32。"""
    img = pil_img.convert("RGB")
    w, h = img.size
    side = max(w, h)
    padded = Image.new("RGB", (side, side), (255, 255, 255))
    padded.paste(img, ((side - w) // 2, (side - h) // 2))
    resized = padded.resize((size, size), Image.LANCZOS)

    arr = np.asarray(resized, dtype=np.float32)
    arr = arr[:, :, ::-1]  # RGB -> BGR
    return arr[np.newaxis, :, :, :]


@app.post("/tag", response_model=TagResponse)
def tag_image(req: TagRequest, threshold: float = 0.35) -> TagResponse:
    if _session is None:
        raise HTTPException(status_code=503, detail="model not loaded")

    if not req.image.startswith("data:image"):
        raise HTTPException(status_code=400, detail="'image' must be a data URL")

    try:
        b64_data = req.image.split(",", 1)[1]
        pil_img = Image.open(io.BytesIO(base64.b64decode(b64_data)))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid image data: {e}") from e

    batch = preprocess(pil_img, _input_size)
    input_name = _session.get_inputs()[0].name
    output_name = _session.get_outputs()[0].name
    probs = _session.run([output_name], {input_name: batch})[0][0]

    tags = [
        TagItem(tag=_tag_names[i], score=float(probs[i]))
        for i in range(len(_tag_names))
        if i not in _rating_tag_indices and probs[i] >= threshold
    ]
    tags.sort(key=lambda t: t.score, reverse=True)
    return TagResponse(tags=tags)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=Path("models/wd14"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    load_model(args.model_dir)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
