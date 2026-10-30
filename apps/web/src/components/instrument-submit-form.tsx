"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import type { User } from "@deposit360/shared";
import { api } from "@/lib/api";
import { HelpdeskCopilot } from "@/components/helpdesk-copilot";
import { WorkspaceSidebar } from "@/components/workspace-sidebar";

export function InstrumentSubmitForm() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    const storedToken = window.sessionStorage.getItem("deposit360_token") ?? "";
    queueMicrotask(() => {
      if (active) setToken(storedToken);
    });
    if (!storedToken) {
      queueMicrotask(() => {
        if (active) setReady(true);
      });
      return;
    }
    api.me(storedToken)
      .then((currentUser) => {
        if (active) setUser(currentUser);
      })
      .catch((requestError: unknown) => {
        if (active) setError(requestError instanceof Error ? requestError.message : "Unable to load account.");
      })
      .finally(() => {
        if (active) setReady(true);
      });
    return () => {
      active = false;
    };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    if (!token) {
      setError("Sign in before registering a deposit.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const instrument = await api.createInstrument(token, {
        instrument_number: String(form.get("instrument_number")),
        bank_name: String(form.get("bank_name")),
        branch_name: String(form.get("branch_name")) || null,
        holder_name: String(form.get("holder_name")),
        amount: String(form.get("amount")),
        issue_date: String(form.get("issue_date")),
        maturity_date: String(form.get("maturity_date"))
      });
      router.push(`/lifecycle/${instrument.id}`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to register the deposit.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!ready) return <main className="loading-screen">Loading deposit form…</main>;
  if (!token) {
    return <main className="app-shell"><p className="notice">Sign in to register a deposit. <Link href="/">Go to sign in</Link></p></main>;
  }
  if (!user) {
    return (
      <main className="app-shell">
        <p className="notice notice-error" role="alert">{error || "Your session could not be verified."}</p>
        <Link className="button button-primary" href="/">Sign in again</Link>
      </main>
    );
  }
  if (!user.roles.some((role) => ["institution_applicant", "institution_user"].includes(role))) {
    return (
      <main className="app-shell">
        <p className="notice notice-error" role="alert">
          Only institution applicants can register FDRs. <Link href="/">Return to your dashboard</Link>
        </p>
      </main>
    );
  }
  if (user && !user.institution_id) {
    return <main className="app-shell"><p className="notice">Set up your institution before registering deposits. <Link href="/">Go to dashboard</Link></p></main>;
  }

  return (
    <main className="app-shell">
      <WorkspaceSidebar roles={user.roles} />
      <header className="topbar">
        <div className="account-menu">
          <div><strong>{user.full_name}</strong><span>Institution Applicant</span></div>
        </div>
      </header>
      <section className="page-heading">
        <div><p className="eyebrow">Institution</p><h1>Register a deposit</h1><p className="muted">Enter the details exactly as shown on the deposit instrument.</p></div>
      </section>
      {error && <p className="notice notice-error" role="alert">{error}</p>}
      <section className="panel">
        <form className="form-grid" onSubmit={(event) => void submit(event)}>
          <label>Instrument number<input name="instrument_number" required maxLength={100} /></label>
          <label>Bank<input name="bank_name" required maxLength={200} /></label>
          <label>Branch (optional)<input name="branch_name" maxLength={200} /></label>
          <label>Account holder<input name="holder_name" required maxLength={200} /></label>
          <label>Amount<input name="amount" type="number" min="0.01" step="0.01" required /></label>
          <label>Issue date<input name="issue_date" type="date" required /></label>
          <label>Maturity date<input name="maturity_date" type="date" required /></label>
          <button className="button button-primary form-action" disabled={submitting || !user?.institution_id} type="submit">
            {submitting ? "Saving…" : "Register deposit"}
          </button>
        </form>
      </section>
      <HelpdeskCopilot roles={user.roles} />
    </main>
  );
}
