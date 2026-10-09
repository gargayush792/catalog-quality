"""Normalizers and extractors.

Rules live in checks.py. This module only turns messy catalogue text into
sets of labels those rules can compare. Matching is literal and longest-phrase
first. There is no fuzzy edit distance: a one-character typo should stay
visible, while a known alias such as "3/4th" or "Embriodered" is mapped by hand.
"""

from __future__ import annotations

import re

_SENTINELS = {
    "na",
    "n/a",
    "n.a",
    "n.a.",
    "null",
    "none",
    "nil",
    "-",
    "--",
    ".",
    "not applicable",
    "undefined",
    "not available",
}

_AUDIENCE_TOKEN = {
    "men": "men",
    "man": "men",
    "women": "women",
    "woman": "women",
    "boys": "boys",
    "boy": "boys",
    "girls": "girls",
    "girl": "girls",
    "baby": None,
    "babies": None,
    "infant": None,
    "infants": None,
    "toddler": None,
    "toddlers": None,
    "unisex": "unisex",
    "couple": "unisex",
    "couples": "unisex",
    "kids": "kids",
    "kid": "kids",
    "children": "kids",
    "child": "kids",
    "and": None,
    "for": None,
    "all": None,
    "the": None,
    "of": None,
    "a": None,
    "an": None,
    "adult": None,
    "adults": None,
    "both": None,
    "only": None,
}

_TITLE_AUDIENCE = re.compile(
    r"\b(?:women's|womens|women|woman|girls'|girls|girl's|girl|boys'|boys|boy's|boy|men's|mens|men)\b",
    re.IGNORECASE,
)
_TITLE_AUDIENCE_MAP = {
    "women's": "women",
    "womens": "women",
    "women": "women",
    "woman": "women",
    "girls'": "girls",
    "girls": "girls",
    "girl's": "girls",
    "girl": "girls",
    "boys'": "boys",
    "boys": "boys",
    "boy's": "boys",
    "boy": "boys",
    "men's": "men",
    "mens": "men",
    "men": "men",
}

# "man" is omitted on purpose. It matches inside brand fragments and "human",
# and ecommerce titles use "Men", not "man".

OPPOSITE_GENDER = {"men": "women", "women": "men", "boys": "girls", "girls": "boys"}

# Longer phrases first so "light blue" is not also counted as "blue".
_COLOR_TERMS = [
    ("light blue", "blue"),
    ("dark blue", "blue"),
    ("navy blue", "blue"),
    ("sky blue", "blue"),
    ("royal blue", "blue"),
    ("light green", "green"),
    ("dark green", "green"),
    ("light pink", "pink"),
    ("hot pink", "pink"),
    ("off white", "white"),
    ("off-white", "white"),
    ("navy", "blue"),
    ("olive", "green"),
    ("mint", "green"),
    ("cream", "white"),
    ("ivory", "white"),
    ("charcoal", "grey"),
    ("gray", "grey"),
    ("grey", "grey"),
    ("maroon", "maroon"),
    ("meroon", "maroon"),
    ("burgundy", "maroon"),
    ("mustard", "yellow"),
    ("beige", "beige"),
    ("khaki", "beige"),
    ("tan", "beige"),
    ("black", "black"),
    ("white", "white"),
    ("blue", "blue"),
    ("pink", "pink"),
    ("green", "green"),
    ("red", "red"),
    ("brown", "brown"),
    ("yellow", "yellow"),
    ("orange", "orange"),
    ("purple", "purple"),
    ("violet", "purple"),
    ("lavender", "purple"),
    ("magenta", "pink"),
    ("peach", "pink"),
    ("teal", "teal"),
    ("turquoise", "teal"),
    ("blck", "black"),
    ("wht", "white"),
    ("multicolour", "multicolor"),
    ("multicolor", "multicolor"),
    ("multi color", "multicolor"),
    ("multi-color", "multicolor"),
    ("gold", "gold"),
    ("silver", "silver"),
    ("copper", "copper"),
]

# In a title these usually mean the metal or the plating, not the product color.
TITLE_METAL_COLORS = {"gold", "silver", "copper"}

