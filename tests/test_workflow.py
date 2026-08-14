from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from traffic_sim.workflow import WORKFLOW_STATUSES, generate_decision_workflow


class DecisionWorkflowTests(unittest.TestCase):
    def test_abay_dossier_moves_to_post_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workflow = generate_decision_workflow(
                "reports/dossiers/abay-signal-retiming/dossier.json",
                out_dir=tmp_dir,
            )
            self.assertEqual(workflow["status"], "audited")
            self.assertEqual([item["toStatus"] for item in workflow["history"]], list(WORKFLOW_STATUSES))
            self.assertTrue(workflow["evidenceCompleteness"]["allRequiredEvidencePresent"])
            self.assertEqual(workflow["claimLevel"], "demo")
            self.assertGreaterEqual(len(workflow["artifactLocks"]), 4)
            self.assertTrue(all(item["available"] for item in workflow["artifactLocks"]))

            outputs = workflow["outputs"]
            self.assertTrue(Path(outputs["workflowJson"]).exists())
            self.assertTrue(Path(outputs["engineerTasksCsv"]).exists())
            self.assertTrue(Path(outputs["monitoringJson"]).exists())
            self.assertTrue(Path(outputs["postAuditJson"]).exists())

            post_audit = json.loads(Path(outputs["postAuditJson"]).read_text(encoding="utf-8"))
            self.assertEqual(post_audit["kind"], "forecast-vs-fact-audit")
            self.assertTrue(post_audit["items"])
            self.assertIn("forecastVsFact", workflow["history"][-1])


if __name__ == "__main__":
    unittest.main()
