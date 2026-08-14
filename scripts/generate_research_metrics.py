from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from traffic_sim.research_metrics import generate_research_metrics_pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate dossier-adjacent research metrics and visual appendix.")
    parser.add_argument("--dossier", default="reports/dossiers/abay-signal-retiming/dossier.json")
    parser.add_argument("--portfolio-matrix", default="reports/portfolio/month1/kpi_matrix.csv")
    parser.add_argument("--out", default="reports/research_metrics/abay-signal-retiming")
    args = parser.parse_args()

    pack = generate_research_metrics_pack(
        dossier_path=args.dossier,
        portfolio_matrix_path=args.portfolio_matrix,
        out_dir=args.out,
    )
    print(
        json.dumps(
            {
                "id": pack["id"],
                "claimLevel": pack["claimLevel"],
                "metricIds": [metric["id"] for metric in pack["metrics"]],
                "outputs": pack["outputs"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
