import mimetypes
import secrets
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, Form
from fastapi.responses import FileResponse, PlainTextResponse

from .config import settings
from .models import ALLOWED_EXTENSIONS, ALLOWED_MODELS, Job, JobStatus
from .storage import (
    delete_job,
    ensure_job_dir,
    get_artifact_path,
    get_input_path,
    list_jobs,
    load_meta,
    save_meta,
    save_upload,
)
from .worker import enqueue

router = APIRouter(prefix="/api")


def _error(code: str, message: str, status: int = 400) -> HTTPException:
    return HTTPException(status_code=status, detail={"error": {"code": code, "message": message}})


@router.get("/health")
async def health():
    import shutil
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    # List models that are already cached in memory
    from .transcriber import _model_cache
    models_loaded = list(_model_cache.keys())
    return {
        "status": "ok",
        "ffmpeg": ffmpeg_ok,
        "models_loaded": models_loaded,
    }


@router.post("/jobs", status_code=201)
async def create_job(
    file: UploadFile,
    model: str = Form(default=settings.whisper_default_model),
    language: str = Form(default="auto"),
):
    # Validate model
    if model not in ALLOWED_MODELS:
        raise _error("INVALID_MODEL", f"Model '{model}' not supported. Choose from: {', '.join(sorted(ALLOWED_MODELS))}")

    # Validate file extension
    filename = file.filename or "upload.mp4"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise _error(
            "INVALID_FILE_TYPE",
            f"File type '{ext}' is not supported. Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Generate job ID
    job_id = f"j_{secrets.token_hex(4)}"
    ensure_job_dir(job_id)

    # Stream upload to disk
    async def _stream():
        while True:
            chunk = await file.read(65536)
            if not chunk:
                break
            yield chunk

    try:
        saved_path, total_bytes = await save_upload(
            job_id, _stream(), filename, settings.max_file_size
        )
    except ValueError as e:
        delete_job(job_id)
        raise _error("FILE_TOO_LARGE", str(e), status=413)

    # Create job metadata
    job = Job(
        id=job_id,
        status=JobStatus.QUEUED,
        file_name=filename,
        file_size=total_bytes,
        model=model,
        language=language,
    )
    save_meta(job)

    # Enqueue for processing
    enqueue(job_id)

    return job.model_dump(exclude_none=True)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = load_meta(job_id)
    if job is None:
        raise _error("JOB_NOT_FOUND", f"Job '{job_id}' not found", status=404)
    return job.model_dump(exclude_none=True)


@router.get("/jobs/{job_id}/captions.srt")
async def get_srt(job_id: str):
    job = load_meta(job_id)
    if job is None:
        raise _error("JOB_NOT_FOUND", f"Job '{job_id}' not found", status=404)
    if job.status != JobStatus.COMPLETED:
        raise _error("JOB_NOT_READY", "Job is still processing", status=409)

    path = get_artifact_path(job_id, "captions.srt")
    if path is None:
        raise _error("INTERNAL_ERROR", "SRT file not found", status=500)

    return PlainTextResponse(
        path.read_text(encoding="utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{job.file_name}.srt"'},
    )


@router.get("/jobs/{job_id}/captions.vtt")
async def get_vtt(job_id: str):
    job = load_meta(job_id)
    if job is None:
        raise _error("JOB_NOT_FOUND", f"Job '{job_id}' not found", status=404)
    if job.status != JobStatus.COMPLETED:
        raise _error("JOB_NOT_READY", "Job is still processing", status=409)

    path = get_artifact_path(job_id, "captions.vtt")
    if path is None:
        raise _error("INTERNAL_ERROR", "VTT file not found", status=500)

    return PlainTextResponse(
        path.read_text(encoding="utf-8"),
        media_type="text/vtt; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{job.file_name}.vtt"'},
    )


@router.get("/jobs/{job_id}/transcript.txt")
async def get_txt(job_id: str):
    job = load_meta(job_id)
    if job is None:
        raise _error("JOB_NOT_FOUND", f"Job '{job_id}' not found", status=404)
    if job.status != JobStatus.COMPLETED:
        raise _error("JOB_NOT_READY", "Job is still processing", status=409)

    path = get_artifact_path(job_id, "transcript.txt")
    if path is None:
        raise _error("INTERNAL_ERROR", "Transcript file not found", status=500)

    return PlainTextResponse(
        path.read_text(encoding="utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{job.file_name}.txt"'},
    )


@router.get("/jobs/{job_id}/video")
async def get_video(job_id: str):
    job = load_meta(job_id)
    if job is None:
        raise _error("JOB_NOT_FOUND", f"Job '{job_id}' not found", status=404)

    path = get_input_path(job_id)
    if path is None:
        raise _error("INTERNAL_ERROR", "Video file not found", status=500)

    content_type = mimetypes.guess_type(str(path))[0] or "video/mp4"
    return FileResponse(path, media_type=content_type)


@router.delete("/jobs/{job_id}", status_code=204)
async def remove_job(job_id: str):
    if not delete_job(job_id):
        raise _error("JOB_NOT_FOUND", f"Job '{job_id}' not found", status=404)
    return None
