import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";

export type ReminderRule = {
  id: string;
  days_before: number;
  channel: string;
  audience: "employee" | "coordinator" | "both";
  is_active: boolean;
};

export type ReminderEvent = {
  id: string;
  employee_id: string;
  due_on: string;
  channel: string;
  recipient: string;
  subject: string;
  body: string;
  status: "queued" | "sent" | "failed" | "skipped";
  sent_at: string | null;
};

export function useReminderRules() {
  return useQuery({
    queryKey: ["reminder-rules"],
    queryFn: () => api.get<ReminderRule[]>("/v1/reminder-rules"),
  });
}

export function useReminderEvents() {
  return useQuery({
    queryKey: ["reminder-events"],
    queryFn: () => api.get<ReminderEvent[]>("/v1/reminders?limit=50"),
  });
}

export function useCreateRule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: { days_before: number; audience: ReminderRule["audience"] }) =>
      api.post<ReminderRule>("/v1/reminder-rules", input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reminder-rules"] }),
  });
}

export function useToggleRule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: { id: string; is_active: boolean }) =>
      api.patch<ReminderRule>(`/v1/reminder-rules/${input.id}`, { is_active: input.is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reminder-rules"] }),
  });
}

export function useDeleteRule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/v1/reminder-rules/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reminder-rules"] }),
  });
}

export function useRunReminders() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.post<{ generated: number; sent: number }>("/v1/reminders/run"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reminder-events"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
    },
  });
}
