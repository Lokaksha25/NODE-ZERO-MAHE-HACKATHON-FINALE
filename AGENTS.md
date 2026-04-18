# AGENTS.md

## What This Repository Is

Research repository for a hackathon exploring three connected mobility themes:
1. Cellular network-aware routing  
2. Geo-deferred notifications
3. Wrong-way driver detection beyond ramps

This is NOT a codebase with tests or build scripts—it's literature survey + data files.

## Data Files

| File | Description |
|------|------------|
| `413.csv.gz` | GSM cell tower data (MCC=413 = Norway). Fields: network type, country code, operator ID, cell ID, lat, lon, signal, etc. |
| `Literature and Project Survey...md` | Academic survey with references, algorithms, datasets, and prototype design implications for each theme |

## How to Use This Repo

- Read the survey markdown for research context and prototype design ideas
- Decompress `413.csv.gz` with `zcat 413.csv.gz | head -n` to see sample data
- No build/test commands exist—this is analysis/reference material only

## Key References in Survey

- CARP (Connectivity-Aware Route Planner) - crowdsourced signal + OSM routing
- "Snooze!" - user-defined notification deferral
- Optical-flow-based wrong-way detection with lane orientation modeling
- OSM map-matching for GPS traces