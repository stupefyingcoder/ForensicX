import { useMutation, useQuery } from "@tanstack/react-query";
import { runsApi } from "../api/client";
import type { CreateRunRequest } from "../api/types";

export function useCreateRun() {
  return useMutation({
    mutationFn: (data: CreateRunRequest) => runsApi.create(data),
  });
}

export function useRunStatus(id: number | null) {
  return useQuery({
    queryKey: ["runs", id, "status"],
    queryFn: () => runsApi.getStatus(id!),
    enabled: id !== null && id > 0,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 3000; // fallback polling
    },
  });
}

export function useRunResults(runId: number | null, enabled: boolean) {
  return useQuery({
    queryKey: ["runs", runId, "results"],
    queryFn: () => runsApi.getResults(runId!),
    enabled: enabled && runId !== null && runId > 0,
  });
}
