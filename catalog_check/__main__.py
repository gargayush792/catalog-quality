"""Read a catalogue slice and write the correctness report."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from catalog_check.checks import SCORED_ATTRIBUTES
from catalog_check.evaluate import Evaluation, quality_summary, rate, evaluate

DEFAULT_CSV = Path(
    "/Users/ayushgarg/Downloads/Copy of Copy of catalog_slice_v1 - catalog_slice_v1.csv"
)

REVIEW_FIELDS = (
    "product_key",
    "attribute",
    "verdict",
    "rule",
    "confidence",
    "value",
    "evidence",
    "title",
    "explanation",
)


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def summary_payload(result: Evaluation) -> dict:
    attributes = {}
    for attribute in SCORED_ATTRIBUTES:
        counts = result.verdicts[attribute]
        filled = result.products - counts["unfilled"]
        judged_clean = counts["supported"] + counts["contradicted"] + counts["invalid"]
        attributes[attribute] = {
            "filled": filled,
            "supported": counts["supported"],
            "contradicted": counts["contradicted"],
            "contested": counts["contested"],
            "invalid": counts["invalid"],
            "unverified": counts["unverified"],
            "detected_error_rate": _round(rate(counts["contradicted"] + counts["invalid"], filled)),
            "contested_rate": _round(rate(counts["contested"], filled)),
            "supported_rate": _round(rate(counts["supported"], filled)),
            "consistency_among_uncontested": _round(rate(counts["supported"], judged_clean)),
        }
    rules = [
        {"attribute": attribute, "rule": rule, "kind": kind, "count": count}
        for (attribute, rule, kind), count in sorted(result.rules.items())
    ]
    examples = [
        example
        for key in sorted(result.examples)
        for example in result.examples[key]
    ]
    return {
        "products": result.products,
        "catalog_quality": quality_summary(result),
        "products_with_detected_error": len(result.products_with_error),
        "products_in_review_queue": len(result.products_in_review),
        "attributes": attributes,
        "rules": rules,
        "examples": examples,
        "definitions": {
            "supported": "A second source agrees and none disagrees.",
            "contradicted": "A second source disagrees and none agrees.",
            "contested": "One source agrees and another disagrees. Queued for review, not counted as an error.",
            "invalid": "The value is not a possible value for the attribute.",
            "unverified": "Filled, but nothing else on the row can confirm or deny it. Not counted as correct.",
            "detected_error_rate": "(contradicted + invalid) / filled.",
            "catalog_quality_score": "clean applicable values / applicable values. Equals completeness × correctness.",
            "completeness": "filled applicable values / applicable values.",
            "correctness": "undisputed filled values / filled applicable values. Contested values are not undisputed.",
        },
    }


def render_report(result: Evaluation) -> str:
    payload = summary_payload(result)
    quality = payload["catalog_quality"]
    lines = [
        "Catalogue quality",
        f"Products: {result.products}",
        "",
        f"Catalog Quality Score: {_pct(quality['catalog_quality_score'])}%",
        f"  completeness {_pct(quality['completeness'])}%  ×  correctness {_pct(quality['correctness'])}%",
        (
            f"  {quality['clean']} clean / {quality['applicable']} applicable values"
            f"  ({quality['missing']} missing, {quality['defect']} disputed or invalid)"
        ),
        "A value is clean when it is filled and no check disputes it.",
        "Missing values lower completeness. Disputed values lower correctness.",
        "",
        f"{'attribute':<18} {'applies':>8} {'clean':>8} {'missing':>8} {'defect':>8} {'score%':>8}",
    ]
    for attribute, stats in quality["by_attribute"].items():
        lines.append(
            f"{attribute:<18} {stats['applicable']:8d} {stats['clean']:8d} {stats['missing']:8d} "
            f"{stats['defect']:8d} {_pct(stats['catalog_quality_score']):>8}"
        )
    lines.extend(
        [
            "",
            "Correctness detail",
            "Detected error rate is (contradicted + invalid) / filled, on every filled value, not only applicable ones.",
            "Contested is excluded there and included in the quality score: a disputed value is not clean.",
            "",
        ]
    )
    lines.extend(
        [
            f"Products with a detected error (contradicted or invalid): {len(result.products_with_error)}",
            f"Products in the review queue (those, plus contested): {len(result.products_in_review)}",
            "",
            f"{'attribute':<18} {'filled':>8} {'support':>8} {'contrad':>8} {'contest':>8} {'invalid':>8} {'unverif':>8} {'error%':>8} {'contest%':>8}",
        ]
    )
    for attribute, stats in payload["attributes"].items():
        lines.append(
            f"{attribute:<18} {stats['filled']:8d} {stats['supported']:8d} {stats['contradicted']:8d} "
            f"{stats['contested']:8d} {stats['invalid']:8d} {stats['unverified']:8d} "
            f"{_pct(stats['detected_error_rate']):>8} {_pct(stats['contested_rate']):>8}"
        )
    lines.extend(["", "Rules", f"{'attribute':<18} {'rule':<24} {'kind':<12} {'count':>8}"])
    for rule in payload["rules"]:
        lines.append(f"{rule['attribute']:<18} {rule['rule']:<24} {rule['kind']:<12} {rule['count']:8d}")
    lines.extend(["", "Examples"])
    shown = 0
    for example in payload["examples"]:
        if example["verdict"] == "supported":
            continue
        if shown >= 24:
            break
        shown += 1
        lines.append(
            f"- [{example['verdict']}] {example['attribute']} {example['product_key']}: {example['explanation']}"
        )
        lines.append(f"  title: {example['title']}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(result: Evaluation, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = summary_payload(result)
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (out_dir / "report.txt").write_text(render_report(result), encoding="utf-8")
    with (out_dir / "review.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(result.review_rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check correctness of catalogue attributes.")
    parser.add_argument("csv", nargs="?", type=Path, help="Path to the catalogue CSV.")
    parser.add_argument("--out", type=Path, default=Path("output"), help="Directory for summary.json, report.txt, and review.csv.")
    args = parser.parse_args(argv)
    path = args.csv or DEFAULT_CSV
    if not path.is_file():
        print(f"Catalogue file not found: {path}", file=sys.stderr)
        return 1
    rows = load_rows(path)
    result = evaluate(rows)
    write_outputs(result, args.out)
    print(render_report(result))
    print(f"Wrote {args.out / 'summary.json'}")
    print(f"Wrote {args.out / 'report.txt'}")
    print(f"Wrote {args.out / 'review.csv'} ({len(result.review_rows)} review rows)")
    return 0


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}"


if __name__ == "__main__":
    raise SystemExit(main())
