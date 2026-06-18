import { useMutation, useQuery } from "@tanstack/react-query";
import { experimentsApi, reportsApi } from "../api/client";
import type { CreateExperimentRequest, GenerateReportRequest } from "../api/types";

export function useCreateExperiment() {
  return useMutation({
    mutationFn: (data: CreateExperimentRequest) => experimentsApi.create(data),
  });
}

export function useExperimentSummary(id: number | null) {
  return useQuery({
    queryKey: ["experiments", id],
    queryFn: () => experimentsApi.getSummary(id!),
    enabled: id !== null && id > 0,
  });
}

export function useGenerateReport() {
  return useMutation({
    mutationFn: (data: GenerateReportRequest) => reportsApi.generate(data),
  });
}

export function useDownloadCsvBlob() {
  return useMutation({
    mutationFn: (id: number) => experimentsApi.getCsvBlob(id),
  });
}

export function useDownloadReportBlob() {
  return useMutation({
    mutationFn: (id: number) => reportsApi.getBlob(id),
  });
}
