from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from traffic_sim.data_sources import inspect_roads_geojson, write_provider_registry


class DataSourceRegistryTests(unittest.TestCase):
    def test_roads_geojson_status_is_real_data_snapshot(self) -> None:
        status = inspect_roads_geojson("data/almaty_roads.geojson")
        self.assertEqual(status.id, "roads-geojson")
        self.assertEqual(status.claim_label, "real-data")
        self.assertTrue(status.available)
        self.assertGreater(status.feature_count or 0, 100)
        self.assertIsNotNone(status.sha256)
        self.assertIn("not a live", " ".join(status.limitations).lower())

    def test_provider_registry_writes_api_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            registry = write_provider_registry(tmp_dir)
            self.assertGreaterEqual(registry["summary"]["providerCount"], 6)
            self.assertGreaterEqual(registry["summary"]["realDataAvailableCount"], 1)
            ids = {provider["id"] for provider in registry["providers"]}
            self.assertIn("roads-geojson", ids)
            self.assertIn("yandex-display", ids)
            payload = json.loads(Path(registry["outputs"]["registryJson"]).read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["refreshableSource"], "roads-geojson")


if __name__ == "__main__":
    unittest.main()
