"""Collapse signals into one verdict per attribute, then count them."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from catalog_check.checks import SCORED_ATTRIBUTES, check_row
from catalog_check.parse import is_blank
from catalog_check.quality import DEFECT_VERDICTS, applicable_attributes, score_counts
from catalog_check.signals import Signal

VERDICTS = ("supported", "contradicted", "contested", "invalid", "unverified", "unfilled")
REVIEW = {"contradicted", "contested", "invalid"}

# Sibling fields are often the same seller entry copied into a second column.
# They can confirm a value when the title is silent, but they cannot outvote the title.
RULE_SOURCE = {
    "taxonomy_gender": "taxonomy",
    "title_gender": "title",
    "title_color": "title",
    "color_fields": "sibling",
    "seller_brand": "sibling",
    "title_brand": "title",
    "title_sleeve": "title",
    "title_pattern": "title",
    "pack_text": "title",
    "pack_contents": "sibling",
    "title_product_type": "title",
    "title_material": "title",
    "sentinel": "schema",
    "audience_vocabulary": "schema",
    "pack_number": "schema",
    "size_shape": "schema",
}


@dataclass
class AttributeVerdict:
    attribute: str
    verdict: str
    signals: list[Signal]


@dataclass
class Evaluation:
    products: int = 0
    verdicts: dict[str, Counter[str]] = field(default_factory=dict)
    rules: Counter[tuple[str, str, str]] = field(default_factory=Counter)
    examples: dict[tuple[str, str], list[dict[str, str]]] = field(default_factory=lambda: defaultdict(list))
    review_rows: list[dict[str, str]] = field(default_factory=list)
    products_with_error: set[str] = field(default_factory=set)
    products_in_review: set[str] = field(default_factory=set)
    quality_applicable: int = 0
    quality_filled: int = 0
    quality_clean: int = 0
    quality_by_attribute: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))

    def __post_init__(self) -> None:
        for attribute in SCORED_ATTRIBUTES:
            self.verdicts.setdefault(attribute, Counter())


def resolve(attribute: str, filled: bool, signals: list[Signal]) -> AttributeVerdict:
    """One verdict per attribute.

    Invalid wins, because a placeholder is not rescued by a title that happens
    to look right. Support and contradiction together become contested: the
    checker refuses to call the value right or wrong when its own sources disagree.
    """
    own = [signal for signal in signals if signal.attribute == attribute]
    if not filled:
        return AttributeVerdict(attribute, "unfilled", [])
    invalids = [signal for signal in own if signal.kind == "invalid"]
    if invalids:
        return AttributeVerdict(attribute, "invalid", invalids)
    contras = [signal for signal in own if signal.kind == "contradict"]
    supports = [signal for signal in own if signal.kind == "support"]
    if any(RULE_SOURCE.get(signal.rule) == "title" for signal in contras):
        supports = [signal for signal in supports if RULE_SOURCE.get(signal.rule) != "sibling"]
    if contras and supports:
        return AttributeVerdict(attribute, "contested", contras + supports)
    if contras:
        return AttributeVerdict(attribute, "contradicted", contras)
    if supports:
        return AttributeVerdict(attribute, "supported", supports)
    return AttributeVerdict(attribute, "unverified", [])


def evaluate(rows: list[dict[str, str]], example_limit: int = 5) -> Evaluation:
    result = Evaluation()
    for row in rows:
        result.products += 1
        product_key = (row.get("product_key") or "").strip()
        signals = check_row(row)
        for signal in signals:
            result.rules[(signal.attribute, signal.rule, signal.kind)] += 1
        saw_error = False
        saw_review = False
        verdicts: dict[str, str] = {}
        for attribute in SCORED_ATTRIBUTES:
            verdict = resolve(attribute, not is_blank(row.get(attribute)), signals)
            verdicts[attribute] = verdict.verdict
            result.verdicts[attribute][verdict.verdict] += 1
            if verdict.verdict in {"contradicted", "invalid"}:
                saw_error = True
            if verdict.verdict in REVIEW:
                saw_review = True
                _store_examples(result, row, product_key, verdict, example_limit)
                _store_review(result, row, product_key, verdict)
        _add_quality(result, row.get("cms_vertical") or "", verdicts)
        if saw_error:
            result.products_with_error.add(product_key)
        if saw_review:
            result.products_in_review.add(product_key)
    return result


def _add_quality(result: Evaluation, cms_vertical: str, verdicts: dict[str, str]) -> None:
    for attribute in applicable_attributes(cms_vertical):
        verdict = verdicts.get(attribute, "unfilled")
        result.quality_applicable += 1
        bucket = result.quality_by_attribute[attribute]
        bucket["applicable"] += 1
        if verdict == "unfilled":
            bucket["missing"] += 1
        elif verdict in DEFECT_VERDICTS:
            result.quality_filled += 1
            bucket["defect"] += 1
        else:
            result.quality_filled += 1
            result.quality_clean += 1
            bucket["clean"] += 1


def quality_summary(result: Evaluation) -> dict:
    folded = score_counts(result.quality_applicable, result.quality_clean, result.quality_filled)
    by_attribute = {}
    for attribute, counts in result.quality_by_attribute.items():
        applicable = counts["applicable"]
        clean = counts["clean"]
        filled = clean + counts["defect"]
        folded_attribute = score_counts(applicable, clean, filled)
        by_attribute[attribute] = {
            "applicable": applicable,
            "clean": clean,
            "missing": counts["missing"],
            "defect": counts["defect"],
            **folded_attribute,
        }
    return {
        **folded,
        "applicable": result.quality_applicable,
        "clean": result.quality_clean,
        "filled": result.quality_filled,
        "missing": result.quality_applicable - result.quality_filled,
        "defect": result.quality_filled - result.quality_clean,
        "by_attribute": by_attribute,
        "reading": (
            "Share of applicable attribute values that are filled and undisputed. "
            "Equals completeness times correctness. Unverified filled values count as "
            "clean, so this is an upper bound: a value nobody could check still passes."
        ),
    }


def _store_examples(result: Evaluation, row: dict[str, str], product_key: str, verdict: AttributeVerdict, limit: int) -> None:
    key = (verdict.attribute, verdict.verdict)
    if len(result.examples[key]) >= limit:
        return
    signal = verdict.signals[0]
    result.examples[key].append(
        {
            "product_key": product_key,
            "attribute": verdict.attribute,
            "verdict": verdict.verdict,
            "rule": signal.rule,
            "value": signal.value,
            "title": (row.get("title") or "").replace("\n", " ")[:180],
            "explanation": signal.explanation,
        }
    )


def _store_review(result: Evaluation, row: dict[str, str], product_key: str, verdict: AttributeVerdict) -> None:
    title = (row.get("title") or "").replace("\n", " ")
    for signal in verdict.signals:
        if signal.kind == "support":
            continue
        result.review_rows.append(
            {
                "product_key": product_key,
                "attribute": verdict.attribute,
                "verdict": verdict.verdict,
                "rule": signal.rule,
                "confidence": signal.confidence,
                "value": signal.value,
                "evidence": signal.evidence,
                "title": title,
                "explanation": signal.explanation,
            }
        )


def rate(count: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return count / denominator
