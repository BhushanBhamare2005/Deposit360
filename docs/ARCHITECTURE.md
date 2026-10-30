# Architecture

Deposit360 is a small monorepo with a Next.js client, a FastAPI service, and a
shared TypeScript contract package.

```text
Browser ── HTTP/JSON ──> Next.js UI
   │                         │
   └──── /api/v1 ────────────┴──> FastAPI ── SQLAlchemy ──> SQLite or PostgreSQL
                                             └──> local PDF storage
```

The API owns authentication, validation, institution-level access checks, and
database writes. Passwords are stored as salted PBKDF2 hashes. API access tokens
are signed JWTs; production deployments must provide a strong `SECRET_KEY`.

The app uses SQLite for local development and can use PostgreSQL by changing
`DATABASE_URL`. PDF upload size is configurable. Files are stored under the
configured storage directory with generated names; original names are metadata
only.

The Compose setup places Nginx in front of the web and API containers. The web
client sends `/api/v1` requests through that same origin.

## Core flow

1. A user registers and receives an institution-user role.
2. The user creates an institution linked to their account.
3. The user records deposits and uploads PDF documents.
4. The user opens a compliance case for a deposit.
5. A reviewer account created with `python -m app.cli` can review cases.

Database tables are initialized on API startup for this MVP. Use reviewed schema
migrations before deploying schema changes to production.