

## Phase 0 — Production Deployment *without* Celery & Docker

This phase delivers a lean, production‑ready deployment on **DigitalOcean App Platform** that comfortably supports 2‑3 concurrent users.  Heavy PDF extraction remains synchronous in web workers; scalability is handled by running ≥ 3 Gunicorn workers.

### Product Requirements (PRD)
1. **Public Landing Page** – Informational page with CTA buttons ("Sign Up", "API Docs").
2. **User Management** – Users can sign‑up, log‑in/out via Django allauth screens.
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
| **0.1** | Create `portal` app (`python manage.py startapp portal`) |  |  |
| **0.2** | Add `portal` to `INSTALLED_APPS` |  |  |
| **0.3** | Templates & static: add `templates/portal/base.html`, `landing.html`, `dashboard.html` using Bootstrap 5 |  |  |
| **0.4** | `portal/urls.py` (routes: `/`, `/dashboard/`, `/api-keys/`, `/docs/`) and include in project `urls.py` under `path('', include('portal.urls'))` |  |  |
| **0.5** | Views: `LandingView` (TemplateView), `DashboardView` (login required), `APIKeyListCreateView` (leverages endpoints API via Ajax or DRF serializer) |  |  |
| **0.6** | Enable Django allauth URLs for sign‑up/login; style with Bootstrap |  |  |
| **0.7** | Embed Swagger UI via iframe in `/docs/` page |  |  |
| **0.8** | Add `gunicorn`, `whitenoise`, `django-environ`, `psycopg2-binary` to `requirements.txt` |  |  |
| **0.9** | Production settings:   
   – `DEBUG=False`,   
   – `ALLOWED_HOSTS` from env,   
   – Whitenoise middleware,   
   – `STATIC_ROOT = BASE_DIR / 'staticfiles'`,   
   – DB config from `DATABASE_URL` via django‑environ |  |  |
| **0.10** | Create `Procfile`, `runtime.txt` |  |  |
| **0.11** | Update `.env.sample` with required variables (SECRET_KEY, DATABASE_URL, ALLOWED_HOSTS, JWT settings) |  |  |
| **0.12** | Add `release` command in Procfile to run migrations on deploy |  |  |
| **0.13** | Smoke‑test on local: `gunicorn api.backend.wsgi --workers 3` + visit landing/dashboard |  |  |
| **0.14** | Push to DigitalOcean, configure App Spec (build‑from‑source), set env vars, attach DO Managed Postgres (or use SQLite for demo) |  |  |
| **0.15** | Post‑deploy validation:   
   – Visit landing page, sign‑up, generate API key.   
   – Run `testt.py` using obtained JWT + API key from two terminals concurrently → ensure both succeed. |  |  |

### Notes / Constraints
- **Concurrency**: 3 workers suffice for 2‑3 simultaneous heavy requests; monitor and scale vertically if CPU usage spikes.
- **Static files** served by Whitenoise for simplicity; DO CDN can be added later.
- **Database**: Prod should use Postgres; if demo, SQLite will work on DO but is not recommended for multi‑instance scaling.
- **SSL**: DO automatically provisions a certificate for the `ondigitalocean.app` subdomain.
- Future phase will re‑introduce Celery for larger scale.

