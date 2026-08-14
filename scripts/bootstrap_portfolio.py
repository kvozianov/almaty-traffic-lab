from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Callable, Sequence, TextIO


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from traffic_sim.portfolio_release import (
    Generator,
    PortfolioLockTimeout,
    PortfolioReleaseError,
    SUPPORTED_SCENARIO_ID,
    generate_abay_portfolio_bundle,
    promote_portfolio_release,
    read_current_manifest,
    retry_alias_sync,
    verify_compatibility_aliases,
    verify_source_slice,
)


LOCK_TIMEOUT_EXIT = 75
GENERATION_FAILURE_EXIT = 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate and atomically promote the controlled Abay portfolio evidence pack."
    )
    parser.add_argument("--repository-root", default=str(ROOT))
    parser.add_argument("--source-manifest", default="portfolio.sources.json")
    parser.add_argument("--scenario-id", default=SUPPORTED_SCENARIO_ID)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--lock-timeout", type=float, default=10.0)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify-current", action="store_true")
    mode.add_argument("--verify-sources", action="store_true")
    mode.add_argument("--retry-aliases", action="store_true")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    generator: Generator | None = None,
    stdout: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    args = build_parser().parse_args(argv)
    root = Path(args.repository_root).resolve()
    try:
        if args.scenario_id != SUPPORTED_SCENARIO_ID:
            raise PortfolioReleaseError(
                f"Only scenarioId={SUPPORTED_SCENARIO_ID!r} is accepted by this bootstrap"
            )
        if args.verify_current:
            manifest = read_current_manifest(repository_root=root)
            compatibility = verify_compatibility_aliases(
                repository_root=root,
                route_manifest=manifest,
            )
            summary: dict[str, Any] = {
                "status": "verified",
                "runId": manifest["runId"],
                "scenarioId": manifest["scenarioId"],
                "artifactCount": len(manifest["artifacts"]),
                "aliases": manifest["aliases"],
                "compatibilityAliases": compatibility,
            }
        elif args.verify_sources:
            summary = {
                "status": "verified",
                "scenarioId": SUPPORTED_SCENARIO_ID,
                "sourceVerification": verify_source_slice(
                    repository_root=root,
                    source_manifest_path=args.source_manifest,
                ),
            }
        elif args.retry_aliases:
            summary = retry_alias_sync(
                repository_root=root,
                lock_timeout_seconds=args.lock_timeout,
            )
        else:
            summary = promote_portfolio_release(
                generator or generate_abay_portfolio_bundle,
                repository_root=root,
                source_manifest_path=args.source_manifest,
                scenario_id=args.scenario_id,
                run_id=args.run_id,
                lock_timeout_seconds=args.lock_timeout,
            )
        _emit(output, summary)
        return 0
    except PortfolioLockTimeout as error:
        _emit(
            output,
            {
                "status": "error",
                "code": "lock_timeout",
                "message": str(error),
            },
        )
        return LOCK_TIMEOUT_EXIT
    except (PortfolioReleaseError, OSError, ValueError, KeyError, TypeError) as error:
        _emit(
            output,
            {
                "status": "error",
                "code": "generation_failed",
                "errorType": type(error).__name__,
                "message": str(error),
            },
        )
        return GENERATION_FAILURE_EXIT


def _emit(output: TextIO, payload: dict[str, Any]) -> None:
    output.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")
    output.flush()


if __name__ == "__main__":
    raise SystemExit(main())
