# SPEC.md

## Title

Operator-Specific Connectivity-Aware Routing and Geo-Deferred Notifications for Indian Road Corridors

## Goal

Build a hackathon prototype that combines:

1. Cellular network-aware routing
2. Geo-deferred notifications

The prototype should estimate operator-specific connectivity along candidate routes and use that estimate to:

- rank routes by connectivity vs ETA tradeoff
- identify weak coverage stretches
- defer non-urgent notifications until the vehicle reaches predicted strong-coverage segments
- optionally activate a safety-prioritized route mode

## Scope

### In Scope

- Operator-specific route comparison for `Jio` and `Airtel`
- Corridor-focused demo, not full India coverage
- Coverage estimation from OpenCellID infrastructure data
- Connectivity score per route and per route segment
- Notification queue with delivery deferral based on predicted connectivity
- Safety mode toggle that reweights routing and notification behavior
- Interactive map UI for route playback and notification release behavior

### Out of Scope

- Live signal measurement
- Real-time operator congestion/load prediction
- Guaranteed SOS availability claims
- Full nationwide data ingestion
- Personalized ML notification scheduling
- Wrong-way driver detection

## Demo Story

Primary story:

A user selects a route on a corridor such as Bengaluru to Mysuru and chooses a carrier profile such as Jio or Airtel. The system evaluates alternate routes, estimates which one has stronger connectivity continuity, highlights weak stretches, and defers non-urgent notifications until stronger coverage segments. In safety mode, the routing engine prioritizes connectivity continuity more strongly than ETA.

## Honest Framing

The system does not use live measured signal quality from the user’s phone. It uses operator-specific cell infrastructure and tower metadata from OpenCellID to estimate connectivity continuity.

Recommended language for demo and documentation:

- "carrier-specific coverage estimation"
- "predicted connectivity continuity"
- "estimated high-coverage segments"
- "safety-prioritized route recommendation"

Avoid saying:

- "live signal map"
- "real-time network quality"
- "guaranteed network availability"
- "forces the cab to follow a route"

## Data Sources

### Primary

#### OpenCellID
Use OpenCellID API area queries and optionally country downloads if available.

Relevant fields:

- `radio`
- `mcc`
- `net` (MNC)
- `area` (LAC/TAC)
- `cell`
- `lon`
- `lat`
- `range`
- `samples`
- `changeable`
- `created`
- `updated`
- `averageSignal`

Important notes:

- `averageSignal` may be sparse or zero in many exports
- `range`, `samples`, `radio`, and spatial density are more reliable for this prototype
- large area queries are restricted, so corridor tiling is required

### Secondary / Reference Only

#### nPerf
Use only as presentation/reference material unless commercial access is secured.

Potential use:
- screenshot-based validation
- external benchmark reference in deck

Do not build the implementation around nPerf unless paid access is obtained immediately.

### Map / Routing

- OpenStreetMap for roads and context
- OSRM or GraphHopper or Google Directions for alternate route generation

Recommended:
- OSRM for free routing
- OSM basemap / route rendering
- precomputed route alternatives for demo reliability

## Target Geography

### Phase 1 Corridor

Primary demo corridor:
- Bengaluru to Mysuru

Fixed demo endpoints:
- Origin: `Koramangala, Bengaluru`
- Destination: `Mysuru Palace, Mysuru`

### Phase 2 Optional Corridor

Choose one additional corridor only if Phase 1 is stable:
- Bengaluru to Airport
- Bengaluru to Electronic City side
- Bengaluru to Tumakuru highway

## Operator Support

### Required

- Jio
- Airtel

### Initial Mapping

Start with explicit mapping in code and refine after sampling OpenCellID data.

Suggested starting set:
- Jio: `405-86`, `405-87`
- Airtel: `404-10`, `404-49`

Implementation rule:
- treat operator mapping as configuration
- verify actual MNC presence in fetched corridor tiles before final demo

## Functional Requirements

### FR1. Operator Selection

The user can choose:
- Jio
- Airtel

The selected operator filters the cell dataset used for scoring.

### FR2. Route Alternatives

The system returns at least 2 route alternatives for a given origin and destination.

Each route must expose:
- ETA
- distance
- overall connectivity score
- weak coverage stretches
- longest weak stretch

### FR3. Segment Connectivity Scoring

Each route is split into fixed-length segments, recommended:
- 100m segments

Each segment gets an estimated connectivity score based on nearby towers for the selected operator.

### FR4. Route Ranking

The system computes route ranking under two modes:
- fastest
- most connected

A slider interpolates between ETA weighting and connectivity weighting.

### FR4A. Weak-Zone Warning And User Decision

Before the playback enters a predicted weak segment, the system should proactively warn the user that a weak zone is ahead.

The warning must show:
- estimated distance to weak zone
- estimated weak-zone length
- current route mode (`fastest` or `most connected`)
- a prompt asking whether to continue on the current route or switch to a better-connected alternative

The user decision options must be:
- continue on current route
- switch to a better-connected route

If the user chooses the better-connected alternative, the system should update the selected route and restart or continue playback on the new route in a deterministic way suitable for demo mode.