_SLEEVE_LENGTH = [
    ("three quarter sleeve", "three_quarter"),
    ("three-quarter sleeve", "three_quarter"),
    ("three quarter sleeves", "three_quarter"),
    ("3/4th sleeve", "three_quarter"),
    ("3/4 sleeve", "three_quarter"),
    ("3/4 sleeves", "three_quarter"),
    ("full sleeves", "full"),
    ("full sleeve", "full"),
    ("long sleeves", "full"),
    ("long sleeve", "full"),
    ("half sleeves", "half"),
    ("half sleeve", "half"),
    ("short sleeves", "short"),
    ("short sleeve", "short"),
    ("sleeveless", "sleeveless"),
    ("no sleeves", "sleeveless"),
    ("no sleeve", "sleeveless"),
]

_PATTERN_TERMS = [
    ("graphic print", "graphic"),
    ("floral print", "floral"),
    ("polka print", "printed"),
    ("color block", "colorblock"),
    ("colour block", "colorblock"),
    ("colorblock", "colorblock"),
    ("colourblock", "colorblock"),
    ("embroidered", "embroidered"),
    ("embriodered", "embroidered"),
    ("embroidery", "embroidered"),
    ("checkered", "checkered"),
    ("checked", "checkered"),
    ("striped", "striped"),
    ("stripes", "striped"),
    ("printed", "printed"),
    ("print", "printed"),
    ("floral", "floral"),
    ("graphic", "graphic"),
    ("solid", "solid"),
    ("plain", "solid"),
]

# Attribute values that name a pattern plus a compatible parent.
_PATTERN_VALUE = {
    "solid": {"solid"},
    "solid/plain": {"solid"},
    "plain": {"solid"},
    "printed": {"printed"},
    "floral print": {"floral", "printed"},
    "graphic print": {"graphic", "printed"},
    "polka print": {"printed"},
    "typography": {"printed"},
    "striped": {"striped"},
    "checkered": {"checkered"},
    "checked": {"checkered"},
    "embroidered": {"embroidered"},
    "embriodered": {"embroidered"},
    "colorblock": {"colorblock"},
    "color block": {"colorblock"},
    "colourblock": {"colorblock"},
    "floral": {"floral"},
    "graphic": {"graphic"},
}

# Only these pairs are treated as mutually exclusive. Embroidered-and-printed
# can both be true of one garment, so that pair is not here.
PATTERN_ANTONYMS = {
    frozenset({"solid", "printed"}),
    frozenset({"solid", "striped"}),
    frozenset({"solid", "checkered"}),
    frozenset({"solid", "floral"}),
    frozenset({"solid", "colorblock"}),
    frozenset({"solid", "graphic"}),
    frozenset({"solid", "embroidered"}),
}

_MATERIAL_TERMS = [
    ("genuine leather", "leather"),
    ("artificial leather", "faux_leather"),
    ("synthetic leather", "faux_leather"),
    ("faux leather", "faux_leather"),
    ("pu leather", "faux_leather"),
    ("leatherette", "faux_leather"),
    ("leather", "leather"),
    ("cotton", "cotton"),
    ("polyester", "polyester"),
    ("nylon", "nylon"),
    ("silk", "silk"),
    ("wool", "wool"),
    ("denim", "denim"),
    ("canvas", "canvas"),
    ("linen", "linen"),
    ("rayon", "rayon"),
    ("chiffon", "chiffon"),
    ("georgette", "georgette"),
    ("velvet", "velvet"),
    ("mesh", "mesh"),
]

_GENERIC_MATERIALS = {
    "fabric",
    "synthetic",
    "plastic",
    "metal",
    "textile",
    "others",
    "other",
    "pvc",
    "eva",
    "rubber",
    "resin",
    "foam",
}

MATERIAL_ANTONYMS = {
    frozenset({"leather", "faux_leather"}),
    frozenset({"leather", "canvas"}),
    frozenset({"cotton", "polyester"}),
    frozenset({"cotton", "silk"}),
    frozenset({"cotton", "nylon"}),
    frozenset({"silk", "polyester"}),
}

