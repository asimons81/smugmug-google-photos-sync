import type { Segment } from "../types";

interface Props {
  segments: Segment[];
}

export default function TranscriptEditor({ segments }: Props) {
  return (
    <div className="transcript-editor">
      <h3 className="transcript-title">Transcript</h3>
      <div className="transcript-content">
        {segments.map((seg, i) => (
          <div key={i} className="transcript-segment">
            <span className="transcript-time">
              {formatTime(seg.start)}
            </span>
            <span className="transcript-text">{seg.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
