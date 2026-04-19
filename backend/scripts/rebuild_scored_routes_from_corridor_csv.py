from __future__ import annotations

import csv
import json
import time
from pathlib import Path

from build_corridor_dataset import (
    ROUTES_CACHE_PATH,
    TOWERS_CACHE_PATH,
    Tower,
    build_scored_routes,
    serialize_towers,
)


ROOT = Path(__file__).resolve().parents[2]
CORRIDOR = "oslo-drammen"
SOURCE_ROUTES_PATH = ROOT / "data" / "cache" / "corridor_routes_scored.json"
SOURCE_CSV_PATH = ROOT / "data" / "cache" / "corridor_csv" / f"{CORRIDOR}-242.csv"


def load_route_records() -> tuple[str, list[dict]]:
    payload = json.loads(SOURCE_ROUTES_PATH.read_text(encoding="utf-8"))
    corridor = str(payload.get("corridor", CORRIDOR))
    route_records: list[dict] = []

    for route in payload.get("routes", []):
        geometry = route.get("geometry", [])
        if not geometry:
            continue

        route_records.append(
            {
                "distance": float(route.get("distance_km", 0.0)) * 1000.0,
                "duration": int(route.get("eta_minutes", 0)) * 60.0,
                "geometry": {"coordinates": geometry},
            }
        )

    return corridor, route_records


def load_corridor_towers() -> list[Tower]:
    towers: list[Tower] = []

    with SOURCE_CSV_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if len(row) < 13:
                continue

            try:
                towers.append(
                    Tower(
                        lat=float(row[7]),
                        lon=float(row[6]),
                        mcc=int(row[1]),
                        mnc=int(row[2]),
                        lac=int(row[3]),
                        cellid=int(row[4]),
                        radio=str(row[0]).upper(),
                        range_m=max(200.0, min(float(row[8] or 1000), 5000.0)),
                        samples=int(row[9] or 0),
                    )
                )
            except ValueError:
                continue

    return towers


def main() -> None:
    corridor, route_records = load_route_records()
    towers = load_corridor_towers()

    if not route_records:
        raise RuntimeError("No route records available to rebuild scored cache")
    if len(towers) < 50:
        raise RuntimeError("Too few towers in corridor CSV to rebuild scored cache")

    scored_routes = build_scored_routes(route_records, towers)
    now = int(time.time())

    ROUTES_CACHE_PATH.write_text(
        json.dumps(
            {
                "source": "osrm+opencellid-corridor-csv",
                "corridor": corridor,
                "generated_at": now,
                "route_count": len(scored_routes),
                "tower_count": len(towers),
                "routes": scored_routes,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    TOWERS_CACHE_PATH.write_text(
        json.dumps(
            {
                "source": "opencellid-corridor-csv",
                "corridor": corridor,
                "generated_at": now,
                "tower_count": len(towers),
                "towers": serialize_towers(towers),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {ROUTES_CACHE_PATH}")
    print(f"Wrote {TOWERS_CACHE_PATH}")
    print(
        f"Corridor: {corridor} | Routes: {len(scored_routes)} | Towers: {len(towers)}"
    )


if __name__ == "__main__":
    main()
