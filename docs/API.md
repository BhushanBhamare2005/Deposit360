# API overview

Base path: `/api/v1`. Interactive API documentation is available at `/docs`.

## Authentication

- `POST /auth/register` — create an institution user.
- `POST /auth/login` — return a bearer access token.
- `GET /users/me` — current account profile.

Pass tokens in the `Authorization: Bearer <token>` header.

## Institutions and deposits

- `POST /institutions` — create and link an institution to the current account.
- `GET /institutions/me` — read the linked institution.
- `POST /instruments` — register a deposit for the linked institution.
- `GET /instruments` — list deposits; supports `offset` and `limit`.
- `GET /instruments/{instrument_id}` — read a deposit.
- `POST /instruments/{instrument_id}/documents` — upload a PDF.
- `GET /instruments/{instrument_id}/documents` — list document metadata.
- `GET /instruments/{instrument_id}/documents/{document_id}/download` — download an
  authorized PDF.

## Compliance and dashboard

- `POST /cases/instruments/{instrument_id}` — create a review case.
- `GET /cases` — list cases; accepts an optional `status` filter.
- `PATCH /cases/{case_id}` — update case status, reviewer-only.
- `GET /dashboard/summary` — portfolio counts and value.
- `GET /audit` — recent audit records, admin/auditor-only.

All authenticated queries are scoped to the user's institution unless the account
has an administrative, scrutiny, or auditor role. The API returns validation and
authorization errors instead of silently accepting invalid data.