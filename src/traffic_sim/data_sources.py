from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Mapping

from .run_metadata import CLAIM_LABELS


DEFAULT_PROVIDER_REGISTRY_DIR = Path("reports/data_sources")
DEFAULT_ROADS_GEOJSON = Path("data/almaty_roads.geojson")

SOURCE_ROLES = ("roadsGeojson", "trafficProfileCsv", "scenarioLibrary")
DEFAULT_SOURCE_PATHS: dict[str, Path] = {
    "roadsGeojson": DEFAULT_ROADS_GEOJSON,
    "trafficProfileCsv": Path("data/traffic_profiles/sample_almaty.csv"),
    "scenarioLibrary": Path("data/scenarios/library/municipal_presets.json"),
}
OUTPUT_ROLES = ("registryJson", "roadsStatusJson")


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    id: str
    label: str
    provider: str
    source_type: str
    legal_mode: str
    owner: str
    path: str
    claim_label: str
    available: bool
    last_refresh: str | None
    freshness: str
    feature_count: int | None
    sha256: str | None
    bytes: int | None
    fallback_behavior: str
    limitations: list[str]


def inspect_roads_geojson(
    path: str | Path = DEFAULT_ROADS_GEOJSON,
    *,
    source_ref: str | None = None,
) -> ProviderStatus:
    source = Path(path)
    available = source.exists()
    feature_count = None
    if available:
        payload = json.loads(source.read_text(encoding="utf-8"))
        features = payload.get("features", [])
        feature_count = len(features) if isinstance(features, list) else 0
    return ProviderStatus(
        id="roads-geojson",
        label="Cached/imported Almaty road geometry",
        provider="OpenStreetMap/OSMnx import snapshot",
        source_type="cached public road geometry",
        legal_mode="public OSM-derived snapshot; verify ODbL attribution policy before buyer publication",
        owner="data steward",
        path=_logical_ref(source_ref, role="roadsGeojson") if source_ref is not None else str(source),
        claim_label="real-data" if available else "demo",
        available=available,
        last_refresh=_mtime_iso(source) if available else None,
        freshness="local file modification time; not live",
        feature_count=feature_count,
        sha256=_sha256(source) if available else None,
        bytes=source.stat().st_size if available else None,
        fallback_behavior="If refresh fails, keep using cached road geometry with visible timestamp and hash.",
        limitations=[
            "This is not a live road feed.",
            "OSM completeness and tagging quality must be reviewed before procurement claims.",
            "Traffic speeds, counts, and restrictions are not guaranteed by geometry alone.",
        ],
    )


