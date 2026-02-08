import type { Job } from "./types";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

class ApiError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let code = "UNKNOWN";
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.error) {
        code = body.error.code || code;
        message = body.error.message || message;
      } else if (body.detail?.error) {
        code = body.detail.error.code || code;
        message = body.detail.error.message || message;
      }
    } catch {
      // response wasn't JSON
    }
    throw new ApiError(code, message);
  }
  return res.json();
}

export async function createJob(
  file: File,
  model: string,
  language: string,
  onProgress?: (pct: number) => void
): Promise<Job> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file);
    form.append("model", model);
    form.append("language", language);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API}/api/jobs`);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status === 201) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          const body = JSON.parse(xhr.responseText);
          const err = body.detail?.error || body.error || {};
          reject(new ApiError(err.code || "UNKNOWN", err.message || `HTTP ${xhr.status}`));
        } catch {
          reject(new ApiError("UNKNOWN", `HTTP ${xhr.status}`));
        }
      }
    };

    xhr.onerror = () => reject(new ApiError("NETWORK", "Network error — is the backend running?"));
    xhr.send(form);
  });
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`${API}/api/jobs/${jobId}`);
  return handleResponse<Job>(res);
}

export async function deleteJob(jobId: string): Promise<void> {
  const res = await fetch(`${API}/api/jobs/${jobId}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) {
    throw new ApiError("DELETE_FAILED", `HTTP ${res.status}`);
  }
}

export function captionsUrl(jobId: string, format: "srt" | "vtt" | "txt"): string {
  const ext = format === "txt" ? "transcript.txt" : `captions.${format}`;
  return `${API}/api/jobs/${jobId}/${ext}`;
}

export function videoUrl(jobId: string): string {
  return `${API}/api/jobs/${jobId}/video`;
}

export { ApiError };
