from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from traffic_sim.reproducibility import generate_reproduction_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Reproduce the first Abay Scenario Dossier evidence pack.")
    parser.add_argument("--config", default="simulation.config.json")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    metadata = generate_reproduction_run(args.config, out_dir=args.out)
    print(
        json.dumps(
            {
                "id": metadata["id"],
                "claimLevel": metadata["claimLevel"],
                "seed": metadata["seed"],
                "outputs": metadata["outputs"],
                "artifactCount": metadata["artifactCount"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
