# Deposit360 five-role synthetic demo

## Prepare the local demo

Start the API and web app using the local development instructions, then seed the
role-play dataset from `apps/api`:

```powershell
python -m app.demo_seed
```

The seed command creates five role-specific accounts, a synthetic applicant
institution, five FDR records, an explicitly synthetic PDF, extracted demo fields,
compliance rules, sample cases, a mock verification record, and release requests
at both finance-review stages. It is idempotent and does not overwrite existing
demo records.

All five accounts use the local-demo-only password `Demo360-SIH-2026!`:

| Role | Demo email |
|---|---|
| Institution Applicant | `applicant.deposit360@example.com` |
| Scrutiny Officer | `scrutiny.deposit360@example.com` |
| Compliance Administrator | `compliance.deposit360@example.com` |
| Finance Officer | `finance.deposit360@example.com` |
| Approving Authority | `approver.deposit360@example.com` |

These are shared prototype credentials, not production credentials. Do not reuse
the password outside a local demo.

## Demo flow

1. Sign in as the Institution Applicant. Review the submitted FDRs, upload
   corrected evidence for the record returned for changes, and resubmit the case.
2. Sign in as the Scrutiny Officer. Review the open case and extracted fields;
   request corrections or record the scrutiny outcome.
3. Sign in as the Compliance Administrator. Review escalations and rule versions,
   publish a new rule version, and inspect verification evidence.
4. Sign in as the Finance Officer. Review maturity and renewal information, then
   move the submitted release request to `under review` after its financial review.
5. Sign in as the Approving Authority. Inspect the finance-cleared request and
   approve or reject it. A final approval marks the deposit released and records
   the decision in the audit trail.

## Synthetic-data and verification boundaries

The demo uses familiar Indian bank names to make the workflow recognizable, but
all account holders, FDR identifiers, branches, dates, and amounts are fabricated.
The generated PDF is labeled **not a bank-issued document** and is not valid for
financial use. OCR confidence and extracted-field matches are review aids only;
they do not prove document or bank authenticity. The mock verification adapter
does not contact a bank. Show a bank-confirmed result only when an authorized bank
verification provider has actually returned it.

Registration creates Institution Applicant accounts only. Staff roles are
provisioned separately for the local demo, and API authorization independently
enforces role-specific workflow permissions.
