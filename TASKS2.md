

## Phase 0 — Production Deployment *without* Celery & Docker

This phase delivers a lean, production‑ready deployment on **DigitalOcean App Platform** that comfortably supports 2‑3 concurrent users.  Heavy PDF extraction remains synchronous in web workers; scalability is handled by running ≥ 3 Gunicorn workers.

### Product Requirements (PRD)
1. **Public Landing Page** – Informational page with CTA buttons ("Sign Up", "API Docs").
2. **User Management** – Users can sign‑up, log‑in/out via Django allauth screens.
3. **API‑Key Console** – After login, users can create/list/regenerate their API Keys.
4. **Interactive API Docs** – Embed existing Swagger (`/api/docs/`) within the portal.
5. **Operational Endpoints** – Existing `/api/v1/*` routes continue to function (JWT auth + API Key management).
6. **Concurrent Usage** – Run 3 Gunicorn workers so that up to 3 lengthy PDF analyses can run in parallel.
7. **Deployment Target** – DigitalOcean App Platform, build directly from Git repo (no Docker).

### Deliverables
- `portal` Django app (templates, urls, minimal views, Bootstrap‑powered).
- `Procfile` (web + release).  Example:
  ```
  release: python manage.py migrate
  web: gunicorn api.backend.wsgi --log-file - --bind 0.0.0.0:$PORT --workers 3
  ```
- `runtime.txt` (e.g., `python-3.11.2`).
- Updated `requirements.txt` (add `gunicorn`, `whitenoise`, `django-environ`, `psycopg2-binary`).
- Production settings tweaks (Whitenoise, env‑vars, `ALLOWED_HOSTS`).
- Basic Bootstrap templates: `base.html`, `landing.html`, `dashboard.html`.
- README section describing DigitalOcean deployment steps & required env vars.

### Task Breakdown
| # | Task | Assignee | Status |
|---|------|----------|--------|
| **0.1** | Create `portal` app (`python manage.py startapp portal`) |  | [x] |
| **0.2** | Add `portal` to `INSTALLED_APPS` |  | [x] |
| **0.3** | Templates & static: add `templates/portal/base.html`, `landing.html`, `dashboard.html` using Bootstrap 5 |  | [x] |
| **0.4** | `portal/urls.py` (routes: `/`, `/dashboard/`, `/api-keys/`, `/docs/`) and include in project `urls.py` under `path('', include('portal.urls'))` |  | [x] |
| **0.5** | Views: `LandingView` (TemplateView), `DashboardView` (login required), `APIKeyListCreateView` (leverages endpoints API via Ajax or DRF serializer) |  | [x] |
| **0.6** | Enable Django allauth URLs for sign‑up/login; style with Bootstrap |  | [x] |
| **0.7** | Embed Swagger UI via iframe in `/docs/` page |  | [x] |
