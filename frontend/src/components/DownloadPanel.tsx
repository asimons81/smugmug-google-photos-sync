import { captionsUrl } from "../api";

interface Props {
  jobId: string;
}

export default function DownloadPanel({ jobId }: Props) {
  const downloads = [
    { label: "SRT", desc: "SubRip (most compatible)", url: captionsUrl(jobId, "srt") },
    { label: "VTT", desc: "WebVTT (web players)", url: captionsUrl(jobId, "vtt") },
    { label: "TXT", desc: "Plain text transcript", url: captionsUrl(jobId, "txt") },
  ];

  return (
    <div className="download-panel">
      <h3 className="download-title">Download Captions</h3>
      <div className="download-buttons">
        {downloads.map((d) => (
          <a
            key={d.label}
            href={d.url}
            download
            className="download-btn"
          >
            <span className="download-btn-label">{d.label}</span>
            <span className="download-btn-desc">{d.desc}</span>
          </a>
        ))}
      </div>
    </div>
  );
}
