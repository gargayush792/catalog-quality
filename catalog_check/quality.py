"""The one catalogue quality number.

Catalog Quality Score = clean applicable values / applicable values.

An applicable value is clean when the cell is filled and no check disputes it.
Supported and unverified both count as clean. Unverified is filled and
undisputed, which is not the same thing as proven true, so the score is an
upper bound on real quality.

The score factors:

    score = completeness × correctness
    completeness = filled / applicable
    correctness  = clean / filled

A missing value lowers completeness. A contradicted, invalid, or contested
value is filled, so it lowers correctness and not completeness. Contested
counts as not clean: the row's own evidence disagrees, so the value is not
something we would ship without a look.

Which attributes apply depends on the product type. A necklace is not missing
a sleeve. A shoe is missing a size. Brand, audience, color, and product type
apply to every product.
"""

from __future__ import annotations

DEFECT_VERDICTS = frozenset({"contradicted", "invalid", "contested"})
CLEAN_VERDICTS = frozenset({"supported", "unverified"})

_BASE = ("brand", "ideal_for", "color", "cms_vertical")
_JEWELLERY = (
    "earring",
    "necklace",
    "pendant",
    "locket",
    "bangle",
    "bracelet",
    "mangalsutra",
    "jewellery",
    "jewelry",
    "brooch",
    "kamarband",
    "anklet",
    "nose_ring",
    "nose_pin",
)
_BAGS = ("backpack", "rucksack", "wallet", "duffel", "messenger", "sling", "handbag")
_FOOTWEAR = ("shoe", "sandal", "slipper", "flip_flop", "boot", "loafer")
_NO_SIZE = ("lace", "cream", "polish", "stud", "strap", "cover")
_TOPS = (
    "t_shirt",
    "shirt",
    "kurta",
    "kurti",
    "sweatshirt",
    "sweater",
    "jacket",
    "dress",
    "blouse",
    "gown",
    "shrug",
    "blazer",
    "tunic",
    "nighty",
    "night_dress",
    "hoodie",
    "windcheater",
    "camisole",
    "vest",
)
_BOTTOMS = (
    "jean",
    "trouser",
    "track_pant",
    "legging",
    "jegging",
    "skirt",
    "cargo",
    "harem",
    "palazzo",
    "pyjama",
    "tight",
)
_OUTFITS = (
    "ethnic_set",
    "apparel_combo",
    "apparel_set",
    "salwar",
    "lehenga",
    "track_suit",
    "night_suit",
)
_NO_SLEEVE = ("bra", "panty", "brief", "boxer", "sock", "lingerie")


def applicable_attributes(cms_vertical: str) -> tuple[str, ...]:
    """Attributes a listing of this type is expected to have."""
    name = (cms_vertical or "").strip().lower()
    if not name or name == "na":
        return _BASE
    if any(token in name for token in _JEWELLERY) or name in {"ring"}:
        return _BASE
    if name == "bag" or name.endswith("_bag") or any(token in name for token in _BAGS):
        return _BASE
    if any(token in name for token in _NO_SIZE):
        return _BASE
    if "fabric" in name or name in {"watch", "sunglass", "frame"}:
        return _BASE
    if any(token in name for token in _FOOTWEAR):
        return _BASE + ("size", "outer_material")
    if "sari" in name:
        return _BASE + ("pattern", "size")
    if any(token in name for token in _NO_SLEEVE):
        return _BASE + ("pattern", "size")

    is_top = any(token in name for token in _TOPS) or name.endswith("_top") or name == "top"
    is_bottom = any(token in name for token in _BOTTOMS) or name.endswith("short") or "_short" in name
    is_outfit = any(token in name for token in _OUTFITS)
    if is_outfit or (is_top and not is_bottom):
        return _BASE + ("pattern", "size", "sleeve")
    if is_bottom and not is_top:
        return _BASE + ("pattern", "size")
    if is_top and is_bottom:
        return _BASE + ("pattern", "size", "sleeve")
    return _BASE


def score_counts(applicable: int, clean: int, filled: int) -> dict[str, float | None]:
    """Fold slot counts into the one score and its two factors."""
    if applicable == 0:
        return {"catalog_quality_score": None, "completeness": None, "correctness": None}
    completeness = filled / applicable
    correctness = (clean / filled) if filled else None
    return {
        "catalog_quality_score": clean / applicable,
        "completeness": completeness,
        "correctness": correctness,
    }
