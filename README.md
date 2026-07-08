# ClothDecorator

マスクで切り取った服の領域を、**プロンプト経由（生成AI連携）** または
**直接画像処理（拡散モデル不要）** で装飾する ComfyUI カスタムノード集です。

[Face Prompt Studio](https://github.com/glasssoundforest-lab/Face-Prompt-Studio)
の設計思想・実装パターンを参考にしていますが、独立した新規リポジトリです。

## 特徴

- 標準 ComfyUI の `MASK` 型を入力に取るため、SAM やクリック選択など
  既存のセグメンテーションノードとそのまま組み合わせられます。
- 2つの装飾方式に対応:
  - **🧵 Prompt Composer**（生成AI連携）: 装飾内容をプロンプト化し、
    `VAE Encode (for Inpainting)` / `SetLatentNoiseMask` / `KSampler` などの
    標準インペイント系ノードにそのまま接続できる `prompt` / `negative_prompt` /
    `prepared_mask` を出力します。実際のピクセル生成はしません。
  - **🎨 Direct Paint**（直接画像処理）: 拡散モデルを使わず、PIL/numpy で
    単色塗り・グラデーション・柄タイリング・テクスチャ合成・明るさ/コントラスト・
    色相シフトをマスク領域に直接適用します。軽量・決定的・GPU不要。
- 🧩 **Auto** ノードで、上記2方式をワークフローを組み替えずに切り替え可能。
- 🖼️ **Region Extract** / 🔀 **Paste Back** で、マスクのbbox（+パディング）
  だけを切り出して処理し、フェザー付きで元画像へ自然に貼り戻せます。
- **モデルに合わせたプロンプトの自動生成・拡張**: `target_model` を選択すると、
  同じ装飾内容でも SD1.5アニメ系 / Pony / Illustrious / NoobAI / SDXL /
  FLUX.1 / SD3 それぞれの慣習（タグ書式・quality/negativeタグ・自然文への
  拡張・FLUXのネガティブ非対応など）に合わせた `model_prompt` /
  `model_negative_prompt` を自動生成します（🧵 Prompt Composer / 🧩 Auto /
  🧠 Model Prompt Adapter）。詳細は `nodes/model_profiles.py` を参照。
- コアロジック（マスク処理・装飾語彙・画素処理・モデル適応ロジック）は
  torch 非依存の純粋関数として分離されており、`pytest` で単体テスト可能です
  （`tests/`）。
- **🔍 Image Analyzer**: マスク領域の画像を解析して装飾内容を自動提案します。
  - `color_only`（常時利用可・外部通信不要）: 軽量k-meansでマスク領域の
    代表色を抽出し、日本の伝統色/BASE_COLORSの中から最も近い色を提案
  - `http_tagger`（任意）: 自前で用意したWD14/Florence2系タガーHTTPサーバー
    にマスク領域を送り、返ってきたタグから装飾/柄/素材の候補も提案
  - 提案結果は 🧵 Prompt Composer / 🧩 Auto の `color` や `*_override`
    入力にそのまま接続できます（ユーザーが選ぶ方式と画像解析方式を併用可能）
- **出力言語の選択（英語/日本語）**: 🧵 Prompt Composer / 🧩 Auto の
  `output_language` で `prompt` / `merged_prompt` / `model_prompt` /
  `negative_prompt` を英語・日本語どちらで組み立てるか選べます
  （`free_text` / `base_prompt` はユーザーの生入力のため自動翻訳されません）。
- **異常入力に対する堅牢性**: 負値・空データ・NaN/Inf・極端に大きい値
  （巨大なpx指定やクラスタ数など）が渡されてもクラッシュ・ハング・
  未定義動作が起きないよう、`tests/test_robustness.py` で継続的に検証
  しています。詳細は CHANGELOG の v0.7.1 を参照。
- **タグの統合（順不同での重複除去）**: `color` / `decoration_preset` /
  `pattern` / `material` / `free_text` から集められた全タグは、
  大文字小文字・前後や連続する空白の違いを無視した上で、**入力順序に
  関係なく完全一致する重複タグを1つに統合**します。`free_text` に
  `"dress, jacket, dress"` のようにカンマ区切りで複数タグを書いた場合も、
  個々のタグへ分割してから重複除去されます（`base_prompt` とのマージ時も
  同様）。ただし "dress" と "gown" のように**綴りが異なる同義語・
  似た意味のタグを意味的に1つへ統合する機能ではありません**（日本語の
  対象語 `subject_hint` 1件を選ぶ場合のみ、辞書上の同義語が英訳段階で
  統一されます）。
- **タグの衝突検出と確認ゲート**: `color` / `free_text` / `subject_hint`
  の間で、**同じカテゴリ（色・対象の服/部位）に属する異なるタグが
  複数指定されている**場合（例: `color="red"` なのに `free_text` にも
  `"blue"`、`subject_hint="dress"` なのに `free_text` にも `"jacket"`
  と書かれている等）、🧵 Prompt Composer / 🧩 Auto（`generative_prompt`
  モード）は既定（`confirm_continue=OFF`）では**処理を中断してエラーを
  表示**します（ComfyUI上でノードが赤くハイライトされ、競合内容が
  メッセージに表示されます）。内容を確認した上で意図通りであれば
  `confirm_continue` を ON にして再実行すると、そのまま両方のタグを
  含めて続行します。競合の有無・詳細は `conflict_warning` 出力と
  `debug_json` でも確認できます。
- **カテゴリ別ブロック整形（`group_by_category`）**: 🧵 Prompt Composer /
  🧩 Auto で `group_by_category` を ON にすると、`color` /
  `decoration_preset` / `pattern` / `material` / `free_text` から
  集めたタグを、**色→装飾技法→柄→素材→その他 の順でカテゴリごとの
  ブロックにまとめて**並べ替えます（各カテゴリ内の相対順序は保持）。
  `free_text` に色・装飾・柄などのタグが順不同・混在で書かれていても、
  出力プロンプトでは同じカテゴリのタグが隣接するように整形されます。
  既定は OFF（従来通り、入力順を保ったまま出力）。
  ```
  free_text = "blue, lace trim, floral pattern, gold, silk fabric, sparkly"（color="red"）
  group_by_category=False → "red, ..., blue, lace trim, floral pattern, gold, silk fabric, sparkly"（混在）
  group_by_category=True  → "red, blue, gold, ..., lace trim, floral pattern, silk fabric, sparkly"（色→装飾→柄→素材の順にブロック化）
  ```

## インストール

```bash
cd ComfyUI/custom_nodes
git clone <このリポジトリのURL> ClothDecorator
pip install -r ClothDecorator/requirements.txt
# ComfyUI 再起動 → "ClothDecorator" カテゴリにノードが出現
```

torch は ComfyUI 本体が既に依存として同梱しているため追加インストール不要です。

## ノード一覧

| ノード | 表示名 | 役割 |
|---|---|---|
| `ClothMaskPrep`      | ✂️ Cloth Decorator - Mask Prep      | MASKの膨張/収縮/ぼかし/反転/合成 |
| `ClothRegionExtract` | 🖼️ Cloth Decorator - Region Extract | マスクのbboxで画像/マスクを切り出す |
| `ClothPasteBack`     | 🔀 Cloth Decorator - Paste Back     | 加工済みパッチを元画像へフェザー合成で貼り戻す |
| `ClothPromptComposer`| 🧵 Cloth Decorator - Prompt Composer| 装飾プロンプト＋準備済みマスクを生成（生成AI連携用） |
| `ClothDirectPaint`   | 🎨 Cloth Decorator - Direct Paint   | マスク領域に直接ピクセル加工を適用 |
| `ClothDecoratorAuto` | 🧩 Cloth Decorator - Auto           | 上記2方式をmodeで切り替える統合ノード |
| `ClothPromptModelAdapter` | 🧠 Cloth Decorator - Model Prompt Adapter | 任意のプロンプトを対象モデル系統向けに変換・拡張 |
| `ClothImageAnalyzer` | 🔍 Cloth Decorator - Image Analyzer | マスク領域の画像を解析し色/装飾候補を自動提案 |

## ワークフロー例

### A. 生成AI連携（インペイントで装飾）

```
[LoadImage] ──┬─ image ─────────────────────────────────────────────┐
              │                                                       │
[SAM/クリック選択] ─ mask ─→ [✂️ Mask Prep] ─→ [🧵 Prompt Composer] ─┤
                                                  │  │                │
                                        prompt ───┘  └─ prepared_mask │
                                          │                │          │
                                 [CLIP Text Encode]  [VAE Encode (for Inpainting)]
                                          │                │          │
                                          └──────┬─────────┘          │
                                            [KSampler] ←───────────────┘
                                                  │
                                            [VAE Decode] → [SaveImage]
```

### B. 直接画像処理（拡散モデル不要・高速プレビュー）

```
[LoadImage] ── image ─┐
                        ├─→ [🖼️ Region Extract] ─→ [🎨 Direct Paint] ─→ [🔀 Paste Back] → [SaveImage]
[SAM/クリック選択] mask ┘         │  │  │                                    ↑
                          cropped_image cropped_mask original_image ────────┘
                                              │
                                        bbox_json ──────────────────────────→ (Paste Back へ)
```

Region Extract を挟まず、`LoadImage` の image と mask を直接
`🎨 Direct Paint` に接続して画像全体に対して処理することも可能です
（服の領域が画像に対して大きい場合など）。

### C. その場で方式を切り替えたい場合

```
[LoadImage] ── image ─┐
                        ├─→ [🧩 Auto (mode=direct_paint / generative_prompt)]
[SAM/クリック選択] mask ┘
```

## 🔍 画像解析による装飾の自動提案

これまでの `decoration_preset` 等はユーザーが語彙から選ぶ方式でしたが、
🔍 Image Analyzer を挟むと「画像から読み取って提案する」経路を追加できます。

### D. 画像解析→提案→プロンプト作成

```
[LoadImage] ── image ─┐
                        ├─→ [🔍 Image Analyzer] ─┬─ suggested_color_ja ──→ [🧵 Prompt Composer] color
[SAM/クリック選択] mask ┘   analysis_source:      ├─ suggested_decoration_preset → decoration_preset_override
                            color_only / http_tagger ├─ suggested_pattern → pattern_override
                                                     └─ suggested_material → material_override
```

- **`color_only`**（既定・外部通信不要）: マスク領域の画素を軽量k-meansで
  クラスタリングし、代表色を抽出。日本の伝統色（`TRADITIONAL_COLORS_JA`）と
  `BASE_COLORS` の中から最も近い色を `suggested_color_en` /
  `suggested_color_ja` として提案します（色プレビュー画像 `color_preview`
  も出力）。
- **`http_tagger`**（任意）: 自前で用意した WD14/Florence2 系タガーの
  HTTPサーバーに `tagger_url` でマスク領域の切り出し画像を送信し、
  返ってきたタグをキーワード一致で `decoration_preset` / `pattern` /
  `material` の候補にマッピングします（`nodes/tag_mapping.py`）。
  通信に失敗した場合は `color_only` の結果のみで続行します（処理は止まりません）。

  **HTTPタガーの通信プロトコル**（自前でサーバーを用意する場合）:
  ```
  POST {tagger_url}
  Request  body: {"image": "data:image/png;base64,...."}
  Response body: {"tags": [{"tag": "lace_trim", "score": 0.87}, ...]}
  ```

  サーバーの立て方・運用方法の詳細（依存ライブラリ不要のモックサーバー、
  WD14 Taggerを使った本番向け実装例、セキュリティ・トラブルシューティング等）は
  **[docs/TAGGER_SERVER.md](docs/TAGGER_SERVER.md)** を参照してください。
  すぐ試せる実装例は `examples/mock_tagger_server.py`（依存追加無し）と
  `examples/wd14_tagger_server.py`（本番向け）にあります。

`suggested_*` の出力は STRING のため、🧵 Prompt Composer / 🧩 Auto の
`decoration_preset_override` / `pattern_override` / `material_override`
（STRING、指定時はドロップダウン選択より優先）や `color`（STRING）に
そのまま接続できます。ドロップダウンでの手動選択と画像解析の自動提案は
併用可能です（override を空のままにすればドロップダウン選択が使われます）。

## 出力言語（英語・日本語）の選択

🧵 Prompt Composer / 🧩 Auto に `output_language`（`en` / `ja`）があります。
`ja` を選ぶと `prompt` / `merged_prompt` / `model_prompt` /
`negative_prompt` を日本語語彙で組み立てます（各キーの日本語ラベル・
伝統色名・和訳ネガティブ語を使用）。`free_text` / `base_prompt` は
ユーザーの生入力のため自動翻訳されません。

```python
# 例: decoration_preset=embroidery, pattern=floral, material=silk,
#     color=red, subject_hint=dress
output_language="en" → "dress, red, intricate embroidery, embroidered pattern, floral pattern, silk fabric"
output_language="ja" → "ワンピース, 赤, 刺繍, 花柄, シルク"
```

なお `target_model` によるタグ整形（quality/negativeタグの付与や
アンダースコア化）は英語圏モデルの学習慣習を前提にしているため、
`output_language="ja"` と組み合わせた場合の `model_prompt` は
「クオリティタグ等は英語、装飾語は日本語」が混在する形になります
（実際の生成品質は使用モデル依存・未検証の実験的機能です）。

## 大項目・中項目カテゴリ分類

`nodes/categories.py` に、各語彙辞書のキーを大項目（major）・中項目（mid）で
分類する対応表を定義しています。ComfyUI のドロップダウンには
`"[大項目 > 中項目] english_key | 日本語ラベル"` の形式でグルーピング表示され、
項目数が多くても目的の装飾技法を探しやすくなっています。

- **decoration_preset**（200種）: 大項目8 × 中項目2〜3の2階層分類
- **pattern**（200種）/ **material**（200種）/ 伝統色（203種）/ **subject_hint**（233種）:
  大項目のみの1階層分類

### decoration_preset の大項目・中項目一覧

| 大項目 | 中項目 |
|---|---|
| 刺繍・ビーズ手芸 | 刺繍技法 / ビーズ・宝飾 / アップリケ・パッチ |
| トリム・縁飾り | レース・リボン / フリンジ・タッセル・羽根 / パイピング・ブロケード |
| 染色・プリント技法 | 和染め技法 / 世界の染め技法 / プリント技法 |
| 織り・構造技法 | 織り柄技法 / キルト・重ね構造 |
| 金具・留め具 | ボタン・スタッズ / 編み上げ・留め構造 |
| 加工・仕上げ効果 | 光沢・煌めき / 手仕事・アート / テクノロジー系 |
| テーマ・スタイル装飾 | ゴシック・パンク / ブライダル・フォーマル / 民族衣装モチーフ |
| アクティブウェア・機能技法 | 機能ディテール / 安全・視認性 |
| 季節・イベントモチーフ | 花・植物モチーフ / 祝祭・イベント装飾 |

### pattern / material / 伝統色 / subject_hint の大項目

| 辞書 | 大項目 |
|---|---|
| pattern | 幾何学柄 / 自然モチーフ柄 / 和柄 / 世界の織物柄 / アートスタイル柄 / 時代スタイル柄 |
| material | 天然繊維 / 和素材 / 化学繊維 / 皮革・毛皮 / 織り・特殊質感 / 世界の伝統素材 / モダン・工業素材 |
| 伝統色 | 紅・赤系統 / 藍・青系統 / 緑系統 / 黄・橙系統 / 紫系統 / 白・黒・鼠系統 |
| subject_hint | 和装 / 洋装フォーマル / 洋装カジュアル / アウター / 小物・その他 / 世界の民族衣装 / スポーツ・ワークウェア / コスチューム・ファンタジー衣装 |

語彙データの実体は `nodes/decoration_data.py` / `nodes/pattern_data.py` /
`nodes/material_data.py` / `nodes/color_data.py` / `nodes/subject_data.py`
に「大項目・中項目でグループ化された生データ」として集約されています。
`nodes/vocabulary.py` のフラット辞書（`DECORATION_PRESETS` 等）と
`nodes/categories.py` のカテゴリ対応表（`DECORATION_CATEGORY_OF` 等）は
どちらもこの同じ生データから自動的に構築されるため、新しい項目を
追加する際は各 `*_data.py` に1件追記するだけで、語彙辞書とカテゴリ分類の
両方に自動的に反映されます（手動で2箇所に書いてズレる、という事故が
起きない設計です。`tests/test_categories.py` が万一の分類漏れも検出します）。

## 日本語対応

Stable Diffusion系モデルは英語プロンプトの方が精度が出やすいため、辞書の
実体（プロンプトへ展開される語句）は英語のまま維持しつつ、以下の3方式で
日本語入力に対応しています。

1. **ドロップダウン表示のバイリンガル化**: `decoration_preset` / `pattern` /
   `material` は ComfyUI 上で `"embroidery | 刺繍"` のように英語キーと
   日本語ラベルを併記して表示されます。選択した値は自動的に正しい英語キー
   に解決されます。
2. **色の自由入力（日本の伝統色）**: `color` フィールドに `藍色` や
   `ai-iro` のように日本の伝統色名（漢字・ローマ字どちらも可）を入力すると、
   🧵 Prompt Composer では CLIPプロンプト向けの英語表現（例:
   `deep indigo blue`）に、🎨 Direct Paint / 🧩 Auto では対応する
   16進カラーコード（例: `#1e50a2`）に、それぞれ自動変換されます。
   該当しない入力（`red` や `#ff0000` など）はそのまま渡されます。
3. **対象語（subject_hint）の日本語入力**: `着物` `浴衣` `ドレス` `制服` など
   服飾用語を直接入力すると英語（`kimono` / `yukata` / `dress` / `uniform`）
   に変換されます。

対応する日本の伝統色・和柄・和素材の例:

| 種別 | 例 |
|---|---|
| 伝統色 | 藍色・茜色・山吹色・若草色・桜色・藤色・鴇色・群青色・朱色・抹茶色・紅色・黄金色・深緑・白銀・漆黒・浅葱色・紫紺・生成り |
| 和柄（pattern） | 青海波・麻の葉・市松模様・唐草模様・桜柄・亀甲柄・七宝柄・雷紋 |
| 和素材（material） | 和紙・ちりめん・金襴・西陣織・紬 |
| 装飾技法の追加分 | 刺し子・藍染め・金継ぎ風ステッチ・折り紙モチーフ・家紋風エンブレム・バティック染め・手描きペイント・リボン刺繍・ラインストーン・フリル・チェーン装飾・フェザートリム 等 |

## モデルに合わせたプロンプトの自動生成・拡張

`nodes/model_profiles.py` に、対象モデル系統ごとの書式ルール
（`ModelProfile`）を定義しています。🧵 Prompt Composer / 🧩 Auto の
`target_model`、または単体の 🧠 Model Prompt Adapter で選択すると、
同じ装飾内容から以下のように書式・内容が自動的に変換・拡張されます。

| target_model | 系統 | 出力形式 | quality接頭辞の例 | negative |
|---|---|---|---|---|
| `generic` | 汎用 | タグ列（無加工） | なし | 追加分のみ |
| `sd15_anime` | SD1.5アニメ系（Danbooruタグ） | タグ列（`_`区切り） | `masterpiece, best quality, highres` | `worst_quality` 等 |
| `pony_v6` | Pony Diffusion V6 XL | タグ列（`_`区切り） | `score_9, score_8_up, score_7_up` | `score_6, score_5, score_4` 等 |
| `illustrious` | Illustrious XL | タグ列（`_`区切り） | `masterpiece, best quality, very aesthetic, absurdres` | `worst_quality` 等 |
| `noobai` | NoobAI XL | タグ列（`_`区切り） | `masterpiece, best quality, newest` | `worst_quality, old, early` 等 |
| `sdxl_base` | SDXL Base | 自然文 | `High quality highly detailed.` | タグ列（対応） |
| `sd3` | Stable Diffusion 3/3.5 | 自然文 | なし | タグ列（対応） |
| `flux` | FLUX.1 | 自然文 | なし | **常に空文字**（FLUXはnegativeを使わない） |

例（decoration_preset=embroidery, pattern=floral, material=silk, color=red,
subject_hint=dress）:

- `sd15_anime` → `masterpiece, best quality, highres, dress, red, intricate_embroidery, embroidered_pattern, floral_pattern, silk_fabric`
- `pony_v6` → `score_9, score_8_up, score_7_up, dress, red, intricate_embroidery, ...`（negativeに `score_6, score_5, score_4` を自動付与）
- `sdxl_base` / `sd3` → `High quality highly detailed. A dress elaborately decorated with red, intricate embroidery, embroidered pattern, floral pattern, and silk fabric, rendered with fine, photorealistic fabric detail and natural draping.`
- `flux` → 上記と同様の自然文。`model_negative_prompt` は空文字。

新しいモデル系統を追加したい場合は `nodes/model_profiles.py` の
`MODEL_PROFILES` に `ModelProfile` を1件追加するだけで、全ノードの
`target_model` ドロップダウンに自動的に反映されます。

## decoration_preset（🧵 Prompt Composer / 🧩 Auto）

200種類のプリセットを収録（`nodes/vocabulary.py` の `DECORATION_PRESETS`、
実体は `nodes/decoration_data.py`）。上記の大項目・中項目カテゴリ一覧も
参照してください。主なカテゴリ:

- 基本装飾: `embroidery` / `lace_trim` / `sequins` / `beading` / `ribbon_bow` /
  `floral_applique` / `glitter` / `studs` / `printed_pattern` 等
- 染め技法: `gradient_dye` / `tie_dye` / `batik_dye` / `indigo_dye` /
  `shibori_dye` / `yuzen_dye` / `katazome_stencil`
- 和装飾: `sashiko_stitch` / `kintsugi_seam` / `origami_applique` /
  `kamon_emblem`
- フォーマル系: `pocket_square` / `cufflinks_detail` / `brass_buttons` /
  `epaulette_trim`
- ゴシック/パンク系: `gothic_lace` / `cameo_brooch` / `bat_wing_applique` /
  `safety_pin_accent`
- ストリート系: `graffiti_print` / `distressed_denim` / `patch_badges` /
  `mesh_panel` / `reflective_strip`
- ブライダル: `bridal_veil_lace` / `pearl_trim`
- 世界の染織技法: `zari_embroidery` / `mirror_work` / `block_print` /
  `ikat_weave` / `kente_pattern` / `fair_isle_knit` / `damask_weave` /
  `toile_print` / `frog_buttons`
- モダン: `laser_cut_pattern` / `led_light_trim`
- `custom`（free_text のみで構成）

同様に pattern（200種）・material（200種）・伝統色（203種）・subject_hint
（233種）も拡充されています。プロジェクト固有の装飾語・色・柄・素材を
追加したい場合はこのファイルの各辞書（`DECORATION_PRESETS` /
`PATTERN_VOCAB` / `MATERIAL_VOCAB` / `TRADITIONAL_COLORS_JA` /
`SUBJECT_HINT_JA_TO_EN`）と、対応する `*_LABELS_JA` を編集してください。

## decoration_type（🎨 Direct Paint / 🧩 Auto）

`solid_color` / `gradient_fill` / `pattern_tile`（`pattern_image`接続が必要）/
`texture_blend`（`texture_image`接続が必要）/ `brightness_contrast` / `hue_shift`

## 開発・テスト

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

コアロジック（`nodes/mask_utils.py` / `nodes/paint_ops.py` /
`nodes/vocabulary.py`）は torch に依存しないため、ComfyUI 環境が無くても
テストできます。ノード本体（`nodes/*_node.py` 相当のIMAGE/MASKテンソル変換）
は ComfyUI 実行環境（torch あり）での動作確認を別途推奨します。

## ライセンス

MIT License（`LICENSE` を参照）
