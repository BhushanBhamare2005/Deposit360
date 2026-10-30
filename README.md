# Deposit360

Deposit360 is a small full-stack workspace for recording fixed-deposit instruments,
tracking maturity dates, storing PDF evidence, and following compliance cases.

## Local development

Requirements: Python 3.11+, Node.js 20+, and npm.

1. Prepare the API:

   ```powershell
   cd apps/api
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -e ".[dev]"
   Copy-Item .env.example .env
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   Put the generated value in `SECRET_KEY` in `apps/api/.env`. SQLite is the local
   default; the database and PDF storage folder are created as needed.

2. In a separate terminal, start the API from `apps/api`:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   uvicorn app.main:app --reload
   ```

3. In another terminal, prepare and start the web app from the repository root:

   ```powershell
   Copy-Item apps/web/.env.local.example apps/web/.env.local
   npm install
   npm run dev:web
   ```

Open <http://localhost:3000>. API documentation is at <http://localhost:8000/docs>.
Create an account, add an institution, then register deposits and upload PDF files.
The five role dashboards are Institution Applicant, Scrutiny Officer, Compliance
Administrator, Finance Officer, and Approving Authority. Role-scoped API checks
enforce the same separation as the frontend navigation. Seed the local, synthetic
role-play dataset from `apps/api` with `python -m app.demo_seed`; the demo accounts
and fabricated FDR records are described in [docs/DEMO_SCRIPT.md](./docs/DEMO_SCRIPT.md).
The scrutiny, renewals, releases, notifications, and audit pages expose the
corresponding role-scoped workflows. Finance review must precede final authority
approval. Bank checks use an explicit mock adapter and
never contact a bank unless an HTTP provider is explicitly configured. Email and
SMS default to a local development log sink; configure HTTP delivery endpoints and
their optional API keys to connect messaging providers. The API also supports
Tesseract OCR for scanned PDFs; install Tesseract locally and set `TESSERACT_CMD`
if it is not on `PATH`. An enabled background scheduler refreshes lifecycle states
and maturity reminders hourly by default. In multi-instance deployments, enable
the scheduler on only one API instance.

The web app's deterministic end-to-end tests use a mocked API and do not require
provider credentials:

```powershell
npm --workspace apps/web run test:e2e:install
npm --workspace apps/web run test:e2e
```

## Docker

Copy `.env.example` to `.env`, set non-empty random values for `POSTGRES_PASSWORD`
and `SECRET_KEY`, then run:

```powershell
docker compose -f infra/docker/docker-compose.yml up --build
```

Open <http://localhost:8080>. The API is also available on port 8000. Shut down with:

```powershell
docker compose -f infra/docker/docker-compose.yml down
```

The API applies the Alembic schema migration at startup. The API image includes
Tesseract for OCR; Docker Compose itself must be installed to run this stack.

## Tests

```powershell
cd apps/api
python -m pip install -e ".[dev]"
pytest
ruff check .
```

## Workspace

- `apps/api` — FastAPI, SQLAlchemy, authentication, and API tests
- `apps/web` — Next.js dashboard
- `packages/shared` — shared TypeScript contracts
- `infra` — Docker and reverse-proxy configuration