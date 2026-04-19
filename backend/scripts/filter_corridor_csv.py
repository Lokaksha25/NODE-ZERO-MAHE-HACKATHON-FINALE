from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROUTES_PATH = ROOT / "data" / "cache" / "corridor_routes_scored.json"
SOURCE_CSV_PATH = ROOT / "242.csv"
OUTPUT_DIR = ROOT / "data" / "cache" / "corridor_csv"


def route_bounds(routes_path: Path) -> tuple[float, float, float, float, str]:
    payload = json.loads(routes_path.read_text(encoding="utf-8"))
    corridor = str(payload.get("corridor", "corridor"))

    min_lon = float("inf")
    max_lon = float("-inf")
    min_lat = float("inf")
    max_lat = float("-inf")

    for route in payload.get("routes", []):
        for lon, lat in route.get("geometry", []):
            min_lon = min(min_lon, float(lon))
            max_lon = max(max_lon, float(lon))
            min_lat = min(min_lat, float(lat))
            max_lat = max(max_lat, float(lat))

    return min_lon, max_lon, min_lat, max_lat, corridor


def main() -> None:
    min_lon, max_lon, min_lat, max_lat, corridor = route_bounds(ROUTES_PATH)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    filtered_rows: list[list[str]] = []
    by_mnc: Counter[str] = Counter()
    by_radio: Counter[str] = Counter()

    with SOURCE_CSV_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if len(row) < 8:
                continue

            try:
                mcc = int(row[1])
                mnc = row[2]
                lon = float(row[6])
                lat = float(row[7])
            except ValueError:
                continue

            if mcc != 242:
                continue

            if lon < min_lon or lon > max_lon or lat < min_lat or lat > max_lat:
                continue

            filtered_rows.append(row)
            by_mnc[mnc] += 1
            by_radio[row[0]] += 1

    corridor_csv_path = OUTPUT_DIR / f"{corridor}-242.csv"
    with corridor_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(filtered_rows)

    for mnc in sorted(by_mnc):
        mnc_path = OUTPUT_DIR / f"{corridor}-242-{mnc}.csv"
        with mnc_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerows(row for row in filtered_rows if row[2] == mnc)

    summary = {
        "corridor": corridor,
        "source_csv": str(SOURCE_CSV_PATH.relative_to(ROOT)),
        "route_bounds": {
            "min_lon": min_lon,
            "max_lon": max_lon,
            "min_lat": min_lat,
            "max_lat": max_lat,
        },
        "row_count": len(filtered_rows),
        "by_mnc": dict(sorted(by_mnc.items())),
        "by_radio": dict(sorted(by_radio.items())),
        "outputs": [
            str(corridor_csv_path.relative_to(ROOT)),
            *[
                str((OUTPUT_DIR / f"{corridor}-242-{mnc}.csv").relative_to(ROOT))
                for mnc in sorted(by_mnc)
            ],
        ],
    }

    summary_path = OUTPUT_DIR / f"{corridor}-242-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
