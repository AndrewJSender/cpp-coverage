# Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
# Licensed under the MIT License. See LICENSE for details.

"""Enforce the changed-coverage gate and report findings to GitHub Actions."""

import argparse
import json
import os
from pathlib import Path
import sys


def escape_annotation(value: object) -> str:
    return (
        str(value)
        .replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
        .replace(",", "%2C")
        .replace(":", "%3A")
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "report",
        nargs="?",
        type=Path,
        default=Path("diff-coverage.json"),
        help="Path to the JSON report produced by src/git.py",
    )
    args = parser.parse_args(argv)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        parser.error("GITHUB_STEP_SUMMARY environment variable is required")

    report = json.loads(args.report.read_text(encoding="utf-8"))
    gate = report["gate"]
    for finding in gate["lines"]:
        reasons = "; ".join(finding["reasons"])
        print(
            f"::error file={escape_annotation(finding['file'])},"
            f"line={finding['line']}::{escape_annotation(reasons)}"
        )

    with Path(summary_path).open("a", encoding="utf-8") as summary:
        summary.write(
            f"\n### PR diff coverage\n\n"
            f"Failing changed lines: {gate['uncovered']}\n\n"
            f"Validation errors: {gate['errors']}\n"
        )

    if gate["uncovered"] > 0 or gate["errors"] > 0:
        print(
            "PR coverage requirements not met; see diff-coverage artifact.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
