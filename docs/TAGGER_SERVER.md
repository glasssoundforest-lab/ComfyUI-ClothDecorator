# HTTPタガーサーバーの立て方・運用ガイド

🔍 **Cloth Decorator - Image Analyzer** の `analysis_source = http_tagger` は、
自前で用意したHTTPサーバー（WD14 Tagger や Florence2 などの画像タグ推定AI）
と連携し、マスク領域から「どんな服・柄・素材か」のタグを取得して
`decoration_preset` / `pattern` / `material` の候補を自動提案します。

本リポジトリはタガーモデルそのものは同梱していません（モデルのライセンス・
配布条件が個別に存在するため）。このドキュメントでは、通信仕様と、
実際に動かせるサーバー実装例（`examples/`）の使い方を説明します。

---

## 1. 通信プロトコル（必ずこの形式に従うこと）

`ClothDecorator` の `🔍 Image Analyzer` は、`tagger_url` に対して以下の
リクエストを送信します。

### リクエスト

```
POST {tagger_url}
Content-Type: application/json

{
  "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
}
```

- `image` はマスク領域（バウンディングボックス+パディング）を切り出した
  PNG画像の [data URL](https://developer.mozilla.org/ja/docs/Web/URI/Schemes/data)
  です。
- タイムアウトはノード側で15秒に設定されています（通信が遅い場合は
  サーバー側の推論を高速化するか、`examples/wd14_tagger_server.py` のような
  軽量モデルを使ってください）。

### レスポンス（期待する形式）

```json
{
  "tags": [
    {"tag": "lace_trim", "score": 0.87},
    {"tag": "floral_pattern", "score": 0.62},
    {"tag": "silk_fabric", "score": 0.41}
  ]
}
```

- `tag` は英語のタグ文字列（アンダースコア区切りでもスペース区切りでも可。
  `nodes/tag_mapping.py` 側で正規化して語彙とマッチングします）。
- `score` は 0.0〜1.0 の信頼度。`confidence_threshold` 未満のタグは
  ノード側で除外されます。`score` を省略した場合は 1.0 として扱われます
  （`{"tags": ["lace_trim", "floral_pattern"]}` のような単純な文字列配列も
  受け付けます）。
- HTTPステータスは `200` を返してください。エラー時に非200を返すと、
  ノード側は `color_only` の結果のみで処理を継続します（ワークフロー全体は
  止まりません）。

この契約さえ満たせば、WD14 Tagger 以外にも Florence2・独自の分類器・
CLIP ベースのタガーなど、どんな実装でも接続できます。

---

## 2. すぐ試す: モックサーバー（依存ライブラリ追加不要）

実際のAIモデルを用意する前に、まずノード側の接続・後段の処理
（`decoration_preset_override` 等への配線）が正しく動くかを確認したい場合は
`examples/mock_tagger_server.py` を使ってください。画像の平均色から
それらしいダミータグを返すだけの軽量サーバーで、Pillow 以外の追加
依存ライブラリは不要です（ClothDecorator本体の `requirements.txt` で足ります）。

```bash
python3 examples/mock_tagger_server.py --port 8765
```

ComfyUI 側の 🔍 Image Analyzer ノードで:

```
analysis_source = http_tagger
tagger_url       = http://127.0.0.1:8765/tag
```

これで接続・タグマッピング・`*_override` への配線までの一連の流れを
本物のモデル無しで確認できます。

---

## 3. 本番運用: WD14 Tagger サーバー実装例

`examples/wd14_tagger_server.py` は、[SmilingWolf 氏の WD14 タガー
モデル](https://huggingface.co/SmilingWolf)（ONNX形式）を使った、
実際に動作するサーバー実装例です（FastAPI + onnxruntime）。

### 3.1 モデルの入手

Hugging Face から以下の2ファイルをダウンロードし、同じディレクトリに置きます
（例: `models/wd14/`）。

- `model.onnx`
- `selected_tags.csv`

例: `wd-v1-4-swinv2-tagger-v2`、`wd-v1-4-moat-tagger-v2` など、
`SmilingWolf/wd-*-tagger-*` シリーズのリポジトリから入手できます。
**モデルのライセンス・利用条件は配布元のページに従ってください**
（本リポジトリはモデルを同梱・再配布しません）。

### 3.2 依存ライブラリのインストール

```bash
pip install -r examples/requirements-tagger.txt
```

### 3.3 起動

```bash
python3 examples/wd14_tagger_server.py --model-dir models/wd14 --port 8765
```

起動時に `loaded N tags, input_size=448` のようなログが出れば成功です。

### 3.4 ComfyUI 側の設定

```
analysis_source = http_tagger
tagger_url       = http://127.0.0.1:8765/tag
confidence_threshold = 0.35   # 必要に応じて調整
```

### 3.5 実装の要点（自作する場合の参考に）

- 前処理: 正方形にパディング（白背景）してから `input_size × input_size`
  （多くのWD14系モデルは448px）にリサイズし、RGB→BGRへ変換
- rating系タグ（general/sensitive/questionable/explicit）は
  `decoration_preset`/`pattern`/`material` の推定には無関係なので、
  レスポンスから除外することを推奨（`selected_tags.csv` の `category==9`）
- スコアは降順ソートして返すと、後段の閾値フィルタや目視確認がしやすい

---

## 4. 自前のタガーを実装する場合のヒント

- **Florence2 のような自然文キャプションモデルを使う場合**: キャプション文を
  そのまま1つの「タグ」として `{"tags": [{"tag": "<キャプション全文>", "score": 1.0}]}`
  のように返すよりも、キャプションから名詞句・形容詞を簡単に分かち書きして
  複数の短いタグに分割してから返す方が、`nodes/tag_mapping.py` の
  キーワード一致マッピングと相性が良くなります。
- **タグの命名**: `nodes/vocabulary.py` の英語プロンプト語（例:
  `"lace trim"`, `"floral pattern"`, `"silk fabric"`）に近い単語を含む
  タグほどマッチしやすくなります。迷ったら Danbooru/WD14 系の慣習
  （アンダースコア区切りの英語タグ）に寄せるのが無難です。
- **マッチしないタグは無視される設計です**: `nodes/tag_mapping.py` は
  0点マッチのカテゴリには空文字を返すため、無理に全カテゴリを埋めようと
  せず、自信のあるタグだけを高いスコアで返す実装で問題ありません。

---

## 5. 運用上の注意（セキュリティ・パフォーマンス）

- **ローカル/信頼できるネットワークでの利用を前提としています。**
  `examples/` のサーバーは認証機構を持たないため、インターネットに直接
  公開しないでください。リモートで使いたい場合は、リバースプロキシ側で
  Basic認証やIP制限、HTTPS終端を行うことを推奨します。
- **タイムアウト**: ノード側の待ち時間は15秒固定です。GPU推論でも
  この時間内に収まるモデル・バッチサイズを選んでください。
- **画像サイズ**: 送信される画像はマスク領域の切り出し（バウンディング
  ボックス+パディング16px）のみです。フル解像度の元画像全体は送信されません。
- **失敗時のフォールバック**: サーバーが応答しない/エラーを返す場合でも
  ワークフロー全体は止まらず、`color_only` の結果（色提案のみ）で
  処理が継続されます。`debug_json` 出力の `tagger_error` で原因を確認できます。
- **同時実行**: ComfyUI 側からのリクエストは基本的に逐次実行です。
  複数ワークフローを並行運用する場合は、タガーサーバー側で
  リクエストキューイング・ワーカー数の調整を検討してください。

---

## 6. トラブルシューティング

| 症状 | 確認ポイント |
|---|---|
| `debug_json` に `tagger_error` が出る | `tagger_url` が正しいか、サーバーが起動しているか、ファイアウォールでブロックされていないか |
| タグは返るが `suggested_*` が全て空 | `nodes/tag_mapping.py` とのキーワード一致が無いだけの可能性。タグの語彙が `vocabulary.py` の英語表現とかけ離れていないか確認 |
| レスポンスがJSONとしてパースできないとエラーになる | `Content-Type: application/json` を返しているか、レスポンスbodyが正しいJSON形式か |
| 推論が遅くタイムアウトする | モデルを軽量版に変更、GPU推論を有効化、画像サイズ・バッチを見直す |
| WD14サーバーで `model.onnx / selected_tags.csv が見つかりません` | `--model-dir` の指定パスに2ファイルが揃っているか確認 |

---

関連: [README.md](README.md) の「🔍 画像解析による装飾の自動提案」セクションも参照してください。
