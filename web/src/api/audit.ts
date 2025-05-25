import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";

export type AuditEvent = {
  id: string;
  actor_name: string;
  action: string;
  entity: string;
  entity_id: string | null;
  data: Record<string, unknown>;
  created_at: string;
};

export function useAuditEvents() {
  return useQuery({
    queryKey: ["audit"],
    queryFn: () => api.get<AuditEvent[]>("/v1/audit?limit=100"),
  });
}
