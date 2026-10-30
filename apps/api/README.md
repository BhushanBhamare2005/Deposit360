# Deposit360 API

FastAPI service for managing institutions, fixed-deposit instruments, documents, and
compliance cases.

## Run locally

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Set `SECRET_KEY` in `.env` to a randomly generated value of at least 32 characters:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then start the API:

```powershell
uvicorn app.main:app --reload
```

Alembic migrations are applied when the API starts; the local SQLite database and
upload directory are created as needed. The initial schema migration is in
`alembic/versions`.
Interactive API documentation is available at <http://localhost:8000/docs>.

Create a reviewer/admin user from the API directory:

```powershell
python -m app.cli
```

Seed the five local demo roles and fabricated FDR data:

```powershell
python -m app.demo_seed
```

The seed command creates an Institution Applicant, Scrutiny Officer, Compliance
Administrator, Finance Officer, and Approving Authority account. See
`docs/DEMO_SCRIPT.md` for the local-only demo credentials and end-to-end sequence.
Staff accounts are deliberately provisioned separately; public registration
creates Institution Applicant accounts only.

## Run tests and lint

```powershell
pytest
ruff check .
ruff format --check .
```

For PostgreSQL, set `DATABASE_URL` to a SQLAlchemy PostgreSQL URL and ensure the
database is available before starting the API.

## Workflow capabilities and boundaries

- Scrutiny officers and administrators can review compliance cases and make
  documented release decisions. Institution users can submit release requests and
  link a previous deposit with its replacement.
- The five demo roles have distinct API permissions: applicants submit their own
  institution's records; scrutiny and compliance roles review cases; only
  compliance administrators manage policy versions and bank-verification
  evidence; finance officers advance submitted release requests to finance
  review; and approving authorities make the final decision. Final approval is
  not available until finance review is complete. Legacy `admin` accounts remain
  privileged for backwards-compatible local administration.
- Case reviewers can request corrections; only the institution applicant can
  resubmit the case. Policy rule versions are recorded for the prototype's
  compliance workflow and are not an automatic decision engine.
- Workflow notifications are persisted in the application and can be acknowledged
  in the web interface. Email and SMS default to a local log sink
  (`EMAIL_DELIVERY_ADAPTER=log`, `SMS_DELIVERY_ADAPTER=log`); SMS is sent only to
  users with a phone number. Delivery errors are logged and do not roll back the
  in-app notification. Set either adapter to `http` and provide its URL and
  optional API key to configure a real delivery endpoint. The generic HTTP
  contract is `POST` JSON with `to`, `subject`, and `body` for email, or `to` and
  `body` for SMS; configure an endpoint that accepts this contract. The key, if
  provided, is sent as a Bearer token. No vendor or credentials are assumed.
- `BANK_VERIFICATION_ADAPTER=mock` deliberately simulates a verification request;
  it never contacts a bank. A real integration can be explicitly configured with
  `BANK_VERIFICATION_ADAPTER=http`, `BANK_VERIFICATION_URL`, and an optional
  `BANK_VERIFICATION_API_KEY`. The configured endpoint receives a JSON POST with
  `instrument_number` and `bank_name`, and must return JSON with a supported
  `status` (`pending_external`, `confirmed`, `failed`, or `unable_to_verify`) and
  optional string `note`. Provider errors are returned as HTTP 502; no bank is
  contacted unless the `http` adapter is explicitly selected.
- PDF text extraction is available for text-based PDFs. Scanned pages require
  Tesseract; the API Docker image installs it. For local OCR, install Tesseract
  and set `TESSERACT_CMD` if it is not on `PATH`. The API returns an explicit
  error rather than claiming OCR succeeded when Tesseract is unavailable.
- The lifecycle scheduler refreshes maturity states and sends recurring in-app
  maturity reminders. Configure `LIFECYCLE_SCHEDULER_ENABLED`,
  `LIFECYCLE_SCHEDULER_INTERVAL_SECONDS`, and
  `MATURITY_REMINDER_INTERVAL_DAYS` as needed. The in-process scheduler is intended
  for a single API process; for multi-worker or multi-replica deployments, run
  only one scheduler-enabled instance to prevent duplicate jobs.