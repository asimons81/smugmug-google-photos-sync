import json
import os
import tempfile
from pathlib import Path
from typing import AsyncIterator

from .config import settings
from .models import Job


def _jobs_dir() -> Path:
    d = settings.jobs_dir
    d.mkdir(parents=True, exist_ok=True)
    return d


def job_dir(job_id: str) -> Path:
    return _jobs_dir() / job_id


def ensure_job_dir(job_id: str) -> Path:
    d = job_dir(job_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_meta(job: Job) -> None:
    """Atomically write job metadata to meta.json."""
    d = job_dir(job.id)
    target = d / "meta.json"
    fd, tmp_path = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(job.model_dump_json(indent=2))
        os.replace(tmp_path, target)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_meta(job_id: str) -> Job | None:
    meta_path = job_dir(job_id) / "meta.json"
    if not meta_path.exists():
        return None
    data = json.loads(meta_path.read_text())
    return Job(**data)


def delete_job(job_id: str) -> bool:
    d = job_dir(job_id)
    if not d.exists():
        return False
    import shutil
    shutil.rmtree(d)
    return True


def list_jobs() -> list[str]:
    d = _jobs_dir()
    return sorted(
        [p.name for p in d.iterdir() if p.is_dir() and (p / "meta.json").exists()],
        reverse=True,
    )


async def save_upload(
    job_id: str, stream: AsyncIterator[bytes], filename: str, max_size: int
) -> tuple[Path, int]:
    """Stream uploaded file to disk. Returns (path, total_bytes).

    Raises ValueError if file exceeds max_size.
    """
    ext = Path(filename).suffix.lower() or ".mp4"
    d = ensure_job_dir(job_id)
    target = d / f"input{ext}"

    total = 0
    fd, tmp_path = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            async for chunk in stream:
                total += len(chunk)
                if total > max_size:
                    raise ValueError(f"File exceeds maximum size of {max_size} bytes")
                f.write(chunk)
        os.replace(tmp_path, target)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return target, total


def get_artifact_path(job_id: str, filename: str) -> Path | None:
    p = job_dir(job_id) / filename
    return p if p.exists() else None


def get_input_path(job_id: str) -> Path | None:
    d = job_dir(job_id)
    for ext in (".mp4", ".mov", ".webm", ".mkv"):
        p = d / f"input{ext}"
        if p.exists():
            return p
    return None
