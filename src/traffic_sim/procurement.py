from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import csv
import json
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Mapping


DEFAULT_PROCUREMENT_DIR = Path("reports/procurement")

DEFAULT_EVIDENCE_REFS: dict[str, str] = {
    "procurementReadinessDoc": "docs/procurement_readiness.md",
    "workflow": "reports/workflows/abay-signal-retiming-decision-workflow.json",
    "runMetadataSource": "src/traffic_sim/run_metadata.py",
    "artifactRegistry": "docs/obsidian/03-registries/Artifact Registry.md",
    "dossierJson": "reports/dossiers/abay-signal-retiming/dossier.json",
    "methodsReadme": "README_METHODS.md",
    "dockerfile": "Dockerfile",
    "composeFile": "docker-compose.yml",
    "dataSourcesDoc": "docs/data_sources.md",
    "dossierMarkdown": "reports/dossiers/abay-signal-retiming/dossier.md",
    "postAudit": "reports/workflows/abay-signal-retiming-decision-workflow-post-audit.json",
}
OUTPUT_ROLES = ("json", "csv")


@dataclass(frozen=True, slots=True)
class TenderRequirement:
    id: str
    area: str
    requirement: str
    status: str
    claim_level: str
    evidence: list[str]
    gap: str
    next_action: str


def tender_requirements(
    *,
    evidence_refs: Mapping[str, str] | None = None,
) -> list[TenderRequirement]:
    refs = _resolve_evidence_refs(evidence_refs)
    return [
        TenderRequirement(
            id="roles-responsibilities",
            area="roles",
            requirement="Named municipal roles and responsibilities for scenario review, approval, deployment, and audit.",
            status="prototype",
            claim_level="demo",
            evidence=[
                refs["procurementReadinessDoc"],
                refs["workflow"],
            ],
            gap="Owners are string labels, not authenticated users or legally delegated signatories.",
            next_action="Add authenticated role model and approval policy before procurement-ready claims.",
        ),
        TenderRequirement(
            id="audit-log",
            area="audit",
            requirement="Every recommendation links to run metadata, artifact hashes, claim labels, and workflow history.",
            status="prototype",
            claim_level="demo",
            evidence=[
                refs["runMetadataSource"],
                refs["workflow"],
                refs["artifactRegistry"],
            ],
            gap="Audit events are file-based; no append-only signed audit store exists.",
            next_action="Add append-only audit storage and export policy.",
        ),
        TenderRequirement(
            id="scenario-versioning",
            area="governance",
            requirement="Scenario, dossier, workflow, and post-audit artifacts are versioned by path and SHA-256 hash.",
            status="prototype",
            claim_level="demo",
            evidence=[
                refs["workflow"],
                refs["dossierJson"],
            ],
            gap="No multi-user branch/merge policy or immutable scenario registry is implemented.",
            next_action="Add scenario version registry and change-control policy.",
        ),
        TenderRequirement(
            id="onprem-run-path",
            area="deployment",
            requirement="Local/on-premises run path exists for Next app and Python artifact generation.",
            status="prototype",
            claim_level="demo",
            evidence=[refs["methodsReadme"], refs["dockerfile"], refs["composeFile"]],
            gap="Container image is not hardened, scanned, or deployed to a municipal environment.",
            next_action="Run container build in target infrastructure and attach scan/deployment evidence.",
        ),
        TenderRequirement(
            id="kazakhstan-data-residency",
            area="data-residency",
            requirement="Data residency posture states that municipal raw data can remain in Kazakhstan-controlled storage.",
            status="documented",
            claim_level="demo",
            evidence=[refs["procurementReadinessDoc"], refs["dataSourcesDoc"]],
            gap="No signed hosting agreement, DPA, or city-provided infrastructure proof is attached.",
            next_action="Confirm target hosting model and attach legal/security review.",
        ),
        TenderRequirement(
            id="backup-retention",
            area="operations",
            requirement="Backup and retention policy is named for configs, artifacts, reports, and audit records.",
            status="documented",
            claim_level="demo",
            evidence=[refs["procurementReadinessDoc"]],
            gap="Backup jobs and restore drills are not implemented.",
            next_action="Add backup automation and restore-test evidence.",
        ),
        TenderRequirement(
            id="sla-security-posture",
            area="security",
            requirement="SLA and security posture lists assumptions, controls, and missing certifications.",
            status="documented",
            claim_level="demo",
            evidence=[refs["procurementReadinessDoc"]],
            gap="No penetration test, vulnerability scan, SSO/RBAC, or production SLA is attached.",
            next_action="Add security controls and third-party validation before stronger claims.",
        ),
        TenderRequirement(
            id="training-acceptance",
            area="training",
            requirement="Training and acceptance checklist maps buyer sign-off to reproducible artifacts.",
            status="prototype",
            claim_level="demo",
            evidence=[
                refs["procurementReadinessDoc"],
                refs["dossierMarkdown"],
                refs["postAudit"],
            ],
            gap="No signed acceptance records from municipal users.",
            next_action="Run pilot training and attach acceptance minutes.",
        ),
        TenderRequirement(
            id="three-year-tco",
            area="commercial",
            requirement="Three-year TCO framing identifies cost categories and open inputs.",
            status="documented",
            claim_level="demo",
            evidence=[refs["procurementReadinessDoc"]],
            gap="No vendor quote, municipal hosting quote, staffing agreement, or sourced cost ledger.",
            next_action="Replace placeholders with sourced quotations.",
        ),
    ]


