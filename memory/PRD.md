# SIH 2026 PS26251 — Predictive Forward Logistics

## Original problem statement
Build a production-quality hackathon project for Indian Army Predictive Logistics & Forward Supply Chain as a decision-support and simulation platform using synthetic/demo data. The platform must demonstrate Observe → Predict → Explain → Simulate → Optimize → Recommend → Human Approval → Measure Impact.

## Architecture decisions
- React 19 frontend with a dark Logistics Intelligence Control Tower and light geographic workspace.
- FastAPI backend with MongoDB persistence for users and audit decisions.
- Synthetic digital twin data is kept explicit and readable for a reliable 3-minute demo.
- Leaflet/OpenStreetMap provides the geographic network view.
- Forecasting exposes a reproducible Random Forest baseline plus MAE/RMSE metadata; risk and recommendation logic are transparent rules.
- JWT demo authentication supports an admin role and keeps human approval separate from recommendations.

## User personas
- Operations planner: monitors the network, activates scenarios, and reviews recommended resupply.
- Operations administrator: reviews configuration, model metadata, data sources, and audit trail.
- Hackathon judge: understands the control tower value within 30 seconds and sees before/after impact.

## Core requirements (static)
- Control tower answers what is happening, what will happen, why, and what should happen.
- Geographic digital twin with locations, routes, status, risk, and inventory.
- Inventory, demand forecast, shortage/risk explanation, scenarios, recommendation, approval, and impact measurement.
- Synthetic data, explicit model metrics, no autonomous military claims.

## Implemented (2026-06-12)
- Authenticated command-center dashboard with role-aware admin navigation.
- KPI overview, alert queue, live network map, node inspector, route state, forecast chart, and mission posture.
- Scenario lab with demand surge, blocked route, weather, and vehicle failure scenarios.
- Before/after simulation view and Approve/Reject human decision workflow with MongoDB audit log.
- Inventory engine and admin configuration views for judge-ready breadth.
- FastAPI endpoints for auth, dashboard, locations, routes, scenarios, simulation, decisions, audit, and admin summary.
- Baseline forecast metrics and documented synthetic data boundary.

## Implemented (2026-06-14) — v2.0 feature set
- Backend split into modules: `db.py`, `auth.py`, `twin.py` (Mongo-persisted locations/routes/vehicles/risk weights, seeded on first start; location risk = Σ weight×factor), `optimizer.py`, `forecast.py`, `simulation.py`, `admin.py`.
- Route Optimizer: `POST /api/optimizer/rank` — K-shortest simple paths over open corridors, score = 100 − (w_time·ETA + w_risk·risk + w_cap·shortfall), vehicle allocation; dedicated "Route optimizer" tab with sliders, top-3 drawn on map (gold/green/grey); overview map shows top corridors for the focus location.
- Admin CRUD: `/api/admin/{locations|routes|vehicles}` GET/POST/PUT/DELETE with validation + cascade; `/api/admin/weights` PUT (must sum to 1); `/api/admin/twin/reset`. Admin console tabs: Data entities, Forecast model, Risk weights, Audit trail.
- Live forecast model: synthetic 180-day consumption history (5 locations × 4 resources) in Mongo; RandomForest trained on lag/rolling features, versions stored (zlib-pickled) with MAE/RMSE/MAPE/importance; retrain, activate version, CSV upload (`date,location_id,resource,quantity`), regenerate synthetic. Dashboard forecast chart reads the active model.
- Simulation now computed: scenarios modify the twin (blocked best corridor / +6h weather / VH-04 out / ×1.42 demand), before/after stockout probability from forecast vs stock, recommendation built from the top-ranked path; decisions store before/after in audit.
- Guided demo (topbar): 8 steps auto-play with captions + progress; pauses at HUMAN DECISION until Approve is clicked; skippable/exit.
- Testing agent iteration_4: backend 34/34 pytest, frontend 100%.

## Implemented (2026-06-13)
- Auth hardened for the same-origin preview/deploy: frontend stores login JWT in localStorage (`ct_token`) and sends `Authorization: Bearer`; cookie kept as secondary. Standard FastAPI CORSMiddleware restored; logout clears cookie with matching Secure/SameSite=None attrs.
- Fixed login → logout → re-login hang and page-reload session restore ("RESTORING SESSION" gate, state reset on logout).
- Before/After impact panel now bound to `/api/simulation/disruption` response; error-variant toast (`toast-error`) for API failures.
- Verified by testing agent iteration_3: backend 10/10, frontend 100%.

## Prioritized backlog
- P0: add CSV/JSON ingestion UI and persist all digital twin entities.
- P0: connect real model training endpoint and store serialized model versions.
- P1: add route optimizer controls, alternative ranking, and vehicle capacity allocation.
- P1: expand audit log UI and downloadable architecture/ER diagrams.
- P2: add richer map layers and scenario comparison across multiple simultaneous disruptions.

## Remaining next tasks
- Add automated unit/API tests for inventory, risk, route, simulation, and auth edge cases.
- Add admin CRUD forms for locations, routes, vehicles, resources, and risk weights.
- Add a dedicated what-if comparison chart with cost, ETA, service level, and stockout probability.