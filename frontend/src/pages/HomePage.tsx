import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createJob, ApiError } from "../api";
import UploadZone from "../components/UploadZone";
import type { ModelOption } from "../types";

export default function HomePage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [model, setModel] = useState<ModelOption>("base");
  const [language, setLanguage] = useState("auto");
  const [uploading, setUploading] = useState(false);
  const [uploadPct, setUploadPct] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(async () => {
    if (!file) return;
    setUploading(true);
    setUploadPct(0);
    setError(null);

    try {
      const job = await createJob(file, model, language, setUploadPct);
      navigate(`/job/${job.id}`);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("Upload failed. Is the backend running?");
      }
      setUploading(false);
    }
  }, [file, model, language, navigate]);

  return (
    <div className="home-page">
      <div className="hero">
        <h1>Generate captions for any video</h1>
        <p className="hero-sub">
          Free, private, powered by open-source AI. No account needed.
        </p>
      </div>

      <UploadZone onFileSelected={setFile} disabled={uploading} />

      {file && !uploading && (
        <div className="upload-options fade-in">
          <div className="file-info">
            <span className="file-name">{file.name}</span>
            <span className="file-size">{formatSize(file.size)}</span>
          </div>

          <div className="options-row">
            <label className="option">
              <span className="option-label">Model</span>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value as ModelOption)}
                className="option-select"
              >
                <option value="tiny">Tiny (fastest)</option>
                <option value="base">Base (balanced)</option>
                <option value="small">Small (best quality)</option>
              </select>
            </label>

            <label className="option">
              <span className="option-label">Language</span>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="option-select"
              >
                <option value="auto">Auto-detect</option>
                <option value="en">English</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
                <option value="it">Italian</option>
                <option value="pt">Portuguese</option>
                <option value="ja">Japanese</option>
                <option value="ko">Korean</option>
                <option value="zh">Chinese</option>
              </select>
            </label>
          </div>

          <button className="btn-primary" onClick={handleSubmit}>
            Generate Captions
          </button>
        </div>
      )}

      {uploading && (
        <div className="uploading-state fade-in">
          <p>Uploading... {uploadPct}%</p>
          <div className="progress-bar">
            <div className="progress-bar-fill" style={{ width: `${uploadPct}%` }} />
          </div>
        </div>
      )}

      {error && <p className="page-error">{error}</p>}
    </div>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
