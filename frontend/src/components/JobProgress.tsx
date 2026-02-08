import type { Job } from "../types";

interface Props {
  job: Job;
}

export default function JobProgress({ job }: Props) {
  const statusLabel = {
    queued: "Waiting in queue...",
    processing: "Generating captions...",
    completed: "Done!",
    failed: "Failed",
  }[job.status];

  const statusClass = `job-status-${job.status}`;

  return (
    <div className={`job-progress ${statusClass}`}>
      <div className="job-progress-header">
        <span className="job-progress-label">{statusLabel}</span>
        {(job.status === "processing" || job.status === "queued") && (
          <span className="job-progress-pct">{job.progress}%</span>
        )}
      </div>

      {(job.status === "queued" || job.status === "processing") && (
        <div className="progress-bar">
          <div
            className="progress-bar-fill"
            style={{ width: `${job.progress}%` }}
          />
        </div>
      )}

      {job.status === "completed" && (
        <div className="progress-bar">
          <div className="progress-bar-fill complete" style={{ width: "100%" }} />
        </div>
      )}

      {job.status === "failed" && job.error && (
        <p className="job-error-message">{job.error.message}</p>
      )}

      <div className="job-meta">
        <span>{job.file_name}</span>
        {job.duration_seconds != null && (
          <span>{formatDuration(job.duration_seconds)}</span>
        )}
        <span>Model: {job.model}</span>
        {job.detected_language && (
          <span>Language: {job.detected_language}</span>
        )}
      </div>
    </div>
  );
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}
