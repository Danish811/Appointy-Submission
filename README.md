Nice — good constraint. Below is a **practical, low-setup design** that lets you run the same codebase either as a **monolith** (everything in one process) or as **microservices** (each module runs independently) with a single `MODE` flag. I’ll call the modules **Link Manager**, **Redirector**, **Analytics**, and **Auth** (as before). I’ll also show exactly how the modules talk to each other in both modes, database recommendations, deployment/run commands, and the tradeoffs so you can choose what fits your Windows laptop and the Appointy task.

---

# Big idea (one codebase, two runtime modes)

* Keep **one repo** organized into clear Python packages: `auth`, `links`, `redirector`, `analytics`, `common` (models, db, utils), `api_gateway` (optional).
* Add a runtime flag `MODE` with two values:

  * `MONOLITH` — everything loaded in one FastAPI instance (single process). Modules call each other as internal function calls.
  * `MICROSERVICE` — each module can run as its own FastAPI app/process. Inter-module calls use HTTP (internal API requests). Analytics events are sent by HTTP from Redirector to Analytics.

Switching modes = flipping `MODE` environment variable. No code duplication — use adapters.

---

# Project layout (single repo)

```
morphlink/
├─ app/                       # python package
│  ├─ common/
│  │  ├─ db.py                # SQLAlchemy engine, SessionLocal, get_db
│  │  ├─ models.py            # Link, Analytics models (shared)
│  │  └─ config.py            # read MODE, DB_URL, service URLs
│  ├─ auth/
│  │  └─ router.py            # hardcoded users + dependency
│  ├─ links/
│  │  └─ router.py            # create/list/delete links (uses common/db)
│  ├─ redirector/
│  │  └─ router.py            # redirect endpoint
│  ├─ analytics/
│  │  └─ router.py            # analytics endpoints / aggregated counts
│  ├─ adapters/
│  │  ├─ service_client.py    # runtime adapter: in-process or HTTP
│  │  └─ analytics_client.py  # functions to call analytics (used by redirector)
│  └─ main.py                 # boots app according to MODE (monolith mux or minimal app for a single module)
├─ scripts/
│  └─ run_monolith.bat
│  └─ run_links.bat
│  └─ run_redirector.bat
├─ requirements.txt
└─ README.md
```

---

# How inter-module communication works

### 1. Adapter pattern (core trick)

Create a small adapter layer (`adapters/analytics_client.py`) that exposes the same functions regardless of mode:

```py
# adapters/analytics_client.py

async def record_click(short_code: str, meta: dict):
    if MODE == "MONOLITH":
        # call the analytics module's in-process function directly
        from app.analytics.service import record_click_sync
        record_click_sync(short_code, meta)
    else:  # MICROSERVICE
        # POST to analytics microservice endpoint
        import httpx
        await httpx.post(f"{ANALYTICS_URL}/events", json={...}, timeout=1.0)
```

* In `MONOLITH` the adapter calls internal functions (fast, no HTTP).
* In `MICROSERVICE` it does an HTTP call (httpx, short timeout).

This single adapter means your redirector/links code never cares which mode it’s running in.

---

### 2. Analytics event flow

* **MONOLITH**:

  * `GET /r/{code}` finds link, immediately returns `RedirectResponse`.
  * Use `BackgroundTasks` to call `adapters.analytics_client.record_click()` which runs in-process and writes to DB via SQLAlchemy session.
* **MICROSERVICE**:

  * `GET /r/{code}` returns redirect immediately.
  * Background task calls `adapters.analytics_client.record_click()` which sends `POST /events` to the Analytics service. Analytics service writes to its DB.

---

# Database strategy (important tradeoffs)

### Minimal/setup-easy option (recommended for the task / local dev):

* Use **SQLite** for `MONOLITH` mode (single process).
* For `MICROSERVICE` mode on a local laptop: SQLite **will** work if you keep services in the **same process** or if you accept lower concurrency and possible locking issues across processes.

  * **Caveat**: SQLite is not great for many simultaneous writer processes. If you split services into separate processes that write concurrently, you may hit `database is locked` errors despite WAL mode. It's workable for a simple demo but fragile.

### Safer production-ready option (slightly more setup):

* Use **PostgreSQL** (single instance shared by services). Very reliable for microservices and concurrent writes. Minimal extra setup:

  * Use a lightweight Docker container locally: `docker run -e POSTGRES_PASSWORD=pass -e POSTGRES_USER=user -e POSTGRES_DB=morph -p 5432:5432 postgres`.
  * Change `DATABASE_URL` env var and everything works.
