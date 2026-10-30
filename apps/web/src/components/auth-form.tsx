"use client";

import { useState, type FormEvent } from "react";
import type { AuthResponse } from "@deposit360/shared";

import { api } from "@/lib/api";
import { HelpdeskCopilot } from "@/components/helpdesk-copilot";

const demoPassword = "Demo360-SIH-2026!";
const demoAccounts = [
  { role: "Institution Applicant", email: "applicant.deposit360@example.com" },
  { role: "Scrutiny Officer", email: "scrutiny.deposit360@example.com" },
  { role: "Compliance Administrator", email: "compliance.deposit360@example.com" },
  { role: "Finance Officer", email: "finance.deposit360@example.com" },
  { role: "Approving Authority", email: "approver.deposit360@example.com" }
];

type AuthFormProps = {
  onAuthenticated: (response: AuthResponse) => void;
};

export function AuthForm({ onAuthenticated }: AuthFormProps) {
  const [registering, setRegistering] = useState(false);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const response = registering
        ? await api.register(email, fullName, password)
        : await api.login(email, password);
      onAuthenticated(response);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to sign in.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="brand-mark">D</div>
        <p className="eyebrow">Deposit360 workspace</p>
        <h1>{registering ? "Create your account" : "Welcome back"}</h1>
        <p className="muted">
          Track deposits, upcoming maturities, documents, and review cases in one place.
        </p>
        <form className="stack-form" onSubmit={submit}>
          {registering && (
            <label>
              Full name
              <input
                autoComplete="name"
                required
                maxLength={200}
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
              />
            </label>
          )}
          <label>
            Email
            <input
              autoComplete="email"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label>
            Password
            <input
              autoComplete={registering ? "new-password" : "current-password"}
              type="password"
              required
              minLength={registering ? 12 : 1}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            {registering && <span className="field-note">Use at least 12 characters.</span>}
          </label>
          {error && <p className="error-message" role="alert">{error}</p>}
          <button className="button button-primary" disabled={submitting} type="submit">
            {submitting ? "Please wait…" : registering ? "Create account" : "Sign in"}
          </button>
        </form>
        {!registering && (
          <section className="demo-login" aria-labelledby="demo-login-heading">
            <h2 id="demo-login-heading">Quick demo login</h2>
            <p className="field-note">Choose a role to fill its demo email and password.</p>
            <div className="demo-role-list">
              {demoAccounts.map((account) => (
                <button
                  className="demo-role-button"
                  key={account.email}
                  onClick={() => {
                    setEmail(account.email);
                    setPassword(demoPassword);
                    setError("");
                  }}
                  type="button"
                >
                  {account.role}
                </button>
              ))}
            </div>
            <p className="field-note">Local prototype accounts only. Click Sign in after choosing a role.</p>
          </section>
        )}
        <p className="auth-switch">
          {registering ? "Already registered?" : "New to Deposit360?"}{" "}
          <button
            className="text-button"
            onClick={() => {
              setRegistering(!registering);
              setError("");
            }}
            type="button"
          >
            {registering ? "Sign in" : "Create an account"}
          </button>
        </p>
      </section>
      <HelpdeskCopilot roles={[]} />
    </main>
  );
}
