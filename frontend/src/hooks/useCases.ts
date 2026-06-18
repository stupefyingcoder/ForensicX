import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { casesApi } from "../api/client";
import type { CreateCaseRequest } from "../api/types";

export function useCases() {
  return useQuery({
    queryKey: ["cases"],
    queryFn: () => casesApi.list(),
  });
}

export function useCase(id: number) {
  return useQuery({
    queryKey: ["cases", id],
    queryFn: () => casesApi.get(id),
    enabled: id > 0,
  });
}

export function useCreateCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateCaseRequest) => casesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cases"] });
    },
  });
}

export function useUploadImage(caseId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => casesApi.uploadImage(caseId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cases", caseId] });
    },
  });
}
