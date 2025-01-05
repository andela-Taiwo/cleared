import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { useMe } from "@/auth/auth";
import AppShell from "@/components/AppShell";
import DashboardPage from "@/routes/DashboardPage";
import LoginPage from "@/routes/LoginPage";

function Boot() {
  return <div className="boot">Loading…</div>;
}

function RequireAuth({ children }: { children: ReactNode }) {
  const me = useMe();

  if (me.isPending) {
    return <Boot />;
  }

  if (me.isError) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route path="/" element={<DashboardPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
