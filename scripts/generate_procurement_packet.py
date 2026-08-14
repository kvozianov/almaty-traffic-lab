from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from traffic_sim.procurement import generate_procurement_packet


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate tender-readiness checklist artifacts.")
    parser.add_argument("--out", default="reports/procurement")
    args = parser.parse_args()

    packet = generate_procurement_packet(args.out)
    print(
        json.dumps(
            {
                "id": packet["id"],
                "claimLevel": packet["claimLevel"],
                "requirementCount": packet["summary"]["requirementCount"],
                "statuses": packet["summary"]["statuses"],
                "outputs": packet["outputs"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
