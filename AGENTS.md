<!-- AUTO-GENERATED. Do not edit. -->
<!-- Version: 1.0.2 | Generated: 2026-05-13T19:19:37Z | Hash: 8f46bfff1789 -->
<!-- Sources: dig-job-server/AGENTS.md -->

# dig-job-server — main

## Purpose and Intended Audience

Execution-focused guidance for contributors and coding agents working in dig-job-server.
Use this file for setup, run, test, and high-frequency change workflows.

## Tech Stack Snapshot

- Backend: FastAPI (Python 3.9+), SQLAlchemy, Alembic
- Frontend: Nuxt 3 (Vue 3), Pinia, PrimeVue 4, Tailwind CSS 4
- Frontend visualization: Chart.js 4 (`chart.js@^4.5.1`), Plotly.js (`plotly.js-dist-min@^3.5.0`)
- Data/infra: MySQL, AWS S3, AWS Batch
- Deployment: GitHub Actions to EC2 (API) and nginx-hosted frontend

## Critical Project Map

- job_server/: API, auth, DB utilities, batch and S3 integrations
- frontend/: Nuxt app (pages, components, stores, middleware)
- alembic/: DB migrations
- tests/: pytest suite and fixtures
- .github/workflows/: CI/CD pipelines

## Code Organization

### Backend Structure (`job_server/`)

Core API modules (Python/FastAPI):

| Module                             | Purpose                                                                   |
| ---------------------------------- | ------------------------------------------------------------------------- |
| `api.py`                           | Main FastAPI router (~850 lines); all REST endpoints                      |
| `server.py`                        | App factory, CLI, CORS setup, middleware                                  |
| `database.py`                      | SQLAlchemy connection pool and context manager                            |
| `database_utils.py`                | Database queries (users, datasets, workflows, jobs)                       |
| `model.py`                         | Pydantic models (User, DatasetInfo, AnalysisRequest, AnalysisMethod enum) |
| `batch.py`                         | AWS Batch job submission and polling                                      |
| `s3.py`                            | S3 utilities (bucket ops, presigned URLs, metadata)                       |
| `file_utils.py`                    | File parsing, delimiter detection, BED validation                         |
| `auth_backend.py`, `auth_mysql.py` | Authentication interface and MySQL implementation                         |
| `jwt_utils.py`                     | JWT token creation and validation                                         |

### Database Schema (via Alembic)

- `users` — User accounts (user_name, password, timestamps)
- `datasets` — GWAS datasets (metadata JSON, uploaded_by, timestamps)
- `workflow_jobs` — Analysis jobs (status, method enum, job logs, timestamps)
- `bed_files` — Annotation files (user, filename, S3 path)

### Frontend Structure (`frontend/`)

**Pages** (Nuxt 4 / Vue 3):

| Page                                                      | Purpose                                     |
| --------------------------------------------------------- | ------------------------------------------- |
| `pages/index.vue`                                         | Landing page (workflows overview)           |
| `pages/upload/index.vue`                                  | 4-step GWAS upload wizard                   |
| `pages/datasets/index.vue`                                | Dataset manager (GWAS table, BED files)     |
| `pages/results/index.vue`                                 | Results dashboard (SLDSC/MAGMA/PIGEAN tabs) |
| `pages/falcon/index.vue`                                  | FALCON visualization dashboard              |
| `pages/login/index.vue`, `pages/login-callback/index.vue` | Authentication pages                        |
| `pages/guide/index.vue`                                   | User guide/documentation                    |

**Components** (`frontend/components/`):

- `results/` — Result tab components (SldscResultsTab, MagmaResultsTab, PigeanResultsTab, AnnotResultsTab)
- `falcon/` — FALCON viewer components (FolderPicker, GlobalFilterBar, TDPTab, GenesScatterTab, VariantsScatterTab, DataTableTab, LogSummaryTab)

**State Management** (Pinia stores in `frontend/stores/`):

| Store            | Scope                                                           |
| ---------------- | --------------------------------------------------------------- |
| `UserStore`      | Auth token, API client, datasets, phenotypes                    |
| `ResultsStore`   | Active tab, workflow status, result visibility flags            |
| `FalconStore`    | FALCON viewer state (genes/variants datasets, filters, caching) |
| `PhenotypeStore` | Phenotype metadata lookup                                       |

**Composables** (`frontend/composables/`):

- `useFalconDataSource.js` — Load FALCON results from local files or server
- `useFalconFileLoader.js` — TSV file parsing (PapaParse wrapper)
- `useFalconPlots.js` — Generate Plotly spec objects
- `useFalconTDP.js` — TDP analysis engine (FALCON Zoom logic)
- `useFalconLogParser.js` — Parse execution logs
- `usePlotly.js` — Plotly rendering integration
- `useToast.js` — Toast notification system

