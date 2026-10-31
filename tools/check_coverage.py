"""Write a source-module coverage report and enforce the documented minimum."""

from __future__ import annotations

import argparse
import configparser
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def coverage_percent(summary: dict, covered_key: str, total_key: str) -> float:
    total = summary.get(total_key, 0)
    return 100.0 * summary.get(covered_key, 0) / total if total else 100.0


def combined_percent(summary: dict) -> float:
    total = summary.get("num_statements", 0) + summary.get("num_branches", 0)
    covered = summary.get("covered_lines", 0) + summary.get("covered_branches", 0)
    return 100.0 * covered / total if total else 0.0


def markdown_report(data: dict, minimum: float) -> str:
    totals = data["totals"]
    total = combined_percent(totals)
    lines = [
        "# Python coverage report",
        "",
        "Coverage includes branch execution across the contracts, pipeline, and study backend source trees.",
        "The report contains source filenames and coverage counts only; test fixture contents are not included.",
        "",
        f"Overall: **{total:.1f}%** (minimum: **{minimum:.1f}%**).",
        "",
        "| Source module | Statements | Line coverage | Branches | Branch coverage | Combined coverage |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for path, file in sorted(data["files"].items()):
        summary = file["summary"]
        if not summary["num_statements"]:
            continue
        branches = summary.get("num_branches", 0)
        branch_coverage = coverage_percent(summary, "covered_branches", "num_branches")
        lines.append(
            "| {path} | {statements} | {line:.1f}% | {branches} | {branch:.1f}% | {combined:.1f}% |".format(
                path=path.replace("|", "\\|"),
                statements=summary["num_statements"],
                line=coverage_percent(summary, "covered_lines", "num_statements"),
                branches=branches,
                branch=branch_coverage,
                combined=combined_percent(summary),
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, required=True, help="coverage.py JSON report")
    parser.add_argument("--markdown", type=Path, required=True, help="path for the readable report")
    args = parser.parse_args()

    config = configparser.ConfigParser(interpolation=None)
    if not config.read(ROOT / ".coveragerc", encoding="utf-8"):
        parser.error("Could not read .coveragerc")
    minimum = config.getfloat("report", "fail_under")
    data = json.loads(args.json.read_text(encoding="utf-8"))
    report = markdown_report(data, minimum)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(report, encoding="utf-8")
    total = combined_percent(data["totals"])
    print(report)
    if total < minimum:
        print(f"Coverage {total:.1f}% is below the required {minimum:.1f}%.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
