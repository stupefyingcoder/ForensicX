import { useMutation, useQuery } from "@tanstack/react-query";
import { analysisApi } from "../api/client";
import type { AnalysisRequest } from "../api/types";

export function useCreateAnalysis() {
  return useMutation({
    mutationFn: (data: AnalysisRequest) => analysisApi.create(data),
  });
}

export function useAnalysisResult(id: number | null) {
  return useQuery({
    queryKey: ["analysis", id],
    queryFn: () => analysisApi.get(id!),
    enabled: id !== null && id > 0,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 2000;
    },
  });
}
