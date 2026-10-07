"""The traffic-lab data artifacts rebuild byte-for-byte from the OSM snapshot."""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lab"))

import build_city_graph  # noqa: E402
import build_demand  # noqa: E402
from osm_names import english_name  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LabDataTest(unittest.TestCase):
    def test_graph_and_demand_rebuild_identically(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph_out = Path(tmp) / "city-graph.json"
            demand_out = Path(tmp) / "demand.json"
            snapshot = ROOT / build_city_graph.DEFAULT_SNAPSHOT
            graph = build_city_graph.build(snapshot)
            graph["source"]["snapshot"] = build_city_graph.DEFAULT_SNAPSHOT.as_posix()
            graph_out.write_text(json.dumps(graph, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            beta = json.loads((ROOT / "public/model/calibration.json").read_text())["beta"]
            demand = build_demand.build(graph_out, snapshot, beta, ROOT / "public/model/observations.json")
            demand_out.write_text(json.dumps(demand, separators=(",", ":")), encoding="utf-8")
            self.assertEqual(sha(graph_out), sha(ROOT / "public/model/city-graph.json"))
            self.assertEqual(sha(demand_out), sha(ROOT / "public/model/demand.json"))

    def test_demand_matrix_is_normalised(self):
        demand = json.loads((ROOT / "public/model/demand.json").read_text())
        self.assertAlmostEqual(sum(t for _, _, t in demand["matrix"]), 1.0, places=3)
        self.assertEqual(demand["claimLevel"], "proxy")

    def test_demand_follows_master_plan_centre_shares(self):
        demand = json.loads((ROOT / "public/model/demand.json").read_text())
        obs = json.loads((ROOT / "public/model/observations.json").read_text())["structure"]
        x0, y0, x1, y1 = obs["centre"]["bbox"]
        inside = [x0 <= z["center"][0] <= x1 and y0 <= z["center"][1] <= y1 for z in demand["zones"]]
        jobs = sum(z["attraction"] for z, i in zip(demand["zones"], inside) if i)
        homes = sum(z["production"] for z, i in zip(demand["zones"], inside) if not i)
        # Small zones are dropped after rescaling, so allow a little slack.
        self.assertAlmostEqual(jobs, obs["jobsInCentreShare"], delta=0.02)
        self.assertAlmostEqual(homes, obs["residentsOutsideCentreShare"], delta=0.02)

    def test_english_street_names(self):
        self.assertEqual(english_name({"name": "Абай даңғылы", "name:ru": "проспект Абая"}), "Abay Avenue")
        self.assertEqual(english_name({"name:en": "Abay avenue"}), "Abay Avenue")
        self.assertEqual(english_name({"name": "улица Жандосова"}), "Zhandosova Street")


if __name__ == "__main__":
    unittest.main()
