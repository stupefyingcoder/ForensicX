import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { Run, RunProgressEvent } from "../api/types";
import { useAuth } from "../context/AuthContext";

const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://127.0.0.1:8000/api";

export function useRunProgress(runId: number | null) {
  const queryClient = useQueryClient();
  const { token } = useAuth();
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!runId || !token) return;

    // Check if run is already in a terminal state
    const cached = queryClient.getQueryData<Run>(["runs", runId, "status"]);
    if (cached && (cached.status === "completed" || cached.status === "failed")) return;

    const url = `${API_BASE}/runs/${runId}/stream?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const data: RunProgressEvent = JSON.parse(event.data);

        // Update the run status in TanStack Query cache
        queryClient.setQueryData<Run>(["runs", runId, "status"], (old) => {
          if (!old) return old;
          return { ...old, progress: data.progress, status: data.status };
        });

        if (data.status === "completed" || data.status === "failed") {
          es.close();
          // Trigger results fetch
          queryClient.invalidateQueries({ queryKey: ["runs", runId, "results"] });
          queryClient.invalidateQueries({ queryKey: ["runs", runId, "status"] });
        }
      } catch {
        // Ignore parse errors
      }
    };

    es.onerror = () => {
      es.close();
      // Fallback: TanStack Query polling in useRunStatus will take over
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [runId, token, queryClient]);
}
