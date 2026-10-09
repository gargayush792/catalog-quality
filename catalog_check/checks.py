"""One function per attribute. Each function returns evidence or nothing.

Returning nothing is a decision: the row does not contain an independent source,
so the value stays unverified. A check does not guess.
"""

from __future__ import annotations

from catalog_check.parse import (
    MATERIAL_ANTONYMS,
    OPPOSITE_GENDER,
    PATTERN_ANTONYMS,
    antonym_conflict,
    brands_compatible,
    cms_compatible,
    color_families,
    integer_count,
    is_blank,
    is_sentinel,
    material_families,
    pack_counts,
    parse_audience,
    pattern_families_in_text,
    pattern_families_in_value,
    product_type_allowed,
    sleeve_length,
    taxonomy_audience,
    title_audience,
    without_brands,
)
from catalog_check.signals import Signal, contradict, invalid, support

SCORED_ATTRIBUTES = (
    "ideal_for",
    "color",
    "color_code",
    "brand",
    "sleeve",
    "pattern",
    "pack_of",
    "cms_vertical",
    "material",
    "outer_material",
    "size",
)


def _cell(row: dict[str, str], name: str) -> str:
    return (row.get(name) or "").strip()


def _title(row: dict[str, str]) -> str:
    """Title with the brand removed, so a brand token is not read as a color or a product type."""
    return without_brands(_cell(row, "title"), _cell(row, "brand"), _cell(row, "seller_entered_brand"))


def check_row(row: dict[str, str]) -> list[Signal]:
    signals: list[Signal] = []
    signals.extend(check_ideal_for(row))
    signals.extend(check_color(row))
    signals.extend(check_brand(row))
    signals.extend(check_sleeve(row))
    signals.extend(check_pattern(row))
    signals.extend(check_pack(row))
    signals.extend(check_cms_vertical(row))
    signals.extend(check_material_field(row, "material"))
    signals.extend(check_material_field(row, "outer_material"))
    signals.extend(check_size(row))
    return signals


def check_ideal_for(row: dict[str, str]) -> list[Signal]:
    value = _cell(row, "ideal_for")
    if is_blank(value):
        return []
    if is_sentinel(value):
        return [invalid("ideal_for", "sentinel", value, f"ideal_for is {value!r}, which is a placeholder, not an audience.")]
    audience = parse_audience(value)
    if audience is None:
        return [
            invalid(
                "ideal_for",
                "audience_vocabulary",
                value,
                "ideal_for is not an audience. The cell contains product copy or some other free text.",
            )
        ]
    if audience == {"unisex"}:
        return []

    signals: list[Signal] = []
    expected = taxonomy_audience(_cell(row, "analytic_super_category"))
    if expected is not None:
        bucket = _cell(row, "analytic_super_category")
        if audience.isdisjoint(expected):
            signals.append(
                contradict(
                    "ideal_for",
                    "taxonomy_gender",
                    "high",
                    value,
                    bucket,
                    f"ideal_for is {value!r}, but {bucket} is a { _audience_phrase(expected) } category. "
                    "At least one of the two is wrong.",
                )
            )
        elif audience == expected or audience < expected:
            signals.append(
                support(
                    "ideal_for",
                    "taxonomy_gender",
                    "medium",
                    value,
                    bucket,
                    f"ideal_for {value!r} agrees with {bucket}.",
                )
            )

    titled = title_audience(_title(row))
    if titled:
        if len(titled) == 1:
            named = next(iter(titled))
            opposite = OPPOSITE_GENDER[named]
            if opposite in audience and named not in audience:
                signals.append(
                    contradict(
                        "ideal_for",
                        "title_gender",
                        "high",
                        value,
                        named,
                        f"ideal_for is {value!r}, but the title names {named} and not {value!r}. "
                        "Women versus girls is ignored here: titles say 'for girls' on adult products.",
                    )
                )
        if titled == audience:
            signals.append(
                support(
                    "ideal_for",
                    "title_gender",
                    "medium",
                    value,
                    ", ".join(sorted(titled)),
                    f"The title names the same audience as ideal_for ({value!r}).",
                )
            )
    return signals


def check_color(row: dict[str, str]) -> list[Signal]:
    """Color and color_code are scored separately and used as evidence for each other.

    Gold, silver, and copper in the title are not read as colors. On jewellery
    they are the metal. A title that lists several colors supports a value when
    the attribute is one of those colors; it contradicts only when the attribute
    is none of them.
    """
    signals: list[Signal] = []
    color = _cell(row, "color")
    code = _cell(row, "color_code")
    title = _title(row)
    # Metals stay in title_all so "Gold" can confirm a gold attribute. They are
    # removed from title_plain so "Gold" cannot condemn a different color.
    title_all = color_families(title, skip_metals=False)
    title_plain = color_families(title, skip_metals=True)
    code_colors = color_families(code) if code and not is_sentinel(code) else set()

    if color and not is_blank(color):
        signals.extend(_color_attribute_signals("color", color, title_all, title_plain, code_colors, code))
    if code and not is_blank(code):
        signals.extend(_color_attribute_signals("color_code", code, title_all, title_plain, color_families(color), color))
    return signals


