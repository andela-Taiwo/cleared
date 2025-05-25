import { useComplianceReport } from "@/api/reports";
import { formatDate, titleCase } from "@/components/format";
import { Badge, Card, EmptyState, Loading } from "@/components/ui";

export default function ReportsPage() {
  const report = useComplianceReport();

  if (report.isPending) {
    return (
      <main className="page">
        <Loading label="Building the report…" />
      </main>
    );
  }

  if (report.isError || !report.data) {
    return (
      <main className="page">
        <EmptyState title="The report did not load" body="Refresh to try again." />
      </main>
    );
  }

  const data = report.data;

  return (
    <main className="page report">
      <header className="page-header">
        <div>
          <p className="eyebrow">Reports</p>
          <h1 className="display">Compliance report</h1>
          <p className="muted small">
            {data.organization_name} · generated {formatDate(data.generated_on)} · {data.total}{" "}
            people
          </p>
        </div>

        <div className="row no-print">
          <a className="btn" href="/v1/reports/compliance.csv">
            Download CSV
          </a>
          <button className="btn btn--primary" type="button" onClick={() => window.print()}>
            Print
          </button>
        </div>
      </header>

      <Card className="card--table">
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Employee</th>
                <th>Role</th>
                <th>Status</th>
                <th>Compliance</th>
                <th className="numeric">Ready</th>
                <th className="numeric">Expired</th>
                <th className="numeric">Expiring</th>
                <th className="numeric">Missing</th>
                <th className="numeric">Unverified</th>
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row) => (
                <tr key={`${row.employee_no}-${row.last_name}`}>
                  <td>
                    <div>
                      {row.last_name}, {row.first_name}
                    </div>
                    <div className="faint mono small">{row.employee_no}</div>
                  </td>
                  <td>{row.role}</td>
                  <td className="muted">{row.status}</td>
                  <td>
                    <Badge
                      tone={
                        row.state === "compliant"
                          ? "ok"
                          : row.state === "at_risk"
                            ? "warn"
                            : "danger"
                      }
                    >
                      {titleCase(row.state)}
                    </Badge>
                  </td>
                  <td className="numeric">{row.readiness}%</td>
                  <td className="numeric">{row.expired || ""}</td>
                  <td className="numeric">{row.expiring || ""}</td>
                  <td className="numeric">{row.missing || ""}</td>
                  <td className="numeric">{row.unverified || ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <p className="report__footnote">
        Produced by Cleared. States are computed from the agency's requirement matrix on{" "}
        {formatDate(data.generated_on)}.
      </p>
    </main>
  );
}
