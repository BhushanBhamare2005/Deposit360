# Deposit360 web app

Next.js client for the Deposit360 API. From the repository root:

```powershell
Copy-Item apps/web/.env.local.example apps/web/.env.local
npm install
npm run dev:web
```

Set `NEXT_PUBLIC_API_URL` to the API's `/api/v1` base URL. The default local value
is `http://localhost:8000/api/v1`; Vercel uses `/api/v1` through the private
service binding. `NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB` controls the browser-side PDF
limit and is set to `4` for Vercel's request-body limit. See the repository
README for API setup.

## End-to-end tests

The Playwright tests run the web app locally and mock API responses in the browser,
so no backend, live service, or credentials are required. From the repository root,
install the Chromium browser once and run the suite:

```powershell
npm install
npm run test:e2e:install --workspace apps/web
npm run test:e2e --workspace apps/web
```

The test runner starts Next.js on `http://127.0.0.1:3100` and uses a deterministic
in-memory API fixture. Tests cover login errors, successful login/session behavior,
registration, and registering a deposit through to its lifecycle details.