def _color_attribute_signals(
    attribute: str,
    value: str,
    title_all: set[str],
    title_plain: set[str],
    other_colors: set[str],
    other_raw: str,
) -> list[Signal]:
    if is_sentinel(value):
        return [invalid(attribute, "sentinel", value, f"{attribute} is {value!r}, which is a placeholder, not a color.")]
    own = color_families(value)
    if not own:
        return []
    signals: list[Signal] = []
    if own == {"multicolor"}:
        if len(title_plain) >= 2:
            signals.append(
                support(
                    attribute,
                    "title_color",
                    "medium",
                    value,
                    ", ".join(sorted(title_plain)),
                    f"{attribute} is Multicolor and the title names more than one color.",
                )
            )
        if len(other_colors - {"multicolor"}) >= 2:
            signals.append(
                support(
                    attribute,
                    "color_fields",
                    "high",
                    value,
                    other_raw,
                    f"{attribute} is Multicolor and the other color field names more than one color.",
                )
            )
        return signals

    own_concrete = own - {"multicolor"}
    # "Multicolor" in the title describes a print. It does not deny a specific color.
    title_specific = (title_all if not own_concrete.isdisjoint(_METAL_COLORS) else title_plain) - {"multicolor"}
    if title_specific & own_concrete:
        signals.append(
            support(
                attribute,
                "title_color",
                "medium",
                value,
                ", ".join(sorted(title_specific)),
                f"{attribute} {value!r} is one of the colors named in the title.",
            )
        )
    elif title_specific and own_concrete.isdisjoint(_METAL_COLORS):
        signals.append(
            contradict(
                attribute,
                "title_color",
                "medium",
                value,
                ", ".join(sorted(title_specific)),
                f"{attribute} is {value!r}, but the title names {', '.join(sorted(title_specific))} "
                "and does not name that color.",
            )
        )
    other_concrete = other_colors - {"multicolor"}
    if other_concrete & own_concrete:
        signals.append(
            support(
                attribute,
                "color_fields",
                "high",
                value,
                other_raw,
                f"{attribute} {value!r} agrees with the other color field {other_raw!r}. "
                "Dark Blue and Blue are the same color.",
            )
        )
    elif other_concrete and other_concrete.isdisjoint(own_concrete):
        signals.append(
            contradict(
                attribute,
                "color_fields",
                "high",
                value,
                other_raw,
                f"{attribute} is {value!r}, but the other color field is {other_raw!r}.",
            )
        )
    return signals


_METAL_COLORS = {"gold", "silver", "copper"}


def check_brand(row: dict[str, str]) -> list[Signal]:
    value = _cell(row, "brand")
    seller = _cell(row, "seller_entered_brand")
    title = _cell(row, "title")
    if is_blank(value):
        return []
    if is_sentinel(value):
        return [invalid("brand", "sentinel", value, f"brand is {value!r}, which is a placeholder, not a brand.")]
    signals: list[Signal] = []
    if seller and not is_sentinel(seller) and not brands_compatible(value, seller):
        signals.append(
            contradict(
                "brand",
                "seller_brand",
                "high",
                value,
                seller,
                f"brand is {value!r} and seller_entered_brand is {seller!r}. "
                "After ignoring case, punctuation, and a shorter name contained in a longer one, "
                "these are different brands, so at least one is wrong.",
            )
        )
    if len(value) >= 3 and value.lower() in title.lower():
        signals.append(
            support(
                "brand",
                "title_brand",
                "medium",
                value,
                value,
                f"The title contains the brand {value!r}.",
            )
        )
    return signals


def check_sleeve(row: dict[str, str]) -> list[Signal]:
    value = _cell(row, "sleeve")
    if is_blank(value):
        return []
    if is_sentinel(value):
        return [invalid("sleeve", "sentinel", value, f"sleeve is {value!r}, which is a placeholder, not a sleeve.")]
    own = sleeve_length(value)
    titled = sleeve_length(_title(row))
    if not own or not titled:
        # "Puff Sleeves" is a style, not a length. A length in the title does
        # not contradict it, and a length we cannot read is left unverified.
        return []
    if own == titled:
        return [
            support(
                "sleeve",
                "title_sleeve",
                "medium",
                value,
                titled,
                f"sleeve {value!r} matches the sleeve length in the title. "
                "Sellers often copy the same phrase into both, so this confirmation is weak.",
            )
        ]
    return [
        contradict(
            "sleeve",
            "title_sleeve",
            "high",
            value,
            titled,
            f"sleeve is {value!r} ({own}), but the title says {titled.replace('_', ' ')}.",
        )
    ]


