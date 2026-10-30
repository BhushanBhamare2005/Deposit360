import Link from "next/link";

type SectionPageProps = {
  title: string;
  description: string;
  reference?: string;
};

export function SectionPage({ title, description, reference }: SectionPageProps) {
  return (
    <main className="app-shell">
      <header className="topbar">
        <Link className="wordmark" href="/">
          <span className="brand-mark brand-mark-small">D</span> Deposit360
        </Link>
      </header>
      <section className="page-heading">
        <div>
          <p className="eyebrow">Workspace</p>
          <h1>{title}</h1>
          <p className="muted">{description}</p>
          {reference && <p className="muted">Reference: {reference}</p>}
        </div>
      </section>
      <section className="panel">
        <p className="muted">
          Use the dashboard to manage your institution, deposits, documents, and cases.
        </p>
        <Link className="button button-primary" href="/">
          Go to dashboard
        </Link>
      </section>
    </main>
  );
}