**Utilities** (`frontend/utils/`):

- `falcon/config.js` — Tab definitions and analysis thresholds
- `falcon/colorPalette.js` — Color assignments for result clumps
- `falcon/pako.js` — Gzip decompression
- `falcon/clinical-trials.js` — Clinical trials data

**Styling & Assets**:

- `tailwind.config.js` — Tailwind CSS customization
- `assets/css/` — Global styles, theme CSS, syntax highlighting
- `public/data/falcon-egl-index.json` — Essential Gene List index

### Data Flow Architecture

User uploads GWAS file → S3 presigned URL → Backend stores metadata in database → AWS Batch job queued → Job writes results to S3 → Frontend polls `/api/job-status/{job_id}` (server-sent events) → Results retrieved from S3, cached, displayed in dashboard.

### Shared Patterns

- **Dataset Identification**: Both backend and frontend use SHA256 hash (`get_dataset_hash()`) for dataset uniqueness
- **File Handling**: Delimiter auto-detection (CSV/Sniffer), gzip decompression support (Python `gzip`, frontend `pako`), BED validation
- **Analysis Methods**: Backend `AnalysisMethod` enum (sldsc, magma, annot-sldsc, pigean) mirrors frontend workflow buttons
- **Caching**: Backend uses `@lru_cache` on result retrieval; frontend caches LD chunks in stores

## Quick Start Workflows

### 1. Backend Setup and Run

bash/zsh:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m job_server.server serve --port 8000
```

PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python -m job_server.server serve --port 8000
```

### 2. Frontend Setup and Run

bash/zsh:

```bash
cd frontend
npm install
echo "NUXT_PUBLIC_API_BASE_URL=http://ec2-98-83-154-159.compute-1.amazonaws.com:5000" > .env
npm run dev
```

PowerShell:

```powershell
Set-Location frontend
npm install
"NUXT_PUBLIC_API_BASE_URL=http://ec2-98-83-154-159.compute-1.amazonaws.com:5000" | Out-File -FilePath .env -Encoding utf8
npm run dev
```

### 3. Local MySQL Helper

```bash
./docker_db/docker_db.sh start 3308
./docker_db/docker_db.sh stop
```

### 4. Testing

- Run: pytest
- Uses TEST_MODE=true flow and test fixtures from tests/conftest.py

### 5. Migration Commands

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

## Constraints and Non-Negotiables

- Keep API business logic in job_server/api.py and DB operations in job_server/database_utils.py.
- Preserve dual auth behavior in get_current_user() (TEST_MODE vs production user service).
- Respect S3 path conventions: userdata/{username}/{genetic|annotation}/{dataset}/{workflow}/{method}/.
- Results page orchestration stays in frontend/pages/results/index.vue.
- New analysis methods must be added coherently across model enums, batch parameters, backend endpoints, and frontend tabs.
- Reuse-first rule for new functionality:
    1. Check whether equivalent logic already exists in `job_server/` modules, `frontend/stores/`, `frontend/composables/`, or `frontend/components/` before creating new files.
    2. If a framework/library is already in use (e.g., PrimeVue components, Pinia stores, Plotly composables), use available patterns before writing custom ones.
    3. If new code is still required, place it in the same folder structure and naming conventions used by existing code (stores in stores/, composables in composables/, components in components/).

## High-Frequency Change Playbooks

### Add API Endpoint

1. Add route in job_server/api.py.
2. Ensure auth behavior is correct in app setup.
3. Wire frontend call via composable/component.
4. Add/update tests.

### Add Analysis Method

1. Add enum/member in job_server/model.py.
2. Update batch job parameter handling.
3. Add method-specific results endpoint.
4. Add frontend tab component and visibility/status wiring.
5. Add tests and validate end-to-end status/result flow.

## Verification Checklist

- Backend starts and health-relevant endpoints respond.
- Frontend dev server loads and can reach configured API base URL.
- pytest passes locally for touched areas.
- Alembic migrations apply cleanly.
- No regressions in workflow status handling (RUNNING/SUCCEEDED/FAILED tabs).

## Integration References

- Upstream auth service defaults: users.kpndataregistry.org (via USER_SERVICE_URL)
- AWS Batch queue/definition wiring lives in job_server/batch.py
- CI/CD definitions: .github/workflows/api-ci.yml and .github/workflows/frontend-ci.yml

## Assumptions and Known Limitations

- Local MySQL commonly uses port 3308 to avoid conflicts.
- No single-command full-stack orchestrator is defined in this repo.
- Some legacy compatibility behavior is intentionally preserved for older frontend consumers.

## Appendix (Optional Deep Context)

Use these files when deeper context is required:

- job_server/api.py
- job_server/database_utils.py
- frontend/pages/results/index.vue
- frontend/components/results/
- frontend/stores/ResultsStore.js
- tests/conftest.py