def provider_registry(
    *,
    source_paths: Mapping[str, str | Path] | None = None,
    source_refs: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Build provider status from either legacy defaults or one closed source map.

    Passing ``source_paths`` opts into staging-safe mode: every source role and
    every logical run-relative reference is required, and no repository-root
    default is consulted.
    """

    physical_paths, logical_refs = _resolve_sources(source_paths, source_refs)
    statuses = [
        inspect_roads_geojson(
            physical_paths["roadsGeojson"],
            source_ref=logical_refs["roadsGeojson"],
        ),
        _local_file_status(
            source_id="traffic-profile-csv",
            label="Sample Almaty traffic profile CSV",
            provider="local CSV",
            path=physical_paths["trafficProfileCsv"],
            source_ref=logical_refs["trafficProfileCsv"],
            claim_label="demo",
            source_type="local sample traffic observations",
            legal_mode="demo/local; replace with approved feed before real-data claims",
            owner="data steward",
            fallback="Use synthetic provider when CSV is absent.",
            limitations=["Small sample profile; not representative of live city traffic."],
        ),
        _local_file_status(
            source_id="scenario-library",
            label="Municipal scenario preset library",
            provider="local curated presets",
            path=physical_paths["scenarioLibrary"],
            source_ref=logical_refs["scenarioLibrary"],
            claim_label="proxy",
            source_type="structured scenario assumptions",
            legal_mode="local planning assumptions",
            owner="transport planner",
            fallback="Use default built-in scenario primitives if library is unavailable.",
            limitations=["Preset effects are proxy assumptions until calibrated with observed data."],
        ),
        _placeholder_status(
            source_id="yandex-display",
            label="Yandex traffic display/API adapter",
            provider="Yandex",
            legal_mode="display layer or approved API only; do not store raw data without terms",
        ),
        _placeholder_status(
            source_id="2gis-display",
            label="2GIS traffic/display adapter",
            provider="2GIS",
            legal_mode="MapGL/display layer or approved API only; do not store raw data without terms",
        ),
        _placeholder_status(
            source_id="sergek-feed",
            label="Sergek/camera municipal feed placeholder",
            provider="municipal/city-provided",
            legal_mode="requires city data agreement and Kazakhstan-controlled storage",
        ),
        _placeholder_status(
            source_id="onay-feed",
            label="Onay/public transport feed placeholder",
            provider="municipal/operator-provided",
            legal_mode="requires operator agreement and retention policy",
        ),
    ]
    payload = {
        "id": "almaty-provider-registry",
        "kind": "data-provider-registry",
        "claimLevel": "demo",
        "createdAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "summary": {
            "providerCount": len(statuses),
            "availableCount": sum(1 for status in statuses if status.available),
            "realDataAvailableCount": sum(1 for status in statuses if status.available and status.claim_label == "real-data"),
            "refreshableSource": "roads-geojson",
        },
        "providers": [asdict(status) for status in statuses],
        "claimRule": "Cached OSM geometry may be labeled real-data snapshot, but never live traffic.",
    }
    return payload


def write_provider_registry(
    out_dir: str | Path = DEFAULT_PROVIDER_REGISTRY_DIR,
    *,
    source_paths: Mapping[str, str | Path] | None = None,
    source_refs: Mapping[str, str] | None = None,
    artifact_refs: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    registry = provider_registry(source_paths=source_paths, source_refs=source_refs)
    physical_outputs = {
        "registryJson": output_dir / "provider_registry.json",
        "roadsStatusJson": output_dir / "roads_geojson_provider_status.json",
    }
    registry["outputs"] = _resolve_artifact_refs(physical_outputs, artifact_refs)
    physical_outputs["registryJson"].write_text(
        json.dumps(registry, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    roads_status = next(provider for provider in registry["providers"] if provider["id"] == "roads-geojson")
    physical_outputs["roadsStatusJson"].write_text(
        json.dumps(roads_status, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    return registry


def _local_file_status(
    *,
    source_id: str,
    label: str,
    provider: str,
    path: str | Path,
    source_ref: str,
    claim_label: str,
    source_type: str,
    legal_mode: str,
    owner: str,
    fallback: str,
    limitations: list[str],
) -> ProviderStatus:
    _claim_label(claim_label)
    source = Path(path)
    available = source.exists()
    return ProviderStatus(
        id=source_id,
        label=label,
        provider=provider,
        source_type=source_type,
        legal_mode=legal_mode,
        owner=owner,
        path=_logical_ref(source_ref, role=source_id),
        claim_label=claim_label,
        available=available,
        last_refresh=_mtime_iso(source) if available else None,
        freshness="local file modification time",
        feature_count=None,
        sha256=_sha256(source) if available else None,
        bytes=source.stat().st_size if available else None,
        fallback_behavior=fallback,
        limitations=limitations,
    )


def _placeholder_status(*, source_id: str, label: str, provider: str, legal_mode: str) -> ProviderStatus:
    return ProviderStatus(
        id=source_id,
        label=label,
        provider=provider,
        source_type="external adapter placeholder",
        legal_mode=legal_mode,
        owner="data steward",
        path="",
        claim_label="demo",
        available=False,
        last_refresh=None,
        freshness="not connected",
        feature_count=None,
        sha256=None,
        bytes=None,
        fallback_behavior="Use local demo/proxy data and make limitations visible.",
        limitations=["Adapter is not connected; do not claim live or real-data access."],
    )


def _resolve_sources(
    source_paths: Mapping[str, str | Path] | None,
    source_refs: Mapping[str, str] | None,
) -> tuple[dict[str, Path], dict[str, str]]:
    if source_paths is None:
        physical = dict(DEFAULT_SOURCE_PATHS)
        if source_refs is None:
            return physical, {role: str(path) for role, path in physical.items()}
    else:
        _require_exact_roles(source_paths, SOURCE_ROLES, map_name="source_paths")
        physical = {role: Path(source_paths[role]) for role in SOURCE_ROLES}
        if source_refs is None:
            raise ValueError("source_refs is required when source_paths is explicit")

    assert source_refs is not None
    _require_exact_roles(source_refs, SOURCE_ROLES, map_name="source_refs")
    logical = {role: _logical_ref(source_refs[role], role=role) for role in SOURCE_ROLES}
    return physical, logical


def _resolve_artifact_refs(
    physical_outputs: Mapping[str, Path],
    artifact_refs: Mapping[str, str] | None,
) -> dict[str, str]:
    if artifact_refs is None:
        return {role: str(path) for role, path in physical_outputs.items()}
    _require_exact_roles(artifact_refs, OUTPUT_ROLES, map_name="artifact_refs")
    return {role: _logical_ref(artifact_refs[role], role=role) for role in OUTPUT_ROLES}


def _require_exact_roles(
    values: Mapping[str, object],
    roles: tuple[str, ...],
    *,
    map_name: str,
) -> None:
    expected = set(roles)
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


def _claim_label(value: str) -> str:
    if value not in CLAIM_LABELS:
        raise ValueError(f"Unsupported claim label: {value}")
    return value


def _mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
