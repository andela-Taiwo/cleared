import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";

export type Upcoming = {
  employee_id: string;
  employee_name: string;
  credential_type_name: string;
  expires_on: string;
  days_left: number;
  state: "expired" | "unverified" | "expiring" | "valid" | "missing";
};

export type RoleBreakdown = {
  job_role_id: string | null;
  role_name: string;
  total: number;
  compliant: number;
  at_risk: number;
  non_compliant: number;
};

export type Overview = {
  total: number;
  states: Record<string, number>;
  expiring: Record<string, number>;
  upcoming: Upcoming[];
  roles: RoleBreakdown[];
};

export function useOverview() {
  return useQuery({
    queryKey: ["overview"],
    queryFn: () => api.get<Overview>("/v1/compliance/overview"),
  });
}
