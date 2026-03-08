import { type FormEvent, useDeferredValue, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "@/api/client";
import {
  type ImportReport,
  useCreateEmployee,
  useEmployees,
  useImportRoster,
  useRoles,
} from "@/api/employees";
import { Badge, Card, EmptyState, Field, Loading, statusTone } from "@/components/ui";

export default function EmployeesPage() {
  const [search, setSearch] = useState("");
  const [roleId, setRoleId] = useState("");
  const [status, setStatus] = useState("");
  const [compliance, setCompliance] = useState("");
  const [adding, setAdding] = useState(false);

  const deferredSearch = useDeferredValue(search);
  const { data, isPending, isError } = useEmployees({
    search: deferredSearch,
    roleId,
    status,
    compliance,
    limit: 50,
  });
  const roles = useRoles();

  const fileInput = useRef<HTMLInputElement>(null);
  const importRoster = useImportRoster();
  const [report, setReport] = useState<ImportReport | null>(null);

  async function onFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setReport(null);
    const result = await importRoster.mutateAsync(file);
    setReport(result);
    event.target.value = "";
  }

  const employees = data?.items ?? [];

  return (
    <main className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Roster</p>
          <h1 className="display">
            People <span className="muted numeric">({data?.total ?? 0})</span>
          </h1>
          <p className="muted small">
            Everyone the agency can deploy, and the role that decides what they must hold.
          </p>
        </div>

        <div className="row">
          <input ref={fileInput} type="file" accept=".csv,text/csv" hidden onChange={onFile} />
          <button
            className="btn"
            type="button"
            onClick={() => fileInput.current?.click()}
            disabled={importRoster.isPending}
          >
            {importRoster.isPending ? "Importing…" : "Import CSV"}
          </button>
          <button className="btn btn--primary" type="button" onClick={() => setAdding((v) => !v)}>
            {adding ? "Close" : "Add employee"}
          </button>
        </div>
      </header>

      {report ? (
        <div className="notice" role="status">
          Imported {report.created} new and updated {report.updated} existing
          {report.failed ? ` — ${report.failed} row(s) skipped` : ""}.
          {report.errors.length ? (
            <ul className="notice__list">
              {report.errors.slice(0, 5).map((error) => (
                <li key={`${error.line}-${error.message}`}>
                  Line {error.line}: {error.message}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {adding ? <AddEmployeeForm onDone={() => setAdding(false)} roles={roles.data ?? []} /> : null}

      <Card className="card--table">
        <div className="toolbar">
          <input
            className="input toolbar__search"
            type="search"
            placeholder="Search name, email or employee number"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            aria-label="Search the roster"
          />

          <select
            className="select"
            value={roleId}
            onChange={(event) => setRoleId(event.target.value)}
            aria-label="Filter by role"
          >
            <option value="">Every role</option>
            {(roles.data ?? []).map((role) => (
              <option key={role.id} value={role.id}>
                {role.name}
              </option>
            ))}
          </select>

          <select
            className="select"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            aria-label="Filter by status"
          >
            <option value="">Every status</option>
            <option value="active">Active</option>
            <option value="onboarding">Onboarding</option>
            <option value="inactive">Inactive</option>
          </select>

          <select
            className="select"
            value={compliance}
            onChange={(event) => setCompliance(event.target.value)}
            aria-label="Filter by compliance"
          >
            <option value="">Anyone</option>
            <option value="compliant">Ready to deploy</option>
            <option value="at_risk">At risk</option>
            <option value="non_compliant">Blocked</option>
          </select>
        </div>

        {isPending ? (
          <Loading label="Loading the roster…" />
        ) : isError ? (
          <EmptyState title="The roster did not load" body="Refresh the page to try again." />
        ) : employees.length === 0 ? (
          <EmptyState
            title="No one matches"
            body="Adjust the filters, or import the roster from the spreadsheet the agency already keeps."
            action={
              <button className="btn" type="button" onClick={() => fileInput.current?.click()}>
                Import a CSV
              </button>
            }
          />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Role</th>
                  <th>Compliance</th>
                  <th>Status</th>
                  <th>Hired</th>
                  <th>Contact</th>
                </tr>
              </thead>
              <tbody>
                {employees.map((employee) => (
                  <tr key={employee.id}>
                    <td>
                      <Link to={`/employees/${employee.id}`}>
                        {employee.last_name}, {employee.first_name}
                      </Link>
                      {employee.employee_no ? (
                        <div className="faint mono small">{employee.employee_no}</div>
                      ) : null}
                    </td>
                    <td>{employee.job_role?.name ?? <span className="faint">—</span>}</td>
                    <td>
                      {employee.compliance ? (
                        <span className="row">
                          <Badge
                            tone={
                              employee.compliance.state === "compliant"
                                ? "ok"
                                : employee.compliance.state === "at_risk"
                                  ? "warn"
                                  : "danger"
                            }
                          >
                            {employee.compliance.state === "compliant"
                              ? "Ready"
                              : employee.compliance.state === "at_risk"
                                ? "At risk"
                                : "Blocked"}
                          </Badge>
                          <span className="faint small numeric">
                            {employee.compliance.readiness}%
                          </span>
                        </span>
                      ) : (
                        <span className="faint">—</span>
                      )}
                    </td>
                    <td>
                      <Badge tone={statusTone(employee.status)}>{employee.status}</Badge>
                    </td>
                    <td className="numeric muted">{employee.hired_on ?? "—"}</td>
                    <td className="muted small">{employee.email ?? employee.phone ?? "—"}</td>
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

function AddEmployeeForm({
  onDone,
  roles,
}: {
  onDone: () => void;
  roles: { id: string; name: string; code: string }[];
}) {
  const create = useCreateEmployee();
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = new FormData(event.currentTarget);

    try {
      await create.mutateAsync({
        first_name: String(form.get("first_name") ?? "").trim(),
        last_name: String(form.get("last_name") ?? "").trim(),
        email: String(form.get("email") ?? "").trim() || undefined,
        employee_no: String(form.get("employee_no") ?? "").trim() || undefined,
        job_role_id: String(form.get("job_role_id") ?? "") || undefined,
      });
      onDone();
    } catch (cause) {
      setError(
        cause instanceof ApiError ? (cause.problem.detail ?? cause.problem.title) : "Failed",
      );
    }
  }

  return (
    <Card className="card--form">
      <form className="form-grid" onSubmit={onSubmit}>
        <Field label="First name" htmlFor="first_name">
          <input className="input" id="first_name" name="first_name" required />
        </Field>
        <Field label="Last name" htmlFor="last_name">
          <input className="input" id="last_name" name="last_name" required />
        </Field>
        <Field label="Email" htmlFor="email">
          <input className="input" id="email" name="email" type="email" />
        </Field>
        <Field label="Employee number" htmlFor="employee_no">
          <input className="input" id="employee_no" name="employee_no" placeholder="NW-014" />
        </Field>
        <Field label="Role" htmlFor="job_role_id">
          <select className="select" id="job_role_id" name="job_role_id" defaultValue="">
            <option value="">Unassigned</option>
            {roles.map((role) => (
              <option key={role.id} value={role.id}>
                {role.name}
              </option>
            ))}
          </select>
        </Field>
        <div className="form-grid__actions">
          {error ? <p className="error-text">{error}</p> : null}
          <button className="btn btn--primary" type="submit" disabled={create.isPending}>
            {create.isPending ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </Card>
  );
}
