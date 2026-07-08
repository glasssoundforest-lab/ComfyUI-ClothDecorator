"""
nodes/vocabulary.py — 服飾「装飾」プロンプト語彙ライブラリ（日本語対応）

Face-Prompt-Studio の fps-core/clothing_refiner が持つ服飾カテゴリ
（服の種類そのもの: tops/bottoms/dress...）とは目的が異なり、
こちらは「既存の服の上に何を足す/どう加工するか」という
装飾（デコレーション）語彙に特化している。

torch / ComfyUI に依存しない純粋データ + 関数のため、単体テスト可能。

── 日本語対応方針 ──────────────────────────────────────────────────
Stable Diffusion 系モデルは基本的に英語プロンプトの方が精度が高いため、
辞書のキー・実際にプロンプトへ展開される語句は英語のまま維持する。
その上で:
  1. 各キーに日本語ラベル（*_LABELS_JA）を対応付け、ComfyUI の
     ドロップダウンに "english_key | 日本語ラベル" の形式で表示する。
  2. resolve_key() が "english_key"・"english_key | 日本語ラベル"・
     日本語ラベルそのもの のどれを渡されても正しいキーへ解決する。
  3. 色・対象語（subject_hint）は自由入力のため、日本語の伝統色名や
     服飾用語を英語のプロンプト語へ変換する辞書（TRADITIONAL_COLORS_JA /
     SUBJECT_HINT_JA_TO_EN）を用意し、resolve_color_term() /
     resolve_subject_hint() で変換する。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ═══════════════════════════════════════════════════════════════════
# 装飾技法プリセット
# ═══════════════════════════════════════════════════════════════════
# キー: UI（ComfyUIのドロップダウン）に出す短い識別子（英語・不変）
# 値:   実際にプロンプトへ展開する語句（複数可、英語）
DECORATION_PRESETS: dict[str, list[str]] = {
    "none": [],
    "embroidery": ["intricate embroidery", "embroidered pattern"],
    "lace_trim": ["lace trim", "delicate lace edging"],
    "sequins": ["sequined", "sparkling sequins"],
    "beading": ["beaded detail", "hand-beaded"],
    "ribbon_bow": ["ribbon bow accent", "satin ribbon"],
    "floral_applique": ["floral applique", "fabric flower decoration"],
    "gradient_dye": ["gradient dye", "ombre coloring"],
    "tie_dye": ["tie-dye pattern"],
    "patchwork": ["patchwork design", "mixed fabric patches"],
    "glitter": ["glitter accents", "shimmering glitter"],
    "holographic": ["holographic finish", "iridescent sheen"],
    "metallic_foil": ["metallic foil print", "metallic accents"],
    "fringe": ["fringe trim", "swaying fringe"],
    "tassel": ["tassel details"],
    "pearl_trim": ["pearl trim", "pearl embellishment"],
    "jewel_encrusted": ["jewel-encrusted", "gemstone embellishments"],
    "studs": ["metal studs", "studded detail"],
    "printed_pattern": ["printed graphic pattern"],
    # ★拡充分
    "ribbon_embroidery": ["ribbon embroidery", "silk ribbon stitched pattern"],
    "rhinestone": ["rhinestone embellishment", "sparkling rhinestones"],
    "frill_ruffle": ["ruffled frill trim", "layered ruffles"],
    "chain_trim": ["chain trim accent", "delicate metal chain detail"],
    "feather_trim": ["feather trim", "soft feather accents"],
    "hand_painted": ["hand-painted design", "artisanal hand-painted motif"],
    "batik_dye": ["batik dye pattern", "wax-resist dye pattern"],
    "indigo_dye": ["indigo dye pattern", "deep indigo dyed fabric, aizome style"],
    "sashiko_stitch": ["sashiko stitching", "traditional Japanese running-stitch pattern"],
    "kintsugi_seam": ["kintsugi-inspired gold seam", "gold-lined seam accent"],
    "origami_applique": ["origami-fold applique", "paper-fold inspired fabric motif"],
    "kamon_emblem": ["kamon-style emblem", "Japanese family crest motif"],
    "bow_accent": ["decorative bow accent"],
    "corset_lacing": ["corset-style lacing detail"],
    # ★さらに拡充分（第2弾）
    "crystal_beading": ["crystal beading", "hand-sewn crystal beadwork"],
    "lace_overlay": ["lace overlay", "sheer lace layered over fabric"],
    "velvet_trim": ["velvet trim accent", "plush velvet edging"],
    "silk_flower": ["silk flower corsage", "fabric flower accent"],
    "ornate_buttons": ["ornate decorative buttons", "engraved button details"],
    "piping_trim": ["contrast piping trim"],
    "quilted_pattern": ["quilted diamond stitching", "padded quilted texture"],
    "drawstring_detail": ["drawstring gathering detail"],
    "corset_boning": ["visible corset boning structure"],
    "epaulette_trim": ["epaulette shoulder trim", "military-style shoulder detail"],
    "brocade_trim": ["brocade trim accent", "woven brocade edging"],
    "shibori_dye": ["shibori dye pattern", "traditional Japanese tie-dye texture"],
    "yuzen_dye": ["yuzen dye artwork", "hand-painted Japanese silk dyeing"],
    "katazome_stencil": ["katazome stencil-dyed pattern", "Japanese paste-resist stencil dyeing"],
    # ★さらに拡充分（第3弾）
    "pocket_square": ["folded pocket square accent"],
    "cufflinks_detail": ["ornate cufflinks detail"],
    "brass_buttons": ["polished brass buttons"],
    "gothic_lace": ["gothic lace trim", "dark victorian lace detail"],
    "cameo_brooch": ["cameo brooch accent"],
    "bat_wing_applique": ["bat-wing applique", "gothic bat motif accent"],
    "graffiti_print": ["graffiti-style print", "spray-paint graphic print"],
    "distressed_denim": ["distressed denim texture", "frayed ripped denim detail"],
    "safety_pin_accent": ["safety pin accents", "punk-style pin detail"],
    "patch_badges": ["embroidered patch badges", "sew-on patch collection"],
    "mesh_panel": ["sheer mesh panel insert"],
    "reflective_strip": ["reflective strip trim", "high-visibility reflective accent"],
    "bridal_veil_lace": ["bridal veil lace trim", "delicate wedding lace"],
    "zari_embroidery": ["zari embroidery", "gold and silver metallic thread embroidery"],
    "mirror_work": ["mirror work embellishment", "shisha embroidered mirrors"],
    "block_print": ["hand block-printed pattern"],
    "ikat_weave": ["ikat woven pattern", "resist-dyed ikat texture"],
    "kente_pattern": ["kente cloth pattern", "West African woven pattern"],
    "fair_isle_knit": ["fair isle knit pattern", "colorwork knit motif"],
    "damask_weave": ["damask woven pattern", "reversible jacquard damask texture"],
    "toile_print": ["toile de jouy print", "pastoral scenic print"],
    "frog_buttons": ["Chinese frog button closures", "knotted frog fastenings"],
    "laser_cut_pattern": ["laser-cut cutout pattern", "precision-cut fabric lacework"],
    "led_light_trim": ["glowing LED light trim", "illuminated fiber-optic accent"],
    "custom": [],  # free_text のみで構成
}

DECORATION_LABELS_JA: dict[str, str] = {
    "none": "なし",
    "embroidery": "刺繍",
    "lace_trim": "レーストリム",
    "sequins": "スパンコール",
    "beading": "ビーズ装飾",
    "ribbon_bow": "リボン",
    "floral_applique": "花柄アップリケ",
    "gradient_dye": "グラデーション染め",
    "tie_dye": "タイダイ染め",
    "patchwork": "パッチワーク",
    "glitter": "グリッター",
    "holographic": "ホログラム加工",
    "metallic_foil": "箔プリント",
    "fringe": "フリンジ",
    "tassel": "タッセル",
    "pearl_trim": "パールトリム",
    "jewel_encrusted": "宝石装飾",
    "studs": "スタッズ",
    "printed_pattern": "プリント柄",
    "ribbon_embroidery": "リボン刺繍",
    "rhinestone": "ラインストーン",
    "frill_ruffle": "フリル",
    "chain_trim": "チェーン装飾",
    "feather_trim": "フェザートリム",
    "hand_painted": "手描きペイント",
    "batik_dye": "バティック染め",
    "indigo_dye": "藍染め",
    "sashiko_stitch": "刺し子",
    "kintsugi_seam": "金継ぎ風ステッチ",
    "origami_applique": "折り紙モチーフ",
    "kamon_emblem": "家紋風エンブレム",
    "bow_accent": "ボウタイ・蝶結び",
    "corset_lacing": "コルセットレース編み上げ",
    "crystal_beading": "クリスタルビーズ刺繍",
    "lace_overlay": "レースオーバーレイ",
    "velvet_trim": "ベルベットトリム",
    "silk_flower": "布花コサージュ",
    "ornate_buttons": "装飾ボタン",
    "piping_trim": "パイピング",
    "quilted_pattern": "キルティング",
    "drawstring_detail": "ドローストリング（絞り紐）",
    "corset_boning": "コルセットボーニング",
    "epaulette_trim": "エポレット（肩章）",
    "brocade_trim": "ブロケードトリム",
    "shibori_dye": "絞り染め",
    "yuzen_dye": "友禅染め",
    "katazome_stencil": "型染め",
    "pocket_square": "ポケットチーフ",
    "cufflinks_detail": "カフスボタン",
    "brass_buttons": "真鍮ボタン",
    "gothic_lace": "ゴシックレース",
    "cameo_brooch": "カメオブローチ",
    "bat_wing_applique": "コウモリ翼アップリケ",
    "graffiti_print": "グラフィティプリント",
    "distressed_denim": "ダメージデニム加工",
    "safety_pin_accent": "セーフティピン装飾",
    "patch_badges": "ワッペン・パッチ",
    "mesh_panel": "メッシュ切替",
    "reflective_strip": "反射材トリム",
    "bridal_veil_lace": "ブライダルベールレース",
    "zari_embroidery": "ザリ刺繍（金銀糸刺繍）",
    "mirror_work": "ミラーワーク刺繍",
    "block_print": "ブロックプリント",
    "ikat_weave": "イカット織り",
    "kente_pattern": "ケンテ織り柄",
    "fair_isle_knit": "フェアアイル編み柄",
    "damask_weave": "ダマスク織り",
    "toile_print": "トワル・ド・ジュイ柄",
    "frog_buttons": "チャイナボタン（組み紐留め）",
    "laser_cut_pattern": "レーザーカット柄",
    "led_light_trim": "LEDライトトリム",
    "custom": "自由入力",
}

# ═══════════════════════════════════════════════════════════════════
# 柄・模様（pattern）語彙
# ═══════════════════════════════════════════════════════════════════
PATTERN_VOCAB: dict[str, str] = {
    "none": "",
    "striped": "striped pattern",
    "polka_dot": "polka dot pattern",
    "floral": "floral pattern",
    "plaid": "plaid pattern",
    "checkered": "checkered pattern",
    "geometric": "geometric pattern",
    "animal_print": "animal print pattern",
    "camouflage": "camouflage pattern",
    "paisley": "paisley pattern",
    "houndstooth": "houndstooth pattern",
    # ★和柄（wagara）
    "seigaiha": "seigaiha, Japanese blue wave pattern",
    "asanoha": "asanoha, Japanese hemp-leaf geometric pattern",
    "ichimatsu": "ichimatsu, Japanese checkerboard pattern",
    "karakusa": "karakusa, Japanese arabesque vine pattern",
    "sakura_pattern": "sakura cherry blossom pattern",
    "kikkou": "kikkou, Japanese tortoiseshell hexagon pattern",
    "shippou": "shippou, Japanese interlocking circles pattern",
    "raimon": "raimon, Japanese thunder/key-fret pattern",
    "uroko": "uroko, Japanese triangular scale pattern",
    "tatewaku": "tatewaku, Japanese rising vapor stripe pattern",
    "sayagata": "sayagata, Japanese interlocking key-fret pattern",
    "kagome": "kagome, Japanese woven basket-weave star pattern",
    "matsukawabishi": "matsukawabishi, Japanese pine-bark diamond pattern",
    "yagasuri": "yagasuri, Japanese arrow-feather pattern",
    "hishi": "hishi, Japanese diamond lattice pattern",
    "kumo": "kumo, Japanese stylized cloud pattern",
    # ★世界の伝統柄
    "damask": "damask pattern",
    "toile": "toile de jouy pattern",
    "ikat": "ikat pattern",
    "kente": "kente cloth pattern",
    "fair_isle": "fair isle pattern",
    "tartan": "tartan pattern",
    "arabesque_tile": "arabesque geometric tile pattern",
    "mandala": "mandala pattern",
    "custom": "",
}

PATTERN_LABELS_JA: dict[str, str] = {
    "none": "なし",
    "striped": "ストライプ",
    "polka_dot": "水玉",
    "floral": "花柄",
    "plaid": "タータンチェック",
    "checkered": "チェック柄",
    "geometric": "幾何学模様",
    "animal_print": "アニマル柄",
    "camouflage": "迷彩柄",
    "paisley": "ペイズリー柄",
    "houndstooth": "千鳥格子",
    "seigaiha": "青海波",
    "asanoha": "麻の葉",
    "ichimatsu": "市松模様",
    "karakusa": "唐草模様",
    "sakura_pattern": "桜柄",
    "kikkou": "亀甲柄",
    "shippou": "七宝柄",
    "raimon": "雷紋",
    "uroko": "鱗文様",
    "tatewaku": "立涌",
    "sayagata": "紗綾形",
    "kagome": "籠目",
    "matsukawabishi": "松皮菱",
    "yagasuri": "矢絣",
    "hishi": "菱文様",
    "kumo": "雲文様",
    "damask": "ダマスク柄",
    "toile": "トワル・ド・ジュイ柄",
    "ikat": "絣（イカット）柄",
    "kente": "ケンテ柄",
    "fair_isle": "フェアアイル柄",
    "tartan": "タータン柄",
    "arabesque_tile": "アラベスク幾何学タイル柄",
    "mandala": "曼荼羅柄",
    "custom": "自由入力",
}

# ═══════════════════════════════════════════════════════════════════
# 素材・質感（material）語彙
# ═══════════════════════════════════════════════════════════════════
MATERIAL_VOCAB: dict[str, str] = {
    "none": "",
    "silk": "silk fabric",
    "leather": "leather texture",
    "denim": "denim fabric",
    "velvet": "velvet texture",
    "satin": "satin sheen",
    "lace": "lace fabric",
    "wool": "wool texture",
    "cotton": "cotton fabric",
    "chiffon": "sheer chiffon",
    "vinyl": "glossy vinyl",
    # ★和素材
    "washi": "washi paper texture, Japanese paper fabric",
    "chirimen": "chirimen, Japanese silk crepe texture",
    "kinran": "kinran, gold brocade fabric",
    "nishijin_ori": "nishijin-ori, Japanese woven brocade texture",
    "tsumugi": "tsumugi, Japanese hand-woven pongee silk texture",
    "hemp_asa": "asa, Japanese hemp fabric texture",
    "ramie": "ramie fabric texture",
    "nishiki_brocade": "nishiki, Japanese luxury brocade texture",
    "habutai": "habutai, smooth plain-weave silk texture",
    "rayon": "rayon fabric",
    "polyester": "polyester fabric",
    "organza": "sheer organza fabric",
    "tulle": "tulle netting fabric",
    "brocade_western": "brocade fabric texture",
    "tweed": "tweed fabric texture",
    "corduroy": "corduroy ribbed texture",
    "faux_fur": "faux fur texture",
    "neoprene": "neoprene fabric texture",
    "mesh_fabric": "sheer mesh fabric",
    "custom": "",
}

MATERIAL_LABELS_JA: dict[str, str] = {
    "none": "なし",
    "silk": "シルク",
    "leather": "レザー",
    "denim": "デニム",
    "velvet": "ベルベット",
    "satin": "サテン",
    "lace": "レース",
    "wool": "ウール",
    "cotton": "コットン",
    "chiffon": "シフォン",
    "vinyl": "ビニール（光沢）",
    "washi": "和紙",
    "chirimen": "ちりめん",
    "kinran": "金襴",
    "nishijin_ori": "西陣織",
    "tsumugi": "紬",
    "hemp_asa": "麻",
    "ramie": "苧麻（ラミー）",
    "nishiki_brocade": "錦",
    "habutai": "羽二重",
    "rayon": "レーヨン",
    "polyester": "ポリエステル",
    "organza": "オーガンジー",
    "tulle": "チュール",
    "brocade_western": "ブロケード",
    "tweed": "ツイード",
    "corduroy": "コーデュロイ",
    "faux_fur": "フェイクファー",
    "neoprene": "ネオプレン",
    "mesh_fabric": "メッシュ生地",
    "custom": "自由入力",
}

# ═══════════════════════════════════════════════════════════════════
# 色
# ═══════════════════════════════════════════════════════════════════
# 基本色パレット（自由入力の補助用。英語のまま）
BASE_COLORS: list[str] = [
    "black",
    "white",
    "red",
    "blue",
    "navy",
    "green",
    "yellow",
    "pink",
    "purple",
    "brown",
    "gray",
    "orange",
    "gold",
    "silver",
    "pastel",
    "beige",
    "cream",
    "burgundy",
    "teal",
    "custom",
]

# 日本の伝統色名 → (ローマ字読み, CLIPプロンプト向け英語表現, 16進カラーコード)
# color フィールドに「藍色」「ai-iro」のいずれを入力しても解決できるようにする。
TRADITIONAL_COLORS_JA: dict[str, dict[str, str]] = {
    "藍色": {"romaji": "ai-iro", "en": "deep indigo blue", "hex": "#1e50a2"},
    "茜色": {"romaji": "akane-iro", "en": "madder red", "hex": "#b7282e"},
    "山吹色": {"romaji": "yamabuki-iro", "en": "golden yellow", "hex": "#f8b500"},
    "若草色": {"romaji": "wakakusa-iro", "en": "young grass green", "hex": "#c3d825"},
    "桜色": {"romaji": "sakura-iro", "en": "pale cherry blossom pink", "hex": "#fef4f4"},
    "藤色": {"romaji": "fuji-iro", "en": "wisteria purple", "hex": "#bbaee0"},
    "鴇色": {"romaji": "toki-iro", "en": "pale ibis pink", "hex": "#f2a0a1"},
    "群青色": {"romaji": "gunjou-iro", "en": "ultramarine blue", "hex": "#4c6cb3"},
    "朱色": {"romaji": "shu-iro", "en": "vermillion red-orange", "hex": "#eb6238"},
    "抹茶色": {"romaji": "matcha-iro", "en": "matcha green", "hex": "#c5b358"},
    "紅色": {"romaji": "beni-iro", "en": "crimson red", "hex": "#cf3721"},
    "黄金色": {"romaji": "koganeiro", "en": "golden", "hex": "#e8b902"},
    "深緑": {"romaji": "fukamidori", "en": "deep forest green", "hex": "#00553e"},
    "白銀": {"romaji": "shirogane", "en": "silver white", "hex": "#c8c8cb"},
    "漆黒": {"romaji": "shikkoku", "en": "lacquer black", "hex": "#0e0e10"},
    "浅葱色": {"romaji": "asagi-iro", "en": "light blue-green", "hex": "#00a3af"},
    "紫紺": {"romaji": "shikon", "en": "deep bluish purple", "hex": "#460e44"},
    "生成り": {"romaji": "kinari", "en": "undyed off-white", "hex": "#f8f4e6"},
    "瑠璃色": {"romaji": "ruri-iro", "en": "lapis lazuli blue", "hex": "#1e50a2"},
    "萌黄色": {"romaji": "moegi-iro", "en": "fresh yellow-green", "hex": "#aacf53"},
    "紅梅色": {"romaji": "koubai-iro", "en": "plum blossom pink", "hex": "#e7609e"},
    "檜皮色": {"romaji": "hihada-iro", "en": "cypress bark brown", "hex": "#78384f"},
    "空色": {"romaji": "sora-iro", "en": "sky blue", "hex": "#8fd8d2"},
    "烏羽色": {"romaji": "karasuba-iro", "en": "raven black with blue sheen", "hex": "#211c1c"},
    "蘇芳": {"romaji": "suou", "en": "dark red-purple", "hex": "#9e3d3f"},
    "芥子色": {"romaji": "karashi-iro", "en": "mustard yellow", "hex": "#d6a418"},
    "東雲色": {"romaji": "shinonome-iro", "en": "dawn pink", "hex": "#f19072"},
    "常磐色": {"romaji": "tokiwa-iro", "en": "evergreen", "hex": "#007b43"},
    "撫子色": {"romaji": "nadeshiko-iro", "en": "soft pink carnation", "hex": "#ee9ca7"},
    "若竹色": {"romaji": "wakatake-iro", "en": "young bamboo green", "hex": "#68be8d"},
    "卯の花色": {"romaji": "unohana-iro", "en": "deutzia flower white", "hex": "#f5f2e9"},
    "千歳緑": {"romaji": "chitose-midori", "en": "ancient pine deep green", "hex": "#38534d"},
    "蒲公英色": {"romaji": "tanpopo-iro", "en": "dandelion yellow", "hex": "#fac03d"},
    "瓶覗": {"romaji": "kamenozoki", "en": "faint pale blue", "hex": "#a8d8ea"},
    "灰桜": {"romaji": "haizakura", "en": "ash-gray cherry pink", "hex": "#e8d3d1"},
    "銀鼠": {"romaji": "gin-nezu", "en": "silver gray", "hex": "#91989f"},
    "江戸紫": {"romaji": "edo-murasaki", "en": "edo purple", "hex": "#745399"},
    "桔梗色": {"romaji": "kikyou-iro", "en": "bellflower purple-blue", "hex": "#4c6cb3"},
}

# ── 服飾対象語（subject_hint）日本語→英語 ─────────────────────────────
SUBJECT_HINT_JA_TO_EN: dict[str, str] = {
    "服": "clothing",
    "衣服": "clothing",
    "ドレス": "dress",
    "ワンピース": "dress",
    "ジャケット": "jacket",
    "コート": "coat",
    "スカート": "skirt",
    "パンツ": "pants",
    "ズボン": "pants",
    "シャツ": "shirt",
    "ブラウス": "blouse",
    "セーター": "sweater",
    "パーカー": "hoodie",
    "制服": "uniform",
    "水着": "swimsuit",
    "着物": "kimono",
    "浴衣": "yukata",
    "帯": "obi",
    "靴": "shoes",
    "帽子": "hat",
    "手袋": "gloves",
    "バッグ": "bag",
    "スカーフ": "scarf",
    "マフラー": "scarf",
    "羽織": "haori",
    "袴": "hakama",
    "甚平": "jinbei",
    "ベスト": "vest",
    "タキシード": "tuxedo",
    "チャイナドレス": "cheongsam",
    "エプロン": "apron",
    "レインコート": "raincoat",
    "ケープ": "cape",
    "ボレロ": "bolero jacket",
    "サロペット": "overalls",
    "喪服": "mourning dress",
    "花嫁衣装": "wedding dress",
    "軍服": "military uniform",
    "白衣": "lab coat",
}

DEFAULT_NEGATIVE_TERMS: list[str] = [
    "blurry",
    "low quality",
    "distorted fabric",
    "extra clothing layers",
    "mismatched pattern",
    "seam artifacts",
    "unnatural texture",
]


@dataclass
class DecorationPromptResult:
    """Prompt Composer ノードの整形結果。"""

    decoration_prompt: str
    inpaint_prompt: str
    negative_prompt: str
    merged_prompt: str
    terms_used: list[str] = field(default_factory=list)
    negative_terms_used: list[str] = field(default_factory=list)
    resolved: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "decoration_prompt": self.decoration_prompt,
            "inpaint_prompt": self.inpaint_prompt,
            "negative_prompt": self.negative_prompt,
            "merged_prompt": self.merged_prompt,
            "terms_used": self.terms_used,
            "negative_terms_used": self.negative_terms_used,
            "resolved": self.resolved,
        }


# ═══════════════════════════════════════════════════════════════════
# 内部ヘルパー
# ═══════════════════════════════════════════════════════════════════

def _dedupe_list(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for t in terms:
        t = t.strip()
        if not t:
            continue
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def _dedupe_join(terms: list[str], sep: str = ", ") -> str:
    return sep.join(_dedupe_list(terms))


def bilingual_options(keys: list[str], labels_ja: dict[str, str]) -> list[str]:
    """ComfyUI ドロップダウン用に "english_key | 日本語ラベル" 形式のリストを作る。"""
    out = []
    for k in keys:
        ja = labels_ja.get(k)
        out.append(f"{k} | {ja}" if ja else k)
    return out


def bilingual_default(key: str, labels_ja: dict[str, str]) -> str:
    """bilingual_options() と同じ形式でデフォルト値の文字列を作る。"""
    ja = labels_ja.get(key)
    return f"{key} | {ja}" if ja else key


def resolve_key(raw: str, valid_keys: set[str] | dict, labels_ja: dict[str, str]) -> str:
    """
    "english_key"・"english_key | 日本語ラベル"・日本語ラベルそのもの の
    いずれを渡されても、辞書の正しい英語キーへ解決する。
    どれにも一致しない場合は raw をそのまま返す（未知値のフォールバック）。
    """
    if isinstance(valid_keys, dict):
        valid_keys = set(valid_keys.keys())
    if raw is None:
        return "none" if "none" in valid_keys else ""
    raw = raw.strip()
    if not raw:
        return "none" if "none" in valid_keys else raw
    if raw in valid_keys:
        return raw
    if " | " in raw:
        candidate = raw.split(" | ", 1)[0].strip()
        if candidate in valid_keys:
            return candidate
    for k, v in labels_ja.items():
        if v == raw:
            return k
    return raw


def _match_traditional_color(raw: str) -> dict[str, str] | None:
    """入力文字列を日本の伝統色辞書（漢字名 or ローマ字）から検索する。"""
    if not raw or not raw.strip():
        return None
    raw_stripped = raw.strip()
    if raw_stripped in TRADITIONAL_COLORS_JA:
        return TRADITIONAL_COLORS_JA[raw_stripped]
    lower = raw_stripped.lower()
    for entry in TRADITIONAL_COLORS_JA.values():
        if entry["romaji"].lower() == lower:
            return entry
    return None


def resolve_color_term(raw: str) -> str:
    """
    色名を CLIP プロンプト向けの英語表現に変換する。
    日本の伝統色名（漢字/ローマ字）に一致すればその英語表現を返し、
    一致しなければ入力をそのまま返す（"red" や "#ff0000" 等はそのまま通す）。
    """
    if not raw or not raw.strip():
        return ""
    match = _match_traditional_color(raw)
    return match["en"] if match else raw.strip()


def resolve_color_to_hex(raw: str) -> str:
    """
    色名を直接画像処理（Direct Paint）向けの16進カラーコードに変換する。
    日本の伝統色名に一致すればその hex を返し、一致しなければ入力を
    そのまま返す（'#rrggbb' や 'r,g,b' 形式はそのまま paint_ops 側で解釈される）。
    """
    if not raw or not raw.strip():
        return raw
    match = _match_traditional_color(raw)
    return match["hex"] if match else raw


def resolve_subject_hint(raw: str) -> str:
    """対象語（subject_hint）の日本語表記を英語のプロンプト語へ変換する。"""
    if not raw or not raw.strip():
        return "clothing"
    raw = raw.strip()
    return SUBJECT_HINT_JA_TO_EN.get(raw, raw)


# ═══════════════════════════════════════════════════════════════════
# メイン関数
# ═══════════════════════════════════════════════════════════════════

def build_decoration_prompt(
    decoration_preset: str = "none",
    pattern: str = "none",
    material: str = "none",
    color: str = "",
    free_text: str = "",
    subject_hint: str = "clothing",
    base_prompt: str = "",
    negative_extra: str = "",
) -> DecorationPromptResult:
    """
    プリセット選択＋自由入力から、装飾用プロンプト一式を組み立てる。

    decoration_preset / pattern / material は、英語キー・
    "english_key | 日本語ラベル"（ComfyUIドロップダウンの表示形式）・
    日本語ラベルそのもの のいずれでも指定できる。
    color / subject_hint は日本語の伝統色名・服飾用語にも対応する
    （例: color="藍色" や "ai-iro" → "deep indigo blue" に変換される）。

    Args:
        decoration_preset: DECORATION_PRESETS のキー（日本語ラベルも可）
        pattern:            PATTERN_VOCAB のキー（日本語ラベルも可）
        material:           MATERIAL_VOCAB のキー（日本語ラベルも可）
        color:               色（自由入力可。日本語の伝統色名にも対応）
        free_text:            追加の自由記述プロンプト
        subject_hint:          対象の呼称（既定 "clothing"。日本語も可）
        base_prompt:            既存プロンプト。指定すると末尾にマージした
                                merged_prompt を生成する
        negative_extra:          追加のネガティブプロンプト（カンマ区切り）

    Returns:
        DecorationPromptResult
    """
    preset_key = resolve_key(decoration_preset, DECORATION_PRESETS, DECORATION_LABELS_JA)
    pattern_key = resolve_key(pattern, PATTERN_VOCAB, PATTERN_LABELS_JA)
    material_key = resolve_key(material, MATERIAL_VOCAB, MATERIAL_LABELS_JA)
    color_term = resolve_color_term(color)
    subject_term = resolve_subject_hint(subject_hint)

    terms: list[str] = []

    if color_term:
        terms.append(color_term)

    terms.extend(DECORATION_PRESETS.get(preset_key, []))

    pattern_term = PATTERN_VOCAB.get(pattern_key, "")
    if pattern_term:
        terms.append(pattern_term)

    material_term = MATERIAL_VOCAB.get(material_key, "")
    if material_term:
        terms.append(material_term)

    if free_text.strip():
        terms.append(free_text.strip())

    terms = _dedupe_list(terms)
    decoration_prompt = _dedupe_join(terms)

    # inpaint_prompt: 対象語＋装飾語（インペイント系ノードにそのまま渡す想定）
    inpaint_terms = [subject_term] if subject_term else []
    inpaint_terms.extend(terms)
    inpaint_prompt = _dedupe_join(inpaint_terms)

    negative_terms = list(DEFAULT_NEGATIVE_TERMS)
    if negative_extra.strip():
        negative_terms.extend(t.strip() for t in negative_extra.split(",") if t.strip())
    negative_terms = _dedupe_list(negative_terms)
    negative_prompt = _dedupe_join(negative_terms)

    if base_prompt.strip():
        # base_prompt はカンマ区切りの既存タグ列として扱い、装飾語との重複を除く
        base_terms = [t.strip() for t in base_prompt.split(",") if t.strip()]
        merged_prompt = _dedupe_join(base_terms + terms)
    else:
        merged_prompt = decoration_prompt

    return DecorationPromptResult(
        decoration_prompt=decoration_prompt,
        inpaint_prompt=inpaint_prompt,
        negative_prompt=negative_prompt,
        merged_prompt=merged_prompt,
        terms_used=terms,
        negative_terms_used=negative_terms,
        resolved={
            "decoration_preset": preset_key,
            "pattern": pattern_key,
            "material": material_key,
            "color": color_term,
            "subject_hint": subject_term,
        },
    )
