import { useParams, Link } from "react-router-dom";
import { useJob } from "../hooks/useJob";
import JobProgress from "../components/JobProgress";
import VideoPlayer from "../components/VideoPlayer";
import TranscriptEditor from "../components/TranscriptEditor";
import DownloadPanel from "../components/DownloadPanel";

export default function JobPage() {
  const { id } = useParams<{ id: string }>();
  const { job, error } = useJob(id);

  if (error) {
    return (
      <div className="job-page">
        <div className="error-card">
          <h2>Error</h2>
          <p>{error}</p>
          <Link to="/" className="btn-secondary">Back to Home</Link>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="job-page">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  return (
    <div className="job-page">
      <JobProgress job={job} />

      {job.status === "completed" && (
        <div className="results fade-in">
          <VideoPlayer jobId={job.id} fileName={job.file_name} />
          <DownloadPanel jobId={job.id} />
          {job.segments && job.segments.length > 0 && (
            <TranscriptEditor segments={job.segments} />
          )}
        </div>
      )}

      <div className="job-actions">
        <Link to="/" className="btn-secondary">
          Caption Another Video
        </Link>
      </div>
    </div>
  );
}
