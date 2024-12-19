import { useMe } from "@/auth/auth";

export default function DashboardPage() {
  const me = useMe();

  return (
    <main className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">{me.data?.organization_name}</p>
          <h1 className="display">Compliance</h1>
        </div>
      </header>

      <section className="card">
        <div className="card__body">
          <h2 className="subtitle">The roster lands here next</h2>
          <p className="muted small" style={{ marginTop: 6, maxWidth: "62ch" }}>
            This is the shell: authentication works, and every screen after this one builds on the
            same layout.
          </p>
        </div>
      </section>
    </main>
  );
}
