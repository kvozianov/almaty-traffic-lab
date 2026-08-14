from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from traffic_sim.operations import generate_operational_playbook


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an operational incident playbook artifact.")
    parser.add_argument("--incident", default="data/operations/sample_incident_abay.json")
    parser.add_argument("--out", default="reports/operations")
    parser.add_argument("--baseline-analytics", default="data/analytics_normal.json")
    args = parser.parse_args()

    incident = json.loads(Path(args.incident).read_text(encoding="utf-8"))
    playbook = generate_operational_playbook(
        incident,
        out_dir=args.out,
        baseline_analytics_path=args.baseline_analytics,
        root=ROOT,
    )
    print(
        json.dumps(
            {
                "id": playbook["id"],
                "outputs": playbook["outputs"],
                "forecastHorizons": [item["horizonMinutes"] for item in playbook["forecast"]],
                "topAction": playbook["recommendedActions"][0],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
