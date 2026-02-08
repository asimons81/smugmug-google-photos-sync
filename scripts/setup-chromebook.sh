#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Caption This: Chromebook Setup ==="
echo ""

# 1. System packages
echo "[1/4] Installing system packages (ffmpeg, python3, node)..."
sudo apt-get update -qq
sudo apt-get install -y -qq ffmpeg python3 python3-pip python3-venv nodejs npm > /dev/null

echo "  ffmpeg: $(ffmpeg -version 2>&1 | head -1)"
echo "  python: $(python3 --version)"
echo "  node:   $(node --version 2>/dev/null || echo 'not found')"
echo ""

# 2. Backend Python environment
echo "[2/4] Setting up Python virtual environment..."
cd "$ROOT_DIR/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install --quiet -r requirements.txt
deactivate
echo "  Backend dependencies installed."
echo ""

# 3. Frontend dependencies
echo "[3/4] Installing frontend dependencies..."
cd "$ROOT_DIR/frontend"
npm install --silent 2>/dev/null
echo "  Frontend dependencies installed."
echo ""

# 4. Download default whisper model
echo "[4/4] Downloading whisper 'base' model (~140 MB)..."
cd "$ROOT_DIR/backend"
source .venv/bin/activate
python3 -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"
deactivate
echo "  Model downloaded and cached."
echo ""

echo "=== Setup complete! ==="
echo ""
echo "To start the app:"
echo "  ./scripts/dev.sh"
echo ""
LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
echo "Then open in your browser:"
echo "  http://${LAN_IP}:5173"
