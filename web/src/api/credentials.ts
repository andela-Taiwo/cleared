import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";

export type CredentialType = {
  id: string;
  name: string;
  code: string;
  category: "license" | "certification" | "clearance" | "health" | "training";
  issuing_authority: string | null;
  validity_months: number | null;
  requires_document: boolean;
};

export type EmployeeCredential = {
  id: string;
  employee_id: string;
  credential_type: CredentialType;
  identifier: string | null;
  issued_on: string | null;
  expires_on: string | null;
  verified_at: string | null;
  notes: string | null;
};

export type CredentialInput = {
  credential_type_id: string;
  identifier?: string;
  issued_on?: string;
  expires_on?: string;
};

export function useCredentialTypes() {
  return useQuery({
    queryKey: ["credential-types"],
    queryFn: () => api.get<CredentialType[]>("/v1/credential-types"),
    staleTime: 60_000,
  });
}

export function useEmployeeCredentials(employeeId: string | undefined) {
  return useQuery({
    queryKey: ["credentials", employeeId],
    queryFn: () => api.get<EmployeeCredential[]>(`/v1/employees/${employeeId}/credentials`),
    enabled: Boolean(employeeId),
  });
}

function invalidateEmployee(queryClient: ReturnType<typeof useQueryClient>, employeeId: string) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: ["credentials", employeeId] }),
    queryClient.invalidateQueries({ queryKey: ["employee-compliance", employeeId] }),
    queryClient.invalidateQueries({ queryKey: ["employee", employeeId] }),
    queryClient.invalidateQueries({ queryKey: ["overview"] }),
    queryClient.invalidateQueries({ queryKey: ["employees"] }),
  ]);
}

export function useCreateCredential(employeeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: CredentialInput) =>
      api.post<EmployeeCredential>(`/v1/employees/${employeeId}/credentials`, input),
    onSuccess: () => invalidateEmployee(queryClient, employeeId),
  });
}

export function useVerifyCredential(employeeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (credentialId: string) =>
      api.post<EmployeeCredential>(`/v1/credentials/${credentialId}/verify`),
    onSuccess: () => invalidateEmployee(queryClient, employeeId),
  });
}

export function useDeleteCredential(employeeId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (credentialId: string) => api.delete<void>(`/v1/credentials/${credentialId}`),
    onSuccess: () => invalidateEmployee(queryClient, employeeId),
  });
}
