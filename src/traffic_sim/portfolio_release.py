from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import time
from typing import Any, IO
from uuid import uuid4

try:  # pragma: no cover - exercised by the explicit non-POSIX guard.
    import fcntl
except ImportError:  # pragma: no cover - Windows is outside the supported release path.
    fcntl = None  # type: ignore[assignment]


ROUTE_MANIFEST_SCHEMA_VERSION = "portfolio-route-manifest/v1"
SOURCE_MANIFEST_SCHEMA_VERSION = "portfolio-sources/v1"
COMPATIBILITY_ALIAS_SCHEMA_VERSION = "portfolio-compatibility-aliases/v1"
COMPATIBILITY_ALIAS_MANIFEST_PATH = "reports/portfolio/compatibility-aliases.json"
SUPPORTED_SCENARIO_ID = "abay-signal-retiming"
CLAIM_LEVELS = frozenset({"demo", "proxy", "calibrated", "real-data", "procurement-ready"})
REQUIRED_ROUTE_ROLES = (
    "dossier",
    "runPassport",
    "providers",
    "workflow",
    "procurement",
    "reproduction",
    "manifest",
    "dataReadiness",
    "procurementPack",
    "applicationPack",
    "pilotPlan",
)
DEFAULT_ALIAS_PATHS: dict[str, str] = {
    "dossier": "reports/dossiers/abay-signal-retiming/dossier.json",
    "runPassport": "data/runs/abay-signal-retiming-run-passport.json",
    "providers": "reports/data_sources/provider_registry.json",
    "workflow": "reports/workflows/abay-signal-retiming-decision-workflow.json",
    "procurement": "reports/procurement/tender_checklist.json",
    "reproduction": "reports/repro/abay/metadata.json",
    "manifest": "reports/repro/abay/artifact_manifest.json",
    "dataReadiness": "reports/akimat/abay-signal-retiming/data_readiness.json",
    "procurementPack": "reports/akimat/abay-signal-retiming/procurement_pack_index.json",
    "applicationPack": "reports/akimat/abay-signal-retiming/application_package_index.json",
    "pilotPlan": "reports/akimat/abay-signal-retiming/pilot_monitoring_plan.json",
}

_PAIR_OUTPUT_REFS = {
    "pairResult": "reports/repro/abay/pair/paired-experiment.json",
    "baselineAnalytics": "reports/repro/abay/pair/baseline.analytics.json",
    "measureAnalytics": "reports/repro/abay/pair/measure.analytics.json",
}
_DOSSIER_OUTPUT_REFS = {
    "json": "reports/dossiers/abay-signal-retiming/dossier.json",
    "markdown": "reports/dossiers/abay-signal-retiming/dossier.md",
    "html": "reports/dossiers/abay-signal-retiming/dossier.html",
    "kpisCsv": "reports/dossiers/abay-signal-retiming/kpis.csv",
}
_WORKFLOW_OUTPUT_REFS = {
    "workflowJson": "reports/workflows/abay-signal-retiming-decision-workflow.json",
    "engineerTasksCsv": "reports/workflows/abay-signal-retiming-decision-workflow-engineer-tasks.csv",
    "monitoringJson": "reports/workflows/abay-signal-retiming-decision-workflow-monitoring.json",
    "postAuditJson": "reports/workflows/abay-signal-retiming-decision-workflow-post-audit.json",
}
_PROVIDER_OUTPUT_REFS = {
    "registryJson": "reports/data_sources/provider_registry.json",
    "roadsStatusJson": "reports/data_sources/roads_geojson_provider_status.json",
}
_PROCUREMENT_OUTPUT_REFS = {
    "json": "reports/procurement/tender_checklist.json",
    "csv": "reports/procurement/tender_checklist.csv",
}
_RESEARCH_OUTPUT_REFS = {
    "researchJson": "reports/research_metrics/abay-signal-retiming/research_metrics.json",
    "researchAppendix": "reports/research_metrics/abay-signal-retiming/dossier_appendix.md",
    "researchVisual": "reports/research_metrics/abay-signal-retiming/research_visual.html",
}
_AKIMAT_OUTPUT_FILENAMES = {
    "application_summary_md": "application_summary.md",
    "application_summary_html": "application_summary.html",
    "data_request_memo_md": "data_request_memo.md",
    "data_readiness_json": "data_readiness.json",
    "missing_evidence_json": "missing_evidence.json",
    "pilot_acceptance_criteria_json": "pilot_acceptance_criteria.json",
    "pilot_monitoring_plan_json": "pilot_monitoring_plan.json",
    "pilot_monitoring_plan_md": "pilot_monitoring_plan.md",
    "executive_brief_md": "executive_brief.md",
    "demo_script_md": "demo_script.md",
    "slide_outline_md": "slide_outline.md",
    "risk_register_json": "risk_register.json",
    "scenario_alternative_comparison_json": "scenario_alternative_comparison.json",
    "scenario_alternative_comparison_md": "scenario_alternative_comparison.md",
    "claim_boundary_md": "claim_boundary.md",
    "local_onprem_deployment_note_md": "local_onprem_deployment_note.md",
    "evidence_manifest_json": "evidence_manifest.json",
    "procurement_pack_index_json": "procurement_pack_index.json",
    "application_package_index_json": "application_package_index.json",
}

# This is deliberately a closed file list. It covers generated dependencies
# serialized by the eleven public route artifacts without mirroring folders.
DEFAULT_SUPPORT_ALIAS_PATHS: dict[str, str] = {
    "pairResult": _PAIR_OUTPUT_REFS["pairResult"],
    "baselineAnalytics": _PAIR_OUTPUT_REFS["baselineAnalytics"],
    "measureAnalytics": _PAIR_OUTPUT_REFS["measureAnalytics"],
    "scenarioConfig": "reports/repro/abay/scenario_config.json",
    "dossierMarkdown": _DOSSIER_OUTPUT_REFS["markdown"],
    "dossierHtml": _DOSSIER_OUTPUT_REFS["html"],
    "dossierKpisCsv": _DOSSIER_OUTPUT_REFS["kpisCsv"],
    "roadsProviderStatus": _PROVIDER_OUTPUT_REFS["roadsStatusJson"],
    "workflowEngineerTasks": _WORKFLOW_OUTPUT_REFS["engineerTasksCsv"],
    "workflowMonitoring": _WORKFLOW_OUTPUT_REFS["monitoringJson"],
    "workflowPostAudit": _WORKFLOW_OUTPUT_REFS["postAuditJson"],
    "procurementCsv": _PROCUREMENT_OUTPUT_REFS["csv"],
    "portfolioResults": "reports/portfolio/month1/portfolio_results.json",
    "portfolioMatrix": "reports/portfolio/month1/kpi_matrix.csv",
    "researchJson": _RESEARCH_OUTPUT_REFS["researchJson"],
    "researchAppendix": _RESEARCH_OUTPUT_REFS["researchAppendix"],
    "researchVisual": _RESEARCH_OUTPUT_REFS["researchVisual"],
    "akimatApplicationSummaryMarkdown": "reports/akimat/abay-signal-retiming/application_summary.md",
    "akimatApplicationSummaryHtml": "reports/akimat/abay-signal-retiming/application_summary.html",
    "akimatDataRequestMemoMarkdown": "reports/akimat/abay-signal-retiming/data_request_memo.md",
    "akimatMissingEvidence": "reports/akimat/abay-signal-retiming/missing_evidence.json",
    "akimatPilotAcceptanceCriteria": "reports/akimat/abay-signal-retiming/pilot_acceptance_criteria.json",
    "akimatPilotMonitoringPlanMarkdown": "reports/akimat/abay-signal-retiming/pilot_monitoring_plan.md",
    "akimatExecutiveBriefMarkdown": "reports/akimat/abay-signal-retiming/executive_brief.md",
    "akimatDemoScriptMarkdown": "reports/akimat/abay-signal-retiming/demo_script.md",
    "akimatSlideOutlineMarkdown": "reports/akimat/abay-signal-retiming/slide_outline.md",
    "akimatRiskRegister": "reports/akimat/abay-signal-retiming/risk_register.json",
    "akimatScenarioAlternativeComparisonJson": "reports/akimat/abay-signal-retiming/scenario_alternative_comparison.json",
    "akimatScenarioAlternativeComparisonMarkdown": "reports/akimat/abay-signal-retiming/scenario_alternative_comparison.md",
    "akimatClaimBoundaryMarkdown": "reports/akimat/abay-signal-retiming/claim_boundary.md",
    "akimatLocalOnpremDeploymentNoteMarkdown": "reports/akimat/abay-signal-retiming/local_onprem_deployment_note.md",
    "akimatEvidenceManifest": "reports/akimat/abay-signal-retiming/evidence_manifest.json",
}

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_HASHED_SOURCE_KINDS = frozenset({"asset", "config", "data", "schema", "upstream-artifact"})


class PortfolioReleaseError(RuntimeError):
    """Base error for a portfolio release that was not safely completed."""


class PortfolioDependencyError(PortfolioReleaseError):
    """A direct dependency required to validate release evidence is absent."""


class SourceManifestError(PortfolioReleaseError):
    """The declared source slice is incomplete, unsafe, or hash-mismatched."""


class ArtifactValidationError(PortfolioReleaseError):
    """A generated route artifact or manifest failed a release gate."""


class PortfolioLockTimeout(PortfolioReleaseError):
    """Another portfolio release owns the process lock."""


class UnsupportedPlatformError(PortfolioReleaseError):
    """The documented POSIX release transaction is not available."""


@dataclass(frozen=True, slots=True)
class SourceRecord:
    role: str
    path: str
    kind: str
    required: bool
    sha256: str | None


@dataclass(frozen=True, slots=True)
class ArtifactRegistration:
    role: str
    logical_path: str
    claim_level: str
    media_type: str = "application/json"


class FileSystem:
    """Small durability seam used by the transaction and failure-injection tests."""

    def fsync_file(self, path: Path) -> None:
        with path.open("rb") as handle:
            os.fsync(handle.fileno())

    def fsync_directory(self, path: Path) -> None:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def rename_directory(self, source: Path, target: Path) -> None:
        os.rename(source, target)

    def replace_file(self, source: Path, target: Path) -> None:
        os.replace(source, target)

    def copy_file(self, source: Path, target: Path) -> None:
        shutil.copyfile(source, target)


