import { useState } from "react";

import { ApiError } from "@/api/client";
import { useCredentialTypes } from "@/api/credentials";
import { useRoles } from "@/api/employees";
import { useRequirements, useSaveRoleRequirements } from "@/api/requirements";
import { Card, EmptyState, Loading } from "@/components/ui";

export default function RequirementsPage() {
  const roles = useRoles();
  const types = useCredentialTypes();
  const requirements = useRequirements();
  const save = useSaveRoleRequirements();
  const [error, setError] = useState<string | null>(null);

  if (roles.isPending || types.isPending || requirements.isPending) {
    return (
      <main className="page">
        <Loading label="Loading the matrix…" />
      </main>
    );
  }

  const roleList = roles.data ?? [];
  const typeList = types.data ?? [];
  const current = requirements.data ?? [];

  const required = new Set(current.map((row) => `${row.job_role_id}:${row.credential_type_id}`));

  function toggle(roleId: string, credentialTypeId: string) {
    setError(null);
    const next = new Set(
      current.filter((row) => row.job_role_id === roleId).map((row) => row.credential_type_id),
    );

    if (next.has(credentialTypeId)) {
      next.delete(credentialTypeId);
    } else {
      next.add(credentialTypeId);
    }

    save.mutate(
      { roleId, credentialTypeIds: [...next] },
      {
        onError: (cause) =>
          setError(
            cause instanceof ApiError ? (cause.problem.detail ?? cause.problem.title) : "Failed",
          ),
      },
    );
  }

  return (
    <main className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Requirements</p>
          <h1 className="display">What each role must hold</h1>
          <p className="muted small">
            A ticked box means the credential is required before someone in that role can work.
            Change the matrix and the whole roster re-scores.
          </p>
        </div>
      </header>

      {error ? (
        <p className="notice notice--error" role="alert">
          {error}
        </p>
      ) : null}

      {roleList.length === 0 || typeList.length === 0 ? (
        <Card>
          <EmptyState
            title="Nothing to configure yet"
            body="Add job roles and credential types first, then come back to decide what each role needs."
          />
        </Card>
      ) : (
        <Card className="card--table">
          <div className="table-wrap">
            <table className="table matrix">
              <thead>
                <tr>
                  <th className="matrix__corner">Credential</th>
                  {roleList.map((role) => (
                    <th key={role.id} className="matrix__role">
                      {role.name}
                      <span className="faint mono small"> {role.code}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {typeList.map((type) => (
                  <tr key={type.id}>
                    <td>
                      <div>{type.name}</div>
                      <div className="faint small">{type.category}</div>
                    </td>
                    {roleList.map((role) => {
                      const checked = required.has(`${role.id}:${type.id}`);
                      return (
                        <td key={role.id} className="matrix__cell">
                          <input
                            type="checkbox"
                            className="checkbox"
                            checked={checked}
                            disabled={save.isPending}
                            onChange={() => toggle(role.id, type.id)}
                            aria-label={`${type.name} for ${role.name}`}
                          />
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </main>
  );
}
