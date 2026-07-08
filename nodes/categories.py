"""
nodes/categories.py — 語彙辞書の大項目・中項目カテゴリ分類

nodes/vocabulary.py のフラットな辞書（DECORATION_PRESETS 等）はそのまま
維持しつつ、このモジュールで各キーに「大項目（major）」「中項目（mid）」の
分類を付与する。ComfyUI のドロップダウンではこの分類を使って
"[大項目 > 中項目] english_key | 日本語ラベル" の形式でグルーピング表示する。

分類階層:
  - decoration_preset: 大項目7 × 中項目2〜3（2階層）
  - pattern / material / color(TRADITIONAL_COLORS_JA) / subject_hint:
    大項目のみ（1階層）。項目数が decoration_preset ほど多くないため、
    中項目までは分割せず大項目のみで分類する。

torch / ComfyUI に依存しない純粋データ + 関数のため、単体テスト可能。
"""

from __future__ import annotations

from . import vocabulary

# ═══════════════════════════════════════════════════════════════════
# 装飾技法プリセット（decoration_preset）— 大項目 × 中項目
# ═══════════════════════════════════════════════════════════════════

DECORATION_MAJOR_LABELS_JA: dict[str, str] = {
    "embroidery_beadwork": "刺繍・ビーズ手芸",
    "trim_edging": "トリム・縁飾り",
    "dye_print": "染色・プリント技法",
    "weave_construction": "織り・構造技法",
    "hardware_fastener": "金具・留め具",
    "finish_effect": "加工・仕上げ効果",
    "theme_style": "テーマ・スタイル装飾",
}

# (大項目キー, 中項目キー) -> 中項目の日本語ラベル
DECORATION_MID_LABELS_JA: dict[tuple[str, str], str] = {
    ("embroidery_beadwork", "embroidery"): "刺繍技法",
    ("embroidery_beadwork", "beadwork"): "ビーズ・宝飾",
    ("embroidery_beadwork", "applique"): "アップリケ・パッチ",
    ("trim_edging", "lace_ribbon"): "レース・リボン",
    ("trim_edging", "fringe_tassel"): "フリンジ・タッセル・羽根",
    ("trim_edging", "piping_brocade"): "パイピング・ブロケード",
    ("dye_print", "japanese_dye"): "和染め技法",
    ("dye_print", "world_dye"): "世界の染め技法",
    ("dye_print", "print_technique"): "プリント技法",
    ("weave_construction", "weave_pattern"): "織り柄技法",
    ("weave_construction", "quilt_layer"): "キルト・重ね構造",
    ("hardware_fastener", "buttons_studs"): "ボタン・スタッズ",
    ("hardware_fastener", "lacing_binding"): "編み上げ・留め構造",
    ("finish_effect", "shine_sparkle"): "光沢・煌めき",
    ("finish_effect", "hand_craft"): "手仕事・アート",
    ("finish_effect", "tech_modern"): "テクノロジー系",
    ("theme_style", "gothic_punk"): "ゴシック・パンク",
    ("theme_style", "bridal_formal"): "ブライダル・フォーマル",
    ("theme_style", "ethnic_world"): "民族衣装モチーフ",
    ("none_custom", "none_custom"): "（分類なし）",
}

