"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import type {
  ComplianceCase,
  DashboardSummary,
  Instrument,
  PolicyRule,
  ReleaseRequest,
  RenewalLink,
  User
} from "@deposit360/shared";

import { api } from "@/lib/api";
import { HelpdeskCopilot } from "@/components/helpdesk-copilot";
import { WorkspaceSidebar } from "@/components/workspace-sidebar";

type RoleDashboardProps = {
  token: string;
  user: User;
  onSignOut: () => void;
};

const roleDetails: Record<string, { title: string; description: string }> = {
  scrutiny_officer: {
    title: "Scrutiny dashboard",
    description: "Review submitted FDR evidence, extracted fields, discrepancies, and correction requests."
  },
  compliance_administrator: {
    title: "Compliance dashboard",
    description: "Manage compliance rule versions, verification evidence, and escalated cases."
  },
  admin: {
    title: "Compliance dashboard",
    description: "Manage compliance rule versions, verification evidence, and escalated cases."
  },
  finance_officer: {
    title: "Finance dashboard",
    description: "Review deposit records, maturities, renewals, and release requests before final approval."
  },
  approving_authority: {
    title: "Approving authority dashboard",
    description: "Review finance-cleared evidence and record final release decisions."
  },
  auditor: {
    title: "Read-only audit dashboard",
    description: "Inspect portfolio records and the audit trail without making workflow decisions."
  }
};

function isRole(user: User, ...roles: string[]) {
  return user.roles.some((role) => roles.includes(role));
}

function money(value: number | string) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0
  }).format(Number(value) || 0);
}

function dateLabel(value: string) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-IN");
}

