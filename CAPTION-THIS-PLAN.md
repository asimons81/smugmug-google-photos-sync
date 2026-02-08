# Caption This — Implementation-Ready Plan & Spec

> **Project**: Free, local-first captioning web app
> **Target repo**: `caption-this` (new, separate repository)
> **Planned by**: Claude Code (Opus 4.6) — Feb 2026
> **To be built by**: Sonnet 4.5 following this spec

---

## Table of Contents

- [A. System Architecture](#a-system-architecture)
- [B. Repo Layout](#b-repo-layout)
- [C. API Contract](#c-api-contract)
- [D. Job Model & Processing Pipeline](#d-job-model--processing-pipeline)
- [E. Subtitle Generation Method](#e-subtitle-generation-method)
- [F. Storage & Retention Strategy](#f-storage--retention-strategy)
- [G. Local Chromebook Setup Plan](#g-local-chromebook-setup-plan)
- [H. Production Deployment Plan](#h-production-deployment-plan)
- [I. Build Plan for Sonnet 4.5](#i-build-plan-for-sonnet-45)
- [J. Test Plan & Definition of Done](#j-test-plan--definition-of-done)

---

## Technical Decisions (Locked In)

### Frontend: Vite + React (not Next.js)

**Why**: This app is a pure client-side SPA that talks to a separate backend API. No SSR needed. Vite wins on every dimension that matters:
- ~100-200MB node_modules vs 700MB-1GB for Next.js
- Instant dev server startup (<1s) vs 5+ seconds for Next.js
- Clean static deployment to Vercel with zero config friction
- No "use client" directive noise, no fighting App Router's SSR assumptions
- Next.js `output: 'export'` has documented bugs with dynamic routes and SPA navigation — deal-breakers for this app

### Backend: FastAPI (Python)

**Why**: The transcription engine (faster-whisper) is a Python library with native Python bindings. FastAPI is the natural choice:
- Direct `import faster_whisper` — no FFI/subprocess shims
- Built-in async support for file uploads and background tasks
- Auto-generated OpenAPI docs (free Swagger UI for debugging)
- Uvicorn serves it; no separate web server needed
- Python is already present in Chromebook Linux containers

### Transcription: faster-whisper (not whisper.cpp)

**Why**: For a Python/FastAPI backend on CPU hardware:
- Install: `pip install faster-whisper` — no C++ compilation, no system deps
- 4x faster than original OpenAI Whisper with int8 quantization on CPU
- Models auto-download from HuggingFace on first use
- Native word-level timestamps (critical for SRT/VTT generation)
- Easier to Dockerize (no build step, pure Python)
- whisper.cpp is better for embedded/minimal environments, but we're in Python already

### Model sizes (faster-whisper, FP16 on disk, int8 at runtime)

| Model | Disk Size | Relative Speed | Quality |
|-------|-----------|----------------|---------|
| tiny  | ~75 MB    | Fastest        | Good for clear speech |
| base  | ~140 MB   | Fast           | Better accuracy |
| small | ~465 MB   | Moderate       | Best quality for MVP |

Default: `base` (good balance). User can select tiny/base/small in the UI.

---

## A. System Architecture

### Local Mode (Chromebook + iPhone on LAN)

```
┌─────────────────────────────────────────────────────┐
│                   Chromebook (Linux)                 │
│                                                     │
│  ┌───────────────┐       ┌────────────────────────┐ │
│  │  Vite Dev     │       │  FastAPI Backend        │ │
│  │  Server       │       │  (uvicorn)              │ │
│  │               │       │                         │ │
│  │  :5173        │       │  :8000                  │ │
│  │               │       │  ┌───────────────────┐  │ │
│  │  React SPA    │ HTTP  │  │ faster-whisper    │  │ │
│  │  ──────────────────>  │  │ (CPU, int8)       │  │ │
│  │               │       │  └───────────────────┘  │ │
│  │               │       │  ┌───────────────────┐  │ │
│  │               │       │  │ ffmpeg            │  │ │
│  │               │       │  │ (audio extract)   │  │ │
│  │               │       │  └───────────────────┘  │ │
│  └───────────────┘       │  ┌───────────────────┐  │ │
│                          │  │ ./data/           │  │ │
│                          │  │ (jobs, captions)  │  │ │
│                          │  └───────────────────┘  │ │
│                          └────────────────────────┘ │
└─────────────────────────────────────────────────────┘
         ▲
         │  http://<chromebook-ip>:5173
         │
    ┌────┴────┐
    │ iPhone  │
    │ Safari  │
    └─────────┘
```

**Networking notes (local mode)**:
- Vite dev server binds to `0.0.0.0:5173` (not localhost) so iPhone can reach it
- Backend binds to `0.0.0.0:8000`
- Frontend `.env.development` sets `VITE_API_URL=http://<chromebook-ip>:8000`
- CORS on backend allows `*` in dev mode (configurable)
- iPhone connects to Chromebook's LAN IP (find via `hostname -I`)
- No HTTPS needed for LAN — mobile Safari allows HTTP for local network

### Production Mode

```
┌──────────────┐         ┌──────────────────────────────┐
│   Vercel     │         │  Container Host               │
│              │         │  (Fly.io / Render / Railway)  │
│  Static SPA  │  HTTPS  │                               │
│  caption-    │ ──────> │  captions-api.tonyreviews...  │
│  this.vercel │         │                               │
│  .app        │         │  FastAPI + faster-whisper      │
│              │         │  + ffmpeg                      │
│  (or custom  │         │                               │
│   subdomain) │         │  Persistent volume: /data      │
└──────────────┘         └──────────────────────────────┘
       ▲
       │  https://captions.tonyreviewsthings.com
       │
  ┌────┴────┐
  │ Browser │
  └─────────┘
```

**Production networking**:
- Frontend served from Vercel CDN as static files
- `VITE_API_URL=https://captions-api.tonyreviewsthings.com` (or your chosen subdomain)
- Backend CORS allows only the frontend origin(s)
- Backend behind HTTPS (provided by the container host's load balancer)
- No reverse proxy needed — the container host handles TLS termination
- `Access-Control-Allow-Origin` set to frontend domain(s) only

---

## B. Repo Layout

```
caption-this/
├── README.md                    # Clone-to-run instructions
├── docker-compose.yml           # Local dev: runs both frontend + backend
├── .gitignore
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── .env.development         # VITE_API_URL=http://localhost:8000
│   ├── .env.production          # VITE_API_URL=https://captions-api.example.com
│   ├── vercel.json              # Rewrite rules for SPA
│   ├── public/
│   │   └── favicon.svg
│   └── src/
│       ├── main.tsx             # Entry point
│       ├── App.tsx              # Router + layout
│       ├── api.ts               # API client (fetch wrapper)
│       ├── types.ts             # Shared TypeScript types
│       ├── components/
│       │   ├── UploadZone.tsx   # Drag-and-drop upload
│       │   ├── JobProgress.tsx  # Status polling + progress bar
│       │   ├── VideoPlayer.tsx  # <video> with VTT track
│       │   ├── TranscriptEditor.tsx  # Editable transcript text
│       │   └── DownloadPanel.tsx     # SRT/VTT/TXT download buttons
│       ├── pages/
│       │   ├── HomePage.tsx     # Upload + recent jobs
│       │   └── JobPage.tsx      # Single job view (progress/results)
│       └── hooks/
│           └── useJob.ts        # Poll job status hook
│
├── backend/
│   ├── pyproject.toml           # Python project config (dependencies)
│   ├── requirements.txt         # Pinned deps for Docker
│   ├── Dockerfile
│   ├── .env.example             # Documented env vars
│   └── app/
│       ├── __init__.py
│       ├── main.py              # FastAPI app, CORS, lifespan
│       ├── config.py            # Settings (env-based via pydantic-settings)
│       ├── models.py            # Job dataclass/pydantic models
│       ├── routes.py            # API route handlers
│       ├── worker.py            # Transcription pipeline (runs in thread)
│       ├── transcriber.py       # faster-whisper wrapper
│       ├── subtitles.py         # SRT/VTT/TXT formatters
│       └── storage.py           # File I/O abstraction (local disk)
│
├── scripts/
│   ├── setup-chromebook.sh      # One-time Chromebook setup
│   ├── dev.sh                   # Start both frontend + backend
│   └── download-model.sh        # Pre-download a whisper model
│
└── deploy/
    ├── Dockerfile               # Production backend Dockerfile
    ├── fly.toml.example         # Fly.io config template
    └── render.yaml.example      # Render config template
```

**Responsibilities**:
- `frontend/` — Pure UI. Zero business logic. Talks to backend via REST.
- `backend/` — All processing. Upload handling, ffmpeg, whisper, file storage.
- `scripts/` — Developer convenience. Setup, run, model management.
- `deploy/` — Production deployment configs. Not used locally.

---

## C. API Contract

Base URL: `http://localhost:8000` (local) or `https://captions-api.example.com` (prod)

All responses use this error envelope when something goes wrong:

```json
{
  "error": {
    "code": "INVALID_FILE_TYPE",
    "message": "File type 'image/png' is not supported. Accepted: video/mp4, video/quicktime, video/webm"
  }
}
```

Error codes: `INVALID_FILE_TYPE`, `FILE_TOO_LARGE`, `JOB_NOT_FOUND`, `PROCESSING_FAILED`, `MODEL_NOT_AVAILABLE`, `NO_AUDIO_TRACK`, `INTERNAL_ERROR`

### POST /api/jobs

Create a new captioning job by uploading a video file.

**Request**: `multipart/form-data`

| Field    | Type   | Required | Description |
|----------|--------|----------|-------------|
| file     | File   | Yes      | Video file (MP4/MOV/WEBM) |
| model    | string | No       | `tiny`, `base` (default), `small` |
| language | string | No       | ISO 639-1 code or `auto` (default) |

**Response** `201 Created`:

```json
{
  "id": "j_a1b2c3d4",
  "status": "queued",
  "created_at": "2026-02-08T12:00:00Z",
  "file_name": "vacation.mp4",
  "file_size": 52428800,
  "model": "base",
  "language": "auto",
  "progress": 0
}
```

**Errors**: `400 INVALID_FILE_TYPE`, `413 FILE_TOO_LARGE`

### GET /api/jobs/{id}

Poll job status.

**Response** `200 OK` (while processing):

```json
{
  "id": "j_a1b2c3d4",
  "status": "processing",
  "created_at": "2026-02-08T12:00:00Z",
  "file_name": "vacation.mp4",
  "file_size": 52428800,
  "model": "base",
  "language": "auto",
  "detected_language": "en",
  "progress": 45,
  "duration_seconds": 127.4
}
```

**Response** `200 OK` (completed):

```json
{
  "id": "j_a1b2c3d4",
  "status": "completed",
  "created_at": "2026-02-08T12:00:00Z",
  "completed_at": "2026-02-08T12:02:15Z",
  "file_name": "vacation.mp4",
  "file_size": 52428800,
  "model": "base",
  "language": "auto",
  "detected_language": "en",
  "progress": 100,
  "duration_seconds": 127.4,
  "segments": [
    {
      "start": 0.0,
      "end": 3.52,
      "text": "Hey everyone, welcome back to another review."
    },
    {
      "start": 3.52,
      "end": 7.18,
      "text": "Today we're looking at something really interesting."
    }
  ]
}
```

**Response** `200 OK` (failed):

```json
{
  "id": "j_a1b2c3d4",
  "status": "failed",
  "created_at": "2026-02-08T12:00:00Z",
  "file_name": "vacation.mp4",
  "file_size": 52428800,
  "model": "base",
  "language": "auto",
  "progress": 0,
  "error": {
    "code": "NO_AUDIO_TRACK",
    "message": "The uploaded video contains no audio track."
  }
}
```

**Error**: `404 JOB_NOT_FOUND`

### GET /api/jobs/{id}/captions.srt

Download captions in SRT format.

**Response** `200 OK` — `Content-Type: text/plain; charset=utf-8`

```
1
00:00:00,000 --> 00:00:03,520
Hey everyone, welcome back to another review.

2
00:00:03,520 --> 00:00:07,180
Today we're looking at something really interesting.
```

**Error**: `404 JOB_NOT_FOUND`, `409 {"error": {"code": "JOB_NOT_READY", "message": "Job is still processing"}}`

### GET /api/jobs/{id}/captions.vtt

Download captions in WebVTT format.

**Response** `200 OK` — `Content-Type: text/vtt; charset=utf-8`

```
WEBVTT

00:00:00.000 --> 00:00:03.520
Hey everyone, welcome back to another review.

00:00:03.520 --> 00:00:07.180
Today we're looking at something really interesting.
```

### GET /api/jobs/{id}/transcript.txt

Download plain text transcript (no timestamps).

**Response** `200 OK` — `Content-Type: text/plain; charset=utf-8`

```
Hey everyone, welcome back to another review. Today we're looking at something really interesting.
```

### DELETE /api/jobs/{id}

Delete a job and all its artifacts.

**Response** `204 No Content`

**Error**: `404 JOB_NOT_FOUND`

### GET /api/health

Health check endpoint.

**Response** `200 OK`:

```json
{
  "status": "ok",
  "ffmpeg": true,
  "models_available": ["tiny", "base"]
}
```

---

## D. Job Model & Processing Pipeline

### Job statuses and transitions

```
  ┌─────────┐
  │ queued  │  (file uploaded, waiting for worker)
  └────┬────┘
       │
       ▼
  ┌──────────────┐
  │ processing   │  (ffmpeg extracting audio → whisper transcribing)
  └──┬───────┬───┘
     │       │
     ▼       ▼
┌─────────┐ ┌────────┐
│completed│ │ failed │
└─────────┘ └────────┘
```

**Status definitions**:
- `queued` — File saved to disk, job metadata written. Waiting for processing thread.
- `processing` — Worker has picked up the job. Progress updates via file.
- `completed` — Transcription done, SRT/VTT/TXT files generated.
- `failed` — Unrecoverable error. Error details saved to job metadata.

### Job data structure (persisted as JSON)

```python
# backend/app/models.py

class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Segment(BaseModel):
    start: float        # seconds, e.g. 3.52
    end: float          # seconds, e.g. 7.18
    text: str           # trimmed caption text

class JobError(BaseModel):
    code: str           # e.g. "NO_AUDIO_TRACK"
    message: str

class Job(BaseModel):
    id: str                          # "j_" + 8 hex chars
    status: JobStatus
    created_at: datetime
    completed_at: datetime | None = None
    file_name: str
    file_size: int                   # bytes
    model: str                       # "tiny" | "base" | "small"
    language: str                    # "auto" | ISO 639-1
    detected_language: str | None = None
    progress: int = 0                # 0-100
    duration_seconds: float | None = None
    segments: list[Segment] | None = None
    error: JobError | None = None
```

### File layout on disk

```
data/
└── jobs/
    └── j_a1b2c3d4/
        ├── meta.json           # Job model serialized
        ├── input.mp4           # Original uploaded file (or .mov/.webm)
        ├── audio.wav           # Extracted by ffmpeg (16kHz mono)
        ├── captions.srt        # Generated on completion
        ├── captions.vtt        # Generated on completion
        └── transcript.txt      # Generated on completion
```

### Processing pipeline (worker.py)

```
1. RECEIVE upload
   ├── Generate job ID (j_ + secrets.token_hex(4))
   ├── Save uploaded file to data/jobs/{id}/input.{ext}
   │   └── Stream to disk in chunks (64KB) — never load full file in memory
   ├── Write meta.json with status=queued
   └── Enqueue job ID to processing queue

2. WORKER picks up job
   ├── Update status → processing, progress → 0
   │
   ├── STEP 1: Probe video with ffprobe (get duration, check audio stream)
   │   ├── If no audio stream → fail with NO_AUDIO_TRACK
   │   └── Save duration_seconds to meta.json
   │
   ├── STEP 2: Extract audio with ffmpeg          [progress: 0 → 20]
   │   └── ffmpeg -i input.mp4 -vn -ar 16000 -ac 1 -f wav audio.wav
   │       (16kHz mono WAV — what whisper expects)
   │
   ├── STEP 3: Transcribe with faster-whisper     [progress: 20 → 90]
   │   ├── Load model (cached in memory after first use)
   │   ├── model.transcribe("audio.wav", language=..., beam_size=5)
   │   ├── Iterate segments, update progress based on segment.end / duration
   │   └── Collect all segments
   │
   ├── STEP 4: Generate output files              [progress: 90 → 100]
   │   ├── Write captions.srt
   │   ├── Write captions.vtt
   │   ├── Write transcript.txt
   │   └── Save segments to meta.json
   │
   └── Update status → completed, progress → 100

3. ON FAILURE at any step:
   ├── Update status → failed
   ├── Write error code + message to meta.json
   └── Clean up partial files (audio.wav if it exists)
```

### Avoiding memory blowups

- **Upload**: Stream file to disk in 64KB chunks using `request.stream()` / `UploadFile.read(size)`. Never `await file.read()` the entire file.
- **ffmpeg**: Writes directly to disk. Subprocess, not in-memory.
- **faster-whisper**: Reads WAV from disk. Returns a generator of segments — iterate, don't collect-all then process.
- **Progress writes**: Atomic write via write-to-temp-then-rename pattern for meta.json.
- **Max file size**: Configurable, default 500MB. Enforced in the upload route via `Content-Length` header check + streaming byte count.

### Processing queue

For MVP (single-user), use a simple `threading.Thread` with a `queue.Queue`:
- One worker thread started at app lifespan startup
- Queue depth of 1 is fine for single-user
- Job picked up immediately if worker is idle, otherwise waits

This is intentionally simple. For production multi-user scaling, replace with Celery/Redis or similar — but that's post-MVP.

### Progress tracking

Progress is stored in `meta.json` and polled by the frontend every 2 seconds.

| Phase | Progress Range | How measured |
|-------|---------------|--------------|
| Queued | 0 | Static |
| Audio extraction | 0 → 20 | Set to 20 when ffmpeg completes |
| Transcription | 20 → 90 | `20 + 70 * (last_segment_end / total_duration)` |
| File generation | 90 → 100 | Set to 100 when files written |

---

## E. Subtitle Generation Method

### Segment data from faster-whisper

faster-whisper returns segments with these fields:
```python
segment.start   # float, seconds (e.g., 3.52)
segment.end     # float, seconds (e.g., 7.18)
segment.text    # str (e.g., " Hey everyone, welcome back.")
```

We strip leading/trailing whitespace from `segment.text`.

### Time formatting

```python
def format_srt_time(seconds: float) -> str:
    """00:01:23,456"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def format_vtt_time(seconds: float) -> str:
    """00:01:23.456"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
```

Note: SRT uses comma for milliseconds (`00:00:03,520`), VTT uses dot (`00:00:03.520`).

### SRT format

```
{index}\n
{start} --> {end}\n
{text}\n
\n
```

Example output:
```
1
00:00:00,000 --> 00:00:03,520
Hey everyone, welcome back to another review.

2
00:00:03,520 --> 00:00:07,180
Today we're looking at something really interesting.
```

Rules:
- Index starts at 1, increments by 1
- Blank line between entries
- No blank line at end of file
- Text is plain (no HTML tags for MVP)

### VTT format

```
WEBVTT\n
\n
{start} --> {end}\n
{text}\n
\n
```

Example:
```
WEBVTT

00:00:00.000 --> 00:00:03.520
Hey everyone, welcome back to another review.

00:00:03.520 --> 00:00:07.180
Today we're looking at something really interesting.
```

Rules:
- Must start with `WEBVTT` header
- No cue numbering needed (optional in spec; omit for simplicity)
- Blank line between cues

### TXT format

All segment texts joined with a single space. No timestamps.

```
Hey everyone, welcome back to another review. Today we're looking at something really interesting.
```

### Subtitle generation (backend/app/subtitles.py)

Three pure functions, each takes `list[Segment]` and returns `str`:
- `generate_srt(segments) -> str`
- `generate_vtt(segments) -> str`
- `generate_txt(segments) -> str`

Written to disk atomically (write to `.tmp`, then `os.rename`).

---

## F. Storage & Retention Strategy

### Local mode (Chromebook)

```
./data/                          # Gitignored, lives at repo root
└── jobs/
    └── j_{id}/
        ├── meta.json
        ├── input.{ext}
        ├── audio.wav
        ├── captions.srt
        ├── captions.vtt
        └── transcript.txt
```

- **Path**: Configurable via `DATA_DIR` env var, default `./data`
- **Persistence**: Survives restarts. Just files on disk.
- **Cleanup**: Manual. User can delete `./data/jobs/j_xxx/` or use `DELETE /api/jobs/{id}`.
- **No TTL enforced locally** — it's your machine, your files.

### Production mode

**Recommended: Persistent volume (not object storage)**

Why:
- ffmpeg and faster-whisper both need local file paths
- Object storage (S3) would require download-process-upload cycles for every step
- Persistent volumes on Fly.io/Render/Railway are simple and cheap (~$0.15/GB/month)
- Files are temporary processing artifacts, not long-term storage

```
/data/                           # Mounted persistent volume
└── jobs/
    └── j_{id}/
        ├── meta.json
        ├── input.{ext}          # Deleted after transcription completes
        ├── audio.wav            # Deleted after transcription completes
        ├── captions.srt         # Retained until TTL or manual delete
        ├── captions.vtt
        └── transcript.txt
```

**Retention plan (production)**:
- Input video + audio.wav: Deleted immediately after transcription completes (save space, privacy)
- Caption files + meta.json: Retained for **24 hours** after completion, then eligible for cleanup
- Cleanup: A simple cron/scheduled task that deletes job dirs older than 24h
  - MVP: Add a `/scripts/cleanup.sh` that can be run via cron
  - Later: Background thread in the app itself
- The `DELETE /api/jobs/{id}` endpoint provides immediate manual deletion

**Storage abstraction**: For MVP, `storage.py` is a thin wrapper around `pathlib.Path` operations. It provides:
- `save_upload(job_id, file_stream, filename) -> Path`
- `read_file(job_id, filename) -> Path`
- `delete_job(job_id)`
- `list_jobs() -> list[str]`

If we ever need S3, we replace this one module. But persistent volume is the right call for this app.

### Privacy notes

- **Local mode**: Files never leave the machine. Period.
- **Production mode**:
  - Input videos are deleted after processing
  - Caption files auto-expire in 24h
  - Users can manually delete at any time
  - No analytics, no logging of file contents
  - Add a simple privacy notice in the UI: "Your video is processed and deleted. Captions are stored for 24 hours."

---

## G. Local Chromebook Setup Plan

### Prerequisites

Chromebook must have Linux (Crostini) enabled:
- Settings → Advanced → Developers → Linux development environment → Turn on

### One-time setup script (`scripts/setup-chromebook.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== Caption This: Chromebook Setup ==="

# 1. System packages
sudo apt update
sudo apt install -y ffmpeg python3 python3-pip python3-venv nodejs npm

# 2. Python virtual environment + backend deps
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# requirements.txt includes: fastapi, uvicorn[standard], faster-whisper,
#   python-multipart, pydantic-settings
deactivate
cd ..

# 3. Frontend deps
cd frontend
npm install
cd ..

# 4. Download default whisper model (base)
echo "Downloading whisper 'base' model (140MB)..."
python3 -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

echo ""
echo "=== Setup complete! ==="
echo "Run: ./scripts/dev.sh"
echo "Then open http://$(hostname -I | awk '{print $1}'):5173 on your iPhone"
```

### Dev run script (`scripts/dev.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail

LAN_IP=$(hostname -I | awk '{print $1}')

echo "Starting Caption This..."
echo "Frontend: http://${LAN_IP}:5173"
echo "Backend:  http://${LAN_IP}:8000"
echo "API docs: http://${LAN_IP}:8000/docs"
echo ""

# Start backend
cd backend
source .venv/bin/activate
DATA_DIR=../data CORS_ORIGINS="*" uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Start frontend
cd frontend
VITE_API_URL="http://${LAN_IP}:8000" npx vite --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!
cd ..

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
```

**Result**: Two commands to go from clone to running:
```
./scripts/setup-chromebook.sh    # once
./scripts/dev.sh                 # every time
```

---

## H. Production Deployment Plan

### Frontend on Vercel

1. **Connect repo** to Vercel (import `caption-this` repo)
2. **Configure build**:
   - Framework preset: Vite
   - Root directory: `frontend`
   - Build command: `npm run build`
   - Output directory: `dist`
3. **Environment variable**:
   - `VITE_API_URL` = `https://captions-api.tonyreviewsthings.com`
4. **vercel.json** (in `frontend/`):
   ```json
   {
     "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
   }
   ```
5. **Custom domain**: Point `captions.tonyreviewsthings.com` to Vercel in DNS (CNAME)

### Backend container (host-agnostic)

**Dockerfile** (`deploy/Dockerfile`):

```dockerfile
FROM python:3.12-slim

# Install ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download models (bake into image for fast cold starts)
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8')"
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

# Copy app code
COPY backend/app ./app

# Data directory (mount persistent volume here)
VOLUME /data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Env vars for production**:
```
DATA_DIR=/data
CORS_ORIGINS=https://captions.tonyreviewsthings.com
MAX_FILE_SIZE=524288000   # 500MB
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

### Deploy to Fly.io (example)

```bash
fly launch --no-deploy
fly volumes create caption_data --size 10 --region ord
# Edit fly.toml to mount volume at /data
fly deploy
fly secrets set CORS_ORIGINS=https://captions.tonyreviewsthings.com
```

### Deploy to Render (example)

- Create new Web Service from Docker
- Mount persistent disk at `/data`
- Set env vars
- Point custom domain `captions-api.tonyreviewsthings.com`

### Deploy to Railway (example)

- New project from Dockerfile
- Add volume mounted at `/data`
- Set env vars
- Custom domain via Railway's settings

### DNS / Subdomain routing

```
captions.tonyreviewsthings.com       → Vercel (frontend)
captions-api.tonyreviewsthings.com   → Container host (backend)
```

Both subdomains get HTTPS automatically from their respective hosts. No reverse proxy needed.

---

## I. Build Plan for Sonnet 4.5

Ordered for fastest path to a working end-to-end slice. Each stop point is a usable milestone.

### Phase 1: Backend skeleton (get transcription working via curl)

**Step 1**: Create repo structure, `.gitignore`, and `README.md` stub.

**Step 2**: Backend foundation — `main.py`, `config.py`, `models.py`, `storage.py`.
- FastAPI app with CORS middleware
- `GET /api/health` endpoint
- Pydantic settings loading env vars
- Job model with Pydantic
- File storage helpers (save, read, delete, list)

**Step 3**: Upload + job creation — `routes.py` `POST /api/jobs`.
- Accept multipart upload
- Stream file to disk in chunks
- Validate file type (check content-type + extension)
- Validate file size (streaming byte counter)
- Create job directory and meta.json
- Return job object with status=queued

**Step 4**: Processing pipeline — `worker.py`, `transcriber.py`.
- Background worker thread with queue
- ffprobe to get duration and verify audio track
- ffmpeg audio extraction (subprocess)
- faster-whisper transcription with progress tracking
- Update meta.json at each stage (atomic writes)

**Step 5**: Subtitle generation — `subtitles.py`.
- `generate_srt()`, `generate_vtt()`, `generate_txt()`
- Write output files on job completion

**Step 6**: Remaining routes.
- `GET /api/jobs/{id}` — read and return meta.json
- `GET /api/jobs/{id}/captions.srt` — return file
- `GET /api/jobs/{id}/captions.vtt` — return file
- `GET /api/jobs/{id}/transcript.txt` — return file
- `DELETE /api/jobs/{id}` — remove job directory

**--- STOP POINT 1 ---**
> Backend is fully functional. You can upload a video via curl, poll status, and download SRT/VTT/TXT. Test this thoroughly before moving on.

```bash
# Test with curl:
curl -F "file=@test.mp4" -F "model=tiny" http://localhost:8000/api/jobs
curl http://localhost:8000/api/jobs/j_abc123
curl http://localhost:8000/api/jobs/j_abc123/captions.srt
```

### Phase 2: Frontend MVP (upload + status + download)

**Step 7**: Frontend scaffold — Vite + React + TypeScript.
- `npm create vite@latest frontend -- --template react-ts`
- Install deps: `react-router-dom`
- Set up router with two routes: `/` and `/job/:id`
- API client module (`api.ts`) with fetch wrapper
- Types matching backend Job model

**Step 8**: Upload page — `HomePage.tsx`, `UploadZone.tsx`.
- Drag-and-drop zone (also tap-to-select for mobile)
- File validation (type, size) with user-friendly errors
- Upload with progress bar (XHR for upload progress)
- Redirect to `/job/:id` on success
- Mobile-first CSS (works on iPhone Safari)

**Step 9**: Job status page — `JobPage.tsx`, `JobProgress.tsx`.
- Poll `GET /api/jobs/{id}` every 2 seconds
- Show status: queued → processing (with progress bar) → completed/failed
- Show file name, size, model used
- Stop polling when completed or failed

**Step 10**: Results — `DownloadPanel.tsx`, `TranscriptEditor.tsx`, `VideoPlayer.tsx`.
- Download buttons for SRT, VTT, TXT (direct links to backend)
- Plain text transcript view (read-only first, editable stretch goal)
- Video player with VTT captions:
  - `<video>` element with `<track kind="captions" src="...captions.vtt">`
  - Backend serves the original video at `GET /api/jobs/{id}/video` (add this route)

**--- STOP POINT 2 ---**
> Full app works end-to-end in a browser on the Chromebook. Upload → process → preview with captions → download. Test on desktop browser.

### Phase 3: Mobile polish + local dev experience

**Step 11**: Mobile Safari polish.
- Test and fix touch interactions for drag-and-drop (fallback to file picker)
- Ensure video player works on iOS (may need `playsinline` attribute)
- Viewport meta tag, responsive layout
- Test on actual iPhone over LAN

**Step 12**: Dev scripts.
- `scripts/setup-chromebook.sh`
- `scripts/dev.sh`
- `scripts/download-model.sh`

**Step 13**: `docker-compose.yml` for local dev.
- Backend service with volume mount
- Frontend service
- Alternative to `dev.sh` for those who prefer Docker

**--- STOP POINT 3 ---**
> Complete local MVP. Works on Chromebook, accessible from iPhone. Setup is two commands. This is the "ship it" milestone for local use.

### Phase 4: Production readiness

**Step 14**: Production Dockerfile (`deploy/Dockerfile`).
- Multi-stage build
- Pre-baked models
- Health check

**Step 15**: Production configs.
- `fly.toml.example`
- `render.yaml.example`
- Environment variable documentation

**Step 16**: Production hardening.
- Input video + audio.wav deletion after transcription
- CORS lockdown (only allow configured origins)
- Request size limits enforced at framework level
- Graceful shutdown (finish current job before stopping)

**Step 17**: README.md with full documentation.
- Clone-to-run instructions for Chromebook
- Architecture diagram
- Production deployment guide
- API reference

**--- STOP POINT 4 ---**
> Production-ready. Can deploy frontend to Vercel + backend to Fly.io and it works.

---

## J. Test Plan & Definition of Done

### Minimal test plan

**Backend unit tests** (pytest):
1. `test_subtitles.py` — SRT/VTT/TXT generation from known segments (pure functions, easy to test)
2. `test_models.py` — Job model serialization/deserialization
3. `test_storage.py` — File operations (save, read, delete, atomic writes)

**Backend integration tests** (pytest + httpx):
4. `test_upload.py` — POST /api/jobs with valid/invalid files, check responses
5. `test_job_status.py` — Create job, poll until completed, verify artifacts exist
6. `test_download.py` — Download SRT/VTT/TXT, verify content format
7. `test_errors.py` — Invalid file type, oversized file, nonexistent job

**Frontend tests** (Vitest + React Testing Library):
8. `UploadZone.test.tsx` — Renders, accepts files, rejects invalid types
9. `JobProgress.test.tsx` — Renders correct UI for each status
10. `api.test.ts` — API client formats requests correctly, handles errors

**Manual end-to-end tests** (checklist):
11. Upload 10-second MP4 via Chromebook browser → completes → download SRT
12. Upload 2-minute MOV → completes → captions look correct
13. Upload from iPhone Safari over LAN → full flow works
14. Upload file with no audio → shows clear error
15. Upload non-video file → rejected with helpful message
16. Upload oversized file → rejected before full upload
17. Refresh during processing → status resumes correctly
18. VTT captions sync with video in preview player
19. Download all three formats, verify each is well-formed

### Definition of Done

- [ ] `git clone` + `./scripts/setup-chromebook.sh` + `./scripts/dev.sh` results in a running app
- [ ] Upload a video from Chromebook browser → see captions generated
- [ ] Upload a video from iPhone Safari (over LAN) → see captions generated
- [ ] Progress bar advances during transcription
- [ ] Download SRT file → valid SRT with correct timestamps
- [ ] Download VTT file → valid VTT with correct timestamps
- [ ] Download TXT file → readable transcript
- [ ] Video preview plays with captions overlaid
- [ ] Error cases show user-friendly messages (no raw stack traces)
- [ ] Backend handles 500MB file without crashing (streaming upload)
- [ ] Refreshing the job page shows current status (not lost)
- [ ] `DELETE /api/jobs/{id}` removes all artifacts
- [ ] Backend Dockerfile builds and runs correctly
- [ ] All automated tests pass
- [ ] No hardcoded IPs or secrets in committed code

---

## Appendix: Key Dependencies

### Backend (`requirements.txt`)

```
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
faster-whisper>=1.1.0
python-multipart>=0.0.18
pydantic>=2.10.0
pydantic-settings>=2.7.0
```

### Frontend (`package.json` deps)

```json
{
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.0.0",
    "typescript": "^5.7.0",
    "vite": "^6.0.0"
  }
}
```

Intentionally minimal. No UI framework — use plain CSS with a few custom styles. The app has ~5 screens. Tailwind or a component library would be overkill and add install weight on the Chromebook.

### System dependencies

- `ffmpeg` (apt install, or in Docker image)
- `python3` >= 3.11
- `node` >= 20
- `npm` >= 10
