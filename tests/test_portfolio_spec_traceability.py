from __future__ import annotations

from pathlib import Path
from io import StringIO
from unittest import mock
import tempfile
import unittest

from scripts.check_portfolio_spec_traceability import main, validate


class PortfolioSpecTraceabilityTests(unittest.TestCase):
    def test_repository_specification_has_exact_traceability_coverage(self) -> None:
        root = Path(__file__).resolve().parents[1]
        result = validate(
            root / ".omx/plans/portfolio-idealization-technical-specification.md",
            root / ".omx/plans/portfolio-idealization-traceability.md",
        )
        self.assertEqual(result["status"], "passed", result)
        self.assertEqual(result["requiredCount"], 92)

    def test_missing_duplicate_and_orphan_ids_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = root / "spec.md"
            traceability = root / "trace.md"
            spec.write_text("### CLAIM-01 — required\n### LANG-01 — required\n", encoding="utf-8")
            traceability.write_text(
                "| Requirement | Gate | Evidence |\n|---|---|---|\n"
                "| CLAIM-01 | gate | evidence |\n| CLAIM-01 | gate | evidence |\n"
                "| DOS-01 | gate | evidence |\n",
                encoding="utf-8",
            )
            result = validate(spec, traceability)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["missing"], ["LANG-01"])
        self.assertEqual(result["orphans"], ["DOS-01"])
        self.assertEqual(result["duplicateTraceabilityIds"], ["CLAIM-01"])

    def test_missing_input_has_a_machine_readable_failure(self) -> None:
        root = Path(__file__).resolve().parents[1]
        output = StringIO()
        with mock.patch("sys.stdout", output):
            status = main(["--specification", str(root / "does-not-exist.md")])
        self.assertEqual(status, 1)
        self.assertIn('"code": "input_unavailable"', output.getvalue())
