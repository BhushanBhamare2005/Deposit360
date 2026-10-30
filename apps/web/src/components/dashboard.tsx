"use client";

import {
  useCallback,
  useEffect,
  useState,
  type FormEvent,
  type InputHTMLAttributes
} from "react";
import type {
  ComplianceCase,
  DashboardSummary,
  DocumentRecord,
  Institution,
  Instrument,
  User
} from "@deposit360/shared";

import { api, MAX_UPLOAD_SIZE_MB } from "@/lib/api";
import { HelpdeskCopilot } from "@/components/helpdesk-copilot";
import { WorkspaceSidebar } from "@/components/workspace-sidebar";

type DashboardProps = {
  token: string;
  user: User;
  onInstitutionCreated: (institutionId: string) => void;
  onSignOut: () => void;
};

const emptySummary: DashboardSummary = {
  total_instruments: 0,
  active_instruments: 0,
  approaching_maturity: 0,
  total_value: "0",
  open_cases: 0
};

export function Dashboard({ token, user, onInstitutionCreated, onSignOut }: DashboardProps) {
  const [summary, setSummary] = useState(emptySummary);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [cases, setCases] = useState<ComplianceCase[]>([]);
  const [documentsByInstrument, setDocumentsByInstrument] = useState<Record<string, DocumentRecord[]>>({});
  const [extractionText, setExtractionText] = useState("");
  const [institution, setInstitution] = useState<Institution | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [nextSummary, nextInstruments, nextCases] = await Promise.all([
        api.summary(token),
        api.instruments(token),
        api.cases(token)
      ]);
      setError("");
      setSummary(nextSummary);
      setInstruments(nextInstruments.items);
      setCases(nextCases);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load dashboard.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    queueMicrotask(() => {
      void refresh();
    });
    if (user.institution_id) {
      api.getInstitution(token).then(setInstitution).catch(() => setInstitution(null));
    }
  }, [refresh, token, user.institution_id]);

  async function submitInstitution(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const created = await api.createInstitution(token, {
        code: String(form.get("code")),
        name: String(form.get("name")),
        contact_email: String(form.get("contact_email"))
      });
      setInstitution(created);
      onInstitutionCreated(created.id);
      setNotice("Institution created.");
      setError("");
      await refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to create institution.");
    }
  }

  async function submitInstrument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      await api.createInstrument(token, {
        instrument_number: String(form.get("instrument_number")),
        bank_name: String(form.get("bank_name")),
        branch_name: String(form.get("branch_name")) || null,
        holder_name: String(form.get("holder_name")),
        amount: String(form.get("amount")),
        issue_date: String(form.get("issue_date")),
        maturity_date: String(form.get("maturity_date"))
      });
      formElement.reset();
      setNotice("Deposit added.");
      await refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to add deposit.");
    }
  }

  async function submitCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      await api.createCase(
        token,
        String(form.get("instrument_id")),
        String(form.get("title")),
        String(form.get("description"))
      );
      formElement.reset();
      setNotice("Review case created.");
      await refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to create case.");
    }
  }

  async function uploadPdf(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const file = form.get("file");
    if (!(file instanceof File) || file.size === 0) {
      setError("Choose a PDF file to upload.");
      return;
    }
    try {
      const instrumentId = String(form.get("instrument_id"));
      const uploaded = await api.uploadDocument(token, instrumentId, file);
      setDocumentsByInstrument((current) => ({
        ...current,
        [instrumentId]: [uploaded, ...(current[instrumentId] ?? [])]
      }));
      formElement.reset();
      setNotice("PDF uploaded.");
      setError("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to upload PDF.");
    }

  }

  async function loadDocuments(instrumentId: string) {
    try {
      const documents = await api.documents(token, instrumentId);
      setDocumentsByInstrument((current) => ({ ...current, [instrumentId]: documents }));
      setError("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load documents.");
    }
  }

  async function extractPdf(documentId: string) {
    try {
      const result = await api.extractDocument(token, documentId);
      const fieldSummary = result.fields
        .map((field) => `${field.field_name}: ${field.extracted_value}`)
        .join("\n");
      setExtractionText(
        `${result.ocr_used ? "OCR" : "Text extraction"} complete.\n${fieldSummary || "No known fields found."}\n\n${result.text}`
      );
      setError("");
      setNotice("Document extraction completed.");
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "Unable to extract document text."
      );
    }
  }

  async function downloadPdf(instrumentId: string, document: DocumentRecord) {
    try {
      const file = await api.downloadDocument(token, instrumentId, document.id);
      const url = URL.createObjectURL(file);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = document.original_filename;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setError("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to download PDF.");
    }
  }

  return (
    <main className="app-shell">
      <WorkspaceSidebar roles={user.roles} />
      <header className="topbar">
        <div className="account-menu">
          <div>
            <strong>{user.full_name}</strong>
            <span>{institution?.name || user.email}</span>
          </div>
          <button className="button button-quiet" onClick={onSignOut} type="button">
            Sign out
          </button>
        </div>
      </header>

      <section className="page-heading">
        <div>
          <p className="eyebrow">Institution Applicant workspace</p>
          <h1>Deposit dashboard</h1>
          <p className="muted">Submit FDR evidence, track corrections, and follow your release requests.</p>
        </div>
        <span className="date-chip">{new Date().toLocaleDateString()}</span>
      </section>

      {error && <p className="notice notice-error" role="alert">{error}</p>}
      {notice && <p className="notice notice-success" role="status">{notice}</p>}
      {instruments.some((item) => item.instrument_number.startsWith("SYN-")) && (
        <p className="notice" role="note">
          Records prefixed SYN- and generated demo PDFs are fabricated. OCR does not confirm a bank
          deposit or establish document authenticity.
        </p>
      )}

      <section className="metric-grid" aria-label="Portfolio summary">
        <Metric label="Total deposits" value={String(summary.total_instruments)} />
        <Metric label="Active" value={String(summary.active_instruments)} />
        <Metric label="Maturing in 30 days" value={String(summary.approaching_maturity)} />
        <Metric label="Portfolio value" value={formatCurrency(summary.total_value)} />
        <Metric label="Open cases" value={String(summary.open_cases)} />
      </section>

      {!user.institution_id && (
        <section className="panel">
          <SectionHeading title="Set up your institution" detail="Add your institution before registering deposits." />
          <form className="form-grid" onSubmit={submitInstitution}>
            <Field label="Institution name" name="name" required />
            <Field label="Institution code" name="code" required />
            <Field label="Contact email" name="contact_email" type="email" required />
            <button className="button button-primary form-action" type="submit">Create institution</button>
          </form>
        </section>
      )}

      {user.institution_id && (
        <div className="content-grid">
          <section className="panel">
            <SectionHeading title="Add a deposit" detail="Record the details shown on the instrument." />
            <form className="form-grid" onSubmit={submitInstrument}>
              <Field label="Instrument number" name="instrument_number" required />
              <Field label="Bank" name="bank_name" required />
              <Field label="Branch (optional)" name="branch_name" />
              <Field label="Account holder" name="holder_name" required />
              <Field label="Amount" name="amount" type="number" min="0.01" step="0.01" required />
              <Field label="Issue date" name="issue_date" type="date" required />
              <Field label="Maturity date" name="maturity_date" type="date" required />
              <button className="button button-primary form-action" type="submit">Save deposit</button>
            </form>
          </section>
          <section className="panel">
            <SectionHeading title="Create a review case" detail="Flag a deposit for follow-up." />
            <form className="stack-form" onSubmit={submitCase}>
              <label>
                Deposit
                <select name="instrument_id" required disabled={instruments.length === 0}>
                  <option value="">Select a deposit</option>
                  {instruments.map((item) => (
                    <option key={item.id} value={item.id}>{item.instrument_number} · {item.bank_name}</option>
                  ))}
                </select>
              </label>
              <Field label="Case title" name="title" required minLength={3} />
              <label>
                Description
                <textarea name="description" rows={3} minLength={5} required />
              </label>
              <button className="button button-primary" disabled={!instruments.length} type="submit">Create case</button>
            </form>
          </section>
        </div>
      )}

      {user.institution_id && (
        <section className="panel">
          <SectionHeading title="Upload a document" detail={`PDF documents are stored with a checksum for integrity. Maximum size: ${MAX_UPLOAD_SIZE_MB} MB.`} />
          <form className="upload-form" onSubmit={uploadPdf}>
            <select name="instrument_id" required disabled={instruments.length === 0} aria-label="Deposit for document">
              <option value="">Select a deposit</option>
              {instruments.map((item) => (
                <option key={item.id} value={item.id}>{item.instrument_number}</option>
              ))}
            </select>
            <input name="file" type="file" accept="application/pdf,.pdf" required />
            <button className="button button-secondary" disabled={!instruments.length} type="submit">Upload PDF</button>
          </form>
        </section>
      )}

      <section className="panel">
        <SectionHeading title="Deposits" detail={loading ? "Loading records…" : `${instruments.length} shown`} />
        {instruments.length === 0 && !loading ? (
          <p className="empty-state">No deposits yet. Create an institution, then add your first deposit.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Instrument</th><th>Bank</th><th>Amount</th><th>Maturity</th><th>Status</th><th>Documents</th></tr>
              </thead>
              <tbody>
                {instruments.map((item) => (
                  <tr key={item.id}>
                    <td><strong>{item.instrument_number}</strong><span className="cell-subtitle">{item.holder_name}</span></td>
                    <td>{item.bank_name}</td>
                    <td>{formatCurrency(item.amount)}</td>
                    <td>{new Date(`${item.maturity_date}T00:00:00`).toLocaleDateString()}</td>
                    <td><span className={`status-pill status-${item.lifecycle_state}`}>{item.lifecycle_state.replaceAll("_", " ")}</span></td>
                    <td>
                      <button className="button button-quiet" type="button" onClick={() => void loadDocuments(item.id)}>
                        {documentsByInstrument[item.id] ? "Refresh" : "Show"}
                      </button>
                      {documentsByInstrument[item.id]?.map((document) => (
                        <div key={document.id} className="document-actions">
                          <span>{document.original_filename}</span>
                          <button className="text-button" type="button" onClick={() => void downloadPdf(item.id, document)}>
                            Download PDF
                          </button>
                          <button className="text-button" type="button" onClick={() => void extractPdf(document.id)}>
                            Extract fields
                          </button>
                        </div>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {extractionText && (
        <section className="panel">
          <SectionHeading title="Latest document extraction" detail="Check extracted content against the original PDF before relying on it." />
          <pre className="extraction-result">{extractionText}</pre>
        </section>
      )}

      <section className="panel">
        <SectionHeading title="Compliance cases" detail={`${cases.length} total`} />
        {cases.length === 0 ? (
          <p className="empty-state">There are no compliance cases to review.</p>
        ) : (
          <div className="case-list">
            {cases.map((item) => (
              <article className="case-item" key={item.id}>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.description}</p>
                </div>
                <span className={`status-pill status-${item.status}`}>{item.status.replaceAll("_", " ")}</span>
                <div>
                  {item.resolution_note && <p>Request: {item.resolution_note}</p>}
                  {item.status === "changes_requested" && (
                    <button
                      className="button button-secondary"
                      type="button"
                      onClick={() => {
                        void api.resubmitCase(token, item.id)
                          .then(async () => {
                            setNotice("Corrected evidence submitted for review.");
                            await refresh();
                          })
                          .catch((requestError: unknown) => {
                            setError(requestError instanceof Error ? requestError.message : "Unable to resubmit corrections.");
                          });
                      }}
                    >
                      Resubmit corrected documents
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
      <HelpdeskCopilot roles={user.roles} />
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <article className="metric-card"><span>{label}</span><strong>{value}</strong></article>;
}

function SectionHeading({ title, detail }: { title: string; detail: string }) {
  return <div className="section-heading"><div><h2>{title}</h2><p>{detail}</p></div></div>;
}

function Field({
  label,
  name,
  type = "text",
  ...inputProps
}: InputHTMLAttributes<HTMLInputElement> & { label: string; name: string }) {
  return <label>{label}<input name={name} type={type} {...inputProps} /></label>;
}

function formatCurrency(value: number | string) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return String(value);
  return new Intl.NumberFormat(undefined, { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(amount);
}
