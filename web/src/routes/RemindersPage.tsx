import { type FormEvent, useState } from "react";

import { ApiError } from "@/api/client";
import {
  type ReminderRule,
  useCreateRule,
  useDeleteRule,
  useReminderEvents,
  useReminderRules,
  useRunReminders,
  useToggleRule,
} from "@/api/reminders";
import { formatDate } from "@/components/format";
import { Badge, Card, EmptyState, Field, Loading } from "@/components/ui";

const audienceLabel: Record<ReminderRule["audience"], string> = {
  employee: "the employee",
  coordinator: "the coordinator",
  both: "both",
};

export default function RemindersPage() {
  const rules = useReminderRules();
  const events = useReminderEvents();
  const run = useRunReminders();

  return (
    <main className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Reminders</p>
          <h1 className="display">Chase renewals before they lapse</h1>
          <p className="muted small">
            A rule fires on the day a credential is exactly that many days from expiry, once per
            credential, per person. Running the schedule twice sends nothing twice.
          </p>
        </div>

        <div className="row">
          <button
            className="btn btn--primary"
            type="button"
            onClick={() => run.mutate()}
            disabled={run.isPending}
          >
            {run.isPending ? "Running…" : "Run today's schedule"}
          </button>
        </div>
      </header>

      {run.data ? (
        <p className="notice" role="status">
          Queued {run.data.generated} message{run.data.generated === 1 ? "" : "s"} and sent{" "}
          {run.data.sent}.
        </p>
      ) : null}

      <div className="detail-grid">
        <Card>
          <div className="card__header">
            <h2 className="subtitle">Rules</h2>
            <span className="muted small">{rules.data?.length ?? 0} active</span>
          </div>

          {rules.isPending ? (
            <Loading label="Loading rules…" />
          ) : (rules.data ?? []).length === 0 ? (
            <EmptyState title="No rules yet" body="Add one below to start chasing renewals." />
          ) : (
            <ul className="rule-list">
              {(rules.data ?? []).map((rule) => (
                <RuleRow key={rule.id} rule={rule} />
              ))}
            </ul>
          )}

          <AddRuleForm />
        </Card>

        <Card className="card--table">
          <div className="card__header">
            <h2 className="subtitle">Outbox</h2>
            <span className="muted small">append-only</span>
          </div>

          {events.isPending ? (
            <Loading label="Loading the outbox…" />
          ) : (events.data ?? []).length === 0 ? (
            <EmptyState
              title="Nothing sent yet"
              body="Run the schedule, or wait for the daily job."
            />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Sent</th>
                    <th>To</th>
                    <th>Subject</th>
                  </tr>
                </thead>
                <tbody>
                  {(events.data ?? []).map((event) => (
                    <tr key={event.id}>
                      <td className="numeric muted">{formatDate(event.sent_at ?? event.due_on)}</td>
                      <td className="small">{event.recipient}</td>
                      <td>
                        <div>{event.subject}</div>
                        <div className="faint small">
                          <Badge tone={event.status === "sent" ? "ok" : "neutral"}>
                            {event.status}
                          </Badge>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </main>
  );
}

function RuleRow({ rule }: { rule: ReminderRule }) {
  const toggle = useToggleRule();
  const remove = useDeleteRule();

  return (
    <li className="rule">
      <div className="rule__main">
        <span className="rule__days numeric">{rule.days_before}</span>
        <div>
          <div className="rule__title">days before expiry</div>
          <div className="faint small">tells {audienceLabel[rule.audience]}</div>
        </div>
      </div>
      <div className="row">
        <label className="switch">
          <input
            type="checkbox"
            checked={rule.is_active}
            onChange={(event) => toggle.mutate({ id: rule.id, is_active: event.target.checked })}
            aria-label={`Rule at ${rule.days_before} days is active`}
          />
          <span className="switch__track" aria-hidden="true" />
        </label>
        <button
          className="btn btn--sm btn--ghost"
          type="button"
          onClick={() => remove.mutate(rule.id)}
          disabled={remove.isPending}
        >
          Delete
        </button>
      </div>
    </li>
  );
}

function AddRuleForm() {
  const create = useCreateRule();
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = new FormData(event.currentTarget);

    try {
      await create.mutateAsync({
        days_before: Number(form.get("days_before")),
        audience: String(form.get("audience")) as ReminderRule["audience"],
      });
      event.currentTarget.reset();
    } catch (cause) {
      setError(
        cause instanceof ApiError ? (cause.problem.detail ?? cause.problem.title) : "Failed",
      );
    }
  }

  return (
    <form className="form-grid form-grid--inset" onSubmit={onSubmit}>
      <Field label="Days before expiry" htmlFor="days_before">
        <input
          className="input"
          id="days_before"
          name="days_before"
          type="number"
          min={0}
          max={365}
          defaultValue={30}
          required
        />
      </Field>
      <Field label="Who" htmlFor="audience">
        <select className="select" id="audience" name="audience" defaultValue="both">
          <option value="employee">The employee</option>
          <option value="coordinator">The coordinator</option>
          <option value="both">Both</option>
        </select>
      </Field>
      <div className="form-grid__actions">
        {error ? <p className="error-text">{error}</p> : null}
        <button className="btn" type="submit" disabled={create.isPending}>
          Add rule
        </button>
      </div>
    </form>
  );
}
