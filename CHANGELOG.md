# CHANGELOG

## v0.6.0
- **画像解析による装飾の自動提案機能を新設**（従来の「語彙から選ぶ」方式に加え、
  「画像から読み取って提案する」経路を追加）:
  - 新規ノード 🔍 **Image Analyzer**（`nodes/image_analyzer.py`）
  - `color_only`: 軽量k-means（`nodes/color_analysis.py`、numpyのみ・外部依存
    なし）でマスク領域の代表色を抽出し、日本の伝統色/BASE_COLORSの中から
    最寄り色を提案（`suggested_color_en` / `suggested_color_ja` / 色プレビュー画像）
  - `http_tagger`: 自前のWD14/Florence2系タガーHTTPサーバーと連携し、
    返ってきたタグを `nodes/tag_mapping.py` のキーワード一致マッピングで
    decoration_preset/pattern/material候補へ変換。通信失敗時はcolor_only
    の結果のみで継続（処理を止めない）
  - 🧵 Prompt Composer / 🧩 Auto に `decoration_preset_override` /
    `pattern_override` / `material_override`（STRING、優先度: override >
    ドロップダウン）を追加し、Image Analyzer の提案をそのまま接続可能に
- **出力言語（英語/日本語）を選択できるように**:
  - `nodes/vocabulary.py`: `BASE_COLOR_HEX` / `BASE_COLOR_EN_TO_JA` /
    `SUBJECT_HINT_EN_TO_JA`（逆引き）/ `DEFAULT_NEGATIVE_TERMS_JA` を追加
  - `resolve_color_bilingual()` / `resolve_subject_bilingual()` を新設
  - `build_decoration_prompt(output_language="en"|"ja")`:
    "ja" 指定で prompt/merged_prompt/negative_prompt を日本語語彙
    （各キーの日本語ラベル・伝統色名・和訳ネガティブ語）で組み立てる
  - 🧵 Prompt Composer / 🧩 Auto に `output_language` ドロップダウンを追加
    （`model_prompt` にも反映。target_modelのquality/negativeタグ英語慣習と
    混在する点はREADMEに明記）
- 単体テスト 99 → 131件（全通過。色解析/タグマッピング/画像アナライザ
  ノード統合/出力言語の各テストを追加）

## v0.5.0
- **大項目・中項目カテゴリ分類を新設**（`nodes/categories.py`）:
  - decoration_preset: 大項目7（刺繍・ビーズ手芸／トリム・縁飾り／染色・
    プリント技法／織り・構造技法／金具・留め具／加工・仕上げ効果／
    テーマ・スタイル装飾）× 中項目2〜3の2階層で全82項目を分類
  - pattern（幾何学柄／自然モチーフ柄／和柄／世界の織物柄）・
    material（天然繊維／和素材／化学繊維／特殊質感）・
    伝統色（紅赤系統／藍青系統／緑系統／黄橙系統／紫系統／白黒鼠系統）・
    subject_hint（和装／洋装フォーマル／洋装カジュアル／アウター／小物）
    は大項目のみの1階層で分類
  - ComfyUIのドロップダウンに `"[大項目 > 中項目] key | 日本語ラベル"`
    形式でグルーピング表示。🧵 Prompt Composer / 🧩 Auto の
    decoration_preset/pattern/material に適用
  - 全キーがカテゴリ分類に漏れなく対応していることを検証するテストを追加
- 語彙辞書をさらに拡充（第5弾。手薄だったカテゴリを補強）:
  - decoration_preset: 72 → 82（感温変色染め・UV反応プリント・
    3Dプリントラティス・スマートファイバー回路／スパイクレザーハーネス・
    チェーンハーネス／ティアードブライダルレース・カテドラルトレーン
    レース／ウイピル刺繍・シュエシュエプリント・韓服ゴルム 等）
  - pattern: 36 → 38（ギンガム・シェブロン・ヘリンボーン・オジー柄）
  - material: 31 → 33（カシミヤ・アンゴラ・スパンデックス・PUレザー）
  - 伝統色: 38 → 43（桃色・鉄紺・柿色・若苗色・京紫）
  - subject_hint: 39 → 42（スーツ・ドレスシャツ・マント）
