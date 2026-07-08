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
- コアロジック（マスク処理・装飾語彙・画素処理）は torch 非依存の純粋関数として
  分離されており、`pytest` で単体テスト可能です（`tests/`）。

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

## decoration_preset（🧵 Prompt Composer / 🧩 Auto）

`embroidery` / `lace_trim` / `sequins` / `beading` / `ribbon_bow` /
`floral_applique` / `gradient_dye` / `tie_dye` / `patchwork` / `glitter` /
`holographic` / `metallic_foil` / `fringe` / `tassel` / `pearl_trim` /
`jewel_encrusted` / `studs` / `printed_pattern` / `ribbon_embroidery` /
`rhinestone` / `frill_ruffle` / `chain_trim` / `feather_trim` /
`hand_painted` / `batik_dye` / `indigo_dye` / `sashiko_stitch` /
`kintsugi_seam` / `origami_applique` / `kamon_emblem` / `bow_accent` /
`corset_lacing` / `custom`

語彙は `nodes/vocabulary.py` に定義されています。プロジェクト固有の
装飾語・色・柄・素材を追加したい場合はこのファイルの各辞書
（`DECORATION_PRESETS` / `PATTERN_VOCAB` / `MATERIAL_VOCAB` /
`TRADITIONAL_COLORS_JA` / `SUBJECT_HINT_JA_TO_EN`）と、対応する
`*_LABELS_JA` を編集してください。

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
