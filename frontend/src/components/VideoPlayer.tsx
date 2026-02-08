import { captionsUrl, videoUrl } from "../api";

interface Props {
  jobId: string;
  fileName: string;
}

export default function VideoPlayer({ jobId, fileName }: Props) {
  const src = videoUrl(jobId);
  const vttSrc = captionsUrl(jobId, "vtt");

  return (
    <div className="video-player">
      <video
        controls
        playsInline
        preload="metadata"
        crossOrigin="anonymous"
        className="video-element"
        key={src}
      >
        <source src={src} />
        <track
          label="Captions"
          kind="captions"
          srcLang="en"
          src={vttSrc}
          default
        />
        Your browser does not support the video element.
      </video>
      <p className="video-filename">{fileName}</p>
    </div>
  );
}