- 単体テスト 83 → 99件（全通過）

## v0.4.0
- 語彙辞書をさらに拡充（第3/4弾）:
  - decoration_preset: 48 → 72（フォーマル系: ポケットチーフ・カフスボタン・
    真鍮ボタン／ゴシック系: ゴシックレース・カメオブローチ・コウモリ翼
    アップリケ／ストリート系: グラフィティプリント・ダメージデニム・
    ワッペン／ブライダル: ベールレース／世界の染織技法: ザリ刺繍・
    ミラーワーク・ブロックプリント・イカット織り・ケンテ柄・
    フェアアイル編み・ダマスク織り・トワル柄・チャイナボタン／
    モダン: レーザーカット・LEDライトトリム 等）
  - pattern: 26 → 36（世界の伝統柄: ダマスク・トワル・イカット・ケンテ・
    フェアアイル・タータン・アラベスク・曼荼羅／和柄追加: 菱文様・雲文様）
  - material: 23 → 31（オーガンジー・チュール・ブロケード・ツイード・
    コーデュロイ・フェイクファー・ネオプレン・メッシュ生地）
  - 伝統色: 28 → 38（撫子色・若竹色・卯の花色・千歳緑・蒲公英色・瓶覗・
    灰桜・銀鼠・江戸紫・桔梗色）
  - subject_hint: 31 → 39（レインコート・ケープ・ボレロ・サロペット・
    喪服・花嫁衣装・軍服・白衣）
- 単体テスト 75 → 83件（全通過）。伝統色ローマ字の重複チェックテストを追加

## v0.3.0
- 語彙辞書をさらに拡充:
  - decoration_preset: 32 → 48（クリスタルビーズ・レースオーバーレイ・
    ベルベットトリム・キルティング・絞り染め・友禅染め・型染め 等）
  - pattern: 18 → 26（鱗文様・立涌・紗綾形・籠目・松皮菱・矢絣 等の和柄を追加）
  - material: 15 → 23（麻・苧麻・錦・羽二重・レーヨン・ポリエステル 等）
  - 伝統色: 18 → 28（瑠璃色・萌黄色・紅梅色・檜皮色・空色・烏羽色・蘇芳・
    芥子色・東雲色・常磐色 を追加）
  - subject_hint: 羽織・袴・甚平・ベスト・タキシード・チャイナドレス・
    エプロン を追加（24 → 31）
- **モデルに合わせたプロンプトの自動生成・拡張機能を新設**
  （`nodes/model_profiles.py`）:
  - SD1.5アニメ系 / Pony Diffusion V6 / Illustrious XL / NoobAI XL /
    SDXL Base / FLUX.1 / SD3-3.5 の7系統＋汎用のプロファイルを収録
  - タグ系モデル: quality/negativeタグの自動付与、アンダースコア表記への変換
  - 自然文系モデル: 装飾語彙を流暢な英語の説明文へ拡張
  - FLUX.1: negative promptを常に空文字で返す（アーキテクチャ上不要なため）
  - 🧵 Prompt Composer / 🧩 Auto に `target_model` 入力と
    `model_prompt` / `model_negative_prompt` 出力を追加
  - 新規ノード 🧠 **Model Prompt Adapter** — 任意のプロンプトを
    対象モデル系統向けに単体で変換・拡張可能
- 単体テスト 54 → 75件（全通過）

## v0.2.0
- 日本語対応: バイリンガルドロップダウン（`"english_key | 日本語ラベル"`）、
  日本の伝統色名（漢字/ローマ字）、日本語服飾用語の自動英語変換を追加
- decoration_preset: 18 → 32、pattern: 10 → 18（和柄8種追加）、
  material: 10 → 15（和素材5種追加）

## v0.1.0
- 初版: ✂️ Mask Prep / 🖼️ Region Extract / 🔀 Paste Back /
  🧵 Prompt Composer / 🎨 Direct Paint / 🧩 Auto の6ノード
