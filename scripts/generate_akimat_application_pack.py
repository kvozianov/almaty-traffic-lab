from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from traffic_sim.akimat_pack import generate_akimat_application_pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the Abay Akimat application and pilot evidence pack.")
    parser.add_argument("--out", default="reports/akimat/abay-signal-retiming")
    args = parser.parse_args()

    pack = generate_akimat_application_pack(args.out)
    print(
        json.dumps(
            {
                "id": pack["id"],
                "claimLevel": pack["claimLevel"],
                "outputDir": pack["outputDir"],
                "generatedArtifactCount": pack["generatedArtifactCount"],
                "files": pack["files"],
                "recommendation": pack["recommendation"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
