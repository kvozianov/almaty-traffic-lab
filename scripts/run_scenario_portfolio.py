from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from traffic_sim.scenario_portfolio import run_portfolio


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a ScenarioPortfolio batch and emit comparable KPI artifacts.")
    parser.add_argument("--portfolio", default="data/scenarios/almaty_portfolio.json")
    parser.add_argument("--out", default="reports/portfolio/month1")
    args = parser.parse_args()

    result = run_portfolio(args.portfolio, args.out)
    print(
        json.dumps(
            {
                "id": result["id"],
                "measureCount": len(result["measures"]),
                "outputs": result["outputs"],
                "topScenario": result["matrix"][0]["scenario_id"] if result["matrix"] else None,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
