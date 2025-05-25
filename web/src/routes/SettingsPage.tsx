import { type FormEvent, useState } from "react";

import { ApiError } from "@/api/client";
import { useCredentialTypes } from "@/api/credentials";
import { Badge, Card, EmptyState, Field, Loading } from "@/components/ui";

const categories = ["license", "certification", "clearance", "health", "training"] as const;

export default function SettingsPage() {
  const types = useCredentialTypes();

  return (
    <main className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Settings</p>
          <h1 className="display">Credential catalogue</h1>
          <p className="muted small">
            The kinds of evidence this agency recognises. Roles decide which of these are required.
          </p>
        </div>
      </header>

      <Card className="card--table">
        <div className="card__header">
          <h2 className="subtitle">Types</h2>
          <span className="muted small">{types.data?.length ?? 0} in the catalogue</span>
        </div>

        {types.isPending ? (
          <Loading label="Loading the catalogue…" />
        ) : (types.data ?? []).length === 0 ? (
          <EmptyState title="Nothing here yet" body="Add the first credential type below." />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Code</th>
                  <th>Category</th>
                  <th>Valid for</th>
                  <th>Issuer</th>
                </tr>
              </thead>
              <tbody>
                {(types.data ?? []).map((type) => (
                  <tr key={type.id}>
                    <td>{type.name}</td>
                    <td className="mono muted">{type.code}</td>
                    <td>
                      <Badge tone="neutral">{type.category}</Badge>
                    </td>
                    <td className="numeric muted">
                      {type.validity_months ? `${type.validity_months} months` : "—"}
                    </td>
                    <td className="muted small">{type.issuing_authority ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <AddTypeForm />
    </main>
  );
}

function AddTypeForm() {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setSaving(true);
    setError(null);

    try {
      const response = await fetch("/v1/credential-types", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: String(data.get("name") ?? ""),
          code: String(data.get("code") ?? ""),
          category: String(data.get("category") ?? "certification"),
          validity_months: data.get("validity_months")
            ? Number(data.get("validity_months"))
            : undefined,
        }),
      });
      if (!response.ok) {
        const problem = await response.json().catch(() => ({ title: "Failed" }));
        throw new Error(problem.detail ?? problem.title ?? "Failed");
      }
      form.reset();
      window.location.reload();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : (cause as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="card--form">
      <form className="form-grid" onSubmit={onSubmit}>
        <Field label="Name" htmlFor="name">
          <input className="input" id="name" name="name" required placeholder="Flu shot" />
        </Field>
        <Field label="Code" htmlFor="code">
          <input className="input" id="code" name="code" required placeholder="FLU" />
        </Field>
        <Field label="Category" htmlFor="category">
          <select className="select" id="category" name="category" defaultValue="health">
            {categories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Valid for (months)" htmlFor="validity_months">
          <input
            className="input"
            id="validity_months"
            name="validity_months"
            type="number"
            min={1}
          />
        </Field>
        <div className="form-grid__actions">
          {error ? <p className="error-text">{error}</p> : null}
          <button className="btn btn--primary" type="submit" disabled={saving}>
            {saving ? "Saving…" : "Add type"}
          </button>
        </div>
      </form>
    </Card>
  );
}
