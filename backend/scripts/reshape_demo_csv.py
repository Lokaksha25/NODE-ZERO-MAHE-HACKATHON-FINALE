"""
BALANCED reshape: Create a clear but not overwhelming dead zone on Route A.

Goal: Route A (24 min) = fastest but has a ~2-3 km weak zone mid-route.
      Route B (25 min) = slower but consistently strong connectivity.

In "Fastest" mode  → Route A wins (ETA advantage outweighs moderate penalty)
In "Most Connected" → Route B wins (better connectivity score)
In "Safety" mode    → Route B wins (weak penalty amplified)
"""

import random
from pathlib import Path

random.seed(42)

ORIGINAL_CSV = Path(r"C:\Users\prana\NODE-ZERO-MAHE-HACKATHON-FINALE\data\cache\corridor_csv\koramangala-whitefield-404-1.csv")

rows = []
with ORIGINAL_CSV.open("r", encoding="utf-8") as f:
    for line in f:
        parts = line.strip().split(",")
        if len(parts) < 10:
            continue
        rows.append(parts)

print(f"Starting towers: {len(rows)}")

# ═══════════════════════════════════════════════════════════════════════
# Route A path:   lon 77.66-77.74, lat ~12.955 (mid-route)
# Route B path:   lon 77.66-77.74, lat ~12.99  (northern loop)
#
# NARROW dead zone: lon 77.69-77.72, lat 12.94-12.97
#   → Only ~3 km of Route A's path, not the full 8 km
# Approach zone:  lon 77.72-77.73, lat 12.94-12.97 (yellow transition)
# ═══════════════════════════════════════════════════════════════════════

# STEP 1: Narrow dead zone – remove towers only in the core 3km gap
DEAD_LON = (77.69, 77.72)
DEAD_LAT = (77.94 / 6.0, 12.97)  # 12.94 to 12.97 (covers Route A at ~12.955)
# Fix: DEAD_LAT should be (12.94, 12.97)
DEAD_LAT = (12.94, 12.97)

filtered = []
removed = 0
for parts in rows:
    lon, lat = float(parts[6]), float(parts[7])
    mcc, mnc = int(parts[1]), int(parts[2])

    in_dead = DEAD_LON[0] <= lon <= DEAD_LON[1] and DEAD_LAT[0] <= lat <= DEAD_LAT[1]

    if in_dead:
        if mcc == 404 and mnc == 10:  # Jio: remove all
            removed += 1
            continue
        if mcc == 405 and mnc == 86:  # Airtel: keep 25%
            if random.random() > 0.25:
                removed += 1
                continue
        if mcc == 404 and mnc == 20:  # Others: remove all
            removed += 1
            continue
        if mcc == 404 and mnc == 16:
            removed += 1
            continue

    filtered.append(parts)

print(f"After dead zone (narrow): {len(filtered)} (removed {removed})")

# STEP 2: Thin the approach zone (yellow transition, only ~1km band)
thinned = []
thin_count = 0
for parts in filtered:
    lon, lat = float(parts[6]), float(parts[7])
    mcc, mnc = int(parts[1]), int(parts[2])

    in_approach = 77.72 < lon <= 77.73 and 12.94 <= lat <= 12.97
    if in_approach and mcc == 404 and mnc == 10:
        if random.random() > 0.45:
            thin_count += 1
            continue

    thinned.append(parts)

print(f"After approach thinning: {len(thinned)} (thinned {thin_count})")

# STEP 3: Add STRONG towers along Route B's northern path
new_towers = []
base_ts = 1776500000

# Jio (404-10) along Route B northern path (lat 12.99-13.01)
for i, (lon, lat) in enumerate([
    (77.660, 12.995), (77.670, 12.993), (77.680, 12.997),
    (77.690, 12.994), (77.700, 12.996), (77.710, 12.993),
    (77.720, 12.998), (77.730, 12.995), (77.740, 12.992),
    (77.665, 13.002), (77.675, 13.004), (77.685, 13.001),
    (77.695, 13.003), (77.705, 13.005), (77.715, 13.002),
    (77.725, 13.004), (77.735, 13.001),
]):
    cellid = 70000000 + i
    new_towers.append(f"LTE,404,10,52001,{cellid},-1,{lon:.6f},{lat:.6f},1000,95,1,{base_ts},{base_ts+100000},0")

# Airtel (405-86) along Route B northern path
for i, (lon, lat) in enumerate([
    (77.662, 12.996), (77.672, 12.994), (77.682, 12.998),
    (77.692, 12.995), (77.702, 12.997), (77.712, 12.994),
    (77.722, 12.996), (77.732, 12.998), (77.742, 12.993),
    (77.668, 13.003), (77.688, 13.004), (77.708, 13.002),
    (77.728, 13.003),
]):
    cellid = 80000000 + i
    new_towers.append(f"LTE,405,86,10101,{cellid},-1,{lon:.6f},{lat:.6f},1100,90,1,{base_ts},{base_ts+100000},0")

print(f"Added {len(new_towers)} Route B reinforcement towers")

# STEP 4: Weak GSM towers in dead zone (not zero, but very weak)
weak = []
for i, (lon, lat) in enumerate([
    (77.695, 12.955), (77.705, 12.956), (77.715, 12.954),
]):
    cellid = 90000000 + i
    weak.append(f"GSM,404,10,52001,{cellid},-1,{lon:.6f},{lat:.6f},5000,2,1,{base_ts},{base_ts+100000},0")

print(f"Added {len(weak)} weak GSM in dead zone")

# STEP 5: Endpoint reinforcement (shared by both routes)
endpoint = []
for i, (lon, lat) in enumerate([
    (77.625, 12.938), (77.630, 12.942), (77.635, 12.945),
    (77.628, 12.940), (77.633, 12.937),
]):
    cellid = 95000000 + i
    endpoint.append(f"LTE,404,10,52002,{cellid},-1,{lon:.6f},{lat:.6f},900,110,1,{base_ts},{base_ts+100000},0")

for i, (lon, lat) in enumerate([
    (77.752, 12.993), (77.756, 12.996), (77.759, 12.998),
]):
    cellid = 96000000 + i
    endpoint.append(f"LTE,404,10,52003,{cellid},-1,{lon:.6f},{lat:.6f},850,115,1,{base_ts},{base_ts+100000},0")

print(f"Added {len(endpoint)} endpoint towers")

# Write
all_lines = [",".join(p) for p in thinned]
all_lines.extend(new_towers)
all_lines.extend(weak)
all_lines.extend(endpoint)

with ORIGINAL_CSV.open("w", encoding="utf-8", newline="") as f:
    for line in all_lines:
        f.write(line + "\n")

print(f"\nFinal CSV: {len(all_lines)} towers")

# Verify
dead_count = sum(1 for l in all_lines
    if DEAD_LON[0] <= float(l.split(",")[6]) <= DEAD_LON[1]
    and DEAD_LAT[0] <= float(l.split(",")[7]) <= DEAD_LAT[1])
north_count = sum(1 for l in all_lines
    if 77.66 <= float(l.split(",")[6]) <= 77.75
    and 12.98 <= float(l.split(",")[7]) <= 13.01)
route_a_mid = sum(1 for l in all_lines
    if 77.66 <= float(l.split(",")[6]) <= 77.74
    and 12.94 <= float(l.split(",")[7]) <= 12.97)
print(f"Dead zone (77.69-77.72): {dead_count} towers")
print(f"Route A mid (77.66-77.74, south): {route_a_mid} towers")
print(f"Route B north (77.66-77.75): {north_count} towers")
