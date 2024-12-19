import { type FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError } from "@/api/client";
import { useLogin, useMe } from "@/auth/auth";

const queue = [
  { name: "Marisol Vega", credential: "CPR / BLS", state: "Expired 2 days ago", tone: "danger" },
  { name: "Dennis Okafor", credential: "RN licence", state: "Expires in 6 days", tone: "warn" },
  { name: "Priya Raman", credential: "TB test", state: "Valid for 9 months", tone: "ok" },
];

export default function LoginPage() {
  const me = useMe();
  const login = useLogin();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (me.data) {
      navigate("/", { replace: true });
    }
  }, [me.data, navigate]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      await login.mutateAsync({ email, password });
      navigate("/", { replace: true });
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? (cause.problem.detail ?? cause.problem.title)
          : "Something went wrong",
      );
    }
  }

  return (
    <div className="auth">
      <section className="auth__pitch">
        <div className="brand">
          <span className="brand__mark" aria-hidden="true">
            ✓
          </span>
          Cleared
        </div>

        <div>
          <h1 className="auth__headline">Nobody works a shift with a lapsed credential.</h1>
          <p className="auth__lede">
            Licences, CPR cards, TB tests and background checks, tracked against each caregiver and
            chased before they expire — so a coordinator never finds out during a state survey.
          </p>
        </div>

        <div className="queue" aria-hidden="true">
          {queue.map((item) => (
            <div className="queue__item" key={item.name}>
              <div>
                <div className="queue__name">{item.name}</div>
                <div className="queue__meta">{item.credential}</div>
              </div>
              <span className={`badge badge--${item.tone}`}>{item.state}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="auth__panel">
        <form className="auth__form" onSubmit={onSubmit} noValidate>
          <div>
            <h2 className="title">Sign in</h2>
            <p className="muted small" style={{ marginTop: 6 }}>
              Use the address your agency signed you up with.
            </p>
          </div>

          <label className="field">
            <span className="label">Email</span>
            <input
              className="input"
              type="email"
              name="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>

          <label className="field">
            <span className="label">Password</span>
            <input
              className="input"
              type="password"
              name="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>

          {error ? (
            <p className="error-text" role="alert">
              {error}
            </p>
          ) : null}

          <button className="btn btn--primary btn--block" type="submit" disabled={login.isPending}>
            {login.isPending ? "Signing in…" : "Sign in"}
          </button>

          <p className="auth__footnote">Sessions last 12 hours. Sign out on shared machines.</p>
        </form>
      </section>
    </div>
  );
}
