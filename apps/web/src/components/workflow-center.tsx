"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";

import type {
  AuditEvent,
  ComplianceCase,
  DocumentRecord,
  Instrument,
  Notification,
  ReleaseRequest,
  RenewalLink,
  User,
  VerificationCheck
} from "@deposit360/shared";
import { api } from "@/lib/api";
import { HelpdeskCopilot } from "@/components/helpdesk-copilot";
import { WorkspaceSidebar } from "@/components/workspace-sidebar";

type WorkflowMode =
  | "scrutiny"
  | "audit"
  | "renewals"
  | "releases"
  | "notifications"
  | "lifecycle"
  | "my-submissions";

function canAccessMode(mode: WorkflowMode, roles: string[]) {
  const has = (...allowed: string[]) => roles.some((role) => allowed.includes(role));
  switch (mode) {
    case "scrutiny":
      return has("scrutiny_officer", "compliance_administrator", "admin");
    case "audit":
      return has("compliance_administrator", "approving_authority", "auditor", "admin");
    case "renewals":
      return has("institution_applicant", "institution_user", "finance_officer", "admin");
    case "releases":
      return has(
        "institution_applicant",
        "institution_user",
        "finance_officer",
        "approving_authority",
        "admin"
      );
    case "notifications":
      return roles.length > 0;
    case "lifecycle":
      return has(
        "institution_applicant",
        "institution_user",
        "scrutiny_officer",
        "compliance_administrator",
        "finance_officer",
        "approving_authority",
        "auditor",
        "admin"
      );
    case "my-submissions":
      return has("institution_applicant", "institution_user");
  }
}

const headings: Record<WorkflowMode, { title: string; description: string }> = {
  scrutiny: {
    title: "Scrutiny queue",
    description: "Review extracted evidence, request corrections, and record a documented case decision."
  },
  audit: {
    title: "Audit trail",
    description: "Review a chronological record of administrative and workflow actions."
  },
  renewals: {
    title: "Renewals",
    description: "Link a maturing deposit to its replacement and review existing links."
  },
  releases: {
    title: "Release requests",
    description: "Applicants submit requests, finance reviews them, and an approving authority records the final decision."
  },
  notifications: {
    title: "Notifications",
    description: "View and acknowledge in-app workflow notifications."
  },
  lifecycle: {
    title: "Deposit lifecycle",
    description: "Review deposits, maturity status, documents, and follow-up actions."
  },
  "my-submissions": {
    title: "My submissions",
    description: "Review deposits and supporting documents submitted by your institution."
  }
};

function requestError(error: unknown): string {
  return error instanceof Error ? error.message : "The request could not be completed.";
}

function instrumentName(instruments: Instrument[], id: string): string {
  const instrument = instruments.find((item) => item.id === id);
  return instrument?.instrument_number ?? id;
}

