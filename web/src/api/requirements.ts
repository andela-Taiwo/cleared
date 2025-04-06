import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";

export type Requirement = { job_role_id: string; credential_type_id: string };

export function useRequirements() {
  return useQuery({
    queryKey: ["requirements"],
    queryFn: () => api.get<{ requirements: Requirement[] }>("/v1/requirements"),
    select: (data) => data.requirements,
  });
}

export function useSaveRoleRequirements() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ roleId, credentialTypeIds }: { roleId: string; credentialTypeIds: string[] }) =>
      api.put<{ requirements: Requirement[] }>(`/v1/requirements/${roleId}`, {
        credential_type_ids: credentialTypeIds,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["requirements"] }),
  });
}
