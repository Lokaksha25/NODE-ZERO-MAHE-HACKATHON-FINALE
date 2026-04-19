# 🛰️ Reachbl — Connectivity-Aware Routing & Geo-Deferred Notifications

<div align="center">

**Operator-Specific Connectivity-Aware Routing and Geo-Deferred Notifications for Indian Road Corridors**

*Built for the MAHE Hackathon Finale*

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://docker.com)

</div>

---

## 📋 What Is Reachbl?

Reachbl is a prototype system that makes mobile routing **connectivity-aware**. Instead of just finding the fastest path between two cities, it evaluates **cellular network coverage** along every candidate route — per operator (Jio, Airtel) — and uses that data to:

1. **Rank routes** by a blend of ETA and predicted connectivity quality
2. **Identify weak coverage stretches** (dead zones) before the driver reaches them
3. **Intelligently defer notifications** so drivers aren't bombarded with messages in areas with poor signal
4. **Recommend safer routes** that avoid prolonged dead zones when safety mode is enabled

---

## 🧩 The Problem

When a vehicle enters a weak-coverage zone:

- **Queued notifications flood** the phone the moment signal returns — OTPs expire, messages arrive out of order, maps freeze mid-navigation
- **Navigation apps don't factor connectivity** — they optimize purely for ETA or distance
- **Drivers get distracted** by a sudden burst of 15+ notifications at once after exiting a tunnel or dead zone
- **Safety-critical alerts** (SOS, emergency calls) compete with spam for the same weak signal

There's no system today that **predicts** where connectivity will be weak and **proactively adapts** both the route and the notification behavior.

---

## 💡 How It Works

### Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Frontend (Next.js)                 │
│  ┌─────────┐  ┌───────────┐  ┌────────────────────┐ │
│  │ Map View│  │  Controls │  │ Notification       │ │
│  │ Leaflet │  │  Panel    │  │ Timeline           │ │
│  └─────────┘  └───────────┘  └────────────────────┘ │
└──────────────────────┬───────────────────────────────┘
                       │ REST API
┌──────────────────────▼───────────────────────────────┐
│                  Backend (FastAPI)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ Corridor     │  │ Scoring &    │  │ Notification│ │
│  │ Builder      │  │ Ranking      │  │ Engine      │ │
│  │ (OSRM +      │  │ Engine       │  │ (Zone-Aware)│ │
│  │  OpenCellID) │  │              │  │             │ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
└──────────────────────────────────────────────────────┘
```

### Pipeline

1. **Corridor Building** — User enters origin & destination. The system queries [OSRM](http://router.project-osrm.org) for real road routes and [OpenCellID](https://opencellid.org) for cell tower data along each route.

2. **Segment Scoring** — Each route is divided into 100m segments. Every segment gets a connectivity score (0–100) based on:
   - Number of nearby towers within range
   - Tower radio technology (LTE > UMTS > GSM)
   - Number of signal samples
   - Tower range (smaller range = denser, better coverage)

3. **Route Ranking** — Routes are ranked by a weighted formula:
   ```
   combined = (eta_weight × eta_score) + (connectivity_weight × connectivity_score) - weak_penalty
   ```
   The user controls the ETA vs Connectivity blend via a slider. Safety mode amplifies the weak-zone penalty.

4. **Playback Simulation** — The driver's journey is simulated segment-by-segment. At each segment, the system classifies the zone:

   | Zone | Score | Behavior |
   |------|-------|----------|
   | 🟢 Green (Strong) | ≥ 65 | All notifications visible; staggered release |
   | 🟡 Yellow (Moderate) | 45–65 | Only urgent + semi-urgent visible |
   | 🔴 Red (Weak) | < 45 | Only urgent notifications visible |

5. **Controlled Release** — When the driver re-enters a green zone, deferred notifications don't dump all at once. They release in a staggered, priority-ordered cascade to avoid overwhelming the driver.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **Operator-Specific Scoring** | Toggle between Jio, Airtel, or All Networks — each operator has different tower coverage |
| **Ranking Mode** | "Fastest" (ETA-optimized) or "Most Connected" (coverage-optimized) presets |
| **ETA vs Connectivity Slider** | Fine-tune the routing tradeoff on a continuous scale |
| **Safety Mode** | Amplifies weak-zone penalties, makes notification release ultra-conservative |
| **Zone-Aware Notifications** | Real-time filtering — red zones hide non-urgent, yellow hides low-priority |
| **Staggered Release** | Deferred notifications release one-by-one in green zones, not all at once |
| **Weak-Zone Warnings** | Lookahead alerts warn the driver before entering a dead zone |
| **Mid-Route Auto-Switch** | Automatically re-routes to a better-connected alternative when a dead zone is detected |
| **Navigation Arrow** | Google Maps-style directional arrow that rotates based on heading |
| **Color-Coded Segments** | Map polylines are green/yellow/red per segment score |
| **Interactive Globe Landing** | 3D rotating globe (cobe) with Indian corridor markers and dark/light mode |
| **Dark / Light Mode** | Full theme toggle across both the landing page and dashboard |

---

## 🚀 Getting Started

### Prerequisites

- **Python** 3.12+
- **Node.js** 18+
- **Docker** (optional, for containerized setup)

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/Lokaksha25/NODE-ZERO-MAHE-HACKATHON-FINALE.git
cd NODE-ZERO-MAHE-HACKATHON-FINALE

# Create .env file in the project root
echo "OPENCELLID_API_KEY=your_api_key_here" > .env

# Build and start both services
docker compose up --build
```