# 装飾プリセットキー -> (大項目キー, 中項目キー)
DECORATION_CATEGORY_OF: dict[str, tuple[str, str]] = {
    # ── 刺繍・ビーズ手芸 ──
    "embroidery": ("embroidery_beadwork", "embroidery"),
    "ribbon_embroidery": ("embroidery_beadwork", "embroidery"),
    "sashiko_stitch": ("embroidery_beadwork", "embroidery"),
    "zari_embroidery": ("embroidery_beadwork", "embroidery"),
    "mirror_work": ("embroidery_beadwork", "embroidery"),
    "huipil_embroidery": ("embroidery_beadwork", "embroidery"),
    "sequins": ("embroidery_beadwork", "beadwork"),
    "beading": ("embroidery_beadwork", "beadwork"),
    "pearl_trim": ("embroidery_beadwork", "beadwork"),
    "jewel_encrusted": ("embroidery_beadwork", "beadwork"),
    "rhinestone": ("embroidery_beadwork", "beadwork"),
    "crystal_beading": ("embroidery_beadwork", "beadwork"),
    "cameo_brooch": ("embroidery_beadwork", "beadwork"),
    "floral_applique": ("embroidery_beadwork", "applique"),
    "bat_wing_applique": ("embroidery_beadwork", "applique"),
    "origami_applique": ("embroidery_beadwork", "applique"),
    "patch_badges": ("embroidery_beadwork", "applique"),
    "silk_flower": ("embroidery_beadwork", "applique"),
    "kamon_emblem": ("embroidery_beadwork", "applique"),
    # ── トリム・縁飾り ──
    "lace_trim": ("trim_edging", "lace_ribbon"),
    "ribbon_bow": ("trim_edging", "lace_ribbon"),
    "lace_overlay": ("trim_edging", "lace_ribbon"),
    "bow_accent": ("trim_edging", "lace_ribbon"),
    "fringe": ("trim_edging", "fringe_tassel"),
    "tassel": ("trim_edging", "fringe_tassel"),
    "feather_trim": ("trim_edging", "fringe_tassel"),
    "chain_trim": ("trim_edging", "fringe_tassel"),
    "epaulette_trim": ("trim_edging", "fringe_tassel"),
    "piping_trim": ("trim_edging", "piping_brocade"),
    "brocade_trim": ("trim_edging", "piping_brocade"),
    "velvet_trim": ("trim_edging", "piping_brocade"),
    "frill_ruffle": ("trim_edging", "piping_brocade"),
    # ── 染色・プリント技法 ──
    "indigo_dye": ("dye_print", "japanese_dye"),
    "shibori_dye": ("dye_print", "japanese_dye"),
    "yuzen_dye": ("dye_print", "japanese_dye"),
    "katazome_stencil": ("dye_print", "japanese_dye"),
    "tie_dye": ("dye_print", "world_dye"),
    "batik_dye": ("dye_print", "world_dye"),
    "gradient_dye": ("dye_print", "world_dye"),
    "ikat_weave": ("dye_print", "world_dye"),
    "shweshwe_print": ("dye_print", "world_dye"),
    "thermochromic_dye": ("dye_print", "world_dye"),
    "printed_pattern": ("dye_print", "print_technique"),
    "graffiti_print": ("dye_print", "print_technique"),
    "toile_print": ("dye_print", "print_technique"),
    "block_print": ("dye_print", "print_technique"),
    "laser_cut_pattern": ("dye_print", "print_technique"),
    "uv_reactive_print": ("dye_print", "print_technique"),
    # ── 織り・構造技法 ──
    "patchwork": ("weave_construction", "weave_pattern"),
    "damask_weave": ("weave_construction", "weave_pattern"),
    "kente_pattern": ("weave_construction", "weave_pattern"),
    "fair_isle_knit": ("weave_construction", "weave_pattern"),
    "quilted_pattern": ("weave_construction", "quilt_layer"),
    "mesh_panel": ("weave_construction", "quilt_layer"),
    "distressed_denim": ("weave_construction", "quilt_layer"),
    "3d_printed_lattice": ("weave_construction", "quilt_layer"),
    # ── 金具・留め具 ──
    "ornate_buttons": ("hardware_fastener", "buttons_studs"),
    "brass_buttons": ("hardware_fastener", "buttons_studs"),
    "studs": ("hardware_fastener", "buttons_studs"),
    "safety_pin_accent": ("hardware_fastener", "buttons_studs"),
    "frog_buttons": ("hardware_fastener", "buttons_studs"),
    "cufflinks_detail": ("hardware_fastener", "buttons_studs"),
    "pocket_square": ("hardware_fastener", "buttons_studs"),
    "corset_lacing": ("hardware_fastener", "lacing_binding"),
    "corset_boning": ("hardware_fastener", "lacing_binding"),
    "drawstring_detail": ("hardware_fastener", "lacing_binding"),
    "hanbok_ribbon": ("hardware_fastener", "lacing_binding"),
    # ── 加工・仕上げ効果 ──
    "glitter": ("finish_effect", "shine_sparkle"),
    "holographic": ("finish_effect", "shine_sparkle"),
    "metallic_foil": ("finish_effect", "shine_sparkle"),
    "reflective_strip": ("finish_effect", "shine_sparkle"),
    "hand_painted": ("finish_effect", "hand_craft"),
    "kintsugi_seam": ("finish_effect", "hand_craft"),
    "led_light_trim": ("finish_effect", "tech_modern"),
    "smart_fiber_circuitry": ("finish_effect", "tech_modern"),
    # ── テーマ・スタイル装飾 ──
    "gothic_lace": ("theme_style", "gothic_punk"),
    "spiked_leather_harness": ("theme_style", "gothic_punk"),
    "chain_harness_accent": ("theme_style", "gothic_punk"),
    "bridal_veil_lace": ("theme_style", "bridal_formal"),
    "tiered_bridal_lace": ("theme_style", "bridal_formal"),
    "ivory_satin_bow": ("theme_style", "bridal_formal"),
    "cathedral_train_lace": ("theme_style", "bridal_formal"),
}

