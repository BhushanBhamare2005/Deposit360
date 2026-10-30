import Link from "next/link";

export default function NotFound() {
  return (
    <main className="loading-screen">
      <section className="auth-card">
        <p className="eyebrow">404</p>
        <h1>Page not found</h1>
        <p className="muted">The page you requested does not exist.</p>
        <Link className="button button-primary" href="/">
          Return to dashboard
        </Link>
      </section>
    </main>
  );
}