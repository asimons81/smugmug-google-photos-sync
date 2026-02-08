#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo "============================================"
echo "  Caption This — Dev Server"
echo "============================================"
echo ""
echo "  Frontend:  http://${LAN_IP}:5173"
echo "  Backend:   http://${LAN_IP}:8000"
echo "  API docs:  http://${LAN_IP}:8000/docs"
echo ""
echo "  Open the Frontend URL on your iPhone!"
echo "============================================"
echo ""

# Create data directory
mkdir -p "$ROOT_DIR/data"

# Start backend
cd "$ROOT_DIR/backend"
source .venv/bin/activate
DATA_DIR="$ROOT_DIR/data" \
CORS_ORIGINS="*" \
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd "$ROOT_DIR"

# Start frontend
cd "$ROOT_DIR/frontend"
VITE_API_URL="http://${LAN_IP}:8000" npx vite --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!
cd "$ROOT_DIR"

# Cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
    echo "Done."
}
trap cleanup EXIT INT TERM

wait
