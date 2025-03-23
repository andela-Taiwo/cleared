import { Link } from "react-router-dom";

import { useOverview } from "@/api/compliance";
import { formatDate, formatDays } from "@/components/format";
import { Badge, Card, EmptyState, Loading } from "@/components/ui";

function percent(part: number, whole: number): number {
  if (whole === 0) return 0;
  return Math.round((100 * part) / whole);
}

export default function DashboardPage() {
  const overview = useOverview();

  if (overview.isPending) {
    return (
      <main className="page">
        <Loading label="Reading the roster…" />
      </main>
    );
  }

  if (overview.isError || !overview.data) {
    return (
      <main className="page">
        <EmptyState title="The overview did not load" body="Refresh to try again." />
      </main>
    );
  }

  const data = overview.data;
  const compliant = data.states.compliant ?? 0;
  const atRisk = data.states.at_risk ?? 0;
  const blocked = data.states.non_compliant ?? 0;

  return (
    <main className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Today</p>
          <h1 className="display">Compliance</h1>
          <p className="muted small">
            {data.total} people on the roster. {compliant} can be deployed without a question.
          </p>
        </div>
        <Link className="btn" to="/employees">
          Open the roster
        </Link>
      </header>

      <section className="kpis">
        <Card className="kpi">
          <p className="eyebrow">Fully compliant</p>
          <p className="kpi__value numeric">{percent(compliant, data.total)}%</p>
          <p className="kpi__note">
            {compliant} of {data.total} people
          </p>
          <div className="meter meter--kpi" aria-hidden="true">
            <span className="meter__fill" style={{ width: `${percent(compliant, data.total)}%` }} />
          </div>
        </Card>

        <Card className="kpi">
          <p className="eyebrow">Cannot be deployed</p>
          <p className="kpi__value numeric kpi__value--danger">{blocked}</p>
          <p className="kpi__note">expired or missing evidence</p>
        </Card>

        <Card className="kpi">
          <p className="eyebrow">At risk</p>
          <p className="kpi__value numeric kpi__value--warn">{atRisk}</p>
          <p className="kpi__note">expiring or unverified</p>
        </Card>

        <Card className="kpi">
          <p className="eyebrow">Expiring</p>
          <p className="kpi__value numeric">{data.expiring.within_7 ?? 0}</p>
          <p className="kpi__note">
            in 7 days · {data.expiring.within_30 ?? 0} in 30 · {data.expiring.within_60 ?? 0} in 60
          </p>
        </Card>
      </section>

      <div className="dash-grid">
        <Card>
          <div className="card__header">
            <h2 className="subtitle">Next 60 days</h2>
            <span className="muted small">renewals a coordinator has to book</span>
          </div>

          {data.upcoming.length === 0 ? (
            <EmptyState
              title="Nothing expiring"
              body="No credential in the next two months. That is unusual — enjoy it."
            />
          ) : (
            <ul className="timeline">
              {data.upcoming.map((item) => (
                <li
                  className="timeline__item"
                  key={`${item.employee_id}-${item.credential_type_name}`}
                >
                  <span
                    className={`timeline__dot timeline__dot--${item.state}`}
                    aria-hidden="true"
                  />
                  <div className="timeline__main">
                    <Link to={`/employees/${item.employee_id}`}>{item.employee_name}</Link>
                    <span className="muted small"> · {item.credential_type_name}</span>
                  </div>
                  <div className="timeline__side">
                    <span className="numeric small">{formatDate(item.expires_on)}</span>
                    <Badge tone={item.days_left <= 7 ? "danger" : "warn"}>
                      {formatDays(item.days_left)}
                    </Badge>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <div className="card__header">
            <h2 className="subtitle">By role</h2>
          </div>
          <div className="card__body stack-sm">
            {data.roles.map((role) => (
              <div className="role-row" key={role.job_role_id ?? role.role_name}>
                <div className="row-between">
                  <span className="role-row__name">{role.role_name}</span>
                  <span className="muted small numeric">
                    {role.compliant}/{role.total}
                  </span>
                </div>
                <div className="stacked-bar" aria-hidden="true">
                  <span
                    className="stacked-bar__part stacked-bar__part--ok"
                    style={{ width: `${percent(role.compliant, role.total)}%` }}
                  />
                  <span
                    className="stacked-bar__part stacked-bar__part--warn"
                    style={{ width: `${percent(role.at_risk, role.total)}%` }}
                  />
                  <span
                    className="stacked-bar__part stacked-bar__part--danger"
                    style={{ width: `${percent(role.non_compliant, role.total)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </main>
  );
}