class SourceManifestResolver:
    """Closed resolver for portfolio domain/config/data inputs.

    Generator code and installed dependencies are execution context. Every
    domain, config, data, schema, asset, or upstream-artifact read must resolve
    through this manifest, where hashed kinds are verified before use.
    """

    def __init__(
        self,
        repository_root: str | Path,
        manifest_path: str | Path = "portfolio.sources.json",
        *,
        scenario_id: str = SUPPORTED_SCENARIO_ID,
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.manifest_relative_path = _repository_relative_path(
            self.repository_root,
            manifest_path,
            label="source manifest",
        )
        if self.manifest_relative_path != "portfolio.sources.json":
            raise SourceManifestError("The canonical source manifest path must be portfolio.sources.json")
        self.manifest_path = _resolve_existing_under(
            self.repository_root,
            self.manifest_relative_path,
            label="source manifest",
            allow_internal_symlink=True,
        )
        try:
            manifest_bytes = self.manifest_path.read_bytes()
            payload = json.loads(manifest_bytes)
        except (OSError, json.JSONDecodeError) as error:
            raise SourceManifestError(f"Cannot read source manifest: {error}") from error
        self._manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        self._records = self._parse(payload, scenario_id=scenario_id)
        self._by_role = {record.role: record for record in self._records}
        self._by_path = {record.path: record for record in self._records}
        self._accessed: set[str] = set()

    @property
    def manifest_sha256(self) -> str:
        return self._manifest_sha256

    @property
    def records(self) -> tuple[SourceRecord, ...]:
        return self._records

    @property
    def accessed_paths(self) -> frozenset[str]:
        return frozenset(self._accessed)

    def resolve(self, role_or_path: str) -> Path:
        record = self._by_role.get(role_or_path) or self._by_path.get(role_or_path)
        if record is None:
            raise SourceManifestError(f"Undeclared portfolio source: {role_or_path!r}")
        path = _resolve_existing_under(
            self.repository_root,
            record.path,
            label=f"source {record.role}",
            allow_internal_symlink=True,
        )
        if not path.is_file():
            raise SourceManifestError(f"Portfolio source is not a regular file: {record.path}")
        actual_hash = sha256_file(path)
        if record.sha256 is not None and actual_hash != record.sha256:
            raise SourceManifestError(
                f"Portfolio source hash mismatch for {record.path}: expected {record.sha256}, got {actual_hash}"
            )
        self._accessed.add(record.path)
        return path

    def resolve_json(self, role_or_path: str) -> Any:
        path = self.resolve(role_or_path)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SourceManifestError(f"Invalid JSON source {path}: {error}") from error

    def verify(self, *, check_git_ignore: bool = True) -> dict[str, Any]:
        verified_hashes = 0
        ignored: list[str] = []
        git_ignore_available = True
        for record in self._records:
            if not record.required:
                candidate = self.repository_root / record.path
                if not candidate.exists():
                    continue
            self.resolve(record.path)
            if record.sha256 is not None:
                verified_hashes += 1
            if check_git_ignore:
                ignored_status = _git_ignore_status(self.repository_root, record.path)
                if ignored_status is None:
                    git_ignore_available = False
                elif ignored_status:
                    ignored.append(record.path)
        if ignored:
            raise SourceManifestError(f"Required portfolio sources are ignored by Git: {sorted(ignored)}")
        return {
            "schemaVersion": SOURCE_MANIFEST_SCHEMA_VERSION,
            "sourceCount": len(self._records),
            "requiredCount": sum(record.required for record in self._records),
            "verifiedHashes": verified_hashes,
            "nonIgnored": not ignored if git_ignore_available else None,
            "gitIgnoreCheck": "verified" if git_ignore_available else "unavailable_not_git_checkout",
            "trackedProof": "pending_git_authorization",
        }

    def materialize(self, target_root: str | Path) -> dict[str, str]:
        """Copy the declared slice into a staging run using repository-relative refs."""

        destination_root = Path(target_root).resolve()
        copied: dict[str, str] = {}
        for record in self._records:
            if not record.required and not (self.repository_root / record.path).exists():
                continue
            source = self.resolve(record.path)
            source_hash_before = sha256_file(source)
            destination = _resolve_for_write_under(
                destination_root,
                record.path,
                label=f"materialized source {record.role}",
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            destination_hash = sha256_file(destination)
            source_hash_after = sha256_file(source)
            expected_hash = record.sha256 or source_hash_before
            if not (
                source_hash_before == source_hash_after == destination_hash == expected_hash
            ):
                raise SourceManifestError(
                    f"Portfolio source changed while materializing {record.path}: "
                    f"before={source_hash_before}, copied={destination_hash}, after={source_hash_after}"
                )
            copied[record.role] = record.path
        manifest_destination = destination_root / self.manifest_relative_path
        manifest_destination.parent.mkdir(parents=True, exist_ok=True)
        manifest_hash_before = sha256_file(self.manifest_path)
        if manifest_hash_before != self._manifest_sha256:
            raise SourceManifestError("portfolio.sources.json changed after resolver initialization")
        shutil.copy2(self.manifest_path, manifest_destination)
        if (
            sha256_file(manifest_destination) != self._manifest_sha256
            or sha256_file(self.manifest_path) != self._manifest_sha256
        ):
            raise SourceManifestError("portfolio.sources.json changed while being materialized")
        return copied

    @staticmethod
    def _parse(payload: Any, *, scenario_id: str) -> tuple[SourceRecord, ...]:
        if not isinstance(payload, dict):
            raise SourceManifestError("portfolio.sources.json must contain an object")
        expected_keys = {"schemaVersion", "scenarioId", "sources"}
        unknown = sorted(set(payload) - expected_keys)
        missing = sorted(expected_keys - set(payload))
        if missing or unknown:
            raise SourceManifestError(f"Invalid source manifest fields: missing={missing}, unknown={unknown}")
        if payload["schemaVersion"] != SOURCE_MANIFEST_SCHEMA_VERSION:
            raise SourceManifestError(f"Unsupported source manifest version: {payload['schemaVersion']!r}")
        if payload["scenarioId"] != scenario_id or scenario_id != SUPPORTED_SCENARIO_ID:
            raise SourceManifestError(f"Only {SUPPORTED_SCENARIO_ID!r} is allowed by this release")
        raw_sources = payload["sources"]
        if not isinstance(raw_sources, list) or not raw_sources:
            raise SourceManifestError("Source manifest must declare at least one source")
        records: list[SourceRecord] = []
        roles: set[str] = set()
        paths: set[str] = set()
        for index, item in enumerate(raw_sources):
            if not isinstance(item, dict):
                raise SourceManifestError(f"sources[{index}] must be an object")
            allowed = {"role", "path", "kind", "required", "sha256"}
            item_unknown = sorted(set(item) - allowed)
            item_missing = sorted({"role", "path", "kind", "required"} - set(item))
            if item_missing or item_unknown:
                raise SourceManifestError(
                    f"Invalid sources[{index}] fields: missing={item_missing}, unknown={item_unknown}"
                )
            role = str(item["role"])
            path = normalize_logical_path(str(item["path"]), label=f"sources[{index}].path")
            kind = str(item["kind"])
            required = item["required"]
            if not role or not isinstance(required, bool):
                raise SourceManifestError(f"Invalid role/required fields in sources[{index}]")
            if kind not in _HASHED_SOURCE_KINDS | {"code", "documentation"}:
                raise SourceManifestError(f"Unsupported source kind {kind!r} in sources[{index}]")
            raw_hash = item.get("sha256")
            source_hash = None if raw_hash is None else str(raw_hash)
            if source_hash is not None and not _SHA256_PATTERN.fullmatch(source_hash):
                raise SourceManifestError(f"Invalid SHA-256 in sources[{index}]")
            if kind in _HASHED_SOURCE_KINDS and source_hash is None:
                raise SourceManifestError(f"Hashed source kind {kind!r} requires sha256: {path}")
            if role in roles or path in paths:
                raise SourceManifestError(f"Duplicate source role or path: role={role!r}, path={path!r}")
            roles.add(role)
            paths.add(path)
            records.append(SourceRecord(role, path, kind, required, source_hash))
        return tuple(records)


class GenerationContext:
    """The only portfolio generator context: sources in, staging artifacts out."""

    def __init__(
        self,
        *,
        run_id: str,
        scenario_id: str,
        repository_root: Path,
        physical_output_root: Path,
        source_resolver: SourceManifestResolver,
    ) -> None:
        if not _RUN_ID_PATTERN.fullmatch(run_id):
            raise PortfolioReleaseError(f"Unsafe release run id: {run_id!r}")
        if scenario_id != SUPPORTED_SCENARIO_ID:
            raise PortfolioReleaseError(f"Unsupported scenario id: {scenario_id!r}")
        self.run_id = run_id
        self.scenario_id = scenario_id
        self.repository_root = repository_root
        self.physical_output_root = physical_output_root
        self.source_resolver = source_resolver
        self.upstream_artifacts: dict[str, str] = {}
        self._route_artifacts: dict[str, ArtifactRegistration] = {}

    @property
    def route_artifacts(self) -> tuple[ArtifactRegistration, ...]:
        return tuple(self._route_artifacts.values())

    def source_path(self, role_or_path: str) -> Path:
        return self.source_resolver.resolve(role_or_path)

    def source_json(self, role_or_path: str) -> Any:
        return self.source_resolver.resolve_json(role_or_path)

    def materialize_sources(self) -> dict[str, str]:
        return self.source_resolver.materialize(self.physical_output_root)

    def physical_path(self, logical_path: str, *, create_parent: bool = False) -> Path:
        path = _resolve_for_write_under(
            self.physical_output_root,
            logical_path,
            label="generated artifact",
        )
        if create_parent:
            path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def write_json(self, logical_path: str, payload: Any) -> Path:
        path = self.physical_path(logical_path, create_parent=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        return path

    def write_text(self, logical_path: str, content: str) -> Path:
        path = self.physical_path(logical_path, create_parent=True)
        path.write_text(content, encoding="utf-8")
        return path

    def publish_upstream(self, role: str, logical_path: str) -> Path:
        if not role or role in self.upstream_artifacts:
            raise PortfolioReleaseError(f"Duplicate or empty upstream role: {role!r}")
        normalized = normalize_logical_path(logical_path, label=f"upstream {role}")
        self.upstream_artifacts[role] = normalized
        return self.physical_path(normalized)

    def register_route_artifact(
        self,
        role: str,
        logical_path: str,
        *,
        claim_level: str,
        media_type: str = "application/json",
    ) -> Path:
        if role not in REQUIRED_ROUTE_ROLES:
            raise PortfolioReleaseError(f"Unsupported route artifact role: {role!r}")
        if role in self._route_artifacts:
            raise PortfolioReleaseError(f"Duplicate route artifact role: {role!r}")
        if claim_level not in CLAIM_LEVELS:
            raise PortfolioReleaseError(f"Unsupported claim level for {role}: {claim_level!r}")
        if media_type != "application/json":
            raise PortfolioReleaseError("All v1 route artifacts must use application/json")
        normalized = normalize_logical_path(logical_path, label=f"route artifact {role}")
        if role not in self.upstream_artifacts:
            self.upstream_artifacts[role] = normalized
        elif self.upstream_artifacts[role] != normalized:
            raise PortfolioReleaseError(f"Route/upstream path mismatch for role {role!r}")
        self._route_artifacts[role] = ArtifactRegistration(role, normalized, claim_level, media_type)
        return self.physical_path(normalized)

    def upstream_paths(self) -> dict[str, Path]:
        return {role: self.physical_path(path) for role, path in self.upstream_artifacts.items()}

    def upstream_refs(self) -> dict[str, str]:
        return dict(self.upstream_artifacts)


Generator = Callable[[GenerationContext], object]
FailureHook = Callable[[str], None]


def promote_portfolio_release(
    generator: Generator,
    *,
    repository_root: str | Path = ".",
    source_manifest_path: str | Path = "portfolio.sources.json",
    scenario_id: str = SUPPORTED_SCENARIO_ID,
    run_id: str | None = None,
    lock_timeout_seconds: float = 10.0,
    alias_paths: Mapping[str, str] | None = None,
    filesystem: FileSystem | None = None,
    failure_hook: FailureHook | None = None,
    clock: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Generate, validate, install, and atomically expose one immutable run.

    Visibility rollback is guaranteed for process failures before pointer
    promotion: readers continue to see the previous ``current.json``. Once the
    pointer names the validated run, later durability or notification failures
    are returned as committed warnings instead of being misreported as a failed
    release. Directory fsync is best-effort POSIX durability, not a claim about
    every power-loss or hardware/filesystem failure.
    """

    _require_posix_lock()
    root = Path(repository_root).resolve()
    fs = filesystem or FileSystem()
    now = clock or (lambda: datetime.now(timezone.utc))
    release_root = _validated_release_root(root, create=True, error_type=PortfolioReleaseError)
    staging_parent = _ensure_release_directory(release_root, ".staging")
    runs_root = _ensure_release_directory(release_root, "runs")
    lock_path = release_root / ".portfolio-release.lock"
    current_path = release_root / "current.json"
    for protected_file, label in ((lock_path, "release lock"), (current_path, "current manifest")):
        if protected_file.is_symlink():
            raise PortfolioReleaseError(f"Symlinks are not allowed for the {label}: {protected_file}")
    selected_run_id = run_id or _new_run_id(now())
    if not _RUN_ID_PATTERN.fullmatch(selected_run_id):
        raise PortfolioReleaseError(f"Unsafe release run id: {selected_run_id!r}")
    staging_root = staging_parent / selected_run_id
    installed_root = runs_root / selected_run_id
    if staging_root.is_symlink() or installed_root.is_symlink():
        raise PortfolioReleaseError(f"Symlinks are not allowed for release run id: {selected_run_id}")
    if staging_root.exists() or installed_root.exists():
        raise PortfolioReleaseError(f"Release run id already exists: {selected_run_id}")

    with _portfolio_lock(lock_path, timeout_seconds=lock_timeout_seconds):
        resolver = SourceManifestResolver(root, source_manifest_path, scenario_id=scenario_id)
        source_verification = resolver.verify()
        aliases = _normalize_alias_paths(alias_paths or DEFAULT_ALIAS_PATHS)
        staging_root.mkdir(parents=False, exist_ok=False)
        context = GenerationContext(
            run_id=selected_run_id,
            scenario_id=scenario_id,
            repository_root=root,
            physical_output_root=staging_root,
            source_resolver=resolver,
        )
        installed = False
        pointer_promoted = False
        commit_warnings: list[str] = []
        try:
            _notify_failure_hook(failure_hook, "after_staging_created")
            generator(context)
            _notify_failure_hook(failure_hook, "after_generation")
            manifest = _build_route_manifest(
                context,
                resolver=resolver,
                aliases=aliases,
                generated_at=now(),
            )
            validate_route_manifest(manifest, repository_root=root, run_root=staging_root)
            _validate_compatibility_alias_closure(
                run_root=staging_root,
                manifest=manifest,
                aliases=aliases,
            )
            _notify_failure_hook(failure_hook, "after_manifest_validated")
            route_manifest_path = staging_root / "route-manifest.json"
            _write_json_file(route_manifest_path, manifest)
            _fsync_tree(staging_root, fs)
            _notify_failure_hook(failure_hook, "after_tree_fsynced")
            fs.rename_directory(staging_root, installed_root)
            installed = True
            fs.fsync_directory(runs_root)
            fs.fsync_directory(release_root)
            _notify_failure_hook(failure_hook, "after_run_installed")
            try:
                _write_json_atomic(current_path, manifest, fs)
            except BaseException as error:
                if not _current_pointer_matches_run(root, selected_run_id):
                    raise
                pointer_promoted = True
                if not isinstance(error, Exception):
                    raise
                commit_warnings.append(
                    f"current pointer committed before write completion: {type(error).__name__}: {error}"
                )
            else:
                pointer_promoted = True
            try:
                fs.fsync_directory(release_root)
                _notify_failure_hook(failure_hook, "after_pointer_promoted")
            except Exception as error:
                commit_warnings.append(
                    f"post-promotion durability/notification warning: {type(error).__name__}: {error}"
                )
        except BaseException:
            if not pointer_promoted:
                rollback_target = installed_root if installed else staging_root
                if rollback_target.exists():
                    shutil.rmtree(rollback_target)
                    fs.fsync_directory(runs_root if installed else staging_parent)
                    fs.fsync_directory(release_root)
            raise

        try:
            alias_errors = _sync_aliases(
                root,
                installed_root,
                manifest,
                aliases,
                fs,
                failure_hook=failure_hook,
            )
        except (OSError, PortfolioReleaseError, ArtifactValidationError) as error:
            alias_errors = [f"alias-sync: {error}"]
        pointer = deepcopy(manifest)
        pointer["aliases"]["status"] = "failed" if alias_errors else "synced"
        pointer["aliases"]["errors"] = alias_errors
        try:
            _write_json_atomic(current_path, pointer, fs)
            fs.fsync_directory(release_root)
        except OSError as error:
            alias_errors.append(f"current alias-status update failed: {error}")
        status = "promoted"
        if commit_warnings:
            status = "promoted_with_warning"
        elif alias_errors:
            status = "promoted_with_alias_error"
        return {
            "status": status,
            "runId": selected_run_id,
            "scenarioId": scenario_id,
            "claimLevel": manifest["claimLevel"],
            "currentManifest": _repository_display_path(root, current_path),
            "immutableRun": _repository_display_path(root, installed_root),
            "routeManifest": _repository_display_path(root, installed_root / "route-manifest.json"),
            "artifactCount": len(manifest["artifacts"]),
            "aliases": {"status": pointer["aliases"]["status"], "errors": alias_errors},
            "warnings": commit_warnings,
            "compatibilityAliases": COMPATIBILITY_ALIAS_MANIFEST_PATH,
            "sourceVerification": source_verification,
            "pointerPromoted": pointer_promoted,
        }


def retry_alias_sync(
    *,
    repository_root: str | Path = ".",
    lock_timeout_seconds: float = 10.0,
    filesystem: FileSystem | None = None,
) -> dict[str, Any]:
    _require_posix_lock()
    root = Path(repository_root).resolve()
    fs = filesystem or FileSystem()
    release_root = _validated_release_root(root, create=False, error_type=ArtifactValidationError)
    current_path = release_root / "current.json"
    lock_path = release_root / ".portfolio-release.lock"
    if lock_path.is_symlink():
        raise ArtifactValidationError("Symlinks are not allowed for the portfolio release lock")
    with _portfolio_lock(lock_path, timeout_seconds=lock_timeout_seconds):
        manifest = read_current_manifest(repository_root=root)
        run_root = release_root / "runs" / manifest["runId"]
        aliases = {item["role"]: item["path"] for item in manifest["aliases"]["paths"]}
        try:
            errors = _sync_aliases(root, run_root, manifest, aliases, fs)
        except (OSError, PortfolioReleaseError, ArtifactValidationError) as error:
            errors = [f"alias-sync: {error}"]
        manifest["aliases"]["status"] = "failed" if errors else "synced"
        manifest["aliases"]["errors"] = errors
        _write_json_atomic(current_path, manifest, fs)
        fs.fsync_directory(release_root)
        return {
            "status": "promoted_with_alias_error" if errors else "promoted",
            "runId": manifest["runId"],
            "aliases": manifest["aliases"],
            "compatibilityAliases": COMPATIBILITY_ALIAS_MANIFEST_PATH,
        }


def read_current_manifest(*, repository_root: str | Path = ".") -> dict[str, Any]:
    root = Path(repository_root).resolve()
    release_root = _validated_release_root(root, create=False, error_type=ArtifactValidationError)
    current_path = _resolve_existing_under(
        release_root,
        "current.json",
        label="promoted current manifest",
    )
    try:
        manifest = json.loads(current_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ArtifactValidationError(f"Cannot read promoted route manifest: {error}") from error
    if not isinstance(manifest, dict):
        raise ArtifactValidationError("Promoted route manifest must be an object")
    run_id = manifest.get("runId")
    if not isinstance(run_id, str) or not _RUN_ID_PATTERN.fullmatch(run_id):
        raise ArtifactValidationError("Promoted route manifest has an invalid runId")
    run_root = _resolve_existing_under(
        release_root,
        f"runs/{run_id}",
        label="promoted immutable run",
        allow_directory=True,
    )
    validate_route_manifest(manifest, repository_root=root, run_root=run_root)
    return manifest


def _current_pointer_matches_run(repository_root: Path, run_id: str) -> bool:
    try:
        return read_current_manifest(repository_root=repository_root).get("runId") == run_id
    except (OSError, PortfolioReleaseError, ValueError, KeyError, TypeError):
        return False


def verify_source_slice(
    *,
    repository_root: str | Path = ".",
    source_manifest_path: str | Path = "portfolio.sources.json",
) -> dict[str, Any]:
    resolver = SourceManifestResolver(repository_root, source_manifest_path)
    return resolver.verify()


def _validate_canonical_release_configs(
    context: GenerationContext,
    *,
    reproduction_config: Any,
    dossier_config: Mapping[str, Any],
) -> str:
    """Bind both canonical configs and all pair inputs to the declared source slice."""

    def drift(message: str) -> None:
        raise SourceManifestError(f"Canonical config drift: {message}")

    expected_dossier_fields = {
        "id",
        "corridor",
        "decisionQuestion",
        "claimLevel",
        "pairedExperimentPath",
        "baseline",
        "measure",
        "runPassportPath",
        "outputDir",
        "costs",
        "assumptions",
        "risks",
        "decisionOptions",
    }
    dossier_fields = set(dossier_config)
    if dossier_fields != expected_dossier_fields:
        drift(
            "dossierScenarioConfig must be closed: "
            f"missing={sorted(expected_dossier_fields - dossier_fields)}, "
            f"unknown={sorted(dossier_fields - expected_dossier_fields)}"
        )

    if reproduction_config.id != "abay-first-epic-reproduction" or reproduction_config.version != 2:
        drift("reproductionConfig id/version does not identify the active Abay v2 contract")
    if reproduction_config.claim_level != "demo":
        drift("reproductionConfig.claimLevel must remain demo")
    scenario = reproduction_config.scenario_config
    if scenario.get("id") != SUPPORTED_SCENARIO_ID:
        drift("embedded scenario id is not abay-signal-retiming")
    for field in (
        "id",
        "corridor",
        "decisionQuestion",
        "claimLevel",
        "baseline",
        "measure",
        "costs",
        "assumptions",
        "risks",
        "decisionOptions",
    ):
        if dossier_config.get(field) != scenario.get(field):
            drift(f"dossierScenarioConfig.{field} does not match reproductionConfig.scenario.{field}")

    paired = reproduction_config.paired_experiment
    if paired.claim_level != "proxy" or scenario.get("claimLevel") != "proxy":
        drift("the active proxy-v1 pair and embedded scenario must retain proxy claim level")
    if scenario["costs"].get("claimLevel") != paired.claim_level:
        drift("scenario cost claim level does not match the paired experiment claim")
    pair_output_dir = normalize_logical_path(
        (PurePosixPath(reproduction_config.output_root) / paired.output_path).as_posix(),
        label="configured paired experiment output directory",
    )
    expected_pair_output_dir = PurePosixPath(_PAIR_OUTPUT_REFS["pairResult"]).parent.as_posix()
    if pair_output_dir != expected_pair_output_dir:
        drift(
            f"paired output directory must be {expected_pair_output_dir}, got {pair_output_dir}"
        )
    if dossier_config.get("pairedExperimentPath") != _PAIR_OUTPUT_REFS["pairResult"]:
        drift("dossierScenarioConfig.pairedExperimentPath does not match configured pair output")
    if dossier_config.get("runPassportPath") != DEFAULT_ALIAS_PATHS["runPassport"]:
        drift("dossierScenarioConfig.runPassportPath changed from the canonical route")
    if dossier_config.get("outputDir") != "reports/dossiers/abay-signal-retiming":
        drift("dossierScenarioConfig.outputDir changed from the canonical route")

    expected_analytics = {
        "baseline": _PAIR_OUTPUT_REFS["baselineAnalytics"],
        "measure": _PAIR_OUTPUT_REFS["measureAnalytics"],
    }
    configured_runs = {item.role: item for item in reproduction_config.analytics_runs}
    for role, expected_path in expected_analytics.items():
        run = configured_runs[role]
        configured_path = normalize_logical_path(
            (PurePosixPath(reproduction_config.output_root) / run.path).as_posix(),
            label=f"configured {role} analytics path",
        )
        if configured_path != expected_path:
            drift(f"analytics role {role} must resolve to {expected_path}, got {configured_path}")
        scenario_variant = scenario[role]
        if scenario_variant["analyticsPath"] != expected_path:
            drift(f"embedded scenario {role} analyticsPath does not match analytics role output")
        if dossier_config[role]["analyticsPath"] != expected_path:
            drift(f"dossierScenarioConfig {role} analyticsPath does not match analytics role output")
        if run.pattern != scenario_variant["scenario"]["pattern"]:
            drift(f"analytics role {role} pattern does not match embedded scenario")

    record_paths = {record.role: record.path for record in context.source_resolver.records}
    configured_source_bindings = {
        "sourceAnalytics": paired.source_analytics_path,
        "aggregateDemand": paired.aggregate_demand_path,
        "roadsGeojson": paired.context_network_path,
    }
    for role, configured_path in configured_source_bindings.items():
        if record_paths.get(role) != configured_path:
            drift(
                f"pairedExperiment path for {role} must equal the manifest-declared role path "
                f"{record_paths.get(role)!r}, got {configured_path!r}"
            )
    schema_path = record_paths.get("pairedExperimentSchema")
    if not schema_path:
        drift("source manifest does not declare pairedExperimentSchema")
    return schema_path


def generate_abay_portfolio_bundle(context: GenerationContext) -> None:
    """Build the bounded single-Abay route DAG without reading mutable root evidence.

    Source files are first verified by ``SourceManifestResolver`` and copied into
    the staging run at their repository-relative logical paths. Existing
    generators then receive explicit physical/logical maps; no generated stage
    consumes a legacy artifact from the repository root.
    """

    from .akimat_pack import GENERATED_FILE_ROLES, generate_akimat_application_pack
    from .config import parse_reproduction_config
    from .data_sources import write_provider_registry
    from .dossier import generate_scenario_dossier
    from .paired_experiment import generate_and_write_abay_signal_pair
    from .procurement import DEFAULT_EVIDENCE_REFS, generate_procurement_packet
    from .research_metrics import generate_research_metrics_pack
    from .run_metadata import default_data_sources
    from .workflow import generate_decision_workflow

    if tuple(_AKIMAT_OUTPUT_FILENAMES) != tuple(GENERATED_FILE_ROLES):
        raise PortfolioReleaseError("Akimat output role registry changed; update the bounded release adapter")

    raw_reproduction_config = context.source_json("reproductionConfig")
    try:
        reproduction_config = parse_reproduction_config(raw_reproduction_config)
    except (TypeError, ValueError) as error:
        raise SourceManifestError(f"Invalid closed reproductionConfig: {error}") from error
    raw_dossier_config = context.source_json("dossierScenarioConfig")
    if not isinstance(raw_dossier_config, dict):
        raise SourceManifestError("The Abay dossier config must contain an object")
    schema_logical_path = _validate_canonical_release_configs(
        context,
        reproduction_config=reproduction_config,
        dossier_config=raw_dossier_config,
    )
    paired = reproduction_config.paired_experiment
    pair_output_dir = (PurePosixPath(reproduction_config.output_root) / paired.output_path).as_posix()
    context.materialize_sources()
    contract_schema_path = context.physical_path(schema_logical_path)
    with _working_directory(context.physical_output_root):
        pair_outputs = generate_and_write_abay_signal_pair(
            paired.source_analytics_path,
            paired.aggregate_demand_path,
            pair_output_dir,
            context_network_path=paired.context_network_path,
            source_analytics_logical_path=paired.source_analytics_path,
            aggregate_demand_logical_path=paired.aggregate_demand_path,
            logical_output_dir=pair_output_dir,
            contract_schema_path=contract_schema_path,
            seed=reproduction_config.seed,
            baseline_delay_s=paired.baseline_delay_s,
            measure_delay_s=paired.measure_delay_s,
            affected_signals_per_trip=paired.affected_signals_per_trip,
            realization_factor=paired.realization_factor,
            claim_level=paired.claim_level,
        )
        _require_output_refs(pair_outputs, _PAIR_OUTPUT_REFS, stage="paired experiment")
        for role, logical in _PAIR_OUTPUT_REFS.items():
            context.publish_upstream(role, logical)

        provider = write_provider_registry(
            "reports/data_sources",
            source_paths={
                "roadsGeojson": "data/almaty_roads.geojson",
                "trafficProfileCsv": "data/traffic_profiles/sample_almaty.csv",
                "scenarioLibrary": "data/scenarios/library/municipal_presets.json",
            },
            source_refs={
                "roadsGeojson": "data/almaty_roads.geojson",
                "trafficProfileCsv": "data/traffic_profiles/sample_almaty.csv",
                "scenarioLibrary": "data/scenarios/library/municipal_presets.json",
            },
            artifact_refs=_PROVIDER_OUTPUT_REFS,
        )
        for role, logical in _PROVIDER_OUTPUT_REFS.items():
            context.publish_upstream("providers" if role == "registryJson" else "roadsProviderStatus", logical)

        scenario_config = deepcopy(raw_dossier_config)
        scenario_config["seed"] = reproduction_config.seed
        scenario_config["pairedExperimentPath"] = _PAIR_OUTPUT_REFS["pairResult"]
        scenario_config["pairedExperimentLogicalPath"] = _PAIR_OUTPUT_REFS["pairResult"]
        scenario_config["baseline"]["analyticsPath"] = _PAIR_OUTPUT_REFS["baselineAnalytics"]
        scenario_config["baseline"]["analyticsLogicalPath"] = _PAIR_OUTPUT_REFS["baselineAnalytics"]
        scenario_config["measure"]["analyticsPath"] = _PAIR_OUTPUT_REFS["measureAnalytics"]
        scenario_config["measure"]["analyticsLogicalPath"] = _PAIR_OUTPUT_REFS["measureAnalytics"]
        scenario_config["runPassportPath"] = DEFAULT_ALIAS_PATHS["runPassport"]
        scenario_config["releaseRunId"] = context.run_id
        scenario_config["outputDir"] = "reports/dossiers/abay-signal-retiming"
        sources = default_data_sources()
        source_overrides = {
            "analytics-normal-abay": _PAIR_OUTPUT_REFS["measureAnalytics"],
            "provider-registry": _PROVIDER_OUTPUT_REFS["registryJson"],
            "roads-provider-status": _PROVIDER_OUTPUT_REFS["roadsStatusJson"],
        }
        for source in sources:
            source_id = str(source.get("id"))
            if source_id in source_overrides:
                source["path"] = source_overrides[source_id]
        scenario_config["dataSources"] = sources
        scenario_config_path = "reports/repro/abay/scenario_config.json"
        context.write_json(scenario_config_path, scenario_config)
        context.publish_upstream("scenarioConfig", scenario_config_path)

        dossier = generate_scenario_dossier(
            scenario_config,
            output_dir="reports/dossiers/abay-signal-retiming",
            run_passport_path=DEFAULT_ALIAS_PATHS["runPassport"],
            release_run_id=context.run_id,
            paired_experiment_schema_path=contract_schema_path,
        )
        _require_output_refs(dossier.get("outputs"), _DOSSIER_OUTPUT_REFS, stage="dossier")
        context.publish_upstream("dossierMarkdown", _DOSSIER_OUTPUT_REFS["markdown"])
        context.publish_upstream("dossierHtml", _DOSSIER_OUTPUT_REFS["html"])
        context.publish_upstream("dossierKpisCsv", _DOSSIER_OUTPUT_REFS["kpisCsv"])
        context.publish_upstream("runPassport", DEFAULT_ALIAS_PATHS["runPassport"])
        context.register_route_artifact("dossier", _DOSSIER_OUTPUT_REFS["json"], claim_level="proxy")
        context.register_route_artifact("runPassport", DEFAULT_ALIAS_PATHS["runPassport"], claim_level="demo")
        context.register_route_artifact("providers", _PROVIDER_OUTPUT_REFS["registryJson"], claim_level="demo")

        workflow_paths = {
            "dossierJson": _DOSSIER_OUTPUT_REFS["json"],
            "dossierMarkdown": _DOSSIER_OUTPUT_REFS["markdown"],
            "dossierHtml": _DOSSIER_OUTPUT_REFS["html"],
            "kpiCsv": _DOSSIER_OUTPUT_REFS["kpisCsv"],
            "runPassport": DEFAULT_ALIAS_PATHS["runPassport"],
        }
        workflow_refs = {
            **workflow_paths,
            **_WORKFLOW_OUTPUT_REFS,
            "claimLedger": "docs/obsidian/03-registries/Claim Ledger.md",
        }
        workflow = generate_decision_workflow(
            _DOSSIER_OUTPUT_REFS["json"],
            out_dir="reports/workflows",
            dossier=dossier,
            artifact_paths=workflow_paths,
            artifact_refs=workflow_refs,
        )
        _require_output_refs(workflow.get("outputs"), _WORKFLOW_OUTPUT_REFS, stage="workflow")
        for role, logical in _WORKFLOW_OUTPUT_REFS.items():
            context.publish_upstream(role, logical)
        context.register_route_artifact("workflow", _WORKFLOW_OUTPUT_REFS["workflowJson"], claim_level="demo")

        procurement = generate_procurement_packet(
            "reports/procurement",
            evidence_refs=dict(DEFAULT_EVIDENCE_REFS),
            artifact_refs=_PROCUREMENT_OUTPUT_REFS,
        )
        _require_output_refs(procurement.get("outputs"), _PROCUREMENT_OUTPUT_REFS, stage="procurement")
        context.publish_upstream("procurementCsv", _PROCUREMENT_OUTPUT_REFS["csv"])
        context.register_route_artifact("procurement", _PROCUREMENT_OUTPUT_REFS["json"], claim_level="demo")

        portfolio_results_path = "reports/portfolio/month1/portfolio_results.json"
        portfolio_matrix_path = "reports/portfolio/month1/kpi_matrix.csv"
        portfolio = _write_single_scenario_portfolio(
            context,
            dossier=dossier,
            results_path=portfolio_results_path,
            matrix_path=portfolio_matrix_path,
            seed=reproduction_config.seed,
        )
        context.publish_upstream("portfolioResults", portfolio_results_path)
        context.publish_upstream("portfolioMatrix", portfolio_matrix_path)

        research = generate_research_metrics_pack(
            dossier_path=_DOSSIER_OUTPUT_REFS["json"],
            portfolio_matrix_path=portfolio_matrix_path,
            out_dir="reports/research_metrics/abay-signal-retiming",
            dossier=dossier,
            input_paths={
                "dossierJson": _DOSSIER_OUTPUT_REFS["json"],
                "portfolioMatrix": portfolio_matrix_path,
                "baselineAnalytics": _PAIR_OUTPUT_REFS["baselineAnalytics"],
                "measureAnalytics": _PAIR_OUTPUT_REFS["measureAnalytics"],
            },
            artifact_refs={
                "dossierJson": _DOSSIER_OUTPUT_REFS["json"],
                "portfolioMatrix": portfolio_matrix_path,
                "baselineAnalytics": _PAIR_OUTPUT_REFS["baselineAnalytics"],
                "measureAnalytics": _PAIR_OUTPUT_REFS["measureAnalytics"],
                **_RESEARCH_OUTPUT_REFS,
            },
        )
        expected_research = {
            "json": _RESEARCH_OUTPUT_REFS["researchJson"],
            "markdownAppendix": _RESEARCH_OUTPUT_REFS["researchAppendix"],
            "htmlVisual": _RESEARCH_OUTPUT_REFS["researchVisual"],
        }
        _require_output_refs(research.get("outputs"), expected_research, stage="research metrics")
        context.publish_upstream("researchJson", _RESEARCH_OUTPUT_REFS["researchJson"])
        context.publish_upstream("researchAppendix", _RESEARCH_OUTPUT_REFS["researchAppendix"])
        context.publish_upstream("researchVisual", _RESEARCH_OUTPUT_REFS["researchVisual"])

        repro_manifest_path = DEFAULT_ALIAS_PATHS["manifest"]
        repro_manifest = _build_reproduction_artifact_manifest(
            context,
            logical_paths=[
                *_PAIR_OUTPUT_REFS.values(),
                scenario_config_path,
                *_DOSSIER_OUTPUT_REFS.values(),
                DEFAULT_ALIAS_PATHS["runPassport"],
                *_PROVIDER_OUTPUT_REFS.values(),
                *_WORKFLOW_OUTPUT_REFS.values(),
                *_PROCUREMENT_OUTPUT_REFS.values(),
                portfolio_results_path,
                portfolio_matrix_path,
                *_RESEARCH_OUTPUT_REFS.values(),
            ],
        )
        context.write_json(repro_manifest_path, repro_manifest)
        context.publish_upstream("reproManifest", repro_manifest_path)

        repro_metadata_path = DEFAULT_ALIAS_PATHS["reproduction"]
        reproduction = _build_reproduction_metadata(
            context,
            dossier=dossier,
            portfolio=portfolio,
            artifact_manifest=repro_manifest,
            scenario_config_path=scenario_config_path,
        )
        context.write_json(repro_metadata_path, reproduction)
        context.publish_upstream("reproMetadata", repro_metadata_path)
        context.register_route_artifact("manifest", repro_manifest_path, claim_level="demo")
        context.register_route_artifact("reproduction", repro_metadata_path, claim_level="demo")

        akimat_dir = "reports/akimat/abay-signal-retiming"
        akimat_output_refs = {
            role: f"{akimat_dir}/{filename}"
            for role, filename in _AKIMAT_OUTPUT_FILENAMES.items()
        }
        akimat_inputs = {
            "dossier": _DOSSIER_OUTPUT_REFS["json"],
            "scenarioConfig": scenario_config_path,
            "runPassport": DEFAULT_ALIAS_PATHS["runPassport"],
            "providers": _PROVIDER_OUTPUT_REFS["registryJson"],
            "workflow": _WORKFLOW_OUTPUT_REFS["workflowJson"],
            "procurement": _PROCUREMENT_OUTPUT_REFS["json"],
            "reproManifest": repro_manifest_path,
            "reproMetadata": repro_metadata_path,
            "portfolioResults": portfolio_results_path,
            "dossierMarkdown": _DOSSIER_OUTPUT_REFS["markdown"],
            "roadsProviderStatus": _PROVIDER_OUTPUT_REFS["roadsStatusJson"],
            "portfolioMatrix": portfolio_matrix_path,
            "researchAppendix": _RESEARCH_OUTPUT_REFS["researchAppendix"],
        }
        akimat = generate_akimat_application_pack(
            akimat_dir,
            inputs=akimat_inputs,
            evidence_refs=akimat_inputs,
            output_refs=akimat_output_refs,
        )
        _require_output_refs(akimat.get("files"), akimat_output_refs, stage="Akimat application pack")
        for role, logical in akimat_output_refs.items():
            context.publish_upstream(f"akimat:{role}", logical)
        context.register_route_artifact("dataReadiness", akimat_output_refs["data_readiness_json"], claim_level="demo")
        context.register_route_artifact("procurementPack", akimat_output_refs["procurement_pack_index_json"], claim_level="demo")
        context.register_route_artifact("applicationPack", akimat_output_refs["application_package_index_json"], claim_level="demo")
        context.register_route_artifact("pilotPlan", akimat_output_refs["pilot_monitoring_plan_json"], claim_level="demo")


def _write_single_scenario_portfolio(
    context: GenerationContext,
    *,
    dossier: Mapping[str, Any],
    results_path: str,
    matrix_path: str,
    seed: int,
) -> dict[str, Any]:
    import csv

    kpis = {
        str(item.get("id")): item
        for item in dossier.get("executiveKpis", {}).get("kpis", [])
        if isinstance(item, dict)
    }

    def value(kpi_id: str) -> Any:
        return kpis.get(kpi_id, {}).get("measure")

    row = {
        "rank": 1,
        "portfolio_id": "abay-controlled-pair-v1",
        "scenario_id": SUPPORTED_SCENARIO_ID,
        "scenario_name": dossier.get("proposedMeasure", {}).get("label"),
        "scenario_type": dossier.get("proposedMeasure", {}).get("type"),
        "corridor_id": dossier.get("corridor", {}).get("id"),
        "claim_level": dossier.get("claimLevel", "proxy"),
        "decision_signal": dossier.get("recommendation", {}).get("decision"),
        "person_hours_saved": value("person_hours_saved"),
        "corridor_speed_delta": value("corridor_speed_delta"),
        "queue_load_proxy": value("queue_load_proxy"),
        "bus_reliability_proxy": value("bus_reliability_proxy"),
        "co2_proxy": value("co2_proxy"),
        "nox_proxy": value("nox_proxy"),
        "capex_placeholder": value("capex_placeholder"),
        "opex_placeholder": value("opex_placeholder"),
        "annual_time_savings_proxy": value("annual_time_savings_proxy"),
        "roi_proxy": value("roi_proxy"),
        "payback_proxy": value("payback_proxy"),
        "analytics_path": _PAIR_OUTPUT_REFS["measureAnalytics"],
        "run_passport_path": DEFAULT_ALIAS_PATHS["runPassport"],
    }
    matrix_file = context.physical_path(matrix_path, create_parent=True)
    with matrix_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    portfolio = {
        "id": "abay-controlled-pair-v1",
        "title": "Controlled Abay signal-retiming portfolio slice",
        "claimLevel": "proxy",
        "seed": seed,
        "baseline": {
            "label": dossier.get("baseline", {}).get("label", "Current modeled baseline"),
            "analyticsPath": _PAIR_OUTPUT_REFS["baselineAnalytics"],
        },
        "matrix": [row],
        "limitations": list(dossier.get("limitations", [])),
        "outputs": {"json": results_path, "kpiMatrixCsv": matrix_path},
    }
    context.write_json(results_path, portfolio)
    return portfolio


def _build_reproduction_artifact_manifest(
    context: GenerationContext,
    *,
    logical_paths: Iterable[str],
) -> dict[str, Any]:
    artifacts = []
    seen: set[str] = set()
    for raw_path in logical_paths:
        logical = normalize_logical_path(raw_path, label="reproduction artifact")
        if logical in seen:
            continue
        seen.add(logical)
        physical = _resolve_existing_under(
            context.physical_output_root,
            logical,
            label="reproduction artifact",
        )
        artifacts.append(
            {
                "kind": _artifact_kind(logical),
                "path": logical,
                "claimLevel": _claim_for_artifact(logical),
                "bytes": physical.stat().st_size,
                "sha256": sha256_file(physical),
            }
        )
    return {
        "id": "abay-first-epic-artifact-manifest",
        "kind": "reproduction-artifact-manifest",
        "claimLevel": "demo",
        "runId": context.run_id,
        "createdAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "artifacts": artifacts,
    }


def _build_reproduction_metadata(
    context: GenerationContext,
    *,
    dossier: Mapping[str, Any],
    portfolio: Mapping[str, Any],
    artifact_manifest: Mapping[str, Any],
    scenario_config_path: str,
) -> dict[str, Any]:
    pair = json.loads(
        context.physical_path(_PAIR_OUTPUT_REFS["pairResult"]).read_text(encoding="utf-8")
    )
    return {
        "id": "abay-first-epic-reproduction",
        "kind": "first-epic-reproduction",
        "claimLevel": "demo",
        "createdAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "releaseRunId": context.run_id,
        "seed": pair["experiment"]["seed"],
        "configPath": "simulation.config.json",
        "scenarioConfigPath": scenario_config_path,
        "sourceControl": {
            "gitHash": None,
            "dirty": None,
            "note": "Source-control state is execution context and is not part of the semantic experiment hash.",
        },
        "inputFingerprints": [
            {
                "path": record.path,
                "available": True,
                "sha256": sha256_file(context.physical_path(record.path)),
                "bytes": context.physical_path(record.path).stat().st_size,
            }
            for record in context.source_resolver.records
            if record.kind in _HASHED_SOURCE_KINDS
            and context.physical_path(record.path).is_file()
        ],
        "commands": [
            {
                "role": "paired-experiment",
                "mode": "controlled-proxy-v1",
                "command": ["python3", "scripts/bootstrap_portfolio.py"],
                "expectedPaths": dict(_PAIR_OUTPUT_REFS),
            }
        ],
        "pairedExperiment": {
            "schemaVersion": pair["schemaVersion"],
            "modelId": pair["modelId"],
            "semanticFingerprint": pair["semanticFingerprint"],
            "controlledDifferences": pair["experiment"]["controlledDifferences"],
            "demandControl": pair["experiment"]["demandControl"],
            "baseSeriesFingerprint": pair["experiment"]["baseSeriesFingerprint"],
            "contextNetworkFingerprint": pair["experiment"]["contextNetworkFingerprint"],
            "outputs": dict(_PAIR_OUTPUT_REFS),
        },
        "outputs": {
            "metadata": DEFAULT_ALIAS_PATHS["reproduction"],
            "artifactManifest": DEFAULT_ALIAS_PATHS["manifest"],
            "dossier": dict(_DOSSIER_OUTPUT_REFS),
            "runPassport": DEFAULT_ALIAS_PATHS["runPassport"],
            "workflow": dict(_WORKFLOW_OUTPUT_REFS),
            "procurement": dict(_PROCUREMENT_OUTPUT_REFS),
            "researchMetrics": {
                "json": _RESEARCH_OUTPUT_REFS["researchJson"],
                "markdownAppendix": _RESEARCH_OUTPUT_REFS["researchAppendix"],
                "htmlVisual": _RESEARCH_OUTPUT_REFS["researchVisual"],
            },
            "providerRegistry": dict(_PROVIDER_OUTPUT_REFS),
            "pairedExperiment": dict(_PAIR_OUTPUT_REFS),
            "portfolio": dict(portfolio.get("outputs", {})),
        },
        "artifactCount": len(artifact_manifest["artifacts"]),
        "reproducibilityNotes": [
            "Baseline and measure share seed, aggregate demand control, and source analytics primitives.",
            "The signal-delay values are bounded proxy sensitivity inputs, not observed controller timings.",
            "Timestamps differ between releases; the paired semantic fingerprint excludes registered volatile fields.",
            "POSIX fsync provides best-effort local durability, not recovery from every power-loss or hardware failure.",
        ],
        "claimLabels": {
            "reproduction": "demo",
            "dossier": dossier.get("claimLevel", "proxy"),
            "portfolio": portfolio.get("claimLevel", "proxy"),
            "workflow": "demo",
            "procurement": "demo",
        },
    }


def _artifact_kind(logical_path: str) -> str:
    if "paired-experiment" in logical_path:
        return "paired-experiment-result"
    if "dossier" in logical_path:
        return "scenario-dossier"
    if "run-passport" in logical_path:
        return "run-passport"
    if "workflow" in logical_path:
        return "decision-workflow"
    if "procurement" in logical_path or "tender" in logical_path:
        return "procurement-evidence"
    if "research" in logical_path:
        return "research-evidence"
    if "portfolio" in logical_path:
        return "portfolio-evidence"
    if "provider" in logical_path:
        return "provider-evidence"
    return "reproduction-artifact"


def _claim_for_artifact(logical_path: str) -> str:
    if any(token in logical_path for token in ("pair/", "dossier", "research", "portfolio")):
        return "proxy"
    if logical_path.endswith("roads_geojson_provider_status.json"):
        return "real-data"
    return "demo"


def _require_output_refs(actual: Any, expected: Mapping[str, str], *, stage: str) -> None:
    if not isinstance(actual, Mapping):
        raise PortfolioReleaseError(f"{stage} did not return an output map")
    normalized = {str(role): str(path) for role, path in actual.items()}
    if normalized != dict(expected):
        raise PortfolioReleaseError(
            f"{stage} output references changed: expected={dict(expected)}, actual={normalized}"
        )


@contextmanager
def _working_directory(path: Path) -> Iterable[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def validate_route_manifest(
    manifest: Mapping[str, Any],
    *,
    repository_root: str | Path,
    run_root: str | Path,
) -> None:
    root = Path(repository_root).resolve()
    run = Path(run_root).resolve()
    _validate_materialized_source_binding(manifest, run_root=run)
    schema_path = _resolve_existing_under(
        run,
        "schemas/portfolio-route-manifest.schema.json",
        label="materialized route manifest schema",
    )
    _validate_route_manifest_schema(manifest, schema_path)
    run_id = str(manifest["runId"])
    entries = manifest["artifacts"]
    roles = [str(entry["role"]) for entry in entries]
    if len(set(roles)) != len(roles):
        raise ArtifactValidationError("Route manifest contains duplicate artifact roles")
    if set(roles) != set(REQUIRED_ROUTE_ROLES):
        raise ArtifactValidationError(
            f"Route manifest role mismatch: missing={sorted(set(REQUIRED_ROUTE_ROLES) - set(roles))}, "
            f"unknown={sorted(set(roles) - set(REQUIRED_ROUTE_ROLES))}"
        )
    alias_entries = manifest["aliases"]["paths"]
    alias_roles = [str(item["role"]) for item in alias_entries]
    if len(alias_roles) != len(set(alias_roles)) or set(alias_roles) != set(REQUIRED_ROUTE_ROLES):
        raise ArtifactValidationError(
            f"Route manifest alias role mismatch: "
            f"missing={sorted(set(REQUIRED_ROUTE_ROLES) - set(alias_roles))}, "
            f"unknown={sorted(set(alias_roles) - set(REQUIRED_ROUTE_ROLES))}"
        )
    alias_paths = [
        normalize_logical_path(str(item["path"]), label=f"alias {item['role']}")
        for item in alias_entries
    ]
    if len(alias_paths) != len(set(alias_paths)):
        raise ArtifactValidationError("Route manifest contains duplicate alias paths")
    logical_paths: set[str] = set()
    for entry in entries:
        if entry["runId"] != run_id:
            raise ArtifactValidationError(f"Mixed release run binding for role {entry['role']}")
        logical = normalize_logical_path(str(entry["logicalPath"]), label=f"artifact {entry['role']}")
        if logical in logical_paths:
            raise ArtifactValidationError(f"Duplicate artifact logical path: {logical}")
        logical_paths.add(logical)
        path = _resolve_existing_under(run, logical, label=f"artifact {entry['role']}")
        if not path.is_file():
            raise ArtifactValidationError(f"Route artifact is not a regular file: {logical}")
        if path.stat().st_size != entry["bytes"]:
            raise ArtifactValidationError(f"Route artifact byte count mismatch: {logical}")
        actual_hash = sha256_file(path)
        if actual_hash != entry["sha256"]:
            raise ArtifactValidationError(f"Route artifact hash mismatch: {logical}")
        if entry["mediaType"] == "application/json":
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise ArtifactValidationError(f"Invalid JSON route artifact {logical}: {error}") from error
            _validate_release_run_binding(
                payload,
                artifact_role=str(entry["role"]),
                expected_run_id=run_id,
            )
            _validate_nested_integrity_records(payload, run_root=run, artifact_role=str(entry["role"]))
            _validate_serialized_references(payload, run_root=run, artifact_role=str(entry["role"]))


def _validate_materialized_source_binding(
    manifest: Mapping[str, Any],
    *,
    run_root: Path,
) -> tuple[SourceRecord, ...]:
    source_binding = manifest.get("sourceManifest")
    if not isinstance(source_binding, Mapping):
        raise ArtifactValidationError("Route manifest sourceManifest must be an object")
    if set(source_binding) != {"path", "sha256"}:
        raise ArtifactValidationError("Route manifest sourceManifest has invalid fields")
    logical = normalize_logical_path(str(source_binding.get("path", "")), label="source manifest binding")
    if logical != "portfolio.sources.json":
        raise ArtifactValidationError("The materialized source manifest must be portfolio.sources.json")
    expected_hash = str(source_binding.get("sha256", ""))
    if not _SHA256_PATTERN.fullmatch(expected_hash):
        raise ArtifactValidationError("Route manifest sourceManifest has an invalid SHA-256")
    source_manifest_path = _resolve_existing_under(
        run_root,
        logical,
        label="materialized source manifest",
    )
    actual_hash = sha256_file(source_manifest_path)
    if actual_hash != expected_hash:
        raise ArtifactValidationError(
            f"Materialized source manifest hash mismatch: expected {expected_hash}, got {actual_hash}"
        )
    try:
        payload = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        records = SourceManifestResolver._parse(payload, scenario_id=SUPPORTED_SCENARIO_ID)
    except (OSError, json.JSONDecodeError, SourceManifestError) as error:
        raise ArtifactValidationError(f"Invalid materialized source manifest: {error}") from error
    for record in records:
        candidate = run_root / record.path
        if not record.required and not candidate.exists():
            continue
        path = _resolve_existing_under(
            run_root,
            record.path,
            label=f"materialized source {record.role}",
        )
        if record.sha256 is not None:
            materialized_hash = sha256_file(path)
            if materialized_hash != record.sha256:
                raise ArtifactValidationError(
                    f"Materialized source hash mismatch for {record.path}: "
                    f"expected {record.sha256}, got {materialized_hash}"
                )
    return records


def _validate_release_run_binding(
    payload: Any,
    *,
    artifact_role: str,
    expected_run_id: str,
) -> None:
    if not isinstance(payload, Mapping):
        raise ArtifactValidationError(f"Route artifact {artifact_role} must contain an object")
    bindings: dict[str, tuple[str, ...]] = {
        "dossier": ("trustMetadata", "runId"),
        "runPassport": ("runId",),
        "reproduction": ("releaseRunId",),
        "manifest": ("runId",),
        "scenarioConfig": ("releaseRunId",),
        "researchJson": ("runPassportId",),
    }
    path = bindings.get(artifact_role)
    if path is None:
        return
    value: Any = payload
    for key in path:
        if not isinstance(value, Mapping) or key not in value:
            pointer = "/" + "/".join(path)
            raise ArtifactValidationError(
                f"Route artifact {artifact_role} is missing release binding {pointer}"
            )
        value = value[key]
    if value != expected_run_id:
        pointer = "/" + "/".join(path)
        raise ArtifactValidationError(
            f"Mixed release run binding in {artifact_role}{pointer}: "
            f"expected {expected_run_id!r}, got {value!r}"
        )


def validate_manifest_fixture(payload: Mapping[str, Any], *, schema_path: str | Path) -> None:
    """Public schema-only helper shared with contract fixtures."""

    _validate_route_manifest_schema(payload, Path(schema_path))


def normalize_logical_path(value: str, *, label: str = "logical path") -> str:
    raw = str(value)
    candidate = PurePosixPath(raw)
    if (
        not raw
        or raw != raw.strip()
        or "\\" in raw
        or candidate.is_absolute()
        or "." in candidate.parts
        or ".." in candidate.parts
        or any(part == ".staging" or ".staging" in part for part in candidate.parts)
        or (candidate.parts and candidate.parts[0].endswith(":"))
    ):
        raise ArtifactValidationError(f"Unsafe {label}: {raw!r}")
    normalized = candidate.as_posix()
    if normalized != raw:
        raise ArtifactValidationError(f"Non-canonical {label}: {raw!r}")
    return normalized


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_route_manifest(
    context: GenerationContext,
    *,
    resolver: SourceManifestResolver,
    aliases: Mapping[str, str],
    generated_at: datetime,
) -> dict[str, Any]:
    registrations = context.route_artifacts
    roles = {item.role for item in registrations}
    if roles != set(REQUIRED_ROUTE_ROLES):
        raise ArtifactValidationError(
            f"Generator did not register the exact route set: "
            f"missing={sorted(set(REQUIRED_ROUTE_ROLES) - roles)}, "
            f"unknown={sorted(roles - set(REQUIRED_ROUTE_ROLES))}"
        )
    artifacts = []
    for registration in registrations:
        path = _resolve_existing_under(
            context.physical_output_root,
            registration.logical_path,
            label=f"generated route artifact {registration.role}",
        )
        if not path.is_file():
            raise ArtifactValidationError(f"Generated route artifact is not a file: {registration.logical_path}")
        artifacts.append(
            {
                "role": registration.role,
                "runId": context.run_id,
                "logicalPath": registration.logical_path,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "mediaType": registration.media_type,
                "claimLevel": registration.claim_level,
            }
        )
    artifacts.sort(key=lambda item: REQUIRED_ROUTE_ROLES.index(item["role"]))
    return {
        "schemaVersion": ROUTE_MANIFEST_SCHEMA_VERSION,
        "runId": context.run_id,
        "scenarioId": context.scenario_id,
        "claimLevel": "demo",
        "generatedAt": _iso_timestamp(generated_at),
        "status": "promoted",
        "sourceManifest": {
            "path": resolver.manifest_relative_path,
            "sha256": resolver.manifest_sha256,
        },
        "artifacts": artifacts,
        "aliases": {
            "status": "pending",
            "errors": [],
            "paths": [
                {"role": role, "path": aliases[role]}
                for role in REQUIRED_ROUTE_ROLES
            ],
        },
    }


def _validate_route_manifest_schema(manifest: Mapping[str, Any], schema_path: Path) -> None:
    try:
        from jsonschema import Draft202012Validator, FormatChecker
        from jsonschema.exceptions import SchemaError, ValidationError
    except ImportError as error:
        raise PortfolioDependencyError(
            "jsonschema>=4.23,<5 is required for Draft 2020-12 portfolio validation"
        ) from error
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ArtifactValidationError(f"Cannot read route manifest schema: {error}") from error
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(dict(manifest))
    except (SchemaError, ValidationError) as error:
        path = "/" + "/".join(str(item) for item in getattr(error, "absolute_path", ()))
        raise ArtifactValidationError(f"Route manifest schema validation failed at {path}: {error.message}") from error


def _validate_serialized_references(payload: Any, *, run_root: Path, artifact_role: str) -> None:
    for reference in _iter_serialized_references(payload):
        if _looks_like_url(reference):
            continue
        normalized = normalize_logical_path(reference, label=f"reference in {artifact_role}")
        path = _resolve_existing_under(
            run_root,
            normalized,
            label=f"reference in {artifact_role}",
            allow_directory=True,
        )
        if not path.exists():  # pragma: no cover - strict resolver already enforces this.
            raise ArtifactValidationError(f"Unresolved reference in {artifact_role}: {normalized}")


def _validate_nested_integrity_records(payload: Any, *, run_root: Path, artifact_role: str) -> None:
    """Verify every available nested ``path``/``sha256``/``bytes`` record.

    This covers the legacy reproduction artifact manifest and Akimat evidence
    manifests/indexes, so a truthful outer route hash cannot hide a lying
    nested artifact claim.
    """

    for record in _iter_nested_integrity_records(payload):
        if record.get("available") is False:
            continue
        path_value = record.get("path")
        hash_value = record.get("sha256")
        bytes_value = record.get("bytes")
        if not isinstance(path_value, str):
            raise ArtifactValidationError(f"Nested integrity path in {artifact_role} must be a string")
        if not isinstance(hash_value, str) or not _SHA256_PATTERN.fullmatch(hash_value):
            raise ArtifactValidationError(
                f"Nested integrity SHA-256 in {artifact_role} is invalid for {path_value!r}"
            )
        if isinstance(bytes_value, bool) or not isinstance(bytes_value, int) or bytes_value < 0:
            raise ArtifactValidationError(
                f"Nested integrity byte count in {artifact_role} is invalid for {path_value!r}"
            )
        logical = normalize_logical_path(path_value, label=f"nested integrity path in {artifact_role}")
        path = _resolve_existing_under(
            run_root,
            logical,
            label=f"nested integrity artifact in {artifact_role}",
        )
        if path.stat().st_size != bytes_value:
            raise ArtifactValidationError(
                f"Nested artifact byte count mismatch in {artifact_role}: {logical}"
            )
        actual_hash = sha256_file(path)
        if actual_hash != hash_value:
            raise ArtifactValidationError(
                f"Nested artifact hash mismatch in {artifact_role}: {logical}"
            )


def _iter_nested_integrity_records(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        if {"path", "sha256", "bytes"}.issubset(value):
            yield value
        for item in value.values():
            yield from _iter_nested_integrity_records(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_nested_integrity_records(item)


def _iter_serialized_references(
    value: Any,
    *,
    parent_key: str = "",
    path_map: bool = False,
) -> Iterable[str]:
    if isinstance(value, dict):
        unavailable = value.get("available") is False
        for raw_key, item in value.items():
            key = str(raw_key)
            key_lower = key.lower()
            scalar_path_keys = {
                "analyticspath",
                "analyticslogicalpath",
                "artifactpath",
                "configpath",
                "evidencepath",
                "matrixpath",
                "outputpath",
                "pairedexperimentpath",
                "pairedexperimentlogicalpath",
                "path",
                "relativepath",
                "runpassportpath",
                "scenarioconfigpath",
                "source_analytics_path",
                "run_passport_path",
            }
            collection_keys = {
                "artifactpaths",
                "evidence",
                "expectedpaths",
                "files",
                "inputs",
                "outputs",
            }
            is_json_pointer = (
                key_lower == "path"
                and isinstance(item, str)
                and item.startswith("/")
                and "baseline" in value
                and "measure" in value
            )
            is_path_key = key_lower in scalar_path_keys and not is_json_pointer
            collection_key = key_lower in collection_keys
            if isinstance(item, str) and item and is_path_key:
                if not unavailable:
                    yield item
            elif isinstance(item, list) and (is_path_key or collection_key):
                if not unavailable:
                    for nested in item:
                        if isinstance(nested, str) and _looks_like_serialized_path(nested):
                            yield nested
                        else:
                            yield from _iter_serialized_references(nested, parent_key=key)
            elif isinstance(item, Mapping) and collection_key:
                if not unavailable and "path" not in {str(nested_key).lower() for nested_key in item}:
                    for nested in item.values():
                        if isinstance(nested, str) and _looks_like_serialized_path(nested):
                            yield nested
                        elif not isinstance(nested, str):
                            yield from _iter_serialized_references(nested, parent_key=key)
                else:
                    yield from _iter_serialized_references(item, parent_key=key)
            else:
                yield from _iter_serialized_references(item, parent_key=key)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_serialized_references(item, parent_key=parent_key)


def _looks_like_serialized_path(value: str) -> bool:
    if _looks_like_url(value):
        return True
    raw = str(value)
    if not raw or raw != raw.strip():
        return False
    if "/" in raw or "\\" in raw or raw.startswith("."):
        return True
    if raw == "Dockerfile":
        return True
    return PurePosixPath(raw).suffix.lower() in {
        ".csv",
        ".geojson",
        ".html",
        ".json",
        ".md",
        ".png",
        ".py",
        ".toml",
        ".yaml",
        ".yml",
    }


def _sync_aliases(
    repository_root: Path,
    run_root: Path,
    manifest: Mapping[str, Any],
    aliases: Mapping[str, str],
    filesystem: FileSystem,
    *,
    failure_hook: FailureHook | None = None,
) -> list[str]:
    specifications = _compatibility_alias_specifications(
        run_root=run_root,
        manifest=manifest,
        aliases=aliases,
    )
    errors: list[str] = []
    compatibility_entries: list[dict[str, Any]] = []
    for specification in specifications:
        role = str(specification["role"])
        kind = str(specification["kind"])
        source_logical = str(specification["sourceLogicalPath"])
        target_relative = str(specification["path"])
        temporary: Path | None = None
        try:
            hook_prefix = "before_alias" if kind == "route" else "before_support_alias"
            _notify_failure_hook(failure_hook, f"{hook_prefix}:{role}")
            source = _resolve_existing_under(
                run_root,
                source_logical,
                label=f"{kind} compatibility alias source {role}",
            )
            target = _resolve_for_write_under(
                repository_root,
                target_relative,
                label=f"{kind} compatibility alias target {role}",
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(f".{target.name}.portfolio-{uuid4().hex}.tmp")
            filesystem.copy_file(source, temporary)
            filesystem.fsync_file(temporary)
            filesystem.replace_file(temporary, target)
            filesystem.fsync_directory(target.parent)
            if target.stat().st_size != specification["bytes"]:
                raise OSError("copied compatibility alias byte count does not match immutable artifact")
            if sha256_file(target) != specification["sha256"]:
                raise OSError("copied alias hash does not match immutable artifact")
        except (OSError, PortfolioReleaseError, ArtifactValidationError) as error:
            errors.append(f"{kind}:{role}: {error}")
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        compatibility_entries.append(dict(specification))

    compatibility_payload = {
        "schemaVersion": COMPATIBILITY_ALIAS_SCHEMA_VERSION,
        "runId": manifest["runId"],
        "generatedAt": manifest["generatedAt"],
        "status": "failed" if errors else "synced",
        "errors": list(errors),
        "aliases": compatibility_entries,
    }
    compatibility_path = _resolve_for_write_under(
        repository_root,
        COMPATIBILITY_ALIAS_MANIFEST_PATH,
        label="compatibility alias manifest",
    )
    try:
        _write_json_atomic(compatibility_path, compatibility_payload, filesystem)
        filesystem.fsync_directory(compatibility_path.parent)
    except OSError as error:
        errors.append(f"compatibility-manifest: {error}")
    return errors


def _compatibility_alias_specifications(
    *,
    run_root: Path,
    manifest: Mapping[str, Any],
    aliases: Mapping[str, str],
) -> list[dict[str, Any]]:
    route_entries = {str(item["role"]): item for item in manifest["artifacts"]}
    specifications: list[dict[str, Any]] = []
    for role in REQUIRED_ROUTE_ROLES:
        entry = route_entries[role]
        specifications.append(
            {
                "role": role,
                "kind": "route",
                "sourceLogicalPath": str(entry["logicalPath"]),
                "path": normalize_logical_path(aliases[role], label=f"alias target {role}"),
                "sha256": str(entry["sha256"]),
                "bytes": int(entry["bytes"]),
            }
        )
    for role, logical_path in DEFAULT_SUPPORT_ALIAS_PATHS.items():
        normalized = normalize_logical_path(logical_path, label=f"support alias source {role}")
        source = _resolve_existing_under(
            run_root,
            normalized,
            label=f"support alias source {role}",
        )
        specifications.append(
            {
                "role": role,
                "kind": "support",
                "sourceLogicalPath": normalized,
                "path": normalized,
                "sha256": sha256_file(source),
                "bytes": source.stat().st_size,
            }
        )
    targets = [str(item["path"]) for item in specifications]
    if len(set(targets)) != len(targets):
        raise ArtifactValidationError("Compatibility alias targets must be unique")
    return specifications


def _validate_compatibility_alias_closure(
    *,
    run_root: Path,
    manifest: Mapping[str, Any],
    aliases: Mapping[str, str],
) -> None:
    specifications = _compatibility_alias_specifications(
        run_root=run_root,
        manifest=manifest,
        aliases=aliases,
    )
    source_paths = {str(item["sourceLogicalPath"]) for item in specifications}
    target_paths = {str(item["path"]) for item in specifications}
    generated_prefixes = ("reports/", "data/runs/")
    for specification in specifications:
        source = _resolve_existing_under(
            run_root,
            str(specification["sourceLogicalPath"]),
            label=f"compatibility closure source {specification['role']}",
        )
        if source.suffix.lower() != ".json":
            continue
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ArtifactValidationError(
                f"Invalid JSON compatibility source {specification['sourceLogicalPath']}: {error}"
            ) from error
        _validate_nested_integrity_records(
            payload,
            run_root=run_root,
            artifact_role=f"compatibility:{specification['role']}",
        )
        _validate_release_run_binding(
            payload,
            artifact_role=str(specification["role"]),
            expected_run_id=str(manifest["runId"]),
        )
        for reference in _iter_serialized_references(payload):
            if _looks_like_url(reference):
                continue
            logical = normalize_logical_path(
                reference,
                label=f"compatibility reference in {specification['role']}",
            )
            _resolve_existing_under(
                run_root,
                logical,
                label=f"compatibility reference in {specification['role']}",
                allow_directory=True,
            )
            if logical.startswith(generated_prefixes) and logical not in source_paths:
                raise ArtifactValidationError(
                    f"Generated compatibility dependency is outside the closed alias list: {logical}"
                )
    # Serialized references use canonical logical paths. A custom route alias
    # cannot silently make a legacy root artifact internally inconsistent.
    missing_targets = sorted(source_paths - target_paths)
    if missing_targets:
        raise ArtifactValidationError(
            f"Compatibility alias targets omit canonical serialized paths: {missing_targets}"
        )


def verify_compatibility_aliases(
    *,
    repository_root: str | Path = ".",
    route_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify the closed mutable compatibility view against one immutable run."""

    root = Path(repository_root).resolve()
    manifest = dict(route_manifest) if route_manifest is not None else read_current_manifest(repository_root=root)
    if manifest.get("aliases", {}).get("status") != "synced":
        raise ArtifactValidationError("Current route manifest compatibility aliases are not synced")
    run_root = root / "reports" / "portfolio" / "runs" / str(manifest["runId"])
    aliases = {str(item["role"]): str(item["path"]) for item in manifest["aliases"]["paths"]}
    expected = _compatibility_alias_specifications(
        run_root=run_root,
        manifest=manifest,
        aliases=aliases,
    )
    compatibility_path = _resolve_existing_under(
        root,
        COMPATIBILITY_ALIAS_MANIFEST_PATH,
        label="compatibility alias manifest",
    )
    try:
        payload = json.loads(compatibility_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ArtifactValidationError(f"Invalid compatibility alias manifest: {error}") from error
    if not isinstance(payload, dict):
        raise ArtifactValidationError("Compatibility alias manifest must contain an object")
    if set(payload) != {"schemaVersion", "runId", "generatedAt", "status", "errors", "aliases"}:
        raise ArtifactValidationError("Compatibility alias manifest has invalid fields")
    if (
        payload.get("schemaVersion") != COMPATIBILITY_ALIAS_SCHEMA_VERSION
        or payload.get("runId") != manifest["runId"]
        or payload.get("generatedAt") != manifest["generatedAt"]
        or payload.get("status") != "synced"
        or payload.get("errors") != []
        or payload.get("aliases") != expected
    ):
        raise ArtifactValidationError("Compatibility alias manifest does not match the current immutable run")
    target_paths = {str(item["path"]) for item in expected}
    generated_prefixes = ("reports/", "data/runs/")
    for entry in expected:
        target = _resolve_existing_under(
            root,
            str(entry["path"]),
            label=f"compatibility alias {entry['kind']}:{entry['role']}",
        )
        if target.stat().st_size != entry["bytes"] or sha256_file(target) != entry["sha256"]:
            raise ArtifactValidationError(
                f"Compatibility alias hash/bytes mismatch: {entry['path']}"
            )
        if target.suffix.lower() != ".json":
            continue
        try:
            artifact_payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ArtifactValidationError(f"Invalid JSON compatibility alias {entry['path']}: {error}") from error
        _validate_nested_integrity_records(
            artifact_payload,
            run_root=root,
            artifact_role=f"root-compatibility:{entry['role']}",
        )
        _validate_release_run_binding(
            artifact_payload,
            artifact_role=str(entry["role"]),
            expected_run_id=str(manifest["runId"]),
        )
        for reference in _iter_serialized_references(artifact_payload):
            if _looks_like_url(reference):
                continue
            logical = normalize_logical_path(reference, label=f"root compatibility reference {entry['role']}")
            _resolve_existing_under(
                root,
                logical,
                label=f"root compatibility reference {entry['role']}",
                allow_directory=True,
            )
            if logical.startswith(generated_prefixes) and logical not in target_paths:
                raise ArtifactValidationError(
                    f"Root compatibility reference is outside the closed alias list: {logical}"
                )
    return {
        "status": "verified",
        "runId": manifest["runId"],
        "aliasCount": len(expected),
        "routeAliasCount": len(REQUIRED_ROUTE_ROLES),
        "supportAliasCount": len(DEFAULT_SUPPORT_ALIAS_PATHS),
        "manifest": COMPATIBILITY_ALIAS_MANIFEST_PATH,
    }


def _normalize_alias_paths(values: Mapping[str, str]) -> dict[str, str]:
    missing = sorted(set(REQUIRED_ROUTE_ROLES) - set(values))
    unknown = sorted(set(values) - set(REQUIRED_ROUTE_ROLES))
    if missing or unknown:
        raise PortfolioReleaseError(f"Invalid alias roles: missing={missing}, unknown={unknown}")
    normalized = {
        role: normalize_logical_path(str(values[role]), label=f"alias {role}")
        for role in REQUIRED_ROUTE_ROLES
    }
    if len(set(normalized.values())) != len(normalized):
        raise PortfolioReleaseError("Alias paths must be unique")
    return normalized


def _write_json_file(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _write_json_atomic(path: Path, payload: Mapping[str, Any], filesystem: FileSystem) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.portfolio-{uuid4().hex}.tmp")
    try:
        _write_json_file(temporary, payload)
        filesystem.fsync_file(temporary)
        filesystem.replace_file(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _fsync_tree(root: Path, filesystem: FileSystem) -> None:
    directories: list[Path] = []
    for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        directories.append(current_path)
        for dirname in dirnames:
            child = current_path / dirname
            if child.is_symlink():
                raise ArtifactValidationError(f"Generated run contains a symlink directory: {child}")
        for filename in filenames:
            child = current_path / filename
            if child.is_symlink():
                raise ArtifactValidationError(f"Generated run contains a symlink file: {child}")
            filesystem.fsync_file(child)
    for directory in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        filesystem.fsync_directory(directory)


@contextmanager
def _portfolio_lock(path: Path, *, timeout_seconds: float) -> Iterable[IO[str]]:
    _require_posix_lock()
    if timeout_seconds < 0:
        raise PortfolioReleaseError("lock_timeout_seconds must be non-negative")
    if path.is_symlink():
        raise PortfolioReleaseError(f"Symlinks are not allowed for the portfolio release lock: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink():
        raise PortfolioReleaseError(f"Symlinks are not allowed for the portfolio release lock: {path}")
    handle = path.open("a+", encoding="utf-8")
    deadline = time.monotonic() + timeout_seconds
    try:
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as error:
                if time.monotonic() >= deadline:
                    raise PortfolioLockTimeout(f"Portfolio release lock timed out after {timeout_seconds:g}s") from error
                time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
        yield handle
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _require_posix_lock() -> None:
    if fcntl is None or os.name != "posix":
        raise UnsupportedPlatformError(
            "Portfolio bootstrap requires a POSIX flock implementation (macOS, Linux, or Docker)"
        )


def _repository_relative_path(repository_root: Path, value: str | Path, *, label: str) -> str:
    raw = Path(value)
    if raw.is_absolute():
        try:
            relative = raw.resolve().relative_to(repository_root)
        except ValueError as error:
            raise SourceManifestError(f"{label} escapes the repository root: {raw}") from error
        return normalize_logical_path(relative.as_posix(), label=label)
    return normalize_logical_path(PurePosixPath(str(value)).as_posix(), label=label)


def _validated_release_root(
    repository_root: Path,
    *,
    create: bool,
    error_type: type[PortfolioReleaseError],
) -> Path:
    """Reject parent symlinks before the release tree is read or created."""

    resolved_repository = repository_root.resolve()
    reports = resolved_repository / "reports"
    release_root = reports / "portfolio"
    for path, label in ((reports, "reports"), (release_root, "reports/portfolio")):
        if path.is_symlink():
            raise error_type(f"Symlinks are not allowed in the portfolio release parent: {label}")
        if path.exists():
            if not path.is_dir():
                raise error_type(f"Portfolio release parent is not a directory: {label}")
            try:
                path.resolve(strict=True).relative_to(resolved_repository)
            except (OSError, ValueError) as error:
                raise error_type(f"Portfolio release parent escapes the repository: {label}") from error
    if create:
        reports.mkdir(exist_ok=True)
        if reports.is_symlink():  # defensive check across the creation boundary
            raise error_type("Symlinks are not allowed in the portfolio release parent: reports")
        release_root.mkdir(exist_ok=True)
    if not release_root.exists() or not release_root.is_dir() or release_root.is_symlink():
        raise error_type("Portfolio release root is missing, invalid, or a symlink: reports/portfolio")
    try:
        release_root.resolve(strict=True).relative_to(resolved_repository)
    except (OSError, ValueError) as error:
        raise error_type("Portfolio release root escapes the repository") from error
    return release_root


def _ensure_release_directory(release_root: Path, logical_path: str) -> Path:
    if logical_path not in {".staging", "runs"}:
        raise PortfolioReleaseError(f"Unsupported internal release directory: {logical_path}")
    resolved_release_root = release_root.resolve(strict=True)
    directory = release_root / logical_path
    if directory.is_symlink():
        raise PortfolioReleaseError(f"Symlinks are not allowed in release directory: {logical_path}")
    directory.mkdir(exist_ok=True)
    if not directory.is_dir() or directory.is_symlink():
        raise PortfolioReleaseError(f"Invalid release directory: {logical_path}")
    try:
        directory.resolve(strict=True).relative_to(resolved_release_root)
    except (OSError, ValueError) as error:
        raise PortfolioReleaseError(f"Release directory escapes the release root: {logical_path}") from error
    return directory


def _resolve_existing_under(
    root: Path,
    logical_path: str,
    *,
    label: str,
    allow_directory: bool = False,
    allow_internal_symlink: bool = False,
) -> Path:
    normalized = normalize_logical_path(logical_path, label=label)
    resolved_root = root.resolve()
    candidate = resolved_root / normalized
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as error:
        raise ArtifactValidationError(f"Missing {label}: {normalized}") from error
    try:
        resolved.relative_to(resolved_root)
    except ValueError as error:
        raise ArtifactValidationError(f"Symlink or path escape in {label}: {normalized}") from error
    if not allow_internal_symlink and _contains_symlink(resolved_root, candidate):
        raise ArtifactValidationError(f"Symlinks are not allowed in {label}: {normalized}")
    if not allow_directory and not resolved.is_file():
        raise ArtifactValidationError(f"Expected file for {label}: {normalized}")
    return resolved


def _resolve_for_write_under(root: Path, logical_path: str, *, label: str) -> Path:
    normalized = normalize_logical_path(logical_path, label=label)
    resolved_root = root.resolve()
    candidate = resolved_root / normalized
    existing_parent = candidate.parent
    while not existing_parent.exists() and existing_parent != resolved_root:
        existing_parent = existing_parent.parent
    try:
        existing_parent.resolve().relative_to(resolved_root)
    except ValueError as error:
        raise ArtifactValidationError(f"Symlink or path escape in {label}: {normalized}") from error
    return candidate


def _contains_symlink(root: Path, candidate: Path) -> bool:
    current = root
    try:
        parts = candidate.relative_to(root).parts
    except ValueError:
        return True
    for part in parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _git_ignore_status(repository_root: Path, relative_path: str) -> bool | None:
    if not (repository_root / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", "--", relative_path],
            cwd=repository_root,
            check=False,
            capture_output=True,
        )
    except OSError as error:
        raise SourceManifestError(f"Cannot run Git ignore check for {relative_path}: {error}") from error
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    detail = result.stderr.decode("utf-8", errors="replace").strip()
    raise SourceManifestError(
        f"Git ignore check failed for {relative_path} with exit {result.returncode}"
        + (f": {detail}" if detail else "")
    )


def _repository_display_path(repository_root: Path, path: Path) -> str:
    try:
        return path.relative_to(repository_root).as_posix()
    except ValueError:
        return str(path)


def _new_run_id(now: datetime) -> str:
    stamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"abay-{stamp}-{uuid4().hex[:10]}"


def _iso_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _notify_failure_hook(hook: FailureHook | None, point: str) -> None:
    if hook is not None:
        hook(point)


def _looks_like_url(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith(("http://", "https://", "urn:", "mailto:"))
