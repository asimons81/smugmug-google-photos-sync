#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

MODEL="${1:-base}"

if [[ ! "$MODEL" =~ ^(tiny|base|small|medium|large-v3)$ ]]; then
    echo "Usage: $0 [tiny|base|small|medium|large-v3]"
    echo "Default: base"
    exit 1
fi

echo "Downloading whisper model: ${MODEL}..."

cd "$ROOT_DIR/backend"
source .venv/bin/activate
python3 -c "from faster_whisper import WhisperModel; WhisperModel('${MODEL}', device='cpu', compute_type='int8')"
deactivate

echo "Model '${MODEL}' downloaded and cached."
