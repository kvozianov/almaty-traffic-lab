from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from traffic_sim.dossier import generate_scenario_dossier


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a municipal Scenario Dossier artifact.")
    parser.add_argument("--config", default="data/scenarios/dossier_abay_signal.json")
    args = parser.parse_args()
    dossier = generate_scenario_dossier(args.config)
    print(json.dumps({"id": dossier["id"], "outputs": dossier["outputs"], "recommendation": dossier["recommendation"]}, indent=2))


if __name__ == "__main__":
    main()