# (name, regex, cms verticals that this noun is allowed to live in).
# Earlier rules consume their span so "t-shirt" is not also read as "shirt",
# and "earring" is not also read as "ring".
_TYPE_RULES: list[tuple[str, re.Pattern[str], frozenset[str]]] = [
    # Accessory phrases come first so "shirt stud" is not read as a shirt.
    ("shirt_stud", re.compile(r"\bshirts?\s+studs?\b", re.I), frozenset({"shirt_stud"})),
    ("shoe_lace", re.compile(r"\bshoes?\s+laces?\b", re.I), frozenset({"shoe_lace"})),
    ("watch_strap", re.compile(r"\bwatch(?:es)?\s+straps?\b", re.I), frozenset({"watch_strap"})),
    ("cover", re.compile(r"\b(?:sarees?|blouses?|shoes?|clothes|clothing|garments?)\s+covers?\b", re.I), frozenset({"garment_cover"})),
    ("nose_ring", re.compile(r"\bnose\s?(?:rings?|pins?|studs?)\b", re.I), frozenset({"nose_ring_stud"})),
    ("pendant", re.compile(r"\bpendants?\b|\blockets?\b", re.I), frozenset({"pendant_locket"})),
    ("pyjama", re.compile(r"\bpyjamas?\b|\bpajamas?\b", re.I), frozenset({"pyjama", "night_suit", "kids_nightwear"})),
    ("thermal", re.compile(r"\bthermals?\b", re.I), frozenset({"thermal", "kids_thermal"})),
    ("sweatshirt", re.compile(r"\bsweat\s?shirts?\b", re.I), frozenset({"sweatshirt"})),
    ("tshirt", re.compile(r"\bt[\s-]?shirts?\b", re.I), frozenset({"t_shirt", "kids_t_shirt"})),
    ("tracksuit", re.compile(r"\btrack\s?suits?\b", re.I), frozenset({"track_suit"})),
    ("sweatpant", re.compile(r"\bsweat\s?pants?\b", re.I), frozenset({"track_pant", "kids_track_pant"})),
    ("trackpant", re.compile(r"\btrack\s?pants?\b", re.I), frozenset({"track_pant", "kids_track_pant"})),
    ("capri", re.compile(r"\bcapris?\b", re.I), frozenset({"trouser", "jean"})),
    ("windcheater", re.compile(r"\bwind\s?cheaters?\b", re.I), frozenset({"windcheater", "jacket"})),
    ("nightwear", re.compile(r"\bnight\s?dress(?:es)?\b|\bnighties\b|\bnighty\b|\bnightwear\b|\bnight\s?suits?\b", re.I), frozenset({"night_dress_nighty", "night_suit", "kids_nightwear"})),
    ("earring", re.compile(r"\bear\s?rings?\b", re.I), frozenset({"earring"})),
    ("saree", re.compile(r"\bsarees?\b|\bsaris?\b", re.I), frozenset({"sari"})),
    ("lehenga", re.compile(r"\blehengas?\b", re.I), frozenset({"lehenga_choli", "kids_lehenga_choli"})),
    ("kurta", re.compile(r"\bkurtas?\b|\bkurtis?\b", re.I), frozenset({"kurta", "ethnic_set", "salwar_kurta_dupatta", "kids_ethnic_set"})),
    ("salwar", re.compile(r"\bsalwars?\b", re.I), frozenset({"salwar_kurta_dupatta", "ethnic_set"})),
    ("dupatta", re.compile(r"\bdupattas?\b", re.I), frozenset({"dupatta", "ethnic_set", "salwar_kurta_dupatta"})),
    ("petticoat", re.compile(r"\bpetticoats?\b", re.I), frozenset({"petticoat"})),
    ("blouse", re.compile(r"\bblouses?\b", re.I), frozenset({"blouse"})),
    ("jean", re.compile(r"\bjeans?\b", re.I), frozenset({"jean"})),
    ("trouser", re.compile(r"\btrousers?\b", re.I), frozenset({"trouser", "cargo"})),
    ("pant", re.compile(r"\bpants?\b", re.I), frozenset({"trouser", "track_pant", "pyjama", "cargo", "kids_track_pant", "harem_pant"})),
    ("short", re.compile(r"\bshorts?\b(?!\s+(?:sleeves?|mangalsutras?|necklaces?|kurtas?|kurtis?|dress(?:es)?|gowns?|coats?)\b)", re.I), frozenset({"short", "kids_short"})),
    ("coat", re.compile(r"\bcoats?\b", re.I), frozenset({"coat", "jacket"})),
    ("costume", re.compile(r"\bcostumes?\b", re.I), frozenset({"kid_costume_wear"})),
    ("shirt", re.compile(r"\bshirts?\b", re.I), frozenset({"shirt"})),
    ("dress", re.compile(r"\bdress(?:es)?\b", re.I), frozenset({"dress", "kids_dress", "gown"})),
    ("gown", re.compile(r"\bgowns?\b", re.I), frozenset({"gown", "dress"})),
    ("skirt", re.compile(r"\bskirts?\b", re.I), frozenset({"skirt"})),
    ("legging", re.compile(r"\bleggings?\b|\bjeggings?\b", re.I), frozenset({"legging", "tight", "jegging"})),
    ("jacket", re.compile(r"\bjackets?\b", re.I), frozenset({"jacket"})),
    ("blazer", re.compile(r"\bblazers?\b", re.I), frozenset({"blazer", "jacket"})),
    ("sweater", re.compile(r"\bsweaters?\b", re.I), frozenset({"sweater"})),
    ("hoodie", re.compile(r"\bhoodies?\b", re.I), frozenset({"sweatshirt"})),
    ("sandal", re.compile(r"\bsandals?\b", re.I), frozenset({"sandal", "kids_sandal"})),
    ("flipflop", re.compile(r"\bflip\s?flops?\b|\bslippers?\b", re.I), frozenset({"slipper_flip_flop"})),
    ("shoe", re.compile(r"\bshoes?\b|\bsneakers?\b", re.I), frozenset({"shoe", "kids_shoe"})),
    ("bra", re.compile(r"\bbralettes?\b|\bbras?\b", re.I), frozenset({"bra", "lingerie_set", "bra_extender"})),
    ("brief", re.compile(r"\bbriefs?\b|\bboxers?\b|\btrunks?\b", re.I), frozenset({"brief", "boxer"})),
    ("panty", re.compile(r"\bpanties\b|\bpanty\b", re.I), frozenset({"panty"})),
    ("vest", re.compile(r"\bvests?\b", re.I), frozenset({"vest"})),
    ("sock", re.compile(r"\bsocks?\b", re.I), frozenset({"sock"})),
    ("watch", re.compile(r"\bwatches?\b|\bwatch\b", re.I), frozenset({"watch"})),
    ("necklace", re.compile(r"\bnecklaces?\b", re.I), frozenset({"necklace_chain"})),
    ("bangle", re.compile(r"\bbangles?\b|\bbracelets?\b", re.I), frozenset({"bangle_bracelet_armlet"})),
    ("ring", re.compile(r"\brings?\b", re.I), frozenset({"ring"})),
    ("backpack", re.compile(r"\bbackpacks?\b", re.I), frozenset({"backpack", "rucksack", "bag"})),
    ("cap", re.compile(r"\bcaps?\b(?!\s+sleeves?\b)", re.I), frozenset({"cap", "kids_cap"})),
    ("belt", re.compile(r"\bbelts?\b", re.I), frozenset({"belt"})),
    ("sunglass", re.compile(r"\bsunglasses\b", re.I), frozenset({"sunglass"})),
    ("camisole", re.compile(r"\bcamisoles?\b", re.I), frozenset({"camisole_slip"})),
    ("shrug", re.compile(r"\bshrugs?\b", re.I), frozenset({"shrug"})),
    ("wallet", re.compile(r"\bwallets?\b", re.I), frozenset({"wallet_card_wallet"})),
]

