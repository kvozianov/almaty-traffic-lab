from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import traffic_sim.portfolio_release as release


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXED_CLOCK = lambda: datetime(2026, 8, 12, 1, 2, 3, tzinfo=timezone.utc)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _make_repository(root: Path) -> None:
    schema = root / "schemas" / "portfolio-route-manifest.schema.json"
    schema.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT_ROOT / "schemas" / "portfolio-route-manifest.schema.json", schema)
    source = root / "inputs" / "source.json"
    _write_json(source, {"value": "declared"})
    _write_json(
        root / "portfolio.sources.json",
        {
            "schemaVersion": release.SOURCE_MANIFEST_SCHEMA_VERSION,
            "scenarioId": release.SUPPORTED_SCENARIO_ID,
            "sources": [
                {
                    "role": "input",
                    "path": "inputs/source.json",
                    "kind": "data",
                    "required": True,
                    "sha256": _sha(source),
                },
                {
                    "role": "routeManifestSchema",
                    "path": "schemas/portfolio-route-manifest.schema.json",
                    "kind": "schema",
                    "required": True,
                    "sha256": _sha(schema),
                },
            ],
        },
    )


def _make_canonical_repository(root: Path) -> None:
    manifest = json.loads((PROJECT_ROOT / "portfolio.sources.json").read_text(encoding="utf-8"))
    for record in manifest["sources"]:
        source = PROJECT_ROOT / record["path"]
        if not source.is_file():
            if record["required"]:
                raise AssertionError(f"Missing canonical test source: {record['path']}")
            continue
        destination = root / record["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if record.get("sha256") is not None:
            record["sha256"] = _sha(destination)
    _write_json(root / "portfolio.sources.json", manifest)


def _mutate_declared_json(root: Path, role: str, mutate: object) -> None:
    manifest_path = root / "portfolio.sources.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    record = next(item for item in manifest["sources"] if item["role"] == role)
    path = root / record["path"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)  # type: ignore[operator]
    _write_json(path, payload)
    record["sha256"] = _sha(path)
    _write_json(manifest_path, manifest)


def _route_payload(role: str, run_id: str) -> dict[str, object]:
    payload: dict[str, object] = {"kind": role, "releaseRunId": run_id}
    if role == "dossier":
        payload["trustMetadata"] = {"runId": run_id}
    elif role == "runPassport":
        payload["runId"] = run_id
    elif role == "reproduction":
        payload["releaseRunId"] = run_id
    elif role == "manifest":
        payload["runId"] = run_id
    return payload


def _generator(
    *,
    support_path: str | None = None,
    nested_lie: bool = False,
    symlink_role: str | None = None,
    shape_regression: bool = False,
):
    def generate(context: release.GenerationContext) -> None:
        context.materialize_sources()
        context.write_text(
            release.DEFAULT_DOWNLOAD_SPECS["dossier-html"]["logicalPath"],
            "<!doctype html><title>Test dossier</title>\n",
        )
        context.write_text(
            release.DEFAULT_DOWNLOAD_SPECS["kpis-csv"]["logicalPath"],
            "kpi,value\ntravel_time,32\n",
        )
        if support_path is not None:
            context.write_json(support_path, {"kind": "support", "releaseRunId": context.run_id})
        for role in release.REQUIRED_ROUTE_ROLES:
            logical = release.DEFAULT_ALIAS_PATHS[role]
            if role == symlink_role:
                path = context.physical_path(logical, create_parent=True)
                path.symlink_to(context.physical_path("inputs/source.json"))
            else:
                payload = _route_payload(role, context.run_id)
                if role == "dossier" and support_path is not None:
                    payload["outputs"] = {"support": support_path}
                if role == "manifest" and nested_lie:
                    payload["artifacts"] = [
                        {
                            "path": "inputs/source.json",
                            "sha256": "0" * 64,
                            "bytes": context.physical_path("inputs/source.json").stat().st_size,
                        }
                    ]
                if role == "procurementPack" and shape_regression and support_path is not None:
                    payload["outputs"] = [
                        {
                            "kind": "application-summary-html",
                            "path": support_path,
                            "sha256": _sha(context.physical_path(support_path)),
                            "bytes": context.physical_path(support_path).stat().st_size,
                            "available": True,
                            "required": True,
                        }
                    ]
                context.write_json(logical, payload)
            context.register_route_artifact(role, logical, claim_level="demo")

    return generate


@contextmanager
def _closed_support(paths: dict[str, str] | None = None):
    with mock.patch.dict(release.DEFAULT_SUPPORT_ALIAS_PATHS, paths or {}, clear=True):
        yield


class RecordingFileSystem(release.FileSystem):
    def __init__(self) -> None:
        self.files: list[Path] = []
        self.directories: list[Path] = []

    def fsync_file(self, path: Path) -> None:
        self.files.append(path)
        super().fsync_file(path)

    def fsync_directory(self, path: Path) -> None:
        self.directories.append(path)
        super().fsync_directory(path)


class FailFirstAliasCopy(release.FileSystem):
    def __init__(self) -> None:
        self.failed = False

    def copy_file(self, source: Path, target: Path) -> None:
        if not self.failed:
            self.failed = True
            raise OSError("injected alias copy failure")
        super().copy_file(source, target)


class FailAfterFirstCurrentReplace(release.FileSystem):
    def __init__(self) -> None:
        self.failed = False

    def replace_file(self, source: Path, target: Path) -> None:
        super().replace_file(source, target)
        if target.name == "current.json" and not self.failed:
            self.failed = True
            raise OSError("injected after current pointer replacement")


class InterruptAfterFirstCurrentReplace(release.FileSystem):
    def __init__(self) -> None:
        self.failed = False

    def replace_file(self, source: Path, target: Path) -> None:
        super().replace_file(source, target)
        if target.name == "current.json" and not self.failed:
            self.failed = True
            raise KeyboardInterrupt("injected interrupt after current pointer replacement")


class PortfolioReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        _make_repository(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def promote(self, run_id: str, **kwargs: object) -> dict[str, object]:
        return release.promote_portfolio_release(
            _generator(),
            repository_root=self.root,
            run_id=run_id,
            clock=FIXED_CLOCK,
            lock_timeout_seconds=0,
            **kwargs,
        )

    def test_promotes_immutable_run_and_fsyncs_tree_and_parents(self) -> None:
        filesystem = RecordingFileSystem()
        with _closed_support():
            result = self.promote("run-fsync", filesystem=filesystem)
            manifest = release.read_current_manifest(repository_root=self.root)
        self.assertEqual(result["status"], "promoted")
        self.assertEqual(manifest["runId"], "run-fsync")
        self.assertEqual(len(manifest["artifacts"]), 11)
        run_root = self.root / "reports" / "portfolio" / "runs" / "run-fsync"
        self.assertTrue((run_root / "route-manifest.json").is_file())
        resolved_directories = {path.resolve() for path in filesystem.directories}
        staging_root = self.root / "reports" / "portfolio" / ".staging" / "run-fsync"
        self.assertIn(staging_root.resolve(), resolved_directories)
        self.assertIn(run_root.parent.resolve(), resolved_directories)
        self.assertTrue(any(path.name == "route-manifest.json" for path in filesystem.files))

    def test_same_run_id_is_never_overwritten(self) -> None:
        with _closed_support():
            self.promote("immutable-run")
            with self.assertRaises(release.PortfolioReleaseError):
                self.promote("immutable-run")
            self.assertEqual(
                release.read_current_manifest(repository_root=self.root)["runId"],
                "immutable-run",
            )

    def test_every_pre_pointer_failure_rolls_back_visibility_and_new_run(self) -> None:
        points = (
            "after_staging_created",
            "after_generation",
            "after_manifest_validated",
            "after_tree_fsynced",
            "after_run_installed",
        )
        with _closed_support():
            self.promote("stable")
            for index, point in enumerate(points):
                failed_run = f"failed-{index}"

                def fail(current: str, expected: str = point) -> None:
                    if current == expected:
                        raise RuntimeError(f"injected at {expected}")

                with self.assertRaisesRegex(RuntimeError, point):
                    release.promote_portfolio_release(
                        _generator(),
                        repository_root=self.root,
                        run_id=failed_run,
                        clock=FIXED_CLOCK,
                        lock_timeout_seconds=0,
                        failure_hook=fail,
                    )
                self.assertEqual(
                    release.read_current_manifest(repository_root=self.root)["runId"],
                    "stable",
                )
                self.assertFalse(
                    (self.root / "reports" / "portfolio" / "runs" / failed_run).exists()
                )
                self.assertFalse(
                    (self.root / "reports" / "portfolio" / ".staging" / failed_run).exists()
                )

    def test_post_pointer_hook_failure_returns_committed_warning(self) -> None:
        def fail(point: str) -> None:
            if point == "after_pointer_promoted":
                raise RuntimeError("injected after pointer promotion")

        with _closed_support():
            result = self.promote("committed-hook-warning", failure_hook=fail)
            current = release.read_current_manifest(repository_root=self.root)

        self.assertEqual(result["status"], "promoted_with_warning")
        self.assertTrue(result["pointerPromoted"])
        self.assertEqual(current["runId"], "committed-hook-warning")
        self.assertEqual(result["aliases"]["status"], "synced")
        self.assertIn("after pointer promotion", result["warnings"][0])
        self.assertTrue(
            (self.root / "reports" / "portfolio" / "runs" / "committed-hook-warning").is_dir()
        )

    def test_error_after_atomic_pointer_replace_returns_committed_warning(self) -> None:
        with _closed_support():
            result = self.promote(
                "committed-replace-warning",
                filesystem=FailAfterFirstCurrentReplace(),
            )
            current = release.read_current_manifest(repository_root=self.root)

        self.assertEqual(result["status"], "promoted_with_warning")
        self.assertTrue(result["pointerPromoted"])
        self.assertEqual(current["runId"], "committed-replace-warning")
        self.assertEqual(result["aliases"]["status"], "synced")
        self.assertIn("current pointer committed", result["warnings"][0])

    def test_interrupt_after_atomic_pointer_replace_never_deletes_committed_run(self) -> None:
        with _closed_support(), self.assertRaisesRegex(KeyboardInterrupt, "after current pointer"):
            self.promote(
                "committed-interrupt",
                filesystem=InterruptAfterFirstCurrentReplace(),
            )

        current = release.read_current_manifest(repository_root=self.root)
        self.assertEqual(current["runId"], "committed-interrupt")
        self.assertTrue(
            (self.root / "reports" / "portfolio" / "runs" / "committed-interrupt").is_dir()
        )

    def test_lock_contention_times_out_without_generation(self) -> None:
        lock = self.root / "reports" / "portfolio" / ".portfolio-release.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                with _closed_support(), self.assertRaises(release.PortfolioLockTimeout):
                    self.promote("contended")
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        self.assertFalse((self.root / "reports" / "portfolio" / "runs" / "contended").exists())

    def test_alias_failure_is_structured_and_retry_is_idempotent(self) -> None:
        with _closed_support():
            result = self.promote("alias-retry", filesystem=FailFirstAliasCopy())
            self.assertEqual(result["status"], "promoted_with_alias_error")
            self.assertEqual(result["aliases"]["status"], "failed")
            retried = release.retry_alias_sync(repository_root=self.root, lock_timeout_seconds=0)
            self.assertEqual(retried["status"], "promoted")
            verified = release.verify_compatibility_aliases(repository_root=self.root)
            self.assertEqual(verified["aliasCount"], 11)
            second = release.retry_alias_sync(repository_root=self.root, lock_timeout_seconds=0)
            self.assertEqual(second["status"], "promoted")

    def test_closed_support_aliases_resolve_and_hash_match(self) -> None:
        support = {"supportArtifact": "reports/support/payload.json"}
        with _closed_support(support):
            result = release.promote_portfolio_release(
                _generator(support_path=support["supportArtifact"], shape_regression=True),
                repository_root=self.root,
                run_id="support-closure",
                clock=FIXED_CLOCK,
                lock_timeout_seconds=0,
            )
            self.assertEqual(result["status"], "promoted")
            verified = release.verify_compatibility_aliases(repository_root=self.root)
            self.assertEqual(verified["routeAliasCount"], 11)
            self.assertEqual(verified["supportAliasCount"], 1)
            support_alias = self.root / support["supportArtifact"]
            support_alias.write_text("tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(
                release.ArtifactValidationError,
                "hash/bytes mismatch|Nested artifact byte count mismatch",
            ):
                release.verify_compatibility_aliases(repository_root=self.root)

    def test_stale_root_alias_cannot_poison_staged_generation(self) -> None:
        stale = self.root / release.DEFAULT_ALIAS_PATHS["dossier"]
        _write_json(stale, {"trustMetadata": {"runId": "stale-root"}})
        with _closed_support():
            self.promote("fresh-run")
        payload = json.loads(stale.read_text(encoding="utf-8"))
        self.assertEqual(payload["trustMetadata"]["runId"], "fresh-run")

    def test_materialized_source_manifest_tamper_is_rejected(self) -> None:
        with _closed_support():
            self.promote("source-tamper")
            installed = self.root / "reports" / "portfolio" / "runs" / "source-tamper"
            _write_json(installed / "portfolio.sources.json", {"tampered": True})
            with self.assertRaisesRegex(release.ArtifactValidationError, "source manifest hash mismatch"):
                release.read_current_manifest(repository_root=self.root)

    def test_route_artifact_hash_tamper_is_rejected(self) -> None:
        with _closed_support():
            self.promote("route-tamper")
            dossier = (
                self.root
                / "reports"
                / "portfolio"
                / "runs"
                / "route-tamper"
                / release.DEFAULT_ALIAS_PATHS["dossier"]
            )
            dossier.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(release.ArtifactValidationError, "byte count mismatch|hash mismatch"):
                release.read_current_manifest(repository_root=self.root)

    def test_manifest_download_allowlist_is_closed_and_bound_to_the_immutable_run(self) -> None:
        with _closed_support():
            self.promote("download-allowlist")
        manifest = release.read_current_manifest(repository_root=self.root)
        downloads = manifest["downloads"]
        self.assertEqual([item["id"] for item in downloads], list(release.REQUIRED_DOWNLOAD_IDS))
        self.assertEqual(len(manifest["artifacts"]), 11)
        run_root = self.root / "reports" / "portfolio" / "runs" / "download-allowlist"
        for entry in downloads:
            spec = release.DEFAULT_DOWNLOAD_SPECS[entry["id"]]
            path = run_root / entry["logicalPath"]
            self.assertEqual(entry["runId"], "download-allowlist")
            self.assertEqual(entry["logicalPath"], spec["logicalPath"])
            self.assertEqual(entry["mediaType"], spec["mediaType"])
            self.assertEqual(entry["filename"], spec["filename"])
            self.assertEqual(entry["bytes"], path.stat().st_size)
            self.assertEqual(entry["sha256"], _sha(path))

    def test_missing_or_mixed_download_allowlist_is_rejected(self) -> None:
        for label, mutate, message in (
            ("missing", lambda downloads: downloads.pop(), "schema validation failed"),
            (
                "mixed-run",
                lambda downloads: downloads[0].__setitem__("runId", "another-run"),
                "Mixed release run binding for download",
            ),
            (
                "wrong-media",
                lambda downloads: downloads[0].__setitem__("mediaType", "application/json"),
                "schema validation failed",
            ),
        ):
            with self.subTest(label=label), _closed_support():
                self.promote(f"download-{label}")
                current_path = self.root / "reports" / "portfolio" / "current.json"
                current = json.loads(current_path.read_text(encoding="utf-8"))
                mutate(current["downloads"])
                _write_json(current_path, current)
                with self.assertRaisesRegex(release.ArtifactValidationError, message):
                    release.read_current_manifest(repository_root=self.root)

    def test_download_hash_or_bytes_tamper_is_rejected(self) -> None:
        with _closed_support():
            self.promote("download-tamper")
        downloaded_html = (
            self.root
            / "reports"
            / "portfolio"
            / "runs"
            / "download-tamper"
            / release.DEFAULT_DOWNLOAD_SPECS["dossier-html"]["logicalPath"]
        )
        downloaded_html.write_text("tampered\n", encoding="utf-8")
        with self.assertRaisesRegex(
            release.ArtifactValidationError,
            "Download artifact byte count mismatch|Download artifact hash mismatch",
        ):
            release.read_current_manifest(repository_root=self.root)

    def test_nested_manifest_lie_is_rejected_before_promotion(self) -> None:
        with _closed_support(), self.assertRaisesRegex(
            release.ArtifactValidationError,
            "Nested artifact hash mismatch",
        ):
            release.promote_portfolio_release(
                _generator(nested_lie=True),
                repository_root=self.root,
                run_id="nested-lie",
                clock=FIXED_CLOCK,
                lock_timeout_seconds=0,
            )
        self.assertFalse((self.root / "reports" / "portfolio" / "current.json").exists())

    def test_rehashed_nested_mixed_run_binding_is_rejected(self) -> None:
        with _closed_support():
            self.promote("bound-run")
            current_path = self.root / "reports" / "portfolio" / "current.json"
            current = json.loads(current_path.read_text(encoding="utf-8"))
            entry = next(item for item in current["artifacts"] if item["role"] == "dossier")
            dossier = (
                self.root
                / "reports"
                / "portfolio"
                / "runs"
                / "bound-run"
                / entry["logicalPath"]
            )
            payload = json.loads(dossier.read_text(encoding="utf-8"))
            payload["trustMetadata"]["runId"] = "another-run"
            _write_json(dossier, payload)
            entry["sha256"] = _sha(dossier)
            entry["bytes"] = dossier.stat().st_size
            download = next(item for item in current["downloads"] if item["id"] == "dossier-json")
            download["sha256"] = _sha(dossier)
            download["bytes"] = dossier.stat().st_size
            _write_json(current_path, current)
            with self.assertRaisesRegex(release.ArtifactValidationError, "Mixed release run binding"):
                release.read_current_manifest(repository_root=self.root)

    def test_outer_mixed_run_entry_is_rejected(self) -> None:
        with _closed_support():
            self.promote("outer-bound")
            current_path = self.root / "reports" / "portfolio" / "current.json"
            current = json.loads(current_path.read_text(encoding="utf-8"))
            current["artifacts"][0]["runId"] = "another-run"
            _write_json(current_path, current)
            with self.assertRaisesRegex(release.ArtifactValidationError, "Mixed release run binding"):
                release.read_current_manifest(repository_root=self.root)

    def test_generated_symlink_is_rejected(self) -> None:
        with _closed_support(), self.assertRaisesRegex(
            release.ArtifactValidationError,
            "Symlinks are not allowed",
        ):
            release.promote_portfolio_release(
                _generator(symlink_role="dossier"),
                repository_root=self.root,
                run_id="symlink-run",
                clock=FIXED_CLOCK,
                lock_timeout_seconds=0,
            )

    def test_release_parent_and_lock_symlinks_are_rejected_before_io(self) -> None:
        for parent in ("reports", "reports/portfolio"):
            with self.subTest(parent=parent), tempfile.TemporaryDirectory() as tmp_dir:
                root = Path(tmp_dir) / "repo"
                outside = Path(tmp_dir) / "outside"
                root.mkdir()
                outside.mkdir()
                _make_repository(root)
                target = root / parent
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(outside, target_is_directory=True)
                with _closed_support(), self.assertRaisesRegex(
                    release.PortfolioReleaseError,
                    "Symlinks are not allowed",
                ):
                    release.promote_portfolio_release(
                        _generator(),
                        repository_root=root,
                        run_id="parent-symlink",
                        clock=FIXED_CLOCK,
                        lock_timeout_seconds=0,
                    )
                self.assertEqual(list(outside.iterdir()), [])
                with self.assertRaisesRegex(
                    release.ArtifactValidationError,
                    "Symlinks are not allowed",
                ):
                    release.read_current_manifest(repository_root=root)
                with self.assertRaisesRegex(
                    release.ArtifactValidationError,
                    "Symlinks are not allowed",
                ):
                    release.retry_alias_sync(repository_root=root, lock_timeout_seconds=0)

        lock_outside = self.root / "outside.lock"
        lock_outside.write_text("do not touch", encoding="utf-8")
        lock = self.root / "reports" / "portfolio" / ".portfolio-release.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.symlink_to(lock_outside)
        with _closed_support(), self.assertRaisesRegex(
            release.PortfolioReleaseError,
            "Symlinks are not allowed",
        ):
            self.promote("lock-symlink")
        self.assertEqual(lock_outside.read_text(encoding="utf-8"), "do not touch")

    def test_source_resolver_rejects_undeclared_and_traversal(self) -> None:
        resolver = release.SourceManifestResolver(self.root)
        with self.assertRaisesRegex(release.SourceManifestError, "Undeclared"):
            resolver.resolve("not-declared")
        payload = json.loads((self.root / "portfolio.sources.json").read_text(encoding="utf-8"))
        payload["sources"][0]["path"] = "../escape.json"
        _write_json(self.root / "portfolio.sources.json", payload)
        with self.assertRaisesRegex(release.ArtifactValidationError, "Unsafe"):
            release.SourceManifestResolver(self.root)

    def test_git_ignore_proof_is_explicit_when_checkout_is_unavailable_or_broken(self) -> None:
        resolver = release.SourceManifestResolver(self.root)
        verification = resolver.verify()
        self.assertIsNone(verification["nonIgnored"])
        self.assertEqual(verification["gitIgnoreCheck"], "unavailable_not_git_checkout")

        (self.root / ".git").mkdir()
        with mock.patch.object(release.subprocess, "run", side_effect=OSError("git unavailable")):
            with self.assertRaisesRegex(release.SourceManifestError, "Cannot run Git ignore check"):
                resolver.verify()

        failed = mock.Mock(returncode=128, stderr=b"fatal: broken repository")
        with mock.patch.object(release.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(release.SourceManifestError, "exit 128"):
                resolver.verify()

    def test_logical_path_rejects_absolute_traversal_and_staging(self) -> None:
        for value in ("/tmp/file.json", "../file.json", "a/../file.json", "reports/.staging/x.json"):
            with self.subTest(value=value), self.assertRaises(release.ArtifactValidationError):
                release.normalize_logical_path(value)

    def test_non_posix_guard_fails_before_writes(self) -> None:
        with mock.patch.object(release, "fcntl", None), self.assertRaises(release.UnsupportedPlatformError):
            self.promote("unsupported")
        self.assertFalse((self.root / "reports").exists())

    def test_copy_preserves_source_mtime_and_detects_copy_race(self) -> None:
        source = self.root / "inputs" / "source.json"
        original_mtime = source.stat().st_mtime_ns
        resolver = release.SourceManifestResolver(self.root)
        destination = self.root / "materialized"
        resolver.materialize(destination)
        self.assertEqual((destination / "inputs" / "source.json").stat().st_mtime_ns, original_mtime)

        race_root = self.root / "race"
        original_copy2 = shutil.copy2

        def racing_copy(source_path: object, target_path: object, *args: object, **kwargs: object):
            result = original_copy2(source_path, target_path, *args, **kwargs)
            if Path(source_path).resolve() == source.resolve():
                source.write_text('{"value":"changed"}\n', encoding="utf-8")
            return result

        resolver = release.SourceManifestResolver(self.root)
        with mock.patch.object(release.shutil, "copy2", side_effect=racing_copy):
            with self.assertRaisesRegex(release.SourceManifestError, "changed while materializing"):
                resolver.materialize(race_root)

    def test_schema_fixtures_use_real_draft_2020_12_validator(self) -> None:
        schema = PROJECT_ROOT / "schemas" / "portfolio-route-manifest.schema.json"
        valid = json.loads(
            (PROJECT_ROOT / "tests" / "fixtures" / "portfolio-route-manifest.valid.json").read_text(
                encoding="utf-8"
            )
        )
        invalid = json.loads(
            (PROJECT_ROOT / "tests" / "fixtures" / "portfolio-route-manifest.invalid.json").read_text(
                encoding="utf-8"
            )
        )
        release.validate_manifest_fixture(valid, schema_path=schema)
        with self.assertRaises(release.ArtifactValidationError):
            release.validate_manifest_fixture(invalid, schema_path=schema)

    def test_canonical_bundle_uses_reproduction_config_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _make_canonical_repository(root)

            def mutate_reproduction(payload: dict[str, object]) -> None:
                payload["seed"] = 11
                scenario = payload["scenario"]
                pair = payload["pairedExperiment"]
                scenario["baseline"]["scenario"]["signal_delay_s"] = 34
                scenario["measure"]["scenario"]["signal_delay_s"] = 30
                pair["baselineDelaySeconds"] = 34
                pair["measureDelaySeconds"] = 30
                pair["affectedSignalsPerTrip"] = 3
                pair["realizationFactor"] = 0.5

            def mutate_dossier(payload: dict[str, object]) -> None:
                payload["baseline"]["scenario"]["signal_delay_s"] = 34
                payload["measure"]["scenario"]["signal_delay_s"] = 30

            _mutate_declared_json(root, "reproductionConfig", mutate_reproduction)
            _mutate_declared_json(root, "dossierScenarioConfig", mutate_dossier)
            result = release.promote_portfolio_release(
                release.generate_abay_portfolio_bundle,
                repository_root=root,
                run_id="configured-pair",
                clock=FIXED_CLOCK,
                lock_timeout_seconds=0,
            )
            self.assertEqual(result["status"], "promoted")
            run_root = root / result["immutableRun"]
            pair = json.loads(
                (run_root / "reports/repro/abay/pair/paired-experiment.json").read_text(
                    encoding="utf-8"
                )
            )
            computed = pair["proxyModel"]["computed"]
            self.assertEqual(pair["experiment"]["seed"], 11)
            self.assertEqual(pair["experiment"]["demandControl"]["seed"], 11)
            self.assertEqual(pair["experiment"]["baselineSignalDelaySeconds"], 34)
            self.assertEqual(pair["experiment"]["measureSignalDelaySeconds"], 30)
            self.assertEqual(computed["affectedSignalsPerTrip"], 3)
            self.assertEqual(computed["realizationFactor"], 0.5)
            self.assertEqual(pair["claimLevel"], "proxy")
            dossier = json.loads(
                (run_root / "reports/dossiers/abay-signal-retiming/dossier.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(dossier["trustMetadata"]["seed"], 11)

    def test_canonical_bundle_injects_seed_from_reproduction_config_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _make_canonical_repository(root)
            _mutate_declared_json(
                root,
                "reproductionConfig",
                lambda payload: payload.__setitem__("seed", 19),
            )
            result = release.promote_portfolio_release(
                release.generate_abay_portfolio_bundle,
                repository_root=root,
                run_id="single-seed-source",
                clock=FIXED_CLOCK,
                lock_timeout_seconds=0,
            )
            run_root = root / result["immutableRun"]
            pair = json.loads(
                (run_root / "reports/repro/abay/pair/paired-experiment.json").read_text(
                    encoding="utf-8"
                )
            )
            dossier = json.loads(
                (run_root / "reports/dossiers/abay-signal-retiming/dossier.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(pair["experiment"]["seed"], 19)
            self.assertEqual(pair["experiment"]["demandControl"]["seed"], 19)
            self.assertEqual(dossier["trustMetadata"]["seed"], 19)

    def test_canonical_bundle_rejects_config_drift_and_unknown_fields(self) -> None:
        mutations = {
            "cross-config drift": (
                "dossierScenarioConfig",
                lambda payload: payload["measure"]["scenario"].__setitem__(
                    "signal_delay_s", 31
                ),
                "Canonical config drift",
            ),
            "unknown reproduction field": (
                "reproductionConfig",
                lambda payload: payload["pairedExperiment"].__setitem__("unregistered", True),
                "Invalid closed reproductionConfig",
            ),
        }
        for label, (role, mutate, message) in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp_dir:
                root = Path(tmp_dir)
                _make_canonical_repository(root)
                _mutate_declared_json(root, role, mutate)
                with self.assertRaisesRegex(release.SourceManifestError, message):
                    release.promote_portfolio_release(
                        release.generate_abay_portfolio_bundle,
                        repository_root=root,
                        run_id="invalid-config",
                        clock=FIXED_CLOCK,
                        lock_timeout_seconds=0,
                    )
                self.assertFalse((root / "reports/portfolio/current.json").exists())

    def test_canonical_bundle_uses_pinned_materialized_pair_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _make_canonical_repository(root)

            def poison_schema(payload: dict[str, object]) -> None:
                payload["properties"]["modelId"]["const"] = "poisoned-model"

            _mutate_declared_json(root, "pairedExperimentSchema", poison_schema)
            with self.assertRaisesRegex(ValueError, "poisoned-model"):
                release.promote_portfolio_release(
                    release.generate_abay_portfolio_bundle,
                    repository_root=root,
                    run_id="poisoned-schema",
                    clock=FIXED_CLOCK,
                    lock_timeout_seconds=0,
                )
            self.assertFalse((root / "reports/portfolio/current.json").exists())


if __name__ == "__main__":
    unittest.main()
