# Data model

- `users` stores account profiles, password hashes, roles, and the linked
  institution.
- `institutions` owns its registered `instruments`.
- `instruments` stores bank, holder, amount, issue date, maturity date, and
  lifecycle state.
- `documents` stores PDF metadata and a generated storage key for each instrument.
- `compliance_cases` tracks review status and resolution notes per instrument.
- `audit_events` records actor, action, resource, and non-sensitive event details.

The SQLAlchemy models use portable UUID, JSON, decimal, date, and enum columns.
Foreign keys enforce the parent-child relationships. SQLite foreign-key checks
are enabled for local development.

Tables are created at API startup for the initial version. Before production
rollout, adopt Alembic migrations and backup/restore procedures for the selected
database.