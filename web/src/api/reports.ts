import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";

export type ReportRow = {
  employee_no: string;
  last_name: string;
  first_name: string;
  role: string;
  status: string;
  state: "compliant" | "at_risk" | "non_compliant";
  readiness: number;
  expired: number;
  expiring: number;
  missing: number;
  unverified: number;
};

export type ComplianceReport = {
  generated_on: string;
  organization_name: string;
  total: number;
  rows: ReportRow[];
};

export function useComplianceReport() {
  return useQuery({
    queryKey: ["compliance-report"],
    queryFn: () => api.get<ComplianceReport>("/v1/reports/compliance"),
  });
}
