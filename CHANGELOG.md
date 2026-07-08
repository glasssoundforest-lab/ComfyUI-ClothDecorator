# CHANGELOG

## v0.7.2
- **画像でないもの・テキストでないデータが入力された場合の堅牢性を強化**:
  - **グレースケール(1ch)・RGBA(4ch)・チャンネル軸なしの2D画像を自動でRGBに
    正規化**するようにした（従来は shape mismatch で例外になっていた）。
    グレースケールは3chへ複製、RGBAはアルファを破棄。1/3/4以外の
    チャンネル数は「画像ではないデータの可能性」と明示するエラーに変更
  - `image`/`mask` に `None` が渡された場合、以前は
    `TypeError`/`IndexError`等の分かりにくい内部例外だったのを、
    「IMAGE/MASK型の入力が接続されているか確認してください」という
    明確なエラーメッセージに変更
  - `image`/`mask` に文字列・数値・dict等の完全に無関係なデータが
    渡された場合も同様に明確なエラーに変更（`nodes/node_base.py`）
  - `color`/`free_text`/`subject_hint`/`base_prompt` 等のSTRING系
    フィールドに数値・None・リスト等が渡されても
    `AttributeError: 'int' object has no attribute 'strip'` のような
    内部エラーで落ちず、安全な文字列変換またはベストエフォートでの
    処理継続、あるいは明確なエラーメッセージのいずれかになるよう
    `nodes/vocabulary.py`・`nodes/paint_ops.py` に型安全化を追加
- 新規テスト9件を `tests/test_robustness.py` に追加（全通過）。
  単体テスト177 → **186件**

## v0.7.1
- **異常入力（負値・空データ・NaN/Inf・極端に大きい値）に対する堅牢性を
  体系的に検証し、発見した複数のクラッシュ/ハングを修正**:
  - `mask_utils.grow_mask`/`shrink_mask`: 巨大な px（例: 100000）で
    OOM（プロセスキル）していた。PILの `MaxFilter`/`MinFilter` は
    カーネルサイズに対して極端に遅く、512x512画像でも px=100 程度で
    実質停止することが判明。maxの冪等性を利用し、3x3カーネルを px 回
    反復適用する方式に変更（結果は数学的に同一・大幅に高速・pxに対して線形）。
    あわせて上限値（300px）でクランプ
  - `mask_utils.feather_mask`: `feather_px=NaN` で **セグメンテーション
    フォルト**していた（PIL の GaussianBlur に NaN 半径を渡すと発生）。
    NaN/Inf/負値を安全に0（無処理）へ丸めるよう修正
  - `mask_utils.pad_bbox`: 大きな負のpadでbboxが反転（x0>x1）する
    バグを修正。反転しないことを保証するガードを追加
  - `paint_ops`: 範囲外RGB文字列（例: `"-10,-20,-30"`）で
    `OverflowError`していたのを 0-255 にクランプするよう修正。
    `hue_shift` の巨大な角度（1e15等）でも `OverflowError`していたのを
    正規化して修正。`brightness_contrast`/`apply_within_mask`のNaN/Inf
    引数によるundefined castも解消
  - `color_analysis.kmeans_colors`: クラスタ数kが画素数に近い巨大値の場合
    （例: `num_dominant_colors=1000000`）、距離行列の確保で**数十GB規模の
    MemoryError**が発生していた。kとiters双方に上限（16 / 50）を設定
  - `tag_mapping.map_tags_to_vocab`: 巨大なタグ列（10万件以上）で処理時間が
    数十秒に爆発していた。タグ数に上限（300件）を設定し、非文字列要素も
    安全に無視するよう修正
  - `nodes/node_base.py`: IMAGE/MASKテンソルにNaN/Infが混入していると
    uint8への未定義キャスト（RuntimeWarning）が発生していた。テンソル→
    numpy変換の境界で `np.nan_to_num` により安全な値へ丸めるよう修正
    （以降の全処理に波及しないようにする設計）
  - `paste_back.py`: 不正な `bbox_json`（範囲外・反転・欠損キー）に対して
    分かりにくい例外や不正な貼り戻しが起きていたのを、実画像サイズへの
    クランプと分かりやすいエラーメッセージで改善
  - 🔍 Image Analyzer の HTTP タガー応答: 1件でも不正な形式のタグ
    （score が文字列/NaN等）が含まれると応答全体を破棄していたのを、
    個々の不正エントリのみskipして有効なタグは活かすよう改善
