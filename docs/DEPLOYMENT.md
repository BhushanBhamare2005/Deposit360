# Deposit360 deployment on Vercel

Deposit360 deploys as one Vercel project with two services: a public Next.js
frontend and a private FastAPI backend. The frontend's same-origin `/api/v1/*`
route forwards authenticated requests over a Vercel service binding. PostgreSQL
stores durable application data, and private Vercel Blob stores PDF evidence.

## Before the first deployment

1. Import the GitHub repository into Vercel and select the repository root as the
   project root. Keep the root `vercel.json`; it defines both services.
2. Connect a Neon PostgreSQL database through the Vercel Storage/Marketplace
   integration. Use a pooled connection URL, and configure separate
   `DATABASE_URL` values for Development, Preview, and Production as needed.
   Do not point a demo or preview deployment at a database containing real
   financial records.
3. Create a **private** Vercel Blob store and connect it to this Vercel project.
   The integration supplies the Blob store ID and Vercel OIDC credentials to
   the runtime. Do not make financial documents public or copy a Blob token into
   source code.
4. Configure the following Vercel environment variables for every environment
   where the app should run:

   | Variable | Value |
   | --- | --- |
   | `APP_ENV` | `production` for Production; use an appropriate value for Preview/Development |
   | `SECRET_KEY` | A unique, randomly generated secret |
   | `DATABASE_URL` | That environment's Neon PostgreSQL pooled connection URL |
   | `STORAGE_BACKEND` | `vercel_blob` |
   | `MAX_UPLOAD_SIZE_MB` | `4` |
   | `NEXT_PUBLIC_API_URL` | `/api/v1` |
   | `NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB` | `4` |
   | `CRON_SECRET` | A randomly generated secret of at least 16 characters |
   | `LIFECYCLE_SCHEDULER_ENABLED` | `false` |

   Set `DEMO_PASSWORD` only if you intend to seed the synthetic role-play
   accounts. The quick-login buttons publish the shared demo password in the
   browser bundle, so this is appropriate only for fabricated demo data. Never
   use that shared account password with real customer data.

5. Redeploy after connecting storage and configuring the environment variables.
   The API service's build command applies Alembic migrations using that
   environment's database. The FastAPI startup skips migrations and the
   in-process scheduler on Vercel; lifecycle states still refresh when the
   deposits list is requested.

## Seed synthetic demo accounts (optional)

To seed the five role accounts, pull the intended environment variables to a
local ignored env file using the Vercel CLI, then run the seed script from
`apps/api`. Keep the file private and do not paste its contents into chat or
commit it:

```powershell
cd apps/api
python -m pip install -e .
python -m app.demo_seed
```

The seed command refuses to use its published demo password in production unless
`DEMO_PASSWORD` is explicitly set. Only use synthetic records in an environment
where the shared demo credentials are enabled.

## Uploads, OCR, and lifecycle

Vercel Function request bodies are limited to 4.5 MB. Deposit360 therefore caps
PDF uploads at 4 MB on Vercel to leave room for multipart form overhead. The
limit is configurable for local development, but increasing it on Vercel will
cause larger requests to be rejected before reaching the API.

Text extraction works for text-based PDFs. Scanned-PDF OCR requires the
Tesseract executable; the Vercel Python runtime does not install it
automatically, so scanned-document OCR remains unavailable unless a compatible
Tesseract binary is added to the deployment.

The serverless API does not run a persistent background process. A secured
Vercel Cron Job invokes the lifecycle refresh daily at 08:00 UTC, which updates
maturity states and queues recurring in-app reminders. Hobby projects can run
cron jobs at most once per day, with up to 59 minutes of scheduling variance.
The authenticated deposits list also refreshes lifecycle states on access.

## Local development and verification

Local development continues to use SQLite and local PDF storage by default.
Set `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` in
`apps/web/.env.local`, and use `STORAGE_BACKEND=local` in `apps/api/.env`.
See the repository README for setup and test commands.

The API's mock bank-verification adapter and log-based email/SMS adapters remain
the defaults. OCR and match scores are not proof of bank authenticity, and no
bank is contacted unless an authorized verification provider is configured.
