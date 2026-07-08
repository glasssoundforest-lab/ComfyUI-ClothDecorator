#!/usr/bin/env python3
"""
examples/mock_tagger_server.py — 依存ライブラリ不要のモックタガーサーバー

🔍 Image Analyzer の http_tagger モードとの疎通確認・開発用。
実際のAIタガー（WD14/Florence2等）は使わず、送られてきた画像の平均色から
それっぽいタグを返すだけの簡易サーバー。ClothDecoratorが期待するHTTPの
リクエスト/レスポンス形式（README / docs/TAGGER_SERVER.md 参照）を
そのまま実装しているので、本番のタガーサーバーを用意する前に
「ノード側の接続や後段の処理が正しく動くか」を確認するのに使える。

起動:
    python3 examples/mock_tagger_server.py --port 8765

ComfyUI 側の 🔍 Image Analyzer ノードで:
    analysis_source = http_tagger
    tagger_url       = http://127.0.0.1:8765/tag

依存: Pillow のみ（ClothDecorator 本体の requirements.txt に既に含まれる）
"""

from __future__ import annotations

import argparse
import base64
import io
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from PIL import Image

try:
    import numpy as np
except ImportError:  # numpy が無い場合の最小フォールバック
    np = None

# 平均色に応じて返すダミータグ（あくまで疎通確認用。精度は無い）
_DEMO_TAG_RULES: list[tuple[str, tuple[int, int, int], list[str]]] = [
    ("red_dominant", (200, 60, 60), ["red_clothing", "embroidery", "floral_pattern"]),
    ("blue_dominant", (60, 90, 200), ["blue_clothing", "indigo_dye", "denim_fabric"]),
    ("green_dominant", (60, 160, 90), ["green_clothing", "leaf_pattern", "cotton_fabric"]),
    ("dark_dominant", (40, 40, 40), ["black_clothing", "gothic_lace", "leather_texture"]),
    ("light_dominant", (220, 220, 220), ["white_clothing", "lace_trim", "silk_fabric"]),
]


def _guess_tags(avg_rgb: tuple[float, float, float]) -> list[dict]:
    best_name, best_dist, best_tags = None, float("inf"), []
    for name, rgb, tags in _DEMO_TAG_RULES:
        dist = sum((a - b) ** 2 for a, b in zip(avg_rgb, rgb)) ** 0.5
        if dist < best_dist:
            best_dist, best_name, best_tags = dist, name, tags
    return [{"tag": t, "score": round(0.9 - i * 0.15, 2)} for i, t in enumerate(best_tags)]


class MockTaggerHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 (http.server の慣習に合わせる)
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            data_url = body.get("image", "")
            if not data_url.startswith("data:image"):
                raise ValueError("'image' が data URL 形式ではありません")

            b64_data = data_url.split(",", 1)[1]
            img = Image.open(io.BytesIO(base64.b64decode(b64_data))).convert("RGB")
            if np is not None:
                avg_rgb = tuple(np.array(img).reshape(-1, 3).mean(axis=0).tolist())
            else:
                pixels = list(img.getdata())
                avg_rgb = tuple(sum(c) / len(pixels) for c in zip(*pixels))

            tags = _guess_tags(avg_rgb)
            response = {"tags": tags}
            status = 200
        except Exception as e:  # noqa: BLE001
            response = {"error": f"{type(e).__name__}: {e}"}
            status = 400

        payload = json.dumps(response).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args) -> None:  # noqa: A002
        print(f"[mock_tagger_server] {self.address_string()} - {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), MockTaggerHandler)
    print(f"Mock tagger server listening on http://{args.host}:{args.port}/")
    print("POST an image here to get demo tags. Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
