# Agro Monitoring System

UAV aerial imagery processing and crop monitoring system. Processes drone photos through an
OpenDroneMap photogrammetry pipeline, calculates vegetation indices (NDVI / NDRE / EVI),
detects anomaly zones, and visualises results on an interactive map.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        Browser                          │
│  React 18 + MapLibre GL + Recharts + TanStack Query     │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP / REST  (JWT Bearer)
┌────────────────────▼────────────────────────────────────┐
│               FastAPI  (uvicorn :8000)                  │
│  /auth  /fields  /flights  /flights/{id}/files          │
│  /flights/{id}/export  /flights/{id}/anomalies          │
└───────┬─────────────────────────┬───────────────────────┘
        │ SQLAlchemy ORM          │ enqueue via RQ
┌───────▼──────────┐   ┌──────────▼────────────────────── ┐
│  PostgreSQL 16   │   │  Redis 7   ←  RQ Worker           │
│  + PostGIS 3.4   │   │             ├─ ODM task           │
│  (fields,        │   └──────────┬──┴─ indices task       │
│   flights,       │              │   └─ segmentation task │
│   index_maps,    │   ┌──────────▼────────────────────── ┐
│   anomaly_zones) │   │  NodeODM  (:3000)                │
└──────────────────┘   │  photogrammetry + orthophoto     │
                       └───────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker ≥ 24 with Compose v2
- 8 GB RAM recommended (NodeODM is memory-hungry)

### 1. Clone and configure

```bash
git clone <repo-url> agro-monitoring
cd agro-monitoring
cp .env.example .env          # edit passwords if needed
```

### 2. Build and start all services

```bash
docker compose up --build -d
```

Services started:

| Service   | Port | Description                  |
|-----------|------|------------------------------|
| frontend  | 5173 | React web UI (nginx)         |
| backend   | 8000 | FastAPI REST API             |
| db        | 5432 | PostgreSQL + PostGIS         |
| redis     | 6379 | Queue broker                 |
| nodeodm   | 3000 | Photogrammetry engine        |

### 3. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 4. Open the app

Navigate to **http://localhost:5173** and log in:

| Field    | Value    |
|----------|----------|
| Username | `admin`  |
| Password | `agro2026` |

---

## Workflow

1. **Add a field** — click "+ Додати поле", enter name and area.
2. **Create a flight** — select the field, click "+ Новий політ", choose the date.
3. **Upload images** — drag-and-drop at least 3 JPG/TIFF drone photos into the upload zone.
4. **Start processing** — click "Запустити обробку". The worker enqueues an ODM task, then calculates vegetation indices and detects anomaly zones.
5. **View results** — the map shows the orthophoto and NDVI/NDRE/EVI overlays. Switch layers with the tab controls. Anomaly zones are highlighted in red and show area on click.
6. **Export** — download GeoTIFF zip, PNG preview, or CSV statistics from the flight detail panel.

---

## API Reference

Interactive docs: **http://localhost:8000/docs**

Key endpoints:

```
POST  /auth/token                    — obtain JWT (form: username/password)
GET   /fields                        — list fields
POST  /fields                        — create field (GeoJSON boundary)
GET   /flights?field_id=<uuid>       — list flights for a field
POST  /flights                       — create flight
POST  /flights/{id}/upload           — upload raw images (multipart)
POST  /flights/{id}/process          — enqueue ODM processing
GET   /flights/{id}/status           — polling status + progress %
GET   /flights/{id}/files/{type}     — serve orthophoto TIF or index PNG preview
GET   /flights/{id}/files/orthophoto/bbox — WGS84 [W,S,E,N] for map overlay
GET   /flights/{id}/export?format=geotiff|png|csv — download results
GET   /flights/{id}/anomalies        — GeoJSON FeatureCollection of anomaly zones
```

---

## Running Tests

```bash
# Unit tests only (no DB required)
docker compose exec backend pytest tests/test_indices.py -v

# API + integration tests (requires running DB)
docker compose exec backend pytest tests/ -v --ignore=tests/test_db.py

# All tests including DB round-trip
docker compose exec backend pytest tests/ -v
```

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py           — FastAPI app, CORS, router registration
│   │   ├── auth.py           — JWT creation/validation, bcrypt password check
│   │   ├── models.py         — SQLAlchemy ORM models
│   │   ├── database.py       — engine, session factory
│   │   ├── config.py         — settings from environment
│   │   ├── routers/
│   │   │   ├── auth.py       — POST /auth/token
│   │   │   ├── fields.py     — CRUD /fields
│   │   │   ├── flights.py    — CRUD /flights + upload
│   │   │   ├── tasks.py      — POST /flights/{id}/process
│   │   │   └── files.py      — file serving + export + anomalies
│   │   ├── schemas/          — Pydantic request/response schemas
│   │   └── services/         — storage helpers
│   ├── alembic/              — database migrations
│   └── tests/                — pytest test suite
├── worker/
│   ├── tasks/
│   │   ├── odm_task.py       — NodeODM integration + polling
│   │   ├── indices_task.py   — NDVI/NDRE/EVI + PNG previews + bbox
│   │   └── segmentation_task.py — anomaly zone detection
│   └── worker.py             — RQ worker entry point
├── frontend/
│   └── src/
│       ├── pages/            — LoginPage, FieldsPage, FlightPage
│       ├── components/
│       │   ├── Layout/       — TopBar, Sidebar
│       │   ├── Flights/      — FlightList, FlightUpload, ProcessingStatus, NdviChart
│       │   └── Map/          — MapView (MapLibre GL), LayerControls
│       ├── store/            — Zustand global state (token, selected IDs, active layer)
│       ├── api/              — axios client with JWT interceptor
│       └── types/            — TypeScript interfaces
├── infra/
│   └── init.sql              — PostGIS extension init
├── docker-compose.yml
└── .env.example
```

---

## Environment Variables

| Variable           | Default          | Description                        |
|--------------------|------------------|------------------------------------|
| `POSTGRES_USER`    | `agro`           | DB username                        |
| `POSTGRES_PASSWORD`| `agro`           | DB password                        |
| `POSTGRES_DB`      | `agrodb`         | Database name                      |
| `POSTGRES_HOST`    | `db`             | DB hostname (Docker service name)  |
| `REDIS_URL`        | `redis://redis:6379/0` | Redis connection URL         |
| `NODEODM_URL`      | `http://nodeodm:3000`  | NodeODM base URL             |
| `DATA_DIR`         | `/data`          | Persistent data volume root        |
| `JWT_SECRET`       | *(hardcoded)*    | Override for production            |