### FR5. Coverage Visualization

The UI shows:
- route alternatives
- per-segment heat coloring
- weak coverage zones
- selected route summary

### FR6. Geo-Deferred Notification Queue

Notifications are stored with a priority tag:
- urgent
- semi-urgent
- non-urgent

Delivery policy:
- urgent: always deliver immediately
- semi-urgent: deliver at next strong segment
- non-urgent: defer until long strong segment or destination

### FR7. Notification Explanation

Each deferred/released notification should include a visible reason:
- deferred due to weak connectivity ahead
- released on entering strong coverage zone
- released at destination
- bypassed because urgent

### FR8. Safety Mode

A toggle activates safety mode.

Effects:
- raises connectivity weight in routing
- penalizes long weak stretches more strongly
- suppresses non-urgent notifications more aggressively
- shows `Safety Mode Active` in UI

## Non-Functional Requirements

- Demo must work without depending on live external responses during presentation
- Corridor data should be prefetched and cached locally before demo
- UI must be understandable in under 30 seconds
- Route scoring should be repeatable and deterministic
- Data pipeline should be documented clearly enough for parallel teammate work

## Architecture

### High-Level Components

1. Data Ingestion
2. Spatial Index / Coverage Engine
3. Routing Engine
4. Scoring Engine
5. Notification Engine
6. Frontend Visualization

### Suggested Stack

#### Backend
- Python
- FastAPI

#### Spatial / Data Processing
- pandas
- scipy.spatial.KDTree or BallTree
- shapely
- geopandas optional

#### Frontend
- React
- Leaflet

#### Routing
- OSRM preferred
- optional Google Directions if already available

## Data Pipeline

### Step 1. Corridor Definition

Define one or more corridor polygons or buffered route areas.

Recommended:
- get one or two route skeletons between Bengaluru and Mysuru
- buffer them
- tile the buffered area into query-safe OpenCellID bounding boxes

### Step 2. OpenCellID Fetching

Use:
- `cell/getInAreaSize`
- `cell/getInArea`

Rules:
- query only small tiles due to area limits
- fetch both `mcc=404` and `mcc=405`
- store raw CSV/JSON per tile
- deduplicate by tower identity

### Step 3. Normalization

Normalize fields into one internal schema:

- `radio`
- `mcc`
- `mnc`
- `area_code`
- `cell_id`
- `lon`
- `lat`
- `range_m`
- `samples`
- `updated_ts`

### Step 4. Operator Filtering

Map each normalized row to:
- Jio
- Airtel
- other / ignore

### Step 5. Quality Filtering

Suggested filtering:
- require valid lat/lon
- drop obviously stale/invalid rows if needed
- optionally prefer `samples >= 2` or `samples >= 5`
- keep LTE/UMTS/GSM all, but weight them differently

## Coverage Estimation Model

### Core Principle

Estimate segment connectivity from nearby tower presence, operator match, radio type, distance, and confidence metadata.

### Segment Definition

- split each route polyline into ~100m segments
- compute midpoint per segment

### Nearby Towers

For each segment midpoint, query towers within radius:
- recommended starting radius: `500m`
- test `750m` and `1000m` as sensitivity variants

### Per-Tower Contribution

Suggested formula:

`contribution = radio_weight * confidence_weight * freshness_weight * distance_decay`

Where:

- `radio_weight`
  - LTE = 1.0
  - UMTS = 0.6
  - GSM = 0.35

- `confidence_weight`
  - derived from samples
  - e.g. `min(1.0, log1p(samples) / log(10))`

- `freshness_weight`
  - lighter penalty for older towers
  - e.g. 1.0 if recent, 0.7 if older than threshold

- `distance_decay`
  - use inverse-distance or soft decay
  - recommended:
    `exp(-distance / effective_range)`
  - where `effective_range` is based on the OpenCellID `range` field with reasonable clamping

### Segment Score

Aggregate nearby tower contributions and normalize to 0-100.

Also compute boolean weak/strong classification:
- weak if score < threshold
- strong if score >= threshold

Recommended initial threshold:
- tune empirically on corridor tiles

### Route Score

Compute:
- average segment score
- minimum segment score
- percentage of weak segments
- longest weak stretch in meters
- number of transitions into/out of weak zones

Recommended route-level combined score:
- prioritize longest weak stretch and weak-segment ratio, not just average

## Routing Strategy

### Inputs

- origin
- destination
- selected operator
- slider value or mode
- optional safety mode

### Candidate Routes

Get 2-3 alternatives from routing engine.

### Re-Ranking

For each route:
- compute ETA score
- compute connectivity score
- compute weak-zone penalty

Combined score example:
`combined = eta_weight * normalized_eta_score + connectivity_weight * normalized_connectivity_score - weak_zone_penalty`

Safety mode:
- increase connectivity weight
- increase penalty for longest weak stretch

## Notification Engine

### Notification Schema

Each notification should include:
- id
- timestamp
- priority
- title
- body
- current status
- release reason

### Priorities

- urgent
- semi-urgent
- non-urgent

### State Machine

Possible states:
- queued
- deferred
- released
- delivered
- expired