# ═══════════════════════════════════════════════════════════════════
# 柄（pattern）— 大項目のみ
# ═══════════════════════════════════════════════════════════════════

PATTERN_MAJOR_LABELS_JA: dict[str, str] = {
    "geometric": "幾何学柄",
    "nature_motif": "自然モチーフ柄",
    "wagara": "和柄",
    "world_textile": "世界の織物柄",
}

PATTERN_CATEGORY_OF: dict[str, str] = {
    "striped": "geometric",
    "polka_dot": "geometric",
    "plaid": "geometric",
    "checkered": "geometric",
    "geometric": "geometric",
    "houndstooth": "geometric",
    "arabesque_tile": "geometric",
    "mandala": "geometric",
    "damask": "geometric",
    "hishi": "geometric",
    "gingham": "geometric",
    "chevron": "geometric",
    "herringbone": "geometric",
    "ogee": "geometric",
    "floral": "nature_motif",
    "animal_print": "nature_motif",
    "camouflage": "nature_motif",
    "paisley": "nature_motif",
    "sakura_pattern": "nature_motif",
    "kumo": "nature_motif",
    "seigaiha": "wagara",
    "asanoha": "wagara",
    "ichimatsu": "wagara",
    "karakusa": "wagara",
    "kikkou": "wagara",
    "shippou": "wagara",
    "raimon": "wagara",
    "uroko": "wagara",
    "tatewaku": "wagara",
    "sayagata": "wagara",
    "kagome": "wagara",
    "matsukawabishi": "wagara",
    "yagasuri": "wagara",
    "toile": "world_textile",
    "ikat": "world_textile",
    "kente": "world_textile",
    "fair_isle": "world_textile",
    "tartan": "world_textile",
}

# ═══════════════════════════════════════════════════════════════════
# 素材（material）— 大項目のみ
# ═══════════════════════════════════════════════════════════════════

MATERIAL_MAJOR_LABELS_JA: dict[str, str] = {
    "natural_fiber": "天然繊維",
    "japanese_textile": "和素材",
    "synthetic_fiber": "化学繊維",
    "special_texture": "特殊質感",
}

