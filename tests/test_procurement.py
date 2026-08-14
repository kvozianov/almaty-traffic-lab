from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from traffic_sim.procurement import generate_procurement_packet


class ProcurementPacketTests(unittest.TestCase):
    def test_packet_covers_required_tender_areas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            packet = generate_procurement_packet(tmp_dir)
            areas = {item["area"] for item in packet["requirements"]}
            self.assertTrue(
                {
                    "roles",
                    "audit",
                    "governance",
                    "deployment",
                    "data-residency",
                    "operations",
                    "security",
                    "training",
                    "commercial",
                }
                <= areas
            )
            self.assertEqual(packet["claimLevel"], "demo")
            self.assertGreaterEqual(packet["summary"]["requirementCount"], 9)
            self.assertTrue(all(item["evidence"] for item in packet["requirements"]))
            self.assertIn("docker compose config", packet["localOnPremRunPath"])

            payload = json.loads(Path(packet["outputs"]["json"]).read_text(encoding="utf-8"))
            with Path(packet["outputs"]["csv"]).open(encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(payload["summary"]["requirementCount"], len(rows))


if __name__ == "__main__":
    unittest.main()
