from __future__ import annotations

import os


def app_config() -> dict[str, object]:
    return {
        "mapProvider": os.getenv("TRAFFIC_SIM_MAP_PROVIDER", "leaflet"),
        "has2GisKey": bool(os.getenv("2GIS_API_KEY")),
        "twoGisApiKey": os.getenv("2GIS_API_KEY", ""),
        "hasYandexKey": bool(os.getenv("YANDEX_MAPS_API_KEY")),
        "trafficDataProvider": os.getenv("TRAFFIC_DATA_PROVIDER", "synthetic"),
        "defaultTime": os.getenv("TRAFFIC_SIM_DEFAULT_TIME", "17:00"),
        "policy": os.getenv("TRAFFIC_SIM_POLICY", "heuristic"),
    }