MATERIAL_CATEGORY_OF: dict[str, str] = {
    "silk": "natural_fiber",
    "wool": "natural_fiber",
    "cotton": "natural_fiber",
    "cashmere": "natural_fiber",
    "angora": "natural_fiber",
    "washi": "japanese_textile",
    "chirimen": "japanese_textile",
    "kinran": "japanese_textile",
    "nishijin_ori": "japanese_textile",
    "tsumugi": "japanese_textile",
    "hemp_asa": "japanese_textile",
    "ramie": "japanese_textile",
    "nishiki_brocade": "japanese_textile",
    "habutai": "japanese_textile",
    "rayon": "synthetic_fiber",
    "polyester": "synthetic_fiber",
    "spandex_lycra": "synthetic_fiber",
    "pu_leather": "synthetic_fiber",
    "neoprene": "synthetic_fiber",
    "leather": "special_texture",
    "denim": "special_texture",
    "velvet": "special_texture",
    "satin": "special_texture",
    "lace": "special_texture",
    "chiffon": "special_texture",
    "vinyl": "special_texture",
    "organza": "special_texture",
    "tulle": "special_texture",
    "brocade_western": "special_texture",
    "tweed": "special_texture",
    "corduroy": "special_texture",
    "faux_fur": "special_texture",
    "mesh_fabric": "special_texture",
}

# ═══════════════════════════════════════════════════════════════════
# 伝統色（TRADITIONAL_COLORS_JA）— 大項目のみ（色系統）
# ═══════════════════════════════════════════════════════════════════

COLOR_MAJOR_LABELS_JA: dict[str, str] = {
    "red_family": "紅・赤系統",
    "blue_family": "藍・青系統",
    "green_family": "緑系統",
    "yellow_orange_family": "黄・橙系統",
    "purple_family": "紫系統",
    "neutral_family": "白・黒・鼠系統",
}

COLOR_CATEGORY_OF: dict[str, str] = {
    "茜色": "red_family",
    "朱色": "red_family",
    "紅色": "red_family",
    "桜色": "red_family",
    "鴇色": "red_family",
    "紅梅色": "red_family",
    "撫子色": "red_family",
    "灰桜": "red_family",
    "東雲色": "red_family",
    "桃色": "red_family",
    "藍色": "blue_family",
    "群青色": "blue_family",
    "浅葱色": "blue_family",
    "瑠璃色": "blue_family",
    "空色": "blue_family",
    "瓶覗": "blue_family",
    "鉄紺": "blue_family",
    "若草色": "green_family",
    "深緑": "green_family",
    "抹茶色": "green_family",
    "若竹色": "green_family",
    "千歳緑": "green_family",
    "常磐色": "green_family",
    "若苗色": "green_family",
    "萌黄色": "green_family",
    "山吹色": "yellow_orange_family",
    "黄金色": "yellow_orange_family",
    "芥子色": "yellow_orange_family",
    "蒲公英色": "yellow_orange_family",
    "柿色": "yellow_orange_family",
    "藤色": "purple_family",
    "紫紺": "purple_family",
    "江戸紫": "purple_family",
    "桔梗色": "purple_family",
    "京紫": "purple_family",
    "白銀": "neutral_family",
    "漆黒": "neutral_family",
    "生成り": "neutral_family",
    "卯の花色": "neutral_family",
    "銀鼠": "neutral_family",
    "烏羽色": "neutral_family",
    "檜皮色": "neutral_family",
    "蘇芳": "red_family",
}

# ═══════════════════════════════════════════════════════════════════
# 対象語（SUBJECT_HINT_JA_TO_EN）— 大項目のみ
# ═══════════════════════════════════════════════════════════════════

SUBJECT_MAJOR_LABELS_JA: dict[str, str] = {
    "japanese_wear": "和装",
    "western_formal": "洋装フォーマル",
    "western_casual": "洋装カジュアル",
    "outerwear": "アウター",
    "accessory_item": "小物・その他",
}

