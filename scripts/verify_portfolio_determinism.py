#!/usr/bin/env python3
"""Compare two isolated portfolio bootstraps without changing the source checkout."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from typing import Any


VOLATILE_FIELDS = frozenset({"runid", "releaserunid", "generatedat", "createdat", "updatedat", "timestamp"})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run two isolated portfolio bootstraps and compare their normalized evidence."
    )
    parser.add_argument("--repository-root", default=".", help="Clean Git checkout to reproduce")
    return parser.parse_args()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def source_archive(repository_root: Path, destination: Path) -> None:
    result = subprocess.run(
        ["git", "-C", str(repository_root), "archive", "--format=tar", "HEAD"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
        archive.extractall(destination, filter="data")


def bootstrap(source_root: Path, run_id: str) -> dict[str, Any]:
    subprocess.run(
        [
            sys.executable,
            "scripts/bootstrap_portfolio.py",
            "--repository-root",
            str(source_root),
            "--run-id",
            run_id,
        ],
        check=True,
        cwd=source_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return json.loads((source_root / "reports/portfolio/current.json").read_text(encoding="utf-8"))


def normalize_json(value: Any, *, run_ids: frozenset[str]) -> Any:
    if isinstance(value, list):
        return [normalize_json(item, run_ids=run_ids) for item in value]
    if not isinstance(value, dict):
        if isinstance(value, str):
            for run_id in run_ids:
                value = value.replace(run_id, "<release-run>")
        return value
    normalized: dict[str, Any] = {}
    for key, item in value.items():
        normalized_key = key.lower()
        if normalized_key in VOLATILE_FIELDS:
            normalized[key] = "<volatile>"
        elif normalized_key == "bytes" or normalized_key.endswith("sha256"):
            normalized[key] = "<derived>"
        else:
            normalized[key] = normalize_json(item, run_ids=run_ids)
    return normalized


def normalized_bundle_hash(source_root: Path, run_id: str, run_ids: frozenset[str]) -> str:
    run_root = source_root / "reports/portfolio/runs" / run_id
    normalized: dict[str, Any] = {}
    for path in sorted(item for item in run_root.rglob("*") if item.is_file()):
        relative = path.relative_to(run_root).as_posix()
        content = path.read_bytes()
        if path.suffix == ".json":
            payload = json.loads(content)
            normalized[relative] = normalize_json(
                payload,
                run_ids=run_ids,
            )
        else:
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                normalized[relative] = {"binarySha256": sha256_bytes(content)}
                continue
            for known_run_id in run_ids:
                text = text.replace(known_run_id, "<release-run>")
            normalized[relative] = text
    return sha256_bytes(canonical_json(normalized).encode("utf-8"))


def read_determinism_values(source_root: Path, manifest: dict[str, Any], run_ids: frozenset[str]) -> dict[str, str]:
    run_root = source_root / "reports/portfolio/runs" / manifest["runId"]
    metadata = json.loads(
        (run_root / "reports/repro/abay/metadata.json").read_text(encoding="utf-8")
    )
    kpis = (run_root / "reports/dossiers/abay-signal-retiming/kpis.csv").read_bytes()
    return {
        "semanticFingerprint": metadata["pairedExperiment"]["semanticFingerprint"],
        "canonicalKpiHash": sha256_bytes(kpis),
        "sourceManifestHash": manifest["sourceManifest"]["sha256"],
        "normalizedReleaseBundleHash": normalized_bundle_hash(source_root, manifest["runId"], run_ids),
    }


def main() -> int:
    args = parse_args()
    repository_root = Path(args.repository_root).resolve()
    if not (repository_root / ".git").exists():
        raise SystemExit("determinism verification requires a Git checkout")

    with tempfile.TemporaryDirectory(prefix="portfolio-determinism-") as temporary:
        temporary_root = Path(temporary)
        first_root = temporary_root / "first"
        second_root = temporary_root / "second"
        first_root.mkdir()
        second_root.mkdir()
        source_archive(repository_root, first_root)
        source_archive(repository_root, second_root)
        first = bootstrap(first_root, "abay-determinism-first")
        second = bootstrap(second_root, "abay-determinism-second")
        run_ids = frozenset({first["runId"], second["runId"]})
        first_values = read_determinism_values(first_root, first, run_ids)
        second_values = read_determinism_values(second_root, second, run_ids)

    if first_values != second_values:
        raise SystemExit(
            "determinism verification failed: "
            + canonical_json({"first": first_values, "second": second_values})
        )
    print(canonical_json({"status": "verified", "runs": 2, **first_values}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
