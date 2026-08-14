from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from traffic_sim.data_sources import write_provider_registry


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh local data-provider status metadata.")
    parser.add_argument("--out", default="reports/data_sources")
    args = parser.parse_args()

    registry = write_provider_registry(args.out)
    print(
        json.dumps(
            {
                "id": registry["id"],
                "providerCount": registry["summary"]["providerCount"],
                "availableCount": registry["summary"]["availableCount"],
                "realDataAvailableCount": registry["summary"]["realDataAvailableCount"],
                "outputs": registry["outputs"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
