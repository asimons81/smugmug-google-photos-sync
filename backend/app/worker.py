import logging
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path

from .config import settings
from .models import Job, JobError, JobStatus, Segment
from .storage import job_dir, save_meta
from .subtitles import generate_srt, generate_txt, generate_vtt
from .transcriber import extract_audio, probe_video, transcribe

logger = logging.getLogger(__name__)

_job_queue: queue.Queue[str] = queue.Queue()
_worker_thread: threading.Thread | None = None


def enqueue(job_id: str) -> None:
    _job_queue.put(job_id)


def start_worker() -> None:
    global _worker_thread
    _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
    _worker_thread.start()
    logger.info("Worker thread started")


def _worker_loop() -> None:
    while True:
        job_id = _job_queue.get()
        try:
            _process_job(job_id)
        except Exception:
            logger.exception("Unhandled error processing job %s", job_id)
        finally:
            _job_queue.task_done()


def _update_job(job: Job, **kwargs) -> Job:
    """Update job fields, save to disk, return updated job."""
    for k, v in kwargs.items():
        setattr(job, k, v)
    save_meta(job)
    return job


def _process_job(job_id: str) -> None:
    from .storage import load_meta, get_input_path

    job = load_meta(job_id)
    if job is None:
        logger.error("Job %s not found on disk", job_id)
        return

    d = job_dir(job_id)
    input_path = get_input_path(job_id)
    if input_path is None:
        _update_job(job,
                     status=JobStatus.FAILED,
                     error=JobError(code="INTERNAL_ERROR", message="Input file not found"))
        return

    audio_path = d / "audio.wav"

    try:
        # Update status to processing
        _update_job(job, status=JobStatus.PROCESSING, progress=0)

        # Step 1: Probe video
        logger.info("[%s] Probing video...", job_id)
        duration, has_audio = probe_video(input_path)
        if not has_audio:
            _update_job(job,
                         status=JobStatus.FAILED,
                         error=JobError(code="NO_AUDIO_TRACK",
                                        message="The uploaded video contains no audio track."))
            return
        _update_job(job, duration_seconds=duration)

        # Step 2: Extract audio
        logger.info("[%s] Extracting audio (duration: %.1fs)...", job_id, duration)
        extract_audio(input_path, audio_path)
        _update_job(job, progress=20)

        # Step 3: Transcribe
        logger.info("[%s] Transcribing with model '%s'...", job_id, job.model)
        segments: list[Segment] = []
        detected_language = None

        for segs, progress, detected in transcribe(audio_path, job.model, job.language, duration):
            segments = segs
            detected_language = detected
            _update_job(job, progress=progress, detected_language=detected_language)

        # Step 4: Generate output files
        logger.info("[%s] Generating subtitle files...", job_id)
        _update_job(job, progress=90)

        srt_content = generate_srt(segments)
        vtt_content = generate_vtt(segments)
        txt_content = generate_txt(segments)

        (d / "captions.srt").write_text(srt_content, encoding="utf-8")
        (d / "captions.vtt").write_text(vtt_content, encoding="utf-8")
        (d / "transcript.txt").write_text(txt_content, encoding="utf-8")

        # Done
        _update_job(
            job,
            status=JobStatus.COMPLETED,
            progress=100,
            completed_at=datetime.now(timezone.utc),
            segments=segments,
            detected_language=detected_language,
        )
        logger.info("[%s] Completed successfully (%d segments)", job_id, len(segments))

    except Exception as e:
        logger.exception("[%s] Processing failed", job_id)
        _update_job(
            job,
            status=JobStatus.FAILED,
            error=JobError(code="PROCESSING_FAILED", message=str(e)[:500]),
        )
    finally:
        # Clean up audio file (not needed after transcription)
        if audio_path.exists():
            try:
                audio_path.unlink()
            except OSError:
                pass
