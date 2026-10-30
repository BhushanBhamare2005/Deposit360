"use client";

type ErrorPageProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  return (
    <main className="loading-screen">
      <section className="auth-card">
        <p className="eyebrow">Something went wrong</p>
        <h1>We could not load this page.</h1>
        <p className="muted">{error.message}</p>
        <button className="button button-primary" onClick={reset} type="button">
          Try again
        </button>
      </section>
    </main>
  );
}