### Delivery Rules

#### Urgent
- deliver immediately

#### Semi-Urgent
- deliver at next strong segment
- optional timeout fallback

#### Non-Urgent
- defer until:
  - long strong stretch
  - route end
  - user reaches destination

### Playback

Demo should simulate movement along route:
- vehicle marker progresses along polyline
- coverage state updates
- weak-zone-ahead warning appears before entering a predicted weak segment
- user can choose to continue or switch to a better-connected alternative
- queued notifications release when conditions are met

## UI Requirements

### Main Map

Show:
- alternate routes
- per-segment coloring
- current playback marker
- weak coverage zones

### Side Panel

Show:
- selected operator
- route metrics
- ETA vs connectivity slider
- safety mode toggle
- weak-zone-ahead warning card when applicable
- current user decision on route continuation vs reroute
- notification queue and release log

### Visual Language

Needed indicators:
- weak coverage = red
- moderate = yellow
- strong = green
- queued notifications visually separated from delivered
- warning state should be visually distinct from queued notifications

## Demo Mode

### Required

Demo must support preloaded data and deterministic playback.

### Recommended Demo Sequence

1. Select operator: Jio
2. Show route alternatives
3. Show fastest vs most connected difference
4. Start playback
5. Show a weak-zone-ahead warning before entering the predicted weak segment
6. Let the user decide whether to continue on the fastest route through the weak zone or switch to a better-connected alternative
7. Enter weak zone if the user continues on the current route
8. Notifications are held while inside the weak zone
9. Enter strong zone
10. Deferred notifications flush
11. Toggle safety mode
12. Route recommendation updates

## Validation Plan

### Internal Validation

- confirm OpenCellID tiles return both 404 and 405 data on selected corridor
- confirm Jio and Airtel both have sufficient tower presence in demo zone
- verify route scores differ meaningfully between alternatives
- verify notification behavior matches route segment states

### External Validation

Use nPerf only as a supporting reference:
- compare rough carrier weak/strong areas visually if possible
- mention this as sanity check, not ground truth integration

## Deliverables

### Required Deliverables

- backend API for route scoring
- normalized corridor cell dataset
- frontend demo UI
- connectivity scoring module
- notification playback module
- safety mode toggle

### Presentation Deliverables

- one architecture diagram
- one decision logic diagram for notification priority handling
- one corridor coverage screenshot
- one side-by-side route comparison
- one safety mode story slide

## Task Split For Teammates

### Agent / Teammate A: OpenCellID Ingestion
Owns:
- corridor tiling
- tile fetch logic
- normalization
- operator mapping
- deduplication
- local caching

Outputs:
- normalized operator-labeled tower dataset for corridor

### Agent / Teammate B: Coverage & Route Scoring
Owns:
- segment generation
- spatial lookup
- per-segment coverage scoring
- route aggregation
- route ranking logic
- weak-zone-ahead prediction and warning trigger logic
- safety mode weights

Outputs:
- scored routes and segment metrics

### Agent / Teammate C: Frontend Map UI
Owns:
- route rendering
- segment heat overlay
- operator selector
- slider
- safety mode toggle
- weak-zone warning modal/card
- route switch / continue interaction
- route summary panel

Outputs:
- user-facing demo screen

### Agent / Teammate D: Notification Engine
Owns:
- queue data model
- state transitions
- delivery logic
- playback integration
- behavior after continue vs reroute decision
- release reason explanations

Outputs:
- deterministic deferred-notification demo

### Agent / Teammate E: Presentation / Story
Owns:
- problem framing
- night/safety corridor story
- demo script
- architecture diagram
- claims language sanity check

Outputs:
- deck and verbal pitch

## Risks

### Risk 1: Weak route differentiation
Mitigation:
- use corridor routes with more spatial variation
- compare Jio vs Airtel as separate overlays
- emphasize longest weak stretch metric

### Risk 2: API limits / fetch volume
Mitigation:
- corridor-only tiling
- prefetch once and cache
- avoid city-wide extraction

### Risk 3: Overclaiming
Mitigation:
- consistently say estimation / predicted connectivity
- do not claim measured signal strength

### Risk 4: UI clutter
Mitigation:
- keep to one map, one side panel, one notification log

## Success Criteria

The prototype is successful if it can show all of the following in one demo flow:

1. user selects Jio or Airtel
2. system compares at least two route options
3. map shows weak vs strong connectivity along the route
4. system warns the user before a predicted weak zone and accepts a dynamic continue vs reroute decision
5. route ranking changes under connectivity weighting
6. notifications defer in weak stretches and release in strong ones
7. safety mode visibly changes route preference and notification policy

## Future Extensions

- add Vi
- ingest actual measured drive-test or handset logs
- calibrate score weights with empirical data
- add push recommendation explanations
- add per-time-of-day confidence
- integrate user-preferred notification rules

## Open Questions

1. Which Jio and Airtel MNC mappings should be included after corridor sampling?
2. Is OSRM sufficient, or does the team already have access to Google Directions?
3. Should safety mode be framed as women’s safety specifically, or more generally as connectivity-prioritized safety mode?