def generate_procurement_packet(
    out_dir: str | Path = DEFAULT_PROCUREMENT_DIR,
    *,
    evidence_refs: Mapping[str, str] | None = None,
    artifact_refs: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    requirements = tender_requirements(evidence_refs=evidence_refs)
    physical_outputs = {
        "json": output_dir / "tender_checklist.json",
        "csv": output_dir / "tender_checklist.csv",
    }
    packet = {
        "id": "almaty-mobility-procurement-readiness",
        "kind": "tender-readiness-checklist",
        "claimLevel": "demo",
        "createdAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "summary": {
            "requirementCount": len(requirements),
            "statuses": _count_by(requirements, "status"),
            "claimLevels": _count_by(requirements, "claim_level"),
            "acceptanceGate": "Checklist covers deployment, roles, audit log, data residency, SLA/security, training, acceptance, and TCO with linked evidence.",
        },
        "localOnPremRunPath": [
            "npm ci",
            "PYTHONPATH=src python3 scripts/generate_dossier.py --config data/scenarios/dossier_abay_signal.json",
            "PYTHONPATH=src python3 scripts/generate_decision_workflow.py --dossier reports/dossiers/abay-signal-retiming/dossier.json --out reports/workflows",
            "PYTHONPATH=src python3 scripts/generate_procurement_packet.py --out reports/procurement",
            "npm run build",
            "docker compose config",
            "docker compose up --build app",
        ],
        "requirements": [asdict(requirement) for requirement in requirements],
        "limitations": [
            "This packet is a procurement-readiness demo, not a certified enterprise deployment.",
            "Security, SLA, legal-signature, and data-processing claims require municipal review and signed evidence.",
            "TCO values are framed as categories until sourced quotations are attached.",
        ],
        "outputs": _resolve_artifact_refs(physical_outputs, artifact_refs),
    }
    physical_outputs["json"].write_text(
        json.dumps(packet, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    _write_csv(requirements, physical_outputs["csv"])
    return packet


def _write_csv(requirements: list[TenderRequirement], path: Path) -> None:
    rows = [asdict(requirement) for requirement in requirements]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["id", "area", "requirement", "status", "claim_level", "evidence", "gap", "next_action"])
        writer.writeheader()
        for row in rows:
            row["evidence"] = "; ".join(row["evidence"])
            writer.writerow(row)


def _count_by(requirements: list[TenderRequirement], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for requirement in requirements:
        value = str(getattr(requirement, field))
        counts[value] = counts.get(value, 0) + 1
    return counts


def _resolve_evidence_refs(evidence_refs: Mapping[str, str] | None) -> dict[str, str]:
    refs = DEFAULT_EVIDENCE_REFS if evidence_refs is None else evidence_refs
    _require_exact_roles(refs, set(DEFAULT_EVIDENCE_REFS), map_name="evidence_refs")
    return {role: _logical_ref(refs[role], role=role) for role in DEFAULT_EVIDENCE_REFS}


def _resolve_artifact_refs(
    physical_outputs: Mapping[str, Path],
    artifact_refs: Mapping[str, str] | None,
) -> dict[str, str]:
    if artifact_refs is None:
        return {role: str(path) for role, path in physical_outputs.items()}
    _require_exact_roles(artifact_refs, set(OUTPUT_ROLES), map_name="artifact_refs")
    return {role: _logical_ref(artifact_refs[role], role=role) for role in OUTPUT_ROLES}


def _require_exact_roles(
    values: Mapping[str, object],
    expected: set[str],
    *,
    map_name: str,
) -> None:
    actual = set(values)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        raise ValueError(f"Invalid {map_name}: missing={missing}, unknown={unknown}")


def _logical_ref(value: str, *, role: str) -> str:
    raw = str(value)
    path = PurePosixPath(raw)
    if (
        not raw
        or raw != raw.strip()
        or "\\" in raw
        or path.is_absolute()
        or ".." in path.parts
        or any(".staging" in part for part in path.parts)
        or (path.parts and path.parts[0].endswith(":"))
        or path.as_posix() != raw
    ):
        raise ValueError(f"Unsafe logical reference for {role}: {raw!r}")
    return path.as_posix()