* **Recommendation**: For the Appointy task, if you must absolutely avoid Docker/installing DB, do `MONOLITH` with SQLite; for a microservice demo, either keep services in one process or accept the SQLite caveats. If you can run Docker, use PostgreSQL when running services separately.

---

# Analytics data model & API

`analytics` table (simple):

* `id` INTEGER PK
* `short_code` TEXT
* `timestamp` DATETIME
* `meta` JSON (optional)

Analytics microservice endpoints (when in MICROSERVICE mode):

* `POST /events` — accept `{ "short_code": "...", "timestamp": "...", "meta": {...} }` → store row
* `GET /stats?user=alice` — return aggregated counts for user's links (join on `links` table or let links service query)

You can implement aggregation two ways:

1. **Analytics service aggregates**: Analytics has access to `links` table or the links service can periodically export. Simpler: analytics service has read-only access to shared DB so it can join `links` -> `analytics` to answer `GET /stats?user=alice`.
2. **Links service aggregates**: Links service queries `analytics` table (same DB) and returns counts. This is simpler if you keep a shared DB.

For minimal dev-work: keep a **shared DB** (common models) accessible to all services. This reduces inter-service calls for simple aggregations, at the cost of coupling DB schema.

---

# Running locally — concrete commands

### MONOLITH (single FastAPI app, minimal setup)

* `.env`:

  ```
  MODE=MONOLITH
  DATABASE_URL=sqlite:///./morphlink.db
  ```
* Run:

  ```
  uvicorn app.main:app --reload --port 8000
  ```
* Behavior: everything available at `http://localhost:8000` (links, redirector, analytics).

### MICROSERVICE (each module as its own FastAPI)

* `.env` for each process:

  * Links: `MODE=MICROSERVICE`, `LINKS_URL=http://localhost:8001`, `DATABASE_URL=postgres://...` or sqlite (with caveats)
  * Redirector: `MODE=MICROSERVICE`, `ANALYTICS_URL=http://localhost:8003`, run on port 8002
  * Analytics: run on port 8003
* Run separate uvicorn commands (or use scripts):

  ```
  uvicorn app.links.router:app --reload --port 8001
  uvicorn app.redirector.router:app --reload --port 8002
  uvicorn app.analytics.router:app --reload --port 8003
  ```
* Redirector sends analytics events to `http://localhost:8003/events`.

This requires slightly more terminal work but no extra external tools if you keep using SQLite (again: limited concurrency).

---

# Health, observability, and the “autopilot” hook

The task doc mentions building a brain that watches the dashboard. Keep this minimal:

* Expose `/metrics` or `/health` endpoints per service.
* Create a small `autopilot.py` script that polls `redirector` metrics (requests/sec or click counts); if it detects a threshold (e.g., simulated high load), it can print a message or trigger a simulated deployment (for the assignment, a log or state change is enough). That’s optional and easy to add once the modular app is done.

---

# Practical recommended approach for your constraints (Windows, minimal install)

1. **Phase 1 (deliverable / low risk)**: Implement as `MONOLITH` using FastAPI + SQLite + BackgroundTasks. This keeps everything simple, works on Windows, and is safe for a timed task.
2. **Phase 2 (demo microservice switch)**: Add the adapter layer and configuration so you can quickly switch `MODE=MICROSERVICE`. For the demo, run all services locally as separate uvicorn processes but **keep a shared SQLite DB** while acknowledging the caveat. If you can run Docker, switch to PostgreSQL before splitting services for reliability.
3. **Phase 3 (optional)**: If you want real isolation, move Analytics to its own PostgreSQL-backed process and show the Redirector calling it via HTTP.

This plan minimizes setup while giving you a real “switchable” architecture to show in the task.

---

# Security & access control refresher

* Keep hardcoded `USERS` and require `?user=alice` or header `X-User: alice`.
* All endpoints that return link lists or analytics filter by `owner_id` server-side.
* Never accept `owner_id` from client payloads.

---

# Next steps I can do right now (pick one)

* Generate a **complete FastAPI monolith skeleton** (runnable on Windows with SQLite) that includes the adapter pattern and a `MODE` flag already wired up so later you can split into services by running different routers. (I recommend this first — you’ll have a working app to hand in.)
* Or generate **the adapter + examples** showing exactly how Redirector calls Analytics in both modes (small focused code).
* Or generate a **README + run scripts** showing how to run the microservice demo locally (with SQLite caveats) and Docker compose for PostgreSQL if you want reliability.

Which do you want next? I can drop the runnable monolith code (models, routers, adapters, and simple tests) right away.
