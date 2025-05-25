import { useAuditEvents } from "@/api/audit";
import { formatDate } from "@/components/format";
import { Card, EmptyState, Loading } from "@/components/ui";

export default function AuditPage() {
  const events = useAuditEvents();

  return (
    <main className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Audit</p>
          <h1 className="display">Who changed what</h1>
          <p className="muted small">
            Append-only. Rows are written in the same transaction as the change they describe, and
            the database refuses to update or delete them.
          </p>
        </div>
      </header>

      <Card className="card--table">
        {events.isPending ? (
          <Loading label="Loading events…" />
        ) : (events.data ?? []).length === 0 ? (
          <EmptyState title="Nothing yet" body="Changing anything in the app shows up here." />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Who</th>
                  <th>Action</th>
                  <th>Record</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {(events.data ?? []).map((event) => (
                  <tr key={event.id}>
                    <td className="numeric muted">{formatDate(event.created_at.slice(0, 10))}</td>
                    <td>{event.actor_name}</td>
                    <td className="mono small">{event.action}</td>
                    <td className="mono faint small">{event.entity}</td>
                    <td className="faint small">
                      {Object.entries(event.data)
                        .map(([key, value]) => `${key}: ${String(value)}`)
                        .join(" · ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </main>
  );
}
