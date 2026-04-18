# Node Zero - Connectivity-Aware Routing Demo

Offline hackathon prototype for:
- operator-specific connectivity-aware routing (`Jio`, `Airtel`)
- weak-zone warning before low predicted coverage
- geo-deferred notification delivery during route playback
- safety mode that biases toward connectivity continuity

## Are We Using OpenStreetMap?

Yes.
- The frontend map uses **OpenStreetMap tiles** via React Leaflet (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`).
- Route geometry is now fetched from **OSRM** (road network based on OSM data), then cached for deterministic replay.
- This means route polylines follow roads rather than straight interpolation lines.

## Tech Stack

- Frontend: Next.js, TypeScript, Tailwind CSS, React Leaflet, Turf
- Backend: FastAPI, Pydantic
- Demo data: deterministic corridor route templates + sample normalized tower file
- Deployment: Docker Compose

## Project Structure

- `frontend/` - UI, map, controls, playback timeline
- `backend/` - route ranking API + notification simulation API
- `data/demo/` - sample normalized corridor tower file
- `docker-compose.yml` - one-command startup for frontend + backend

## Prerequisites

For Docker flow (recommended):
- Docker
- Docker Compose

For local non-Docker flow:
- Node.js 20+ (or compatible with Next.js 15)
- npm
- Python 3.12+ recommended

## Quick Start (Recommended)

1. Build real corridor cache (OSRM routes + OpenCellID towers):

```bash
python backend/scripts/build_corridor_dataset.py
```

This writes:
- `data/cache/corridor_routes_scored.json`
- `data/cache/opencellid_towers.json`

The backend container mounts `./data` into `/app/data` as read-only, so cached files are automatically visible to the API.

2. Build and run everything:

```bash
docker compose up --build
```

3. Open apps:
- Frontend: `http://localhost:3001` (default compose mapping)
- Backend docs: `http://localhost:8000/docs`

If port `3001` is also busy, choose another host port:

```bash
FRONTEND_PORT=3010 docker compose up --build
```

4. Demo flow:
- Choose operator (`Jio` or `Airtel`)
- Choose mode (`Fastest` or `Most Connected`)
- Move ETA vs Connectivity slider
- Toggle Safety Mode
- Click `Play: Continue` or `Play: Switch Route`

## Local Development (Without Docker)

### 1) Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2) Frontend

In a new terminal:

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE=http://localhost:8000/api npm run dev
```

Then open `http://localhost:3000`.

## API Endpoints

Base URL: `http://localhost:8000/api`

### Health
- `GET /health`

### Data Source Status
- `GET /data-source`
- Returns whether backend is using cached OSRM+OpenCellID data or fallback synthetic templates.
- If this shows `fallback`, ensure cache files exist in `data/cache/` and restart Compose so the mount is active.

### Rank Routes
- `POST /routes`

Request body:

```json
{
  "operator": "jio",
  "mode": "fastest",
  "eta_connectivity_blend": 0.5,
  "safety_mode": false
}
```

### Simulate Playback
- `POST /playback`

Request body:

```json
{
  "operator": "jio",
  "route_id": "fast_corridor",
  "mode": "fastest",
  "eta_connectivity_blend": 0.5,
  "safety_mode": false,
  "decision_at_warning": "continue"
}
```

`decision_at_warning` accepts:
- `continue`
- `switch`

## Determinism and Demo Reliability

- Route alternatives and per-segment scores are loaded from cached dataset when available (`data/cache/corridor_routes_scored.json`).
- If cache is missing, backend falls back to synthetic demo templates.
- Connectivity warning/release behavior remains deterministic and rule-based.

## Current Limitations

- No live network measurements from user devices.
- No real-time operator congestion/load prediction.
- OpenCellID API coverage can vary by tile and account quotas.
- Operator mapping is config-driven and currently seeded for Jio/Airtel target MNC sets.

## Useful Files

- `backend/app/api/routes.py`
- `backend/app/core/scoring.py`
- `backend/app/core/notification_engine.py`
- `backend/app/data/demo_routes.py`
- `backend/scripts/build_corridor_dataset.py`
- `frontend/src/app/page.tsx`
- `frontend/src/components/map-view.tsx`
- `data/cache/corridor_routes_scored.json`
- `data/cache/opencellid_towers.json`

## Notes

- If local Python package install fails due to system Python restrictions, use Docker (recommended).
- Frontend dependencies may show advisory warnings from upstream packages; demo flow remains functional.