export function WorkflowCenter({
  mode,
  recordId
}: {
  mode: WorkflowMode;
  recordId?: string;
}) {
  const [token, setToken] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [cases, setCases] = useState<ComplianceCase[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [renewals, setRenewals] = useState<RenewalLink[]>([]);
  const [releases, setReleases] = useState<ReleaseRequest[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [selectedDeposit, setSelectedDeposit] = useState<Instrument | null>(null);
  const [checks, setChecks] = useState<VerificationCheck[]>([]);
  const [selectedInstrument, setSelectedInstrument] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const reviewer = Boolean(
    user?.roles.some((role) =>
      ["admin", "scrutiny_officer", "compliance_administrator"].includes(role)
    )
  );
  const applicant = Boolean(
    user?.roles.some((role) => ["institution_applicant", "institution_user"].includes(role))
  );
  const financeReviewer = Boolean(user?.roles.includes("finance_officer"));
  const approvingAuthority = Boolean(user?.roles.includes("approving_authority"));
  const complianceAdministrator = Boolean(
    user?.roles.some((role) => ["admin", "compliance_administrator"].includes(role))
  );
  const pageHeading = recordId
    ? {
        title:
          mode === "scrutiny"
            ? "Review case"
            : mode === "releases"
              ? "Release request"
              : mode === "lifecycle"
                ? "Deposit details"
                : "Audit event",
        description: headings[mode].description
      }
    : headings[mode];
  const visibleCases = recordId ? cases.filter((item) => item.id === recordId) : cases;
  const visibleAuditEvents = recordId
    ? auditEvents.filter((item) => item.id === recordId)
    : auditEvents;
  const visibleReleases = recordId
    ? releases.filter((item) => item.id === recordId)
    : releases;

  const refresh = useCallback(async (accessToken: string) => {
    try {
      const currentUser = await api.me(accessToken);
      setUser(currentUser);
      if (!canAccessMode(mode, currentUser.roles)) {
        throw new Error("Your role does not have access to this workflow.");
      }
      if (mode === "scrutiny") {
        const [nextCases, nextInstruments] = await Promise.all([
          recordId ? api.case(accessToken, recordId).then((item) => [item]) : api.cases(accessToken),
          api.instruments(accessToken)
        ]);
        setCases(nextCases);
        setInstruments(nextInstruments.items);
      } else if (mode === "audit") {
        setAuditEvents(
          recordId
            ? [await api.auditEvent(accessToken, recordId)]
            : await api.audit(accessToken)
        );
      } else if (mode === "renewals") {
        const [nextRenewals, nextInstruments] = await Promise.all([
          api.renewals(accessToken),
          api.instruments(accessToken)
        ]);
        setRenewals(nextRenewals);
        setInstruments(nextInstruments.items);
      } else if (mode === "releases") {
        const [nextReleases, nextInstruments] = await Promise.all([
          recordId
            ? api.release(accessToken, recordId).then((item) => [item])
            : api.releases(accessToken),
          api.instruments(accessToken)
        ]);
        setReleases(nextReleases);
        setInstruments(nextInstruments.items);
        if (recordId && nextReleases[0]) {
          const deposit = await api.instrument(accessToken, nextReleases[0].instrument_id);
          setSelectedDeposit(deposit);
          setDocuments(await api.documents(accessToken, deposit.id));
        }
      } else if (mode === "lifecycle" || mode === "my-submissions") {
        if (recordId) {
          const deposit = await api.instrument(accessToken, recordId);
          setSelectedDeposit(deposit);
          setInstruments([deposit]);
          setDocuments(await api.documents(accessToken, recordId));
        } else {
          const nextInstruments = await api.instruments(accessToken);
          setSelectedDeposit(null);
          setInstruments(nextInstruments.items);
        }
      } else {
        setNotifications(await api.notifications(accessToken));
      }
      setError("");
    } catch (loadError) {
      setError(requestError(loadError));
    } finally {
      setLoading(false);
    }
  }, [mode, recordId]);

  useEffect(() => {
    const storedToken = window.sessionStorage.getItem("deposit360_token") ?? "";
    if (!storedToken) {
      queueMicrotask(() => setLoading(false));
      return;
    }
    queueMicrotask(() => {
      setToken(storedToken);
      void refresh(storedToken);
    });
  }, [refresh]);

  useEffect(() => {
    if (!token || mode !== "scrutiny" || !selectedInstrument) return;
    let active = true;
    api.verifications(token, selectedInstrument)
      .then((items) => {
        if (active) setChecks(items);
      })
      .catch((loadError: unknown) => {
        if (active) setError(requestError(loadError));
      });
    return () => {
      active = false;
    };
  }, [mode, selectedInstrument, token]);

  async function perform(action: () => Promise<void>, successMessage: string) {
    setWorking(true);
    setError("");
    setNotice("");
    try {
      await action();
      setNotice(successMessage);
      if (token) await refresh(token);
    } catch (actionError) {
      setError(requestError(actionError));
    } finally {
      setWorking(false);
    }
  }

  async function submitRenewal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await perform(
      async () => {
        await api.createRenewal(
          token,
          String(form.get("previous_instrument_id")),
          String(form.get("replacement_instrument_id"))
        );
        formElement.reset();
      },
      "Renewal recorded."
    );
  }

  async function submitRelease(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await perform(async () => {
      await api.createRelease(
        token,
        String(form.get("instrument_id")),
        String(form.get("justification"))
      );
      formElement.reset();
    }, "Release request submitted.");
  }

  async function extractDocument(documentId: string) {
    setWorking(true);
    setError("");
    setNotice("");
    try {
      const result = await api.extractDocument(token, documentId);
      const extracted = result.fields
        .map((field) => `${field.field_name}: ${field.extracted_value}`)
        .join("; ");
      setNotice(
        `${result.ocr_used ? "OCR" : "Text extraction"} completed. ` +
          (extracted || "No known fields were identified.")
      );
    } catch (actionError) {
      setError(requestError(actionError));
    } finally {
      setWorking(false);
    }
  }

  if (!token) {
    return (
      <main className="app-shell">
        <p className="notice">Sign in to access this workflow. <Link href="/">Go to sign in</Link></p>
      </main>
    );
  }

  if (user && !canAccessMode(mode, user.roles)) {
    return (
      <main className="app-shell">
        <p className="notice notice-error" role="alert">
          This workflow is not available to your role. <Link href="/">Return to your dashboard</Link>
        </p>
      </main>
    );
  }

  return (
    <main className="app-shell">
      {user && <WorkspaceSidebar roles={user.roles} />}
      <header className="topbar">
        <div className="account-menu">
          <div>
            <strong>{user?.full_name ?? "Loading account…"}</strong>
            <span>{user?.roles.join(", ")}</span>
          </div>
        </div>
      </header>

      <section className="page-heading">
        <div>
          <p className="eyebrow">Workflow</p>
          <h1>{pageHeading.title}</h1>
          <p className="muted">{pageHeading.description}</p>
        </div>
      </section>

      {error && <p className="notice notice-error" role="alert">{error}</p>}
      {notice && <p className="notice notice-success" role="status">{notice}</p>}
      {loading ? <p className="panel muted">Loading workflow…</p> : null}

      {mode === "scrutiny" && !loading && (
        <>
          <section className="panel">
            <div className="section-heading">
              <div><h2>Compliance cases</h2><p>Review and record a decision for each open case.</p></div>
            </div>
            {visibleCases.length === 0 ? <p className="empty-state">No compliance cases found for this reference.</p> : (
              <div className="case-list">
                {visibleCases.map((item) => (
                  <article className="case-item" key={item.id}>
                    <div>
                      <strong>{item.title} · {instrumentName(instruments, item.instrument_id)}</strong>
                      {!recordId && <Link className="cell-subtitle" href={`/scrutiny/${item.id}`}>Open case</Link>}
                      {recordId && <Link className="cell-subtitle" href={`/lifecycle/${item.instrument_id}`}>Review deposit evidence</Link>}
                      <p>{item.description}</p>
                      <span className={`status-pill status-${item.status}`}>{item.status.replaceAll("_", " ")}</span>
                      {item.resolution_note && <p>Review note: {item.resolution_note}</p>}
                    </div>
                    {reviewer && ["open", "in_review"].includes(item.status) && (
                      <form onSubmit={(event) => {
                        event.preventDefault();
                        const form = new FormData(event.currentTarget);
                        void perform(
                          async () => {
                            await api.reviewCase(token, item.id,
                              String(form.get("status")) as ComplianceCase["status"],
                              String(form.get("resolution_note")));
                          },
                          "Case decision saved."
                        );
                      }}>
                        <select name="status" aria-label="Case decision" defaultValue={item.status === "open" ? "in_review" : "approved"}>
                          {item.status === "open" && <option value="in_review">Move to review</option>}
                          <option value="changes_requested">Request corrections</option>
                          <option value="approved">Approve</option>
                          <option value="rejected">Reject</option>
                        </select>
                        <input name="resolution_note" aria-label="Review note" placeholder="Review note (optional)" />
                        <button className="button button-primary" disabled={working} type="submit">Save decision</button>
                      </form>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="panel">
            <div className="section-heading">
              <div><h2>Bank verification</h2><p>OCR and matching are not proof of authenticity. Only an authorized bank channel can confirm an FDR.</p></div>
            </div>
            <label>
              Deposit
              <select value={selectedInstrument} onChange={(event) => {
                setChecks([]);
                setSelectedInstrument(event.target.value);
              }}>
                <option value="">Select a deposit</option>
                {instruments.map((item) => <option key={item.id} value={item.id}>{item.instrument_number} · {item.bank_name}</option>)}
              </select>
            </label>
            {selectedInstrument && (
              <>
                {complianceAdministrator && <button className="button button-secondary" disabled={working} type="button" onClick={() => {
                  void perform(async () => {
                    await api.verifyInstrument(token, selectedInstrument);
                    setChecks(await api.verifications(token, selectedInstrument));
                  }, "Verification request recorded. Review the provider response and evidence.");
                }}>Request verification</button>}
                <div className="case-list">
                  {checks.map((check) => (
                    <article className="case-item" key={check.id}>
                      <div>
                        <strong>{check.source} · {check.status.replaceAll("_", " ")}</strong>
                        <p>{check.evidence_note}</p>
                      </div>
                      {complianceAdministrator && check.status === "unable_to_verify" && (
                        <form onSubmit={(event) => {
                          event.preventDefault();
                          const form = new FormData(event.currentTarget);
                          void perform(async () => {
                            await api.reviewVerification(token, check.id,
                              String(form.get("status")) as VerificationCheck["status"],
                              String(form.get("evidence_note")));
                            setChecks(await api.verifications(token, selectedInstrument));
                          }, "Verification evidence recorded.");
                        }}>
                          <select name="status" aria-label="Verification result" defaultValue="confirmed">
                            <option value="confirmed">Confirm</option>
                            <option value="failed">Mark failed</option>
                          </select>
                          <input name="evidence_note" aria-label="Verification evidence" required minLength={5} placeholder="Evidence reference" />
                          <button className="button button-primary" disabled={working} type="submit">Record evidence</button>
                        </form>
                      )}
                    </article>
                  ))}
                </div>
              </>
            )}
          </section>
        </>
      )}

      {mode === "audit" && !loading && (
        <section className="panel">
          <div className="table-wrap">
            <table>
              <thead><tr><th>Time</th><th>Action</th><th>Resource</th><th>Actor</th><th>Details</th></tr></thead>
              <tbody>{visibleAuditEvents.map((event) => (
                <tr key={event.id}>
                  <td>{new Date(event.created_at).toLocaleString()}</td>
                  <td>{recordId ? event.action : <Link href={`/audit/${event.id}`}>{event.action}</Link>}</td>
                  <td>{event.resource_type} · {event.resource_id}</td>
                  <td>{event.actor_id ?? "System"}</td>
                  <td>{JSON.stringify(event.details)}</td>
                </tr>
              ))}</tbody>
            </table>
            {visibleAuditEvents.length === 0 && <p className="empty-state">No audit record found for this reference.</p>}
          </div>
        </section>
      )}

      {mode === "renewals" && !loading && (
        <>
          {applicant && <section className="panel">
            <div className="section-heading"><div><h2>Record renewal</h2><p>Select the original deposit and its replacement.</p></div></div>
            <form className="form-grid" onSubmit={(event) => void submitRenewal(event)}>
              <label>Previous deposit<select name="previous_instrument_id" required defaultValue=""><option value="" disabled>Select deposit</option>{instruments.map((item) => <option key={item.id} value={item.id}>{item.instrument_number}</option>)}</select></label>
              <label>Replacement deposit<select name="replacement_instrument_id" required defaultValue=""><option value="" disabled>Select deposit</option>{instruments.map((item) => <option key={item.id} value={item.id}>{item.instrument_number}</option>)}</select></label>
              <button className="button button-primary form-action" disabled={working || instruments.length < 2} type="submit">Record renewal</button>
            </form>
          </section>}
          <section className="panel">
            <h2>Renewal history</h2>
            {renewals.length === 0 ? <p className="empty-state">No renewal links recorded.</p> : (
              <div className="case-list">{renewals.map((link) => (
                <article className="case-item" key={link.id}>
                  <div><strong>{instrumentName(instruments, link.previous_instrument_id)} → {instrumentName(instruments, link.replacement_instrument_id)}</strong><p>Recorded {new Date(link.created_at).toLocaleDateString()}</p></div>
                  <span className="status-pill">{link.status}</span>
                </article>
              ))}</div>
            )}
          </section>
        </>
      )}

      {mode === "releases" && !loading && (
        <>
          {!recordId && applicant && (
            <section className="panel">
              <div className="section-heading"><div><h2>Request a release</h2><p>Provide a reason for releasing the deposit.</p></div></div>
              <form className="form-grid" onSubmit={(event) => void submitRelease(event)}>
                <label>Deposit<select name="instrument_id" required defaultValue=""><option value="" disabled>Select deposit</option>{instruments.map((item) => <option key={item.id} value={item.id}>{item.instrument_number} · {item.lifecycle_state}</option>)}</select></label>
                <label>Justification<textarea name="justification" required minLength={10} maxLength={2000} /></label>
                <button className="button button-primary form-action" disabled={working || instruments.length === 0} type="submit">Submit request</button>
              </form>
            </section>
          )}
          <section className="panel">
            <h2>Release queue</h2>
            {visibleReleases.length === 0 ? <p className="empty-state">No release requests found for this reference.</p> : (
              <div className="case-list">{visibleReleases.map((item) => (
                <article className="case-item" key={item.id}>
                  <div>
                    <strong>{instrumentName(instruments, item.instrument_id)}</strong>
                    {!recordId && <Link className="cell-subtitle" href={`/releases/${item.id}`}>Open request</Link>}
                    <p>{item.justification}</p>
                    {item.review_note && <p>Review note: {item.review_note}</p>}
                    <span className={`status-pill status-${item.status}`}>{item.status.replaceAll("_", " ")}</span>
                  </div>
                  {((financeReviewer && item.status === "submitted") ||
                    (approvingAuthority && item.status === "under_review") ||
                    (user?.roles.includes("admin") && ["submitted", "under_review"].includes(item.status))) && (
                    <form onSubmit={(event) => {
                      event.preventDefault();
                      const form = new FormData(event.currentTarget);
                      void perform(async () => {
                        await api.reviewRelease(token, item.id,
                          String(form.get("status")) as ReleaseRequest["status"],
                          String(form.get("review_note")));
                      }, "Release review saved.");
                    }}>
                      <select name="status" aria-label="Release decision" defaultValue={financeReviewer ? "under_review" : "approved"}>
                        {(financeReviewer || user?.roles.includes("admin")) && item.status === "submitted" && <option value="under_review">Finance cleared — send for final approval</option>}
                        {(approvingAuthority || user?.roles.includes("admin")) && item.status === "under_review" && <option value="approved">Approve and release</option>}
                        {(approvingAuthority || user?.roles.includes("admin")) && item.status === "under_review" && <option value="rejected">Reject final request</option>}
                        {user?.roles.includes("admin") && item.status === "submitted" && <option value="approved">Approve and release</option>}
                        {user?.roles.includes("admin") && item.status === "submitted" && <option value="rejected">Reject</option>}
                      </select>
                      <input name="review_note" aria-label="Review note" placeholder={financeReviewer ? "Finance review note (optional)" : "Final decision note (optional)"} />
                      <button className="button button-primary" disabled={working} type="submit">{financeReviewer ? "Send for approval" : "Record final decision"}</button>
                    </form>
                  )}
                </article>
              ))}</div>
            )}
            {recordId && selectedDeposit && (
              <section className="panel">
                <h3>Deposit evidence · {selectedDeposit.instrument_number}</h3>
                <dl className="detail-grid">
                  <div><dt>Bank</dt><dd>{selectedDeposit.bank_name}</dd></div>
                  <div><dt>Holder</dt><dd>{selectedDeposit.holder_name}</dd></div>
                  <div><dt>Principal</dt><dd>{selectedDeposit.amount}</dd></div>
                  <div><dt>Maturity date</dt><dd>{selectedDeposit.maturity_date}</dd></div>
                </dl>
                {documents.length === 0 ? <p className="empty-state">No supporting documents are attached.</p> : (
                  <div className="case-list">{documents.map((document) => (
                    <article className="case-item" key={document.id}>
                      <div><strong>{document.original_filename}</strong><p>{document.size_bytes} bytes · {document.status}</p></div>
                      <button className="button button-quiet" disabled={working} type="button" onClick={() => {
                        void api.downloadDocument(token, selectedDeposit.id, document.id)
                          .then((file) => {
                            const url = URL.createObjectURL(file);
                            const anchor = window.document.createElement("a");
                            anchor.href = url;
                            anchor.download = document.original_filename;
                            anchor.click();
                            window.setTimeout(() => URL.revokeObjectURL(url), 1000);
                          })
                          .catch((actionError: unknown) => setError(requestError(actionError)));
                      }}>Download evidence</button>
                    </article>
                  ))}</div>
                )}
              </section>
            )}
          </section>
        </>
      )}

      {mode === "notifications" && !loading && (
        <section className="panel">
          <h2>Recent notifications</h2>
          {notifications.length === 0 ? <p className="empty-state">No notifications to display.</p> : (
            <div className="case-list">{notifications.map((item) => (
              <article className="case-item" key={item.id}>
                <div><strong>{item.subject}</strong><p>{item.body}</p><span className={`status-pill status-${item.status}`}>{item.status}</span><span className="cell-subtitle">{new Date(item.created_at).toLocaleString()}</span></div>
                {item.status !== "acknowledged" && <button className="button button-secondary" disabled={working} type="button" onClick={() => {
                  void perform(async () => {
                    await api.acknowledgeNotification(token, item.id);
                  }, "Notification acknowledged.");
                }}>Acknowledge</button>}
              </article>
            ))}</div>
          )}
        </section>
      )}

      {(mode === "lifecycle" || mode === "my-submissions") && !loading && (
        <section className="panel">
          {selectedDeposit ? (
            <>
              <div className="section-heading">
                <div>
                  <h2>{selectedDeposit.instrument_number}</h2>
                  <p>{selectedDeposit.bank_name} · {selectedDeposit.holder_name}</p>
                </div>
                <span className={`status-pill status-${selectedDeposit.lifecycle_state}`}>
                  {selectedDeposit.lifecycle_state.replaceAll("_", " ")}
                </span>
              </div>
              <dl className="detail-grid">
                <div><dt>Amount</dt><dd>{selectedDeposit.amount}</dd></div>
                <div><dt>Issue date</dt><dd>{selectedDeposit.issue_date}</dd></div>
                <div><dt>Maturity date</dt><dd>{selectedDeposit.maturity_date}</dd></div>
                <div><dt>Branch</dt><dd>{selectedDeposit.branch_name || "Not recorded"}</dd></div>
              </dl>
              <p><Link className="button button-secondary" href="/releases">Release requests</Link></p>
              <h2>Documents</h2>
              {documents.length === 0 ? <p className="empty-state">No documents uploaded.</p> : (
                <div className="case-list">{documents.map((document) => (
                  <article className="case-item" key={document.id}>
                    <div><strong>{document.original_filename}</strong><p>{document.size_bytes} bytes · {document.status}</p></div>
                    <div className="document-actions">
                      <button className="button button-quiet" disabled={working} type="button" onClick={() => {
                        void api.downloadDocument(token, selectedDeposit.id, document.id)
                          .then((file) => {
                            const url = URL.createObjectURL(file);
                            const anchor = window.document.createElement("a");
                            anchor.href = url;
                            anchor.download = document.original_filename;
                            anchor.click();
                            window.setTimeout(() => URL.revokeObjectURL(url), 1000);
                          })
                          .catch((actionError: unknown) => setError(requestError(actionError)));
                      }}>Download PDF</button>
                      {(applicant || reviewer) && <button className="button button-secondary" disabled={working} type="button" onClick={() => void extractDocument(document.id)}>
                        Extract PDF
                      </button>}
                    </div>
                  </article>
                ))}</div>
              )}
            </>
          ) : instruments.length === 0 ? (
            <p className="empty-state">No deposits found. <Link href="/institution/submit">Register a deposit</Link>.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Instrument</th><th>Bank</th><th>Amount</th><th>Maturity</th><th>Lifecycle</th><th>Details</th></tr></thead>
                <tbody>{instruments.map((instrument) => (
                  <tr key={instrument.id}>
                    <td>{instrument.instrument_number}</td>
                    <td>{instrument.bank_name}</td>
                    <td>{instrument.amount}</td>
                    <td>{instrument.maturity_date}</td>
                    <td><span className={`status-pill status-${instrument.lifecycle_state}`}>{instrument.lifecycle_state.replaceAll("_", " ")}</span></td>
                    <td><Link href={`/lifecycle/${instrument.id}`}>Open details</Link></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </section>
      )}
      {user && <HelpdeskCopilot roles={user.roles} />}
    </main>
  );
}
