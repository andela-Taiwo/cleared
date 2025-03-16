import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";

export type JobRole = { id: string; name: string; code: string };

export type ComplianceSummary = {
  state: "compliant" | "at_risk" | "non_compliant";
  readiness: number;
  expired: number;
  expiring: number;
  missing: number;
  unverified: number;
};

export type Employee = {
  id: string;
  employee_no: string | null;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  location: string | null;
  hired_on: string | null;
  status: "active" | "inactive" | "onboarding";
  job_role: JobRole | null;
  compliance?: ComplianceSummary | null;
};

export type EmployeePage = {
  items: Employee[];
  next_cursor: string | null;
  total: number;
};

export type ImportReport = {
  created: number;
  updated: number;
  failed: number;
  errors: { line: number; message: string }[];
};

type Filters = {
  search?: string;
  roleId?: string;
  status?: string;
  cursor?: string | null;
  limit?: number;
};

function queryString(filters: Filters): string {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.roleId) params.set("role_id", filters.roleId);
  if (filters.status) params.set("status", filters.status);
  if (filters.cursor) params.set("cursor", filters.cursor);
  if (filters.limit) params.set("limit", String(filters.limit));
  const value = params.toString();
  return value ? `?${value}` : "";
}

export function useEmployees(filters: Filters) {
  return useQuery({
    queryKey: ["employees", filters],
    queryFn: () => api.get<EmployeePage>(`/v1/employees${queryString(filters)}`),
    placeholderData: (previous) => previous,
  });
}

export function useRoles() {
  return useQuery({
    queryKey: ["roles"],
    queryFn: () => api.get<JobRole[]>("/v1/roles"),
    staleTime: 60_000,
  });
}

export type NewEmployee = {
  first_name: string;
  last_name: string;
  email?: string;
  employee_no?: string;
  job_role_id?: string;
  status?: string;
};

export function useCreateEmployee() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (employee: NewEmployee) => api.post<Employee>("/v1/employees", employee),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["employees"] }),
  });
}

export function useImportRoster() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.upload<ImportReport>("/v1/employees/import", form);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["employees"] }),
  });
}

export function useEmployee(employeeId: string | undefined) {
  return useQuery({
    queryKey: ["employee", employeeId],
    queryFn: () => api.get<Employee>(`/v1/employees/${employeeId}`),
    enabled: Boolean(employeeId),
  });
}

export type RequirementStatus = {
  credential_type_id: string;
  credential_type_name: string;
  state: "expired" | "unverified" | "expiring" | "valid" | "missing";
  expires_on: string | null;
  days_left: number | null;
};

export type EmployeeCompliance = {
  state: "compliant" | "at_risk" | "non_compliant";
  readiness: number;
  items: RequirementStatus[];
};

export function useEmployeeCompliance(employeeId: string | undefined) {
  return useQuery({
    queryKey: ["employee-compliance", employeeId],
    queryFn: () => api.get<EmployeeCompliance>(`/v1/compliance/employees/${employeeId}`),
    enabled: Boolean(employeeId),
  });
}
