import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type { LeaveApplication, LeaveBalance, LeaveLedgerEntry, LifecycleRequest, Page } from "./types";

const KEY = "leave";
export const useMyLeave = () => useQuery({
  queryKey: [KEY, "applications"],
  queryFn: async () => (await http.get<Page<LeaveApplication>>("/leave/applications")).data,
});
export const useLeaveBalances = () => useQuery({
  queryKey: [KEY, "balances"],
  queryFn: async () => (await http.get<Page<LeaveBalance>>("/leave/balances")).data,
});
export const useLeaveLedger = () => useQuery({
  queryKey: [KEY, "ledger"],
  queryFn: async () => (await http.get<Page<LeaveLedgerEntry>>("/leave/ledger")).data,
});
export const useLeaveInbox = () => useQuery({
  queryKey: [KEY, "inbox"],
  queryFn: async () => (await http.get<Page<LeaveApplication>>("/leave/inbox")).data,
});
export const useSubstituteInbox = () => useQuery({
  queryKey: [KEY, "substitute-inbox"],
  queryFn: async () => (await http.get<Page<LeaveApplication>>("/leave/substitute/inbox")).data,
});
export const useLifecycleInbox = () => useQuery({
  queryKey: [KEY, "lifecycle-inbox"],
  queryFn: async () => (await http.get<Page<LifecycleRequest>>("/leave/lifecycle/inbox")).data,
});
export const useLifecycleSubstituteInbox = () => useQuery({
  queryKey: [KEY, "lifecycle-substitute-inbox"],
  queryFn: async () => (await http.get<Page<LifecycleRequest>>("/leave/substitute/lifecycle-inbox")).data,
});
export const useMyLifecycle = () => useQuery({
  queryKey: [KEY, "lifecycle-mine"],
  queryFn: async () => (await http.get<Page<LifecycleRequest>>("/leave/lifecycle/mine")).data,
});
export const usePolicies = () => useQuery({
  queryKey: [KEY, "policies"],
  queryFn: async () => (await http.get<Page<Record<string, unknown>>>("/leave/admin/policies")).data,
});
export const useWorkflow = () => useQuery({
  queryKey: [KEY, "workflow"],
  queryFn: async () => (await http.get<Page<Record<string, unknown>>>("/leave/admin/workflow")).data,
});
export const useSla = () => useQuery({
  queryKey: [KEY, "sla"],
  queryFn: async () => (await http.get<Page<Record<string, unknown>>>("/leave/admin/sla")).data,
});
export const useCalendars = () => useQuery({
  queryKey: [KEY, "calendars"],
  queryFn: async () => (await http.get<Page<Record<string, unknown>>>("/leave/admin/calendars")).data,
});

export function useLeaveMutation(path: string, method: "post" | "patch" = "post") {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id?: number; body?: Record<string, unknown> }) => {
      const url = id == null ? path : path.replace(":id", String(id));
      const response = method === "patch"
        ? await http.patch(url, body ?? {})
        : await http.post(url, body ?? {});
      return response.data;
    },
    onSuccess: async () => qc.invalidateQueries({ queryKey: [KEY] }),
  });
}
