import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useLogout, useMe } from "@/auth/auth";

const nav = [{ to: "/", label: "Overview", end: true }];

function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

export default function AppShell() {
  const me = useMe();
  const logout = useLogout();
  const navigate = useNavigate();

  async function signOut() {
    await logout.mutateAsync();
    navigate("/login", { replace: true });
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <span className="brand__mark" aria-hidden="true">
            ✓
          </span>
          <div>
            <div className="sidebar__name">Cleared</div>
            <div className="sidebar__org">{me.data?.organization_name ?? "—"}</div>
          </div>
        </div>

        <nav className="sidebar__nav" aria-label="Main">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `sidebar__link${isActive ? " is-active" : ""}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar__foot">
          <div className="avatar" aria-hidden="true">
            {initials(me.data?.name ?? "")}
          </div>
          <div className="sidebar__who">
            <div className="sidebar__person">{me.data?.name}</div>
            <div className="sidebar__role">{me.data?.role}</div>
          </div>
          <button className="btn btn--ghost btn--sm" type="button" onClick={signOut}>
            Sign out
          </button>
        </div>
      </aside>

      <div className="shell__content">
        <Outlet />
      </div>
    </div>
  );
}