def check_pattern(row: dict[str, str]) -> list[Signal]:
    value = _cell(row, "pattern")
    if is_blank(value):
        return []
    if is_sentinel(value):
        return [invalid("pattern", "sentinel", value, f"pattern is {value!r}, which is a placeholder, not a pattern.")]
    own = pattern_families_in_value(value)
    titled = pattern_families_in_text(_title(row))
    if not own or not titled:
        return []
    if own & titled:
        return [
            support(
                "pattern",
                "title_pattern",
                "medium",
                value,
                ", ".join(sorted(titled)),
                f"pattern {value!r} agrees with the title. Floral Print counts as printed.",
            )
        ]
    if antonym_conflict(own, titled, PATTERN_ANTONYMS):
        return [
            contradict(
                "pattern",
                "title_pattern",
                "medium",
                value,
                ", ".join(sorted(titled)),
                f"pattern is {value!r}, but the title says {', '.join(sorted(titled))}. "
                "Only direct opposites are flagged. Embroidered versus printed is not, "
                "because one garment can be both.",
            )
        ]
    return []


def check_pack(row: dict[str, str]) -> list[Signal]:
    value = _cell(row, "pack_of")
    if is_blank(value):
        return []
    if is_sentinel(value):
        return [invalid("pack_of", "sentinel", value, f"pack_of is {value!r}, which is a placeholder, not a count.")]
    own = integer_count(value)
    if own is None:
        return [invalid("pack_of", "pack_number", value, f"pack_of is {value!r}, which is not a positive whole number.")]
    # The title and the sales-package line are seller text. contents_in_sales_package
    # is a sibling field and is used only when it disagrees: agreement between
    # pack_of and contents is usually the same number typed twice.
    signals: list[Signal] = []
    mentioned = pack_counts(_title(row), _cell(row, "sales_package"))
    if mentioned == {own}:
        signals.append(
            support(
                "pack_of",
                "pack_text",
                "high",
                value,
                str(own),
                f"pack_of {own} agrees with the pack count written in the title or sales package.",
            )
        )
    elif mentioned and own not in mentioned:
        shown = ", ".join(str(item) for item in sorted(mentioned))
        signals.append(
            contradict(
                "pack_of",
                "pack_text",
                "high",
                value,
                shown,
                f"pack_of is {own}, but the title or sales package says pack of {shown}.",
            )
        )
    contents = integer_count(_cell(row, "contents_in_sales_package"))
    if contents is not None and contents != own:
        signals.append(
            contradict(
                "pack_of",
                "pack_contents",
                "high",
                value,
                str(contents),
                f"pack_of is {own}, but contents_in_sales_package is {contents}.",
            )
        )
    return signals


def check_cms_vertical(row: dict[str, str]) -> list[Signal]:
    value = _cell(row, "cms_vertical")
    if is_blank(value):
        return []
    if is_sentinel(value):
        return [invalid("cms_vertical", "sentinel", value, f"cms_vertical is {value!r}, which is a placeholder, not a product type.")]
    allowed = product_type_allowed(_cell(row, "title"), _cell(row, "brand"), _cell(row, "seller_entered_brand"))
    if allowed is None:
        return []
    if cms_compatible(value, allowed):
        return [
            support(
                "cms_vertical",
                "title_product_type",
                "medium",
                value,
                value,
                f"cms_vertical {value!r} matches a product noun in the title.",
            )
        ]
    return [
        contradict(
            "cms_vertical",
            "title_product_type",
            "medium",
            value,
            ", ".join(sorted(allowed)),
            f"cms_vertical is {value!r}, but the title names a product whose vertical is one of "
            f"{', '.join(sorted(allowed))}. A combo title is allowed to sit in a set vertical. "
            "Words after 'pair it with' are ignored.",
        )
    ]


def check_material_field(row: dict[str, str], attribute: str) -> list[Signal]:
    value = _cell(row, attribute)
    if is_blank(value):
        return []
    if is_sentinel(value):
        return [invalid(attribute, "sentinel", value, f"{attribute} is {value!r}, which is a placeholder, not a material.")]
    own = material_families(value)
    if own is None or not own:
        return []
    titled = material_families(_title(row))
    if not titled:
        return []
    if own & titled:
        return [
            support(
                attribute,
                "title_material",
                "medium",
                value,
                ", ".join(sorted(titled)),
                f"{attribute} {value!r} agrees with a material named in the title.",
            )
        ]
    if antonym_conflict(own, titled, MATERIAL_ANTONYMS):
        return [
            contradict(
                attribute,
                "title_material",
                "medium",
                value,
                ", ".join(sorted(titled)),
                f"{attribute} is {value!r}, but the title names {', '.join(sorted(titled))}.",
            )
        ]
    return []


def check_size(row: dict[str, str]) -> list[Signal]:
    """Size has no chart in this extract, so only impossible values are judged.

    An empty size is a completeness miss. A size of "M" or "30" or "5 - 6 Years"
    cannot be called wrong without the vertical's size chart and, for shoes,
    the size is usually only in the title.
    """
    value = _cell(row, "size")
    if is_blank(value):
        return []
    if is_sentinel(value) or len(value) > 40 or len(value.split()) > 6:
        return [
            invalid(
                "size",
                "size_shape",
                value,
                f"size is {value!r}, which is a placeholder or a sentence rather than a size.",
            )
        ]
    return []


def _audience_phrase(genders: set[str]) -> str:
    if genders == {"men"}:
        return "men's"
    if genders == {"women"}:
        return "women's"
    if genders == {"boys", "girls"}:
        return "kids'"
    return " / ".join(sorted(genders))