SUBJECT_CATEGORY_OF: dict[str, str] = {
    "着物": "japanese_wear",
    "浴衣": "japanese_wear",
    "帯": "japanese_wear",
    "羽織": "japanese_wear",
    "袴": "japanese_wear",
    "甚平": "japanese_wear",
    "ドレス": "western_formal",
    "ワンピース": "western_formal",
    "制服": "western_formal",
    "水着": "western_formal",
    "タキシード": "western_formal",
    "チャイナドレス": "western_formal",
    "喪服": "western_formal",
    "花嫁衣装": "western_formal",
    "軍服": "western_formal",
    "スーツ": "western_formal",
    "ドレスシャツ": "western_formal",
    "シャツ": "western_casual",
    "ブラウス": "western_casual",
    "セーター": "western_casual",
    "パーカー": "western_casual",
    "スカート": "western_casual",
    "パンツ": "western_casual",
    "ズボン": "western_casual",
    "ベスト": "western_casual",
    "サロペット": "western_casual",
    "白衣": "western_casual",
    "エプロン": "western_casual",
    "服": "western_casual",
    "衣服": "western_casual",
    "ジャケット": "outerwear",
    "コート": "outerwear",
    "レインコート": "outerwear",
    "ケープ": "outerwear",
    "ボレロ": "outerwear",
    "マント": "outerwear",
    "靴": "accessory_item",
    "帽子": "accessory_item",
    "手袋": "accessory_item",
    "バッグ": "accessory_item",
    "スカーフ": "accessory_item",
    "マフラー": "accessory_item",
}


# ═══════════════════════════════════════════════════════════════════
# 共通ヘルパー
# ═══════════════════════════════════════════════════════════════════

def grouped_decoration_options() -> list[str]:
    """
    decoration_preset を大項目→中項目の順でグルーピングし、
    "[大項目 > 中項目] english_key | 日本語ラベル" 形式のリストを返す。
    ComfyUI のドロップダウンにそのまま渡せる。
    """
    keys = list(vocabulary.DECORATION_PRESETS.keys())

    def sort_key(k: str) -> tuple[str, str, str]:
        major, mid = DECORATION_CATEGORY_OF.get(k, ("none_custom", "none_custom"))
        return (major, mid, k)

    ordered = sorted(keys, key=sort_key)
    out = []
    for k in ordered:
        major, mid = DECORATION_CATEGORY_OF.get(k, ("none_custom", "none_custom"))
        ja = vocabulary.DECORATION_LABELS_JA.get(k, "")
        if major == "none_custom":
            out.append(f"{k} | {ja}" if ja else k)
        else:
            major_ja = DECORATION_MAJOR_LABELS_JA.get(major, major)
            mid_ja = DECORATION_MID_LABELS_JA.get((major, mid), mid)
            out.append(f"[{major_ja} > {mid_ja}] {k} | {ja}")
    return out


def grouped_default_decoration(key: str) -> str:
    """grouped_decoration_options() と同じ形式でデフォルト値文字列を作る。"""
    for opt in grouped_decoration_options():
        body = opt.split("] ", 1)[-1]
        if body.split(" | ", 1)[0] == key:
            return opt
    return key


def resolve_grouped_key(raw: str) -> str:
    """
    "[大項目 > 中項目] key | ja" / "key | ja" / "key" / 日本語ラベル の
    いずれからも英語キーを取り出す（先頭のグループラベルだけを取り除く）。
    残りは vocabulary.resolve_key 側でさらに解決される。
    """
    if raw is None:
        return ""
    raw = raw.strip()
    if "] " in raw:
        raw = raw.split("] ", 1)[1]
    return raw


def grouped_single_level_options(
    keys: list[str],
    labels_ja: dict[str, str],
    category_of: dict[str, str],
    major_labels: dict[str, str],
) -> list[str]:
    """pattern/material/color/subject_hint 用: 大項目のみでグルーピングした選択肢を返す。"""

    def sort_key(k: str) -> tuple[str, str]:
        return (category_of.get(k, "zzz_other"), k)

    ordered = sorted(keys, key=sort_key)
    out = []
    for k in ordered:
        major = category_of.get(k)
        ja = labels_ja.get(k, "")
        label = f"{k} | {ja}" if ja else k
        if major:
            out.append(f"[{major_labels.get(major, major)}] {label}")
        else:
            out.append(label)
    return out


def category_map_summary() -> dict[str, dict[str, list[str]]]:
    """decoration_preset の大項目→中項目→キー一覧をネスト辞書で返す（デバッグ/テスト用）。"""
    summary: dict[str, dict[str, list[str]]] = {}
    for key, (major, mid) in DECORATION_CATEGORY_OF.items():
        summary.setdefault(major, {}).setdefault(mid, []).append(key)
    return summary