COMBO_CMS = frozenset(
    {
        "kids_apparel_combo",
        "apparel_set",
        "ethnic_set",
        "salwar_kurta_dupatta",
        "night_suit",
        "track_suit",
        "lingerie_set",
        "jewellery_set",
        "kids_ethnic_set",
    }
)

_SHOE_NEGATIVE = re.compile(
    r"\b(?:cream|polish|polishing|cleaner|cleaning|spray|shampoo|charger|eliminator|maintenance)\b",
    re.I,
)
# "Blouse Material" and "Shirt Fabric" are unstitched goods. "PU Material" on a
# shoe title also matches; the shoe noun is still allowed alongside fabric.
_FABRIC_SALE = re.compile(r"\b(?:fabrics?|materials?|unstitched)\b", re.I)
_COMBO_WORD = re.compile(r"\b(?:co[\s-]?ords?|combos?|sets?)\b", re.I)
# "Top Shorts" and "Top - Pyjama" are co-ords. "Top" alone is not a product noun:
# it also means "top quality".
_COORD_PAIR = re.compile(
    r"\btops?\b\s*(?:&|and|,|/|-)?\s*(?:shorts?|pants?|skirts?|pyjamas?|pajamas?|leggings?|jeggings?|jackets?|capris?)\b",
    re.I,
)
_STYLING_CUT = re.compile(
    r"\b(?:pair(?:ed)?(?:\s+it)?\s+with|team(?:\s+it)?\s+with|wear\s+it\s+with)\b",
    re.I,
)
_PACK = re.compile(r"\b(?:pack|set|combo)\s+of\s+(\d{1,3})\b", re.I)


