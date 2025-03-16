import { type FormEvent, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "@/api/client";
import {
  type CredentialInput,
  useCreateCredential,
  useCredentialTypes,
  useDeleteCredential,
  useEmployeeCredentials,
  useVerifyCredential,
} from "@/api/credentials";
import { useEmployee, useEmployeeCompliance } from "@/api/employees";
import { formatDate, formatDays, titleCase } from "@/components/format";
import { Badge, Card, EmptyState, Field, Loading, statusTone } from "@/components/ui";

type CredentialState = "expired" | "unverified" | "expiring" | "valid" | "missing";

const stateLabels: Record<CredentialState, string> = {
  valid: "Valid",
  expiring: "Expiring",
  expired: "Expired",
  unverified: "Unverified",
  missing: "Not recorded",
};

function stateTone(state: CredentialState) {
  switch (state) {
    case "valid":
      return "ok" as const;
    case "expiring":
      return "warn" as const;
    case "expired":
      return "danger" as const;
    case "unverified":
      return "info" as const;
    default:
      return "neutral" as const;
  }
}

export default function EmployeePage() {
  const { id } = useParams<{ id: string }>();
  const employee = useEmployee(id);
  const compliance = useEmployeeCompliance(id);
  const credentials = useEmployeeCredentials(id);
  const [adding, setAdding] = useState(false);

  if (employee.isPending) {
    return (
      <main className="page">
        <Loading label="Loading…" />
      </main>
    );
  }

  if (employee.isError || !employee.data) {
    return (
      <main className="page">
        <EmptyState
          title="No such employee"
          body="They may have been removed, or belong to another agency."
          action={
            <Link className="btn" to="/employees">
              Back to the roster
            </Link>
          }
        />
      </main>
    );
  }

  const person = employee.data;
  const summary = compliance.data;

  return (
    <main className="page">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/employees">Roster</Link>
        <span aria-hidden="true">/</span>
        <span>{person.last_name}</span>
      </nav>

      <header className="page-header">
        <div>
          <h1 className="display">
            {person.first_name} {person.last_name}
          </h1>
          <p className="muted small">
            {person.job_role?.name ?? "No role assigned"}
            {person.employee_no ? ` · ${person.employee_no}` : ""}
          </p>
        </div>
        <div className="row">
          <Badge tone={statusTone(person.status)}>{person.status}</Badge>
          {summary ? (
            <Badge
              tone={
                summary.state === "compliant"
                  ? "ok"
                  : summary.state === "at_risk"
                    ? "warn"
                    : "danger"
              }
            >
              {titleCase(summary.state)}
            </Badge>
          ) : null}
        </div>
      </header>

      <div className="detail-grid">
        <div className="stack">
          <Card>
            <div className="card__header">
              <h2 className="subtitle">Requirements</h2>
              <span className="muted small numeric">{summary?.readiness ?? 0}% ready</span>
            </div>

            {compliance.isPending ? (
              <Loading label="Working it out…" />
            ) : !summary || summary.items.length === 0 ? (
              <EmptyState
                title="No requirements yet"
                body="This role has no required credentials. Set them in Requirements so this person's readiness means something."
                action={
                  <Link className="btn" to="/requirements">
                    Open requirements
                  </Link>
                }
              />
            ) : (
              <ul className="req-list">
                {summary.items.map((item) => (
                  <li className={`req req--${item.state}`} key={item.credential_type_id}>
                    <div className="req__main">
                      <span className="req__name">{item.credential_type_name}</span>
                      <span className="req__meta">
                        {item.state === "missing"
                          ? "Nothing on file"
                          : `${formatDate(item.expires_on)} · ${formatDays(item.days_left)}`}
                      </span>
                    </div>
                    <Badge tone={stateTone(item.state)}>{stateLabels[item.state]}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <div className="card__header">
              <h2 className="subtitle">Credentials on file</h2>
              <button className="btn btn--sm" type="button" onClick={() => setAdding((v) => !v)}>
                {adding ? "Close" : "Record a credential"}
              </button>
            </div>

            {adding && id ? (
              <AddCredentialForm employeeId={id} onDone={() => setAdding(false)} />
            ) : null}

            {credentials.isPending ? (
              <Loading label="Loading credentials…" />
            ) : (credentials.data ?? []).length === 0 ? (
              <EmptyState
                title="Nothing recorded"
                body="Add the licence, card or test result, with the date it expires."
              />
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Credential</th>
                      <th>Identifier</th>
                      <th>Expires</th>
                      <th>Verified</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {(credentials.data ?? []).map((credential) => (
                      <tr key={credential.id}>
                        <td>
                          <div>{credential.credential_type.name}</div>
                          <div className="faint small">
                            {titleCase(credential.credential_type.category)}
                          </div>
                        </td>
                        <td className="mono muted">{credential.identifier ?? "—"}</td>
                        <td className="numeric">{formatDate(credential.expires_on)}</td>
                        <td>
                          {credential.verified_at ? (
                            <Badge tone="ok">Checked</Badge>
                          ) : (
                            <Badge tone="info">Unverified</Badge>
                          )}
                        </td>
                        <td className="table__actions">
                          {!credential.verified_at && id ? (
                            <VerifyButton employeeId={id} credentialId={credential.id} />
                          ) : null}
                          {id ? (
                            <DeleteButton employeeId={id} credentialId={credential.id} />
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>

        <aside className="stack">
          <Card>
            <div className="card__body stack">
              <div>
                <p className="eyebrow">Readiness</p>
                <div className="readiness">
                  <span className="readiness__value numeric">{summary?.readiness ?? 0}%</span>
                  <div className="meter" aria-hidden="true">
                    <span
                      className={`meter__fill meter__fill--${summary?.state ?? "compliant"}`}
                      style={{ width: `${summary?.readiness ?? 0}%` }}
                    />
                  </div>
                </div>
              </div>
              <dl className="facts">
                <dt>Expired</dt>
                <dd className="numeric">
                  {summary?.items.filter((i) => i.state === "expired").length ?? 0}
                </dd>
                <dt>Expiring soon</dt>
                <dd className="numeric">
                  {summary?.items.filter((i) => i.state === "expiring").length ?? 0}
                </dd>
                <dt>Not recorded</dt>
                <dd className="numeric">
                  {summary?.items.filter((i) => i.state === "missing").length ?? 0}
                </dd>
                <dt>Unverified</dt>
                <dd className="numeric">
                  {summary?.items.filter((i) => i.state === "unverified").length ?? 0}
                </dd>
              </dl>
            </div>
          </Card>

          <Card>
            <div className="card__body stack">
              <p className="eyebrow">Contact</p>
              <dl className="facts">
                <dt>Email</dt>
                <dd>{person.email ?? "—"}</dd>
                <dt>Phone</dt>
                <dd>{person.phone ?? "—"}</dd>
                <dt>Location</dt>
                <dd>{person.location ?? "—"}</dd>
                <dt>Hired</dt>
                <dd>{formatDate(person.hired_on)}</dd>
              </dl>
            </div>
          </Card>
        </aside>
      </div>
    </main>
  );
}

function AddCredentialForm({ employeeId, onDone }: { employeeId: string; onDone: () => void }) {
  const types = useCredentialTypes();
  const create = useCreateCredential(employeeId);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = new FormData(event.currentTarget);

    const input: CredentialInput = {
      credential_type_id: String(form.get("credential_type_id") ?? ""),
      identifier: String(form.get("identifier") ?? "").trim() || undefined,
      issued_on: String(form.get("issued_on") ?? "") || undefined,
      expires_on: String(form.get("expires_on") ?? "") || undefined,
    };

    if (!input.credential_type_id) {
      setError("Choose a credential type.");
      return;
    }

    try {
      await create.mutateAsync(input);
      onDone();
    } catch (cause) {
      setError(
        cause instanceof ApiError ? (cause.problem.detail ?? cause.problem.title) : "Failed",
      );
    }
  }

  return (
    <form className="form-grid form-grid--inset" onSubmit={onSubmit}>
      <Field label="Type" htmlFor="credential_type_id">
        <select className="select" id="credential_type_id" name="credential_type_id" required>
          <option value="">Choose…</option>
          {(types.data ?? []).map((type) => (
            <option key={type.id} value={type.id}>
              {type.name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Identifier" htmlFor="identifier">
        <input className="input" id="identifier" name="identifier" placeholder="Licence number" />
      </Field>
      <Field label="Issued" htmlFor="issued_on">
        <input className="input" id="issued_on" name="issued_on" type="date" />
      </Field>
      <Field label="Expires" htmlFor="expires_on">
        <input className="input" id="expires_on" name="expires_on" type="date" />
      </Field>
      <div className="form-grid__actions">
        {error ? <p className="error-text">{error}</p> : null}
        <button className="btn btn--primary" type="submit" disabled={create.isPending}>
          {create.isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </form>
  );
}

function VerifyButton({ employeeId, credentialId }: { employeeId: string; credentialId: string }) {
  const verify = useVerifyCredential(employeeId);

  return (
    <button
      className="btn btn--sm"
      type="button"
      onClick={() => verify.mutate(credentialId)}
      disabled={verify.isPending}
    >
      Mark checked
    </button>
  );
}

function DeleteButton({ employeeId, credentialId }: { employeeId: string; credentialId: string }) {
  const remove = useDeleteCredential(employeeId);

  return (
    <button
      className="btn btn--sm btn--ghost"
      type="button"
      onClick={() => {
        if (window.confirm("Delete this credential?")) {
          remove.mutate(credentialId);
        }
      }}
      disabled={remove.isPending}
    >
      Delete
    </button>
  );
}
