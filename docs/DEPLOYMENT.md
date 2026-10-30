# Deposit360 cloud deployment

The web app is deployed on Vercel. The FastAPI backend runs on Render, PostgreSQL
is provided by Neon, and PDF evidence is stored in Cloudflare R2. The API uses the
S3-compatible R2 API; it does not depend on a Render filesystem for uploaded files.

## 1. Create persistent services

Create a PostgreSQL project in Neon and copy its pooled or direct connection URL.
Set the SQLAlchemy URL to use the installed psycopg driver:

```text
postgresql+psycopg://USER:PASSWORD@HOST/DATABASE?sslmode=require
```

In Cloudflare, create a private R2 bucket and an R2 API token with object read/write
access limited to that bucket. Record the account-specific S3 endpoint, bucket
name, access key ID, and secret access key. Do not put credentials in the
repository or send them in chat.

## 2. Deploy the API on Render

Create a Render Blueprint from the Deposit360 GitHub repository and approve the
root `render.yaml`. The service builds `infra/docker/Dockerfile.api` using the
repository root as its Docker context. Set these Render environment variables
through the Render dashboard:

- `DATABASE_URL`: the Neon URL in the SQLAlchemy format above.
- `CORS_ORIGINS`: the exact production Vercel origin, for example
  `https://deposit360.vercel.app` (no trailing slash).
- `DEMO_PASSWORD`: a private, unique password to use only if synthetic demo
  accounts are seeded. Production seeding refuses to use the published local
  demo password.
- `STORAGE_S3_ENDPOINT_URL`: `https://<account-id>.r2.cloudflarestorage.com`.
- `STORAGE_S3_BUCKET`: the private bucket name.
- `STORAGE_S3_ACCESS_KEY_ID` and `STORAGE_S3_SECRET_ACCESS_KEY`: the R2 token
  credentials.

The Blueprint generates `SECRET_KEY`. Keep the initial service on one instance
so the in-process lifecycle scheduler runs once. Render's free service may sleep
when idle; choose a paid plan only if always-on availability is needed.

The API health check is `/health`. On startup, the service applies Alembic
migrations. After deployment, seed synthetic walkthrough records only if needed:
run `python -m app.demo_seed` in the Render Shell. Do not seed demo data into a
production environment that contains real customer records.

## 3. Deploy the web app on Vercel

Import the same GitHub repository into Vercel and set the project root to
`apps/web`. Keep the shared npm workspace enabled. Set this build-time environment
variable for Production (and Preview only if a separate API/CORS origin is set):

```text
NEXT_PUBLIC_API_URL=https://<render-service>.onrender.com/api/v1
```

Deploy the frontend, then add its final production origin to the Render
`CORS_ORIGINS` value and redeploy the API if necessary. The frontend and API
origins must match exactly; do not use `*` for the production API.

## Local verification and limitations

Local development continues to use SQLite and local PDF storage by default.
Deployments must set `STORAGE_BACKEND=s3` and all four R2 settings. The current
demo bank-verification and email/SMS adapters remain simulated/log-based unless
real authorized providers are configured. OCR and matching scores are never
proof of bank authenticity.
