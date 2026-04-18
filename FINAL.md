# Implementation Plan

## Recommended Tech Stack

- Frontend: `Next.js` + `TypeScript` + `Tailwind CSS` + `shadcn/ui`
- Map UI: `MapLibre GL JS`
- Backend API: `FastAPI` + `Pydantic`
- Data store: `PostgreSQL` + `PostGIS`
- Geospatial processing: `Python` + `GeoPandas` + `OSMnx` + `NetworkX` + `PyProj`
- Routing engine: `OSRM` for alternate routes
- Demo data pipeline: offline preprocessing scripts in `Python`
- Deployment for hackathon: `Docker Compose`

This stack is suitable because it keeps the prototype fast to build, strong on geospatial work, and easy to demo offline with cached corridor data.

## Build Stages

### Stage 1: Lock the scope and data model

- Fix the demo corridor to Bengaluru to Mysuru.
- Finalize operator mapping for Jio and Airtel.
- Define the core entities: road segment, route, tower, coverage score, notification, playback event.
- Decide the segment size at 100m and keep it consistent everywhere.

Deliverable:
- A written schema and corridor boundary that every teammate can follow.

### Stage 2: Build the data pipeline first

- Import OpenCellID tower data for the corridor.
- Pull or cache OSM road data for the same corridor.
- Normalize tower metadata by operator and radio type.
- Map-match towers and routes to road segments.
- Precompute segment-level coverage estimates and store them in PostGIS.

Deliverable:
- A local dataset that can answer: "How strong is connectivity on this segment for this operator?"

### Stage 3: Implement route scoring

- Generate at least 2 route alternatives between the fixed endpoints.
- Score each route by ETA, distance, and predicted connectivity continuity.
- Add weak-zone detection and longest weak stretch calculation.
- Support two ranking modes: fastest and most connected.
- Add the slider that blends ETA weight and connectivity weight.

Deliverable:
- A route-ranking API that returns deterministic scores and segment heat data.

### Stage 4: Implement notification deferral

- Build a notification queue with priority levels: urgent, semi-urgent, non-urgent.
- Release urgent notifications immediately.
- Release semi-urgent notifications at the next strong segment.
- Hold non-urgent notifications until a long strong segment or destination.
- Attach an explanation string to every release or defer decision.

Deliverable:
- A notification engine that behaves predictably during route playback.

### Stage 5: Build the demo UI

- Create a map view with route alternatives and segment heat coloring.
- Add route summary cards with ETA, distance, and connectivity score.
- Add a notification timeline showing pending, deferred, and delivered items.
- Add a playback control for moving along the selected route.
- Show weak-zone warnings before entering poor coverage.

Deliverable:
- A usable hackathon interface that explains the system in under 30 seconds.

### Stage 6: Make the demo reliable

- Cache all corridor data locally.
- Remove any dependency on live API responses during the presentation.
- Add seeded demo scenarios for Jio and Airtel.
- Validate that route ranking and notification release are deterministic.

Deliverable:
- A stable offline demo that can be replayed with the same results every time.

### Stage 7: Polish and present

- Clean up labels and copy so the system uses honest language like "predicted connectivity continuity".
- Add a short legend explaining what weak coverage means.
- Prepare one default story and one fallback story.

Deliverable:
- Presentation-ready prototype and demo script.

## Build Order

If we start tomorrow, the correct order is:

1. Data model and corridor selection
2. Offline OpenCellID and OSM preprocessing
3. Route scoring API
4. Notification queue logic
5. Map and timeline UI
6. Caching and demo hardening
7. Final polish

## What Not To Do First

- Do not start with the UI before the scoring pipeline exists.
- Do not optimize for nationwide coverage.
- Do not depend on live network measurements.
- Do not add machine learning for notifications in the first version.
- Do not expand to wrong-way detection in the first build.

## MVP Definition

The first working version should do only this:

- take Jio or Airtel as input
- compare at least 2 routes
- show connectivity-aware ranking
- warn about weak stretches
- defer notifications until strong coverage
- run offline from cached corridor data

If this is working, the project is already demo-worthy.
