import { useEffect, useRef, useState } from "react";
import { getJob } from "../api";
import type { Job } from "../types";

export function useJob(jobId: string | undefined) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!jobId) return;

    let cancelled = false;

    async function poll() {
      try {
        const data = await getJob(jobId!);
        if (cancelled) return;
        setJob(data);

        // Stop polling if job is done
        if (data.status === "completed" || data.status === "failed") {
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        }
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Failed to fetch job");
      }
    }

    // Initial fetch
    poll();

    // Poll every 2 seconds
    intervalRef.current = setInterval(poll, 2000);

    return () => {
      cancelled = true;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [jobId]);

  return { job, error };
}
