import json
import logging
import subprocess
from pathlib import Path
from typing import Generator

from .config import settings
from .models import Segment

logger = logging.getLogger(__name__)

# Cache loaded models by name to avoid reloading
_model_cache: dict[str, object] = {}


def probe_video(input_path: Path) -> tuple[float, bool]:
    """Use ffprobe to get duration and check for audio stream.

    Returns (duration_seconds, has_audio).
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(input_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr[:500]}")

    data = json.loads(result.stdout)

    duration = 0.0
    if "format" in data and "duration" in data["format"]:
        duration = float(data["format"]["duration"])

    has_audio = any(
        s.get("codec_type") == "audio" for s in data.get("streams", [])
    )
    return duration, has_audio


def extract_audio(input_path: Path, output_path: Path) -> None:
    """Extract audio as 16kHz mono WAV using ffmpeg."""
    cmd = [
        "ffmpeg",
        "-i", str(input_path),
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-f", "wav",
        "-y",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extraction failed: {result.stderr[:500]}")


def transcribe(
    audio_path: Path,
    model_name: str,
    language: str | None,
    duration: float,
) -> Generator[tuple[list[Segment], int], None, None]:
    """Transcribe audio file with faster-whisper.

    Yields (segments_so_far, progress_percent) tuples as segments are produced.
    Progress is mapped to the 20-90 range (caller handles the rest).
    """
    from faster_whisper import WhisperModel

    if model_name not in _model_cache:
        logger.info("Loading whisper model '%s' (device=%s, compute=%s)",
                     model_name, settings.whisper_device, settings.whisper_compute_type)
        _model_cache[model_name] = WhisperModel(
            model_name,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )

    model = _model_cache[model_name]

    lang = language if language and language != "auto" else None
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=lang,
        beam_size=5,
        vad_filter=True,
    )

    detected = info.language
    all_segments: list[Segment] = []

    for seg in segments_iter:
        all_segments.append(Segment(
            start=seg.start,
            end=seg.end,
            text=seg.text.strip(),
        ))
        if duration > 0:
            pct = min(90, 20 + int(70 * (seg.end / duration)))
        else:
            pct = 50
        yield all_segments, pct, detected
