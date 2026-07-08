"""
nodes/decoration_data.py — decoration_preset 語彙データ（大項目・中項目でグループ化）

このファイルが decoration_preset の英語キー・プロンプト語・日本語ラベル・
大項目/中項目カテゴリの「唯一の情報源」。ここに追加すれば、
vocabulary.DECORATION_PRESETS / DECORATION_LABELS_JA と
categories.DECORATION_CATEGORY_OF に自動的に反映される
（手動で2箇所に同じキーを書いてズレる、という事故を防ぐための設計）。

構造: (大項目キー, 大項目の日本語ラベル, [
    (中項目キー, 中項目の日本語ラベル, [
        (プリセットキー, [英語プロンプト語, ...], 日本語ラベル),
        ...
    ]),
    ...
])
"""

from __future__ import annotations

DecorationEntry = tuple[str, list[str], str]
MidGroup = tuple[str, str, list[DecorationEntry]]
MajorGroup = tuple[str, str, list[MidGroup]]

DECORATION_GROUPS: list[MajorGroup] = [
    (
        "embroidery_beadwork", "刺繍・ビーズ手芸",
        [
            (
                "embroidery", "刺繍技法",
                [
                    ("embroidery", ["intricate embroidery", "embroidered pattern"], "刺繍"),
                    ("ribbon_embroidery", ["ribbon embroidery", "silk ribbon stitched pattern"], "リボン刺繍"),
                    ("sashiko_stitch", ["sashiko stitching", "traditional Japanese running-stitch pattern"], "刺し子"),
                    ("zari_embroidery", ["zari embroidery", "gold and silver metallic thread embroidery"], "ザリ刺繍（金銀糸刺繍）"),
                    ("mirror_work", ["mirror work embellishment", "shisha embroidered mirrors"], "ミラーワーク刺繍"),
                    ("huipil_embroidery", ["huipil-style embroidery", "Mesoamerican geometric embroidery"], "ウイピル刺繍"),
                    ("crewel_embroidery", ["crewel wool embroidery", "raised crewelwork motif"], "クルーエル刺繍"),
                    ("goldwork_embroidery", ["goldwork embroidery", "raised metal thread embroidery"], "ゴールドワーク刺繍"),
                    ("blackwork_embroidery", ["blackwork embroidery", "geometric counted blackwork pattern"], "ブラックワーク刺繍"),
                    ("cross_stitch", ["cross-stitch pattern", "counted cross-stitch motif"], "クロスステッチ"),
                    ("chikankari_embroidery", ["chikankari embroidery", "white-on-white Lucknow shadow work"], "チカンカリ刺繍"),
                    ("kantha_stitch", ["kantha running stitch", "layered Bengali quilting stitch"], "カンタステッチ"),
                    ("hardanger_embroidery", ["hardanger whitework embroidery", "cutwork geometric embroidery"], "ハーダンガー刺繍"),
                    ("tambour_embroidery", ["tambour hook embroidery", "chain-stitch beaded embroidery"], "タンブール刺繍"),
                    ("stumpwork_embroidery", ["stumpwork raised embroidery", "3D padded embroidery relief"], "スタンプワーク刺繍"),
                    ("ayrshire_whitework", ["Ayrshire whitework embroidery", "fine floral needlework"], "エアシャーホワイトワーク"),
                ],
            ),
            (
                "beadwork", "ビーズ・宝飾",
                [
                    ("sequins", ["sequined", "sparkling sequins"], "スパンコール"),
                    ("beading", ["beaded detail", "hand-beaded"], "ビーズ装飾"),
                    ("pearl_trim", ["pearl trim", "pearl embellishment"], "パールトリム"),
                    ("jewel_encrusted", ["jewel-encrusted", "gemstone embellishments"], "宝石装飾"),
                    ("rhinestone", ["rhinestone embellishment", "sparkling rhinestones"], "ラインストーン"),
                    ("crystal_beading", ["crystal beading", "hand-sewn crystal beadwork"], "クリスタルビーズ刺繍"),
                    ("cameo_brooch", ["cameo brooch accent"], "カメオブローチ"),
                    ("seed_bead_trim", ["seed bead trim", "tiny woven seed beads"], "シードビーズトリム"),
                    ("bugle_bead_fringe", ["bugle bead fringe", "elongated glass bead fringe"], "バグルビーズフリンジ"),
                    ("paillette_trim", ["paillette trim", "large flat metallic discs"], "パイエット装飾"),
                    ("bib_necklace_accent", ["bib necklace-style neckline accent"], "ビブネックレス風襟装飾"),
                    ("brooch_pin_cluster", ["clustered vintage brooch pins"], "ブローチピンクラスター"),
                    ("gemstone_button", ["gemstone-topped buttons"], "宝石ボタン"),
                    ("chandelier_earring_accent", ["chandelier earring-style dangle accent"], "シャンデリアイヤリング風アクセント"),
                    ("cabochon_stone_trim", ["cabochon stone trim accent"], "カボションストーントリム"),
                ],
            ),
            (
                "applique", "アップリケ・パッチ",
                [
                    ("floral_applique", ["floral applique", "fabric flower decoration"], "花柄アップリケ"),
                    ("bat_wing_applique", ["bat-wing applique", "gothic bat motif accent"], "コウモリ翼アップリケ"),
                    ("origami_applique", ["origami-fold applique", "paper-fold inspired fabric motif"], "折り紙モチーフ"),
                    ("patch_badges", ["embroidered patch badges", "sew-on patch collection"], "ワッペン・パッチ"),
                    ("silk_flower", ["silk flower corsage", "fabric flower accent"], "布花コサージュ"),
                    ("kamon_emblem", ["kamon-style emblem", "Japanese family crest motif"], "家紋風エンブレム"),
                    ("leaf_applique", ["leaf-shaped fabric applique"], "リーフアップリケ"),
                    ("butterfly_applique", ["butterfly applique motif"], "蝶アップリケ"),
                    ("animal_applique", ["cute animal-shaped applique"], "動物アップリケ"),
                    ("heart_applique", ["heart-shaped applique accent"], "ハートアップリケ"),
                    ("star_applique", ["star-shaped applique motif"], "星アップリケ"),
                    ("monogram_patch", ["monogram initial patch"], "モノグラムパッチ"),
                    ("varsity_letter_patch", ["varsity letterman chenille patch"], "バーシティレターパッチ"),
                    ("lace_motif_applique", ["lace motif fabric applique"], "レースモチーフアップリケ"),
                    ("geometric_patch_cluster", ["clustered geometric fabric patches"], "幾何学パッチクラスター"),
                ],
            ),
        ],
    ),
    (
        "trim_edging", "トリム・縁飾り",
        [
            (
                "lace_ribbon", "レース・リボン",
                [
                    ("lace_trim", ["lace trim", "delicate lace edging"], "レーストリム"),
                    ("ribbon_bow", ["ribbon bow accent", "satin ribbon"], "リボン"),
                    ("lace_overlay", ["lace overlay", "sheer lace layered over fabric"], "レースオーバーレイ"),
                    ("bow_accent", ["decorative bow accent"], "ボウタイ・蝶結び"),
                    ("chantilly_lace", ["chantilly lace trim", "delicate floral bobbin lace"], "シャンティイレース"),
                    ("guipure_lace", ["guipure lace trim", "heavy raised motif lace"], "ギュピュールレース"),
                    ("crochet_lace_trim", ["crochet lace trim", "handmade crochet edging"], "クロシェレーストリム"),
                    ("scalloped_edge", ["scalloped fabric edge detail"], "スカラップ縁飾り"),
                    ("picot_edge_trim", ["picot-edge ribbon trim"], "ピコットエッジトリム"),
                    ("grosgrain_ribbon_trim", ["grosgrain ribbon trim accent"], "グログランリボントリム"),
                    ("velvet_ribbon_trim", ["velvet ribbon trim accent"], "ベルベットリボントリム"),
                ],
            ),
            (
                "fringe_tassel", "フリンジ・タッセル・羽根",
                [
                    ("fringe", ["fringe trim", "swaying fringe"], "フリンジ"),
                    ("tassel", ["tassel details"], "タッセル"),
                    ("feather_trim", ["feather trim", "soft feather accents"], "フェザートリム"),
                    ("chain_trim", ["chain trim accent", "delicate metal chain detail"], "チェーン装飾"),
                    ("epaulette_trim", ["epaulette shoulder trim", "military-style shoulder detail"], "エポレット（肩章）"),
                    ("pompom_trim", ["pompom fringe trim"], "ポンポントリム"),
                    ("bead_fringe", ["beaded fringe trim"], "ビーズフリンジ"),
                    ("macrame_fringe", ["macrame knotted fringe"], "マクラメフリンジ"),
                    ("ostrich_feather_boa", ["ostrich feather boa trim"], "オーストリッチフェザーボア"),
                    ("marabou_feather_trim", ["marabou feather trim"], "マラブーフェザートリム"),
                ],
            ),
            (
                "piping_brocade", "パイピング・ブロケード",
                [
                    ("piping_trim", ["contrast piping trim"], "パイピング"),
                    ("brocade_trim", ["brocade trim accent", "woven brocade edging"], "ブロケードトリム"),
                    ("velvet_trim", ["velvet trim accent", "plush velvet edging"], "ベルベットトリム"),
                    ("frill_ruffle", ["ruffled frill trim", "layered ruffles"], "フリル"),
                    ("bias_tape_trim", ["contrast bias tape trim"], "バイアステープトリム"),
                    ("cording_detail", ["decorative cording detail"], "コード装飾"),
                    ("welt_seam_trim", ["welt seam trim detail"], "ウェルトシームトリム"),
                    ("rickrack_trim", ["rickrack zigzag trim"], "リックラックトリム"),
                ],
            ),
        ],
    ),
    (
        "dye_print", "染色・プリント技法",
        [
            (
                "japanese_dye", "和染め技法",
                [
                    ("indigo_dye", ["indigo dye pattern", "deep indigo dyed fabric, aizome style"], "藍染め"),
                    ("shibori_dye", ["shibori dye pattern", "traditional Japanese tie-dye texture"], "絞り染め"),
                    ("yuzen_dye", ["yuzen dye artwork", "hand-painted Japanese silk dyeing"], "友禅染め"),
                    ("katazome_stencil", ["katazome stencil-dyed pattern", "Japanese paste-resist stencil dyeing"], "型染め"),
                    ("bingata_dye", ["bingata dye pattern", "vivid Okinawan stencil dyeing"], "紅型"),
                    ("kyokanoko_shibori", ["kyokanoko fawn-spot shibori pattern"], "京鹿の子絞り"),
                    ("rozome_wax_dye", ["rozome wax-resist dye pattern"], "蝋染め"),
                ],
            ),
            (
                "world_dye", "世界の染め技法",
                [
                    ("tie_dye", ["tie-dye pattern"], "タイダイ染め"),
                    ("batik_dye", ["batik dye pattern", "wax-resist dye pattern"], "バティック染め"),
                    ("gradient_dye", ["gradient dye", "ombre coloring"], "グラデーション染め"),
                    ("ikat_weave", ["ikat woven pattern", "resist-dyed ikat texture"], "イカット織り"),
                    ("shweshwe_print", ["shweshwe print", "South African indigo discharge-printed pattern"], "シュエシュエプリント"),
                    ("thermochromic_dye", ["thermochromic color-shifting dye", "heat-reactive color-changing fabric"], "感温変色染め"),
                    ("adire_resist_dye", ["adire resist-dyed pattern", "Yoruba indigo resist textile"], "アディレ染め"),
                    ("plangi_dye", ["plangi tie-dye pattern", "Southeast Asian resist-dye texture"], "プランギ染め"),
                    ("ombre_dip_dye", ["ombre dip-dye gradient"], "ディップダイグラデーション"),
                    ("marbled_suminagashi_dye", ["suminagashi marbled dye pattern"], "墨流し染め"),
                ],
            ),
            (
                "print_technique", "プリント技法",
                [
                    ("printed_pattern", ["printed graphic pattern"], "プリント柄"),
                    ("graffiti_print", ["graffiti-style print", "spray-paint graphic print"], "グラフィティプリント"),
                    ("toile_print", ["toile de jouy print", "pastoral scenic print"], "トワル・ド・ジュイ柄"),
                    ("block_print", ["hand block-printed pattern"], "ブロックプリント"),
                    ("laser_cut_pattern", ["laser-cut cutout pattern", "precision-cut fabric lacework"], "レーザーカット柄"),
                    ("uv_reactive_print", ["UV-reactive print", "blacklight-glowing pattern"], "UV反応プリント"),
                    ("screen_print_graphic", ["screen-printed graphic design"], "シルクスクリーンプリント"),
                    ("digital_photo_print", ["digital photo-realistic print"], "デジタル写真プリント"),
                    ("foil_stamp_print", ["metallic foil-stamped print"], "箔押しプリント"),
                    ("puff_print_texture", ["raised puff-ink print texture"], "パフプリント（立体プリント）"),
                    ("discharge_print", ["discharge print, bleached-out design"], "ディスチャージプリント"),
                    ("ombre_sublimation_print", ["ombre sublimation print"], "オンブレ昇華プリント"),
                    ("photoluminescent_print", ["photoluminescent glow-in-the-dark print"], "蓄光プリント"),
                ],
            ),
        ],
    ),
    (
        "weave_construction", "織り・構造技法",
        [
            (
                "weave_pattern", "織り柄技法",
                [
                    ("patchwork", ["patchwork design", "mixed fabric patches"], "パッチワーク"),
                    ("damask_weave", ["damask woven pattern", "reversible jacquard damask texture"], "ダマスク織り"),
                    ("kente_pattern", ["kente cloth pattern", "West African woven pattern"], "ケンテ織り柄"),
                    ("fair_isle_knit", ["fair isle knit pattern", "colorwork knit motif"], "フェアアイル編み柄"),
                    ("jacquard_weave", ["jacquard woven pattern"], "ジャカード織り"),
                    ("dobby_weave_texture", ["dobby loom woven texture"], "ドビー織り"),
                    ("basketweave_texture", ["basketweave woven texture"], "バスケット織り"),
                    ("cable_knit_texture", ["cable knit texture"], "ケーブル編み"),
                    ("intarsia_knit_motif", ["intarsia knit color-block motif"], "インターシャ編み柄"),
                    ("boro_patchwork", ["boro-style mended patchwork", "Japanese sashiko-reinforced patchwork"], "ぼろ継ぎ"),
                    ("brick_stitch_weave", ["brick-stitch woven pattern"], "レンガ編み"),
                    ("herringbone_weave_texture", ["herringbone weave texture accent"], "ヘリンボーン織りアクセント"),
                ],
            ),
            (
                "quilt_layer", "キルト・重ね構造",
                [
                    ("quilted_pattern", ["quilted diamond stitching", "padded quilted texture"], "キルティング"),
                    ("mesh_panel", ["sheer mesh panel insert"], "メッシュ切替"),
                    ("distressed_denim", ["distressed denim texture", "frayed ripped denim detail"], "ダメージデニム加工"),
                    ("3d_printed_lattice", ["3D-printed lattice texture", "generative lattice structure detail"], "3Dプリントラティス"),
                    ("layered_tulle_skirt", ["layered tulle underskirt volume"], "チュール重ね構造"),
                    ("padded_shoulder_structure", ["structured padded shoulder detail"], "肩パッド構造"),
                    ("cutout_panel_detail", ["strategic cutout panel detail"], "カットアウトパネル"),
                    ("asymmetric_layering", ["asymmetric fabric layering"], "非対称レイヤリング"),
                ],
            ),
        ],
    ),
    (
        "hardware_fastener", "金具・留め具",
        [
            (
                "buttons_studs", "ボタン・スタッズ",
                [
                    ("ornate_buttons", ["ornate decorative buttons", "engraved button details"], "装飾ボタン"),
                    ("brass_buttons", ["polished brass buttons"], "真鍮ボタン"),
                    ("studs", ["metal studs", "studded detail"], "スタッズ"),
                    ("safety_pin_accent", ["safety pin accents", "punk-style pin detail"], "セーフティピン装飾"),
                    ("frog_buttons", ["Chinese frog button closures", "knotted frog fastenings"], "チャイナボタン（組み紐留め）"),
                    ("cufflinks_detail", ["ornate cufflinks detail"], "カフスボタン"),
                    ("pocket_square", ["folded pocket square accent"], "ポケットチーフ"),
                    ("toggle_buttons", ["wooden toggle button fastenings"], "トグルボタン"),
                    ("snap_button_row", ["exposed snap button row"], "スナップボタン列"),
                    ("grommet_eyelet_row", ["metal grommet eyelet row"], "ハトメ列"),
                    ("rivets_detail", ["exposed metal rivets"], "リベット装飾"),
                ],
            ),
            (
                "lacing_binding", "編み上げ・留め構造",
                [
                    ("corset_lacing", ["corset-style lacing detail"], "コルセットレース編み上げ"),
                    ("corset_boning", ["visible corset boning structure"], "コルセットボーニング"),
                    ("drawstring_detail", ["drawstring gathering detail"], "ドローストリング（絞り紐）"),
                    ("hanbok_ribbon", ["hanbok goreum ribbon tie", "Korean traditional ribbon sash"], "韓服（ハンボク）ゴルム"),
                    ("obi_musubi_bow", ["obi musubi-style back bow", "Japanese kimono sash knot"], "帯結び"),
                    ("cross_lace_back", ["cross-laced open back detail"], "クロスレースバック"),
                    ("buckle_belt_detail", ["decorative buckle belt detail"], "バックル装飾"),
                    ("harness_strap_detail", ["structured harness strap detail"], "ハーネスストラップ"),
                ],
            ),
        ],
    ),
    (
        "finish_effect", "加工・仕上げ効果",
        [
            (
                "shine_sparkle", "光沢・煌めき",
                [
                    ("glitter", ["glitter accents", "shimmering glitter"], "グリッター"),
                    ("holographic", ["holographic finish", "iridescent sheen"], "ホログラム加工"),
                    ("metallic_foil", ["metallic foil print", "metallic accents"], "箔プリント"),
                    ("reflective_strip", ["reflective strip trim", "high-visibility reflective accent"], "反射材トリム"),
                    ("iridescent_coating", ["iridescent oil-slick coating"], "イリデセントコーティング"),
                    ("pearlescent_finish", ["pearlescent sheen finish"], "パール加工"),
                    ("metallic_dust_coating", ["fine metallic dust coating"], "メタリックダスト加工"),
                ],
            ),
            (
                "hand_craft", "手仕事・アート",
                [
                    ("hand_painted", ["hand-painted design", "artisanal hand-painted motif"], "手描きペイント"),
                    ("kintsugi_seam", ["kintsugi-inspired gold seam", "gold-lined seam accent"], "金継ぎ風ステッチ"),
                    ("airbrush_art", ["airbrushed artwork design"], "エアブラシアート"),
                    ("hand_stamped_motif", ["hand-stamped fabric motif"], "手押しスタンプ柄"),
                    ("watercolor_dye_effect", ["watercolor dye bleed effect"], "水彩染み風エフェクト"),
                ],
            ),
            (
                "tech_modern", "テクノロジー系",
                [
                    ("led_light_trim", ["glowing LED light trim", "illuminated fiber-optic accent"], "LEDライトトリム"),
                    ("smart_fiber_circuitry", ["embedded smart-fiber circuitry", "e-textile circuit pattern"], "スマートファイバー回路装飾"),
                    ("fiber_optic_weave", ["woven fiber-optic light strands"], "光ファイバー織り込み"),
                    ("solar_cell_panel_trim", ["integrated flexible solar-cell panel trim"], "ソーラーパネルトリム"),
                    ("holographic_circuit_print", ["holographic circuit-board print"], "ホログラフィック回路柄"),
                ],
            ),
        ],
    ),
    (
        "theme_style", "テーマ・スタイル装飾",
        [
            (
                "gothic_punk", "ゴシック・パンク",
                [
                    ("gothic_lace", ["gothic lace trim", "dark victorian lace detail"], "ゴシックレース"),
                    ("spiked_leather_harness", ["spiked leather harness accent"], "スパイクレザーハーネス"),
                    ("chain_harness_accent", ["chain harness accent", "layered chain body harness detail"], "チェーンハーネス"),
                    ("studded_choker_collar", ["studded choker collar detail"], "スタッズチョーカーカラー"),
                    ("torn_fishnet_layer", ["torn fishnet layering accent"], "破れファイシュネット重ね"),
                    ("padlock_charm_accent", ["padlock charm accent detail"], "南京錠チャームアクセント"),
                ],
            ),
            (
                "bridal_formal", "ブライダル・フォーマル",
                [
                    ("bridal_veil_lace", ["bridal veil lace trim", "delicate wedding lace"], "ブライダルベールレース"),
                    ("tiered_bridal_lace", ["tiered bridal lace layers", "cascading lace tiers"], "ティアードブライダルレース"),
                    ("ivory_satin_bow", ["ivory satin bow accent"], "アイボリーサテンボウ"),
                    ("cathedral_train_lace", ["cathedral-length lace train detail"], "カテドラルトレーンレース"),
                    ("boutonniere_accent", ["boutonniere flower accent"], "ブートニアアクセント"),
                    ("something_blue_ribbon", ["hidden blue ribbon accent, bridal tradition"], "サムシングブルーリボン"),
                    ("tuxedo_satin_lapel", ["satin-faced tuxedo lapel detail"], "タキシードサテンラペル"),
                ],
            ),
            (
                "ethnic_world", "民族衣装モチーフ",
                [
                    ("shweshwe_border_accent", ["shweshwe border print accent"], "シュエシュエ柄アクセント"),
                    ("huipil_motif", ["huipil geometric motif band"], "ウイピル文様帯"),
                    ("hanbok_ribbon_accent", ["hanbok-style ribbon accent"], "韓服風リボンアクセント"),
                    ("dashiki_print_accent", ["dashiki graphic print accent"], "ダシキプリントアクセント"),
                    ("aztec_motif_trim", ["Aztec geometric motif trim"], "アステカ文様トリム"),
                    ("scandinavian_folk_motif", ["Scandinavian folk embroidery motif"], "北欧民族柄モチーフ"),
                    ("moroccan_tile_trim", ["Moroccan tile-inspired trim motif"], "モロッコタイル風トリム"),
                ],
            ),
        ],
    ),
    (
        "sportswear_technical", "アクティブウェア・機能技法",
        [
            (
                "performance_detail", "機能ディテール",
                [
                    ("mesh_ventilation_panel", ["mesh ventilation panel detail"], "メッシュベンチレーションパネル"),
                    ("taped_seam_construction", ["heat-taped seam construction"], "テープシーム加工"),
                    ("compression_panel_detail", ["compression panel paneling detail"], "コンプレッションパネル"),
                    ("number_print_accent", ["athletic number print accent"], "ゼッケンナンバープリント"),
                    ("racing_stripe_accent", ["racing stripe accent"], "レーシングストライプ"),
                    ("zip_pocket_detail", ["technical zip pocket detail"], "ジップポケットディテール"),
                    ("bonded_seam_finish", ["bonded seamless finish detail"], "ボンディングシーム加工"),
                    ("moisture_wicking_panel", ["moisture-wicking technical panel"], "吸汗速乾パネル"),
                    ("articulated_paneling", ["articulated performance paneling"], "アーティキュレイテッドパネリング"),
                ],
            ),
            (
                "safety_visibility", "安全・視認性",
                [
                    ("high_vis_piping", ["high-visibility piping accent"], "高視認性パイピング"),
                    ("reflective_logo_print", ["reflective logo print accent"], "反射ロゴプリント"),
                    ("safety_orange_accent", ["safety orange accent trim"], "セーフティオレンジアクセント"),
                ],
            ),
        ],
    ),
    (
        "seasonal_motif", "季節・イベントモチーフ",
        [
            (
                "floral_botanical", "花・植物モチーフ",
                [
                    ("cherry_blossom_motif", ["cherry blossom motif accent"], "桜モチーフアクセント"),
                    ("autumn_leaf_print", ["autumn maple leaf print accent"], "紅葉プリントアクセント"),
                    ("holly_berry_trim", ["holly berry winter trim accent"], "ヒイラギの実トリム"),
                    ("snowflake_applique", ["snowflake applique accent"], "雪の結晶アップリケ"),
                ],
            ),
            (
                "holiday_seasonal", "祝祭・イベント装飾",
                [
                    ("festival_lantern_motif", ["festival paper lantern motif accent"], "祭り提灯モチーフ"),
                    ("celebration_confetti_print", ["celebration confetti print accent"], "パーティー紙吹雪プリント"),
                    ("harvest_wheat_motif", ["harvest wheat sheaf motif accent"], "収穫祭麦穂モチーフ"),
                ],
            ),
        ],
    ),
]