| Service  | URL |
|----------|-----|
| Landing Page | http://localhost:3000 |
| Dashboard | http://localhost:3000/dashboard |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

To stop:
```bash
docker compose down
```

### Option 2: Local Development (Without Docker)

#### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "OPENCELLID_API_KEY=your_api_key_here" > .env

# Start the server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

| Service  | URL |
|----------|-----|
| Landing Page | http://localhost:3000 |
| Dashboard | http://localhost:3000/dashboard |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

---

## 📁 Project Structure

```
NODE-ZERO-MAHE-HACKATHON-FINALE/
├── backend/
│   ├── app/
│   │   ├── api/routes.py            # REST endpoints (routes, playback, corridor jobs)
│   │   ├── core/
│   │   │   ├── config.py            # Scoring thresholds, mode weights
│   │   │   ├── models.py            # Pydantic models for all API types
│   │   │   ├── notification_engine.py  # Zone-aware notification state machine
│   │   │   └── scoring.py           # Route ranking & segment scoring
│   │   ├── data/
│   │   │   └── demo_routes.py       # Route template loader from cached corridors
│   │   └── services/
│   │       └── corridor_jobs.py     # OSRM + OpenCellID corridor builder
│   ├── data/cache/                  # Cached corridor data & job results
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx             # Landing page with interactive globe
│   │   │   └── dashboard/page.tsx   # Main routing dashboard & playback loop
│   │   ├── components/
│   │   │   ├── control-panel.tsx    # Demo controls (operator, mode, slider, safety)
│   │   │   ├── globe.tsx            # Interactive 3D globe (cobe)
│   │   │   ├── map-view.tsx         # Leaflet map with colored segments & nav arrow
│   │   │   └── timeline.tsx         # Notification timeline with zone indicator
│   │   ├── lib/api.ts               # API client functions
│   │   └── types/api.ts             # TypeScript type definitions
│   └── Dockerfile
├── data/cache/corridor_csv/         # Pre-cached OpenCellID tower CSVs
├── docker-compose.yml
├── SPEC.md                          # Full technical specification
└── README.md                        # ← You are here
```

---

## 🎮 Demo Flow

1. **Landing page**: Visit http://localhost:3000 — see the interactive globe and click **Get Started**
2. **Enter corridor**: Type origin (e.g., "Koramangala") and destination (e.g., "Whitefield")
3. **Build Corridor**: Click to fetch routes and tower data
4. **Compare routes**: Route A (faster, has weak zone) vs Route B (slower, better coverage)
5. **Toggle modes**: Switch between Fastest ↔ Most Connected to see BEST badge move
6. **Adjust slider**: Drag ETA vs Connectivity to fine-tune the tradeoff
7. **Start playback**: Click Analyze to simulate driving the selected route
8. **Watch notifications**: Observe zone-aware filtering (green → yellow → red → green)
9. **Enable Safety Mode**: Re-run playback to see conservative notification behavior

---

## 🔧 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENCELLID_API_KEY` | Yes | — | API key from [OpenCellID](https://opencellid.org) |
| `COVERAGE_MAP` | No | `""` | Optional static coverage map path |
| `COVERAGE_PROVIDER` | No | `auto` | Coverage data source |
| `FRONTEND_PORT` | No | `3000` | Frontend port in Docker mode |

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/corridor-jobs` | Create a new corridor analysis job |
| `GET` | `/api/corridor-jobs/{id}` | Poll job status |
| `GET` | `/api/data-source` | Get data source metadata |
| `POST` | `/api/routes` | Get ranked routes for a corridor |
| `POST` | `/api/playback` | Simulate driving with notifications |

Full interactive docs available at `/docs` (Swagger UI) when the backend is running.

---

## 🛡️ Honest Framing

This system uses **estimated coverage** from cell tower infrastructure data, not live signal measurements. We use the following language intentionally:

- ✅ "carrier-specific coverage estimation"
- ✅ "predicted connectivity continuity"
- ✅ "estimated high-coverage segments"
- ❌ ~~"live signal map"~~
- ❌ ~~"real-time network quality"~~
- ❌ ~~"guaranteed network availability"~~

---

## 👥 Team

**Reachbl (Node Zero)** — Built for the MAHE Hackathon Finale 2026

---

## 📄 License

This project was built as a hackathon prototype. All rights reserved.
