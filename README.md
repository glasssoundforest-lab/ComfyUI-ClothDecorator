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

## 大項目・中項目カテゴリ分類

`nodes/categories.py` に、各語彙辞書のキーを大項目（major）・中項目（mid）で
分類する対応表を定義しています。ComfyUI のドロップダウンには
`"[大項目 > 中項目] english_key | 日本語ラベル"` の形式でグルーピング表示され、
項目数が多くても目的の装飾技法を探しやすくなっています。

- **decoration_preset**（82種）: 大項目7 × 中項目2〜3の2階層分類
- **pattern**（38種）/ **material**（33種）/ 伝統色（43種）/ **subject_hint**（42種）:
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

### pattern / material / 伝統色 / subject_hint の大項目

| 辞書 | 大項目 |
|---|---|
| pattern | 幾何学柄 / 自然モチーフ柄 / 和柄 / 世界の織物柄 |
| material | 天然繊維 / 和素材 / 化学繊維 / 特殊質感 |
| 伝統色 | 紅・赤系統 / 藍・青系統 / 緑系統 / 黄・橙系統 / 紫系統 / 白・黒・鼠系統 |
| subject_hint | 和装 / 洋装フォーマル / 洋装カジュアル / アウター / 小物・その他 |

新しい項目を追加する際は、`nodes/vocabulary.py` の各辞書に本体（英語キー・
プロンプト語・日本語ラベル）を追加した上で、`nodes/categories.py` の対応する
`*_CATEGORY_OF` にキー→(大項目, 中項目) の割り当てを追加してください
（`tests/test_categories.py` が未分類キーを検出します）。

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

82種類のプリセットを収録（`nodes/vocabulary.py` の `DECORATION_PRESETS`）。
上記の大項目・中項目カテゴリ一覧も参照してください。主なカテゴリ:

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

同様に pattern（38種）・material（33種）・伝統色（43種）・subject_hint
（42種）も拡充されています。プロジェクト固有の装飾語・色・柄・素材を
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
