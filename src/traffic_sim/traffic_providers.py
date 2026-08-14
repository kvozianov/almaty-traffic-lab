from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol


@dataclass(slots=True)
class RoadTrafficObservation:
    road_id: str
    time: str
    speed_kph: float
    load: float
    source: str


class TrafficDataProvider(Protocol):
    provider_id: str

    def status(self) -> dict[str, object]:
        ...

    def observations_for_road(self, road_id: str) -> list[RoadTrafficObservation]:
        ...


class SyntheticTrafficProvider:
    provider_id = "synthetic"

    def status(self) -> dict[str, object]:
        return {
            "id": self.provider_id,
            "available": True,
            "mode": "synthetic",
            "claimLevel": "demo",
            "sourceType": "generated fallback observations",
            "legalMode": "local demo generator",
            "freshness": "generated at request time",
            "lastRefresh": None,
            "fallbackBehavior": "Used when no approved provider is configured.",
        }

    def observations_for_road(self, road_id: str) -> list[RoadTrafficObservation]:
        base = 0.75 if "al" in road_id.lower() or "farabi" in road_id.lower() else 0.45
        return [
            RoadTrafficObservation(road_id, "08:00", 28.0, min(1.0, base + 0.1), self.provider_id),
            RoadTrafficObservation(road_id, "13:00", 42.0, max(0.1, base - 0.2), self.provider_id),
            RoadTrafficObservation(road_id, "17:00", 18.0, min(1.0, base + 0.25), self.provider_id),
            RoadTrafficObservation(road_id, "22:00", 55.0, 0.18, self.provider_id),
        ]


class CsvTrafficProvider:
    provider_id = "csv"

    def __init__(self, path: str | Path = "data/traffic_profiles/sample_almaty.csv") -> None:
        self.path = Path(path)

    def status(self) -> dict[str, object]:
        return {
            "id": self.provider_id,
            "available": self.path.exists(),
            "path": str(self.path),
            "claimLevel": "demo",
            "sourceType": "local CSV traffic profile",
            "legalMode": "local/demo file; replace with approved feed before real-data claims",
            "freshness": "local file modification time",
            "lastRefresh": _mtime_iso(self.path) if self.path.exists() else None,
            "fallbackBehavior": "Synthetic provider can be used if CSV is absent.",
        }

    def observations_for_road(self, road_id: str) -> list[RoadTrafficObservation]:
        if not self.path.exists():
            return []
        observations = []
        with self.path.open("r", encoding="utf-8", newline="") as file:
            for row in csv.DictReader(file):
                if row["road_id"] == road_id or row["corridor"].lower() in road_id.lower():
                    observations.append(
                        RoadTrafficObservation(
                            road_id=road_id,
                            time=row["time"],
                            speed_kph=float(row["speed_kph"]),
                            load=float(row["load"]),
                            source=self.provider_id,
                        )
                    )
        return observations


class YandexTrafficProvider:
    provider_id = "yandex"

    def status(self) -> dict[str, object]:
        return {
            "id": self.provider_id,
            "available": bool(os.getenv("YANDEX_MAPS_API_KEY")),
            "mode": "display-layer-or-approved-api-only",
            "claimLevel": "demo",
            "sourceType": "commercial display/API adapter placeholder",
            "legalMode": "Do not store raw Yandex traffic data unless API terms explicitly allow it.",
            "freshness": "not connected",
            "lastRefresh": None,
            "note": "Raw Yandex traffic data must not be stored unless the API terms explicitly allow it.",
        }

    def observations_for_road(self, road_id: str) -> list[RoadTrafficObservation]:
        return []


class TwoGisTrafficProvider:
    provider_id = "2gis"

    def status(self) -> dict[str, object]:
        return {
            "id": self.provider_id,
            "available": bool(os.getenv("2GIS_API_KEY")),
            "mode": "mapgl-visual-layer-or-approved-api-only",
            "claimLevel": "demo",
            "sourceType": "commercial display/API adapter placeholder",
            "legalMode": "Do not store raw 2GIS traffic data unless API terms explicitly allow it.",
            "freshness": "not connected",
            "lastRefresh": None,
        }

    def observations_for_road(self, road_id: str) -> list[RoadTrafficObservation]:
        return []


def build_provider(provider_id: str, path: str | Path | None = None) -> TrafficDataProvider:
    if provider_id == "csv":
        return CsvTrafficProvider(path or "data/traffic_profiles/sample_almaty.csv")
    if provider_id == "yandex":
        return YandexTrafficProvider()
    if provider_id == "2gis":
        return TwoGisTrafficProvider()
    return SyntheticTrafficProvider()


def list_provider_statuses() -> list[dict[str, object]]:
    return [
        SyntheticTrafficProvider().status(),
        CsvTrafficProvider().status(),
        YandexTrafficProvider().status(),
        TwoGisTrafficProvider().status(),
    ]


def _mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat()