export function RoleDashboard({ token, user, onSignOut }: RoleDashboardProps) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [cases, setCases] = useState<ComplianceCase[]>([]);
  const [releases, setReleases] = useState<ReleaseRequest[]>([]);
  const [renewals, setRenewals] = useState<RenewalLink[]>([]);
  const [rules, setRules] = useState<PolicyRule[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const compliance = isRole(user, "compliance_administrator", "admin");
  const scrutiny = isRole(user, "scrutiny_officer");
  const finance = isRole(user, "finance_officer");
  const authority = isRole(user, "approving_authority");
  const details = roleDetails[user.roles[0]] ?? roleDetails.auditor;

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [nextSummary, nextInstruments] = await Promise.all([
        api.summary(token),
        api.instruments(token)
      ]);
      setSummary(nextSummary);
      setInstruments(nextInstruments.items);
      if (scrutiny || compliance) setCases(await api.cases(token));
      if (finance || authority) setReleases(await api.releases(token));
      if (finance) setRenewals(await api.renewals(token));
      if (compliance) setRules(await api.policyRules(token));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load this dashboard.");
    } finally {
      setLoading(false);
    }
  }, [compliance, finance, scrutiny, authority, token]);

  useEffect(() => {
    queueMicrotask(() => {
      void refresh();
    });
  }, [refresh]);

  async function createRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    let config: Record<string, unknown>;
    try {
      const parsed: unknown = JSON.parse(String(values.get("config")));
      if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
        throw new Error("Rule criteria must be a JSON object.");
      }
      config = parsed as Record<string, unknown>;
    } catch (parseError) {
      setError(parseError instanceof Error ? parseError.message : "Invalid JSON rule criteria.");
      return;
    }

    try {
      await api.createPolicyRule(token, {
        key: String(values.get("key")),
        description: String(values.get("description")),
        config,
        effective_from: String(values.get("effective_from")),
        effective_to: null
      });
      form.reset();
      setNotice("Compliance rule version published.");
      setError("");
      await refresh();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to publish compliance rule.");
    }
  }

  const openCases = cases.filter((item) => ["open", "in_review"].includes(item.status));
  const correctionCases = cases.filter((item) => item.status === "changes_requested");
  const pendingFinance = releases.filter((item) => item.status === "submitted");
  const pendingApproval = releases.filter((item) => item.status === "under_review");

  return (
    <main className="app-shell">
      <WorkspaceSidebar roles={user.roles} />
      <header className="topbar">
        <div className="account-menu">
          <div><strong>{user.full_name}</strong><span>{details.title}</span></div>
          <button className="button button-quiet" onClick={onSignOut} type="button">Sign out</button>
        </div>
      </header>

      <section className="page-heading">
        <div>
          <p className="eyebrow">{details.title}</p>
          <h1>{details.title}</h1>
          <p className="muted">{details.description}</p>
        </div>
        <span className="date-chip">Role-scoped workspace</span>
      </section>

      <p className="notice" role="note">
        Records prefixed SYN- and the generated demo PDF are fabricated. OCR and match results are
        review aids, not proof of authenticity or bank confirmation.
      </p>
      {error && <p className="notice notice-error" role="alert">{error}</p>}
      {notice && <p className="notice notice-success" role="status">{notice}</p>}

      {loading ? <p className="panel muted">Loading role dashboard…</p> : (
        <>
          <section className="metric-grid" aria-label={`${details.title} summary`}>
            <Metric label="FDR records in scope" value={String(summary?.total_instruments ?? 0)} />
            {scrutiny || compliance ? (
              <>
                <Metric label="Open scrutiny cases" value={String(openCases.length)} />
                <Metric label="Correction requests" value={String(correctionCases.length)} />
                {compliance && <Metric label="Active rule versions" value={String(rules.filter((rule) => !rule.effective_to).length)} />}
              </>
            ) : null}
            {finance && (
              <>
                <Metric label="Awaiting finance review" value={String(pendingFinance.length)} />
                <Metric label="Maturing in 30 days" value={String(summary?.approaching_maturity ?? 0)} />
                <Metric label="Renewal records" value={String(renewals.length)} />
              </>
            )}
            {authority && (
              <>
                <Metric label="Awaiting final decision" value={String(pendingApproval.length)} />
                <Metric label="Portfolio value" value={money(summary?.total_value ?? 0)} />
                <Metric label="Active deposits" value={String(summary?.active_instruments ?? 0)} />
              </>
            )}
            {user.roles.includes("auditor") && (
              <>
                <Metric label="Portfolio value" value={money(summary?.total_value ?? 0)} />
                <Metric label="Open cases" value={String(summary?.open_cases ?? 0)} />
                <Metric label="Maturing in 30 days" value={String(summary?.approaching_maturity ?? 0)} />
              </>
            )}
          </section>

          {(scrutiny || compliance) && (
            <section className="panel">
              <div className="section-heading">
                <div><h2>{scrutiny ? "Scrutiny queue" : "Escalated compliance cases"}</h2><p>Review evidence, record discrepancies, and return cases for corrections.</p></div>
                <Link className="button button-secondary" href="/scrutiny">Open case queue</Link>
              </div>
              {cases.length === 0 ? <p className="empty-state">No compliance cases are waiting.</p> : (
                <div className="case-list">
                  {cases.slice(0, 5).map((item) => (
                    <article className="case-item" key={item.id}>
                      <div><strong>{item.title}</strong><p>{item.description}</p></div>
                      <div><span className={`status-pill status-${item.status}`}>{item.status.replaceAll("_", " ")}</span><p><Link href={`/scrutiny/${item.id}`}>Review case</Link></p></div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          )}

          {compliance && (
            <section className="panel">
              <div className="section-heading"><div><h2>Compliance rule versions</h2><p>Publishing a version retires the previous version from the day before its effective date.</p></div></div>
              {rules.length > 0 && (
                <div className="case-list">
                  {rules.map((rule) => (
                    <article className="case-item" key={rule.id}>
                      <div><strong>{rule.key} · v{rule.version}</strong><p>{rule.description}</p><p>Criteria: {JSON.stringify(rule.config)}</p></div>
                      <span className="status-pill">{rule.effective_to ? `Through ${dateLabel(rule.effective_to)}` : `Effective ${dateLabel(rule.effective_from)}`}</span>
                    </article>
                  ))}
                </div>
              )}
              <form className="form-grid" onSubmit={(event) => void createRule(event)}>
                <label>Rule key<input name="key" pattern="[a-z0-9][a-z0-9_.-]*" minLength={2} maxLength={100} required /></label>
                <label>Description<input name="description" minLength={5} maxLength={500} required /></label>
                <label>Effective from<input name="effective_from" type="date" required /></label>
                <label>Criteria JSON<input name="config" defaultValue='{"minimum_document_count":1}' required /></label>
                <button className="button button-primary form-action" type="submit">Publish rule version</button>
              </form>
            </section>
          )}

          {(finance || authority) && (
            <section className="panel">
              <div className="section-heading">
                <div><h2>{finance ? "Finance review queue" : "Final approval queue"}</h2><p>{finance ? "Move checked release requests to the approving authority." : "Only finance-reviewed requests are ready for a final decision."}</p></div>
                <Link className="button button-secondary" href="/releases">{finance ? "Open finance review" : "Open approval queue"}</Link>
              </div>
              {(finance ? pendingFinance : pendingApproval).length === 0 ? (
                <p className="empty-state">No release requests are waiting at this stage.</p>
              ) : (
                <div className="case-list">
                  {(finance ? pendingFinance : pendingApproval).slice(0, 5).map((item) => (
                    <article className="case-item" key={item.id}>
                      <div><strong>{instruments.find((instrument) => instrument.id === item.instrument_id)?.instrument_number ?? item.instrument_id}</strong><p>{item.justification}</p></div>
                      <Link href={`/releases/${item.id}`}>Review request</Link>
                    </article>
                  ))}
                </div>
              )}
            </section>
          )}

          <section className="panel">
            <div className="section-heading"><div><h2>FDR portfolio</h2><p>Synthetic sample records are marked SYN- and are for workflow demonstration only.</p></div></div>
            {instruments.length === 0 ? <p className="empty-state">No FDR records are available. Run the synthetic demo-data seed script.</p> : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Synthetic FDR</th><th>Bank</th><th>Principal</th><th>Issue date</th><th>Maturity</th><th>Lifecycle</th>{scrutiny || compliance || authority ? <th>Evidence</th> : null}</tr></thead>
                  <tbody>{instruments.map((instrument) => (
                    <tr key={instrument.id}>
                      <td><strong>{instrument.instrument_number}</strong><span className="cell-subtitle">{instrument.holder_name}</span></td>
                      <td>{instrument.bank_name}</td>
                      <td>{money(instrument.amount)}</td>
                      <td>{dateLabel(instrument.issue_date)}</td>
                      <td>{dateLabel(instrument.maturity_date)}</td>
                      <td><span className={`status-pill status-${instrument.lifecycle_state}`}>{instrument.lifecycle_state.replaceAll("_", " ")}</span></td>
                      {scrutiny || compliance || authority ? <td><Link href={`/lifecycle/${instrument.id}`}>Open evidence</Link></td> : null}
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
      <HelpdeskCopilot roles={user.roles} />
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <article className="metric-card"><span>{label}</span><strong>{value}</strong></article>;
}
