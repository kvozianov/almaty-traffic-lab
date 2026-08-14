from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from traffic_sim.workflow import generate_decision_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a closed municipal decision workflow artifact.")
    parser.add_argument("--dossier", default="reports/dossiers/abay-signal-retiming/dossier.json")
    parser.add_argument("--out", default="reports/workflows")
    args = parser.parse_args()

    workflow = generate_decision_workflow(args.dossier, out_dir=args.out)
    print(
        json.dumps(
            {
                "id": workflow["id"],
                "status": workflow["status"],
                "statusPath": [item["toStatus"] for item in workflow["history"]],
                "outputs": workflow["outputs"],
                "recalibrationRequired": workflow["history"][-1]["forecastVsFact"]["recalibrationRequired"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
