#!/usr/bin/env python3
"""Validate that the release traceability table covers each normative requirement once."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from collections import Counter
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
PREFIXES = "CLAIM|LANG|IA|DOS|EXP|SBX|ADR|A11Y|RESP|VIS|PERF|PRIV|SEO|STATE|REL|SEC|DOC|SCI"
HEADING_PATTERN = re.compile(rf"^### ({PREFIXES})-([0-9]{{2}})\b", re.MULTILINE)
TABLE_PATTERN = re.compile(rf"^\| ({PREFIXES})-([0-9]{{2}}) \|", re.MULTILINE)


def requirement_ids(pattern: re.Pattern[str], content: str) -> list[str]:
    return [f"{prefix}-{number}" for prefix, number in pattern.findall(content)]


def duplicates(items: Iterable[str]) -> list[str]:
    return sorted(item for item, count in Counter(items).items() if count > 1)


def validate(specification: Path, traceability: Path) -> dict[str, object]:
    spec_ids = requirement_ids(HEADING_PATTERN, specification.read_text(encoding="utf-8"))
    trace_ids = requirement_ids(TABLE_PATTERN, traceability.read_text(encoding="utf-8"))
    required = set(spec_ids)
    mapped = set(trace_ids)
    result = {
        "specification": str(specification),
        "traceability": str(traceability),
        "requiredCount": len(spec_ids),
        "mappedCount": len(trace_ids),
        "missing": sorted(required - mapped),
        "orphans": sorted(mapped - required),
        "duplicateSpecificationIds": duplicates(spec_ids),
        "duplicateTraceabilityIds": duplicates(trace_ids),
    }
    result["status"] = "passed" if all(
        not result[key]
        for key in ("missing", "orphans", "duplicateSpecificationIds", "duplicateTraceabilityIds")
    ) else "failed"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--specification",
        type=Path,
        default=ROOT / ".omx/plans/portfolio-idealization-technical-specification.md",
    )
    parser.add_argument(
        "--traceability",
        type=Path,
        default=ROOT / ".omx/plans/portfolio-idealization-traceability.md",
    )
    args = parser.parse_args(argv)
    try:
        result = validate(args.specification, args.traceability)
    except OSError as error:
        result = {
            "status": "failed",
            "code": "input_unavailable",
            "message": str(error),
        }
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