def without_brands(title: str, *brands: str) -> str:
    """Remove brand strings before reading color or product type out of a title.

    "PRATHAM BLUE" is a brand, not a blue product. "DAKU SHOES" is a brand, not
    a shoe. The brand check itself still sees the original title.
    """
    text = title or ""
    for brand in brands:
        brand = (brand or "").strip()
        if len(brand) >= 3:
            text = re.sub(re.escape(brand), " ", text, count=1, flags=re.I)
    return text


def is_blank(value: str | None) -> bool:
    return not (value or "").strip()


def is_sentinel(value: str | None) -> bool:
    return (value or "").strip().lower() in _SENTINELS


def norm_brand(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def brands_compatible(left: str, right: str) -> bool:
    """True when the two brand strings are the same name after light normalization.

    Containment covers the cases that are not really two brands: plurals
    ("Creation" / "Creations"), apostrophes ("HOC's" / "HOC"), and a line name
    inside a longer brand ("Adrenex by Ecommerce" / "Adrenex"). A one-character
    difference that does not contain the other string stays incompatible, so
    typos such as "BG TEX" / "BG TAX" are still flagged.
    """
    a, b = norm_brand(left), norm_brand(right)
    if not a or not b:
        return False
    if a == b:
        return True
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    return len(short) >= 3 and short in long


def taxonomy_audience(super_category: str) -> set[str] | None:
    """The audience implied by the analytics bucket, or None if the bucket is ungendered."""
    name = (super_category or "").strip()
    if not name or name.upper() == "NA":
        return None
    if name.startswith("Mens"):
        return {"men"}
    if name.startswith("Women"):
        return {"women"}
    if name.startswith("Kid"):
        return {"boys", "girls"}
    return None


def parse_audience(value: str) -> set[str] | None:
    """Parse ideal_for into a set of genders.

    Returns None when the cell contains words that are not an audience. That is
    an invalid value, not an unknown gender. "Unisex" comes back as {"unisex"}
    so callers can abstain instead of treating it as men or women.
    """
    tokens = re.findall(r"[a-z]+", (value or "").lower())
    if not tokens:
        return None
    genders: set[str] = set()
    for token in tokens:
        if token not in _AUDIENCE_TOKEN:
            return None
        mapped = _AUDIENCE_TOKEN[token]
        if mapped:
            genders.add(mapped)
    if not genders:
        return None
    if "unisex" in genders:
        return {"unisex"}
    if "kids" in genders:
        genders.discard("kids")
        genders.update({"boys", "girls"})
    return genders


def title_audience(title: str, *brands: str) -> set[str] | None:
    """Genders named in the title, after the brand string is removed.

    Returns None when the title names genders that conflict with each other
    (men and women, or an adult and a child). Those titles are keyword-stuffed
    and are not evidence. Returns an empty set when no audience is mentioned.
    "Boys" and "girls" together are kept: that is a real kids audience.
    """
    text = without_brands(title, *brands)
    found = {_TITLE_AUDIENCE_MAP[match.group(0).lower()] for match in _TITLE_AUDIENCE.finditer(text)}
    if not found:
        return set()
    adults = found & {"men", "women"}
    children = found & {"boys", "girls"}
    if adults and children:
        return None
    if len(adults) > 1:
        return None
    return found


def _scan_terms(text: str, terms: list[tuple[str, str]], skip: set[str] | None = None) -> set[str]:
    """Map a string to label families, consuming each character once."""
    hay = (text or "").lower()
    occupied = [False] * len(hay)
    found: set[str] = set()
    for phrase, label in terms:
        if skip and label in skip:
            continue
        start = 0
        while True:
            index = hay.find(phrase, start)
            if index < 0:
                break
            end = index + len(phrase)
            before_ok = index == 0 or not hay[index - 1].isalpha()
            after_ok = end == len(hay) or not hay[end].isalpha()
            if before_ok and after_ok and not any(occupied[index:end]):
                for position in range(index, end):
                    occupied[position] = True
                found.add(label)
            start = index + 1
    return found


def color_families(value: str, skip_metals: bool = False) -> set[str]:
    skip = TITLE_METAL_COLORS if skip_metals else None
    return _scan_terms(value, _COLOR_TERMS, skip=skip)


def sleeve_length(value: str) -> str | None:
    hay = (value or "").lower()
    for phrase, label in _SLEEVE_LENGTH:
        if re.search(r"\b" + re.escape(phrase) + r"\b", hay):
            return label
    return None


def pattern_families_in_value(value: str) -> set[str]:
    key = re.sub(r"\s+", " ", (value or "").strip().lower())
    if key in _PATTERN_VALUE:
        return set(_PATTERN_VALUE[key])
    # Fall back to the same phrase list used on titles, for values like "Floral".
    return _scan_terms(key, _PATTERN_TERMS)


def pattern_families_in_text(value: str) -> set[str]:
    return _scan_terms(value, _PATTERN_TERMS)


def material_families(value: str) -> set[str] | None:
    """Families named in a material string.

    None means the value is generic ("Fabric", "Synthetic") and makes no claim
    a title can confirm or deny. An empty set means it names nothing we know.
    """
    key = (value or "").strip().lower()
    if key in _GENERIC_MATERIALS:
        return None
    return _scan_terms(key, _MATERIAL_TERMS)


def pack_counts(*texts: str) -> set[int]:
    counts: set[int] = set()
    for text in texts:
        for match in _PACK.finditer(text or ""):
            number = int(match.group(1))
            if number > 0:
                counts.add(number)
    return counts


def integer_count(value: str) -> int | None:
    text = (value or "").strip()
    if text.isdigit():
        number = int(text)
        return number if number > 0 else None
    return None


def product_type_allowed(title: str, *brands: str) -> frozenset[str] | None:
    """CMS verticals the title's product nouns are allowed to belong to.

    None means the title did not name a product type we recognize, so the
    vertical is unverified rather than wrong. A styling clause ("pair it with
    jeans") is cut off before matching, so the suggested outfit is not treated
    as the product. Two garment nouns, or the word set / co-ord, also allow the
    combo verticals. Brand text is removed first.
    """
    text = without_brands(title, *brands)
    styling = _STYLING_CUT.search(text)
    if styling:
        text = text[: styling.start()]
    occupied = [False] * len(text)
    allowed: set[str] = set()
    hits = 0
    for name, pattern, cms_values in _TYPE_RULES:
        for match in pattern.finditer(text):
            start, end = match.span()
            if any(occupied[start:end]):
                continue
            if name == "shoe" and _SHOE_NEGATIVE.search(text):
                continue
            for position in range(start, end):
                occupied[position] = True
            allowed.update(cms_values)
            hits += 1
    if hits >= 2 or (hits >= 1 and (_COMBO_WORD.search(text) or _COORD_PAIR.search(text))):
        allowed.update(COMBO_CMS)
    if _FABRIC_SALE.search(text):
        allowed.add("fabric")
    if not allowed:
        return None
    return frozenset(allowed)


def cms_compatible(cms: str, allowed: frozenset[str]) -> bool:
    """True when the vertical is the one the title named, including a kids or uniform variant.

    kids_panty is the kids form of panty. uniform_shirt is a shirt. shirt_stud is
    not: only a qualifier in front of the product word counts, not a word after it.
    """
    if cms in allowed:
        return True
    bases: set[str] = set()
    for prefix in ("kids_", "kid_", "uniform_"):
        if cms.startswith(prefix):
            bases.add(cms[len(prefix) :])
    return bool(bases & set(allowed))


def antonym_conflict(left: set[str], right: set[str], antonyms: set[frozenset[str]]) -> bool:
    """True when the two sets are disjoint and some pair is an antonym split across them."""
    if not left or not right or left & right:
        return False
    for item in left:
        for other in right:
            if frozenset((item, other)) in antonyms:
                return True
    return False