- 新規テストスイート `tests/test_robustness.py`（38件）で上記すべてを
  回帰テストとしてカバー。単体テスト139 → **177件**（全通過）

## v0.7.0
- **全語彙辞書を200件規模まで拡充**（decoration_preset・pattern・material・
  伝統色・subject_hint のすべてを対象）:
  - decoration_preset: 82 → **200**（大項目を7→9に拡張。アクティブウェア・
    機能技法、季節・イベントモチーフを新設。刺繍/ビーズ/染色/織り/金具/
    仕上げ効果/テーマ装飾の各中項目も大幅増量）
  - pattern: 38 → **200**（幾何学柄・自然モチーフ柄・和柄・世界の織物柄に
    加え、アートスタイル柄・時代スタイル柄の大項目を新設）
  - material: 33 → **200**（天然繊維・和素材・化学繊維に加え、皮革・毛皮、
    世界の伝統素材、モダン・工業素材の大項目を新設）
  - 伝統色: 43 → **203**（日本の伝統色を色系統ごとに大幅増量。歴史的な
    色名を多数追加。hexコードは画像生成用途の実用的な参考値である旨を明記）
  - subject_hint: 42 → **233**（和装・洋装に加え、世界の民族衣装、
    スポーツ・ワークウェア、コスチューム・ファンタジー衣装の大項目を新設）
- **アーキテクチャ刷新: 語彙データを「単一の情報源」に集約**
  - 新設: `nodes/decoration_data.py` / `nodes/pattern_data.py` /
    `nodes/material_data.py` / `nodes/color_data.py` /
    `nodes/subject_data.py`（いずれも大項目・中項目でグループ化された
    生データを保持）
  - `nodes/vocabulary.py` のフラット辞書と `nodes/categories.py` の
    カテゴリ対応表は、どちらもこれら `*_data.py` から自動構築されるように
    変更（従来は2箇所を手動で同期する必要があり、分類漏れの実例もあった）
  - 新しい項目の追加は各 `*_data.py` への1件追記のみで完結し、語彙辞書と
    カテゴリ分類の両方に自動反映される
- 単体テスト131件は全てこの大規模拡充後も無変更で通過（既存の網羅性テストが
  分類漏れ・重複キーを検出できることも確認済み）

## v0.6.1
- **HTTPタガーサーバーの構築・運用ガイドを新設**（`docs/TAGGER_SERVER.md`）:
  通信プロトコル仕様、モックサーバーでの疎通確認手順、WD14 Taggerを使った
  本番向け実装例、自作タガーの実装ヒント、セキュリティ/パフォーマンス上の
  注意、トラブルシューティング表を記載
- 実際に動作するサーバー実装例を追加（`examples/`）:
  - `mock_tagger_server.py`: 依存追加不要（Pillowのみ）のダミータガー。
    画像の平均色からそれらしいタグを返す、接続確認・開発用
  - `wd14_tagger_server.py`: FastAPI + onnxruntime による本番向け
    WD14 Tagger実装例（前処理・推論・rating タグ除外・閾値フィルタを実装）
  - `requirements-tagger.txt`: サーバー実装例の依存関係
  - 両サーバーとも実際にHTTPリクエストを送って動作確認済み
    （wd14_tagger_server.py はダミーONNXモデルでの推論〜レスポンス生成まで検証）
- README にドキュメント/サンプルへのリンクを追加

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
