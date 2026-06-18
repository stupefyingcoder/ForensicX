#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/venv"
PYTHON="python3.12"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[ForensicX]${NC} $1"; }
warn() { echo -e "${YELLOW}[ForensicX]${NC} $1"; }
err()  { echo -e "${RED}[ForensicX]${NC} $1"; }

cleanup() {
    log "Shutting down..."
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
    wait 2>/dev/null
    
    log "Done."
}
trap cleanup EXIT INT TERM

# --- Check prerequisites ---

log "Checking prerequisites..."

if ! command -v "$PYTHON" &>/dev/null; then
    err "Python 3.12 not found. Install it with: brew install python@3.12"
    exit 1
fi

if ! command -v node &>/dev/null; then
    err "Node.js not found. Install it with: brew install node"
    exit 1
fi

if ! command -v npm &>/dev/null; then
    err "npm not found. Install it with: brew install node"
    exit 1
fi

# --- Backend setup ---

log "Setting up backend..."

if [ ! -d "$VENV_DIR" ]; then
    log "Creating Python 3.12 virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

log "Installing backend dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r "$BACKEND_DIR/requirements.txt"

# --- Download model weights if missing ---

WEIGHTS_DIR="$BACKEND_DIR/weights"
mkdir -p "$WEIGHTS_DIR"

download_weight() {
    local name="$1" url="$2"
    if [ ! -f "$WEIGHTS_DIR/$name" ]; then
        log "Downloading $name..."
        curl -L -o "$WEIGHTS_DIR/$name" "$url"
        log "$name downloaded."
    fi
}

# Lightweight models only — BSRGAN/x4plus omitted (too heavy for 8GB machines)
download_weight "realesr-general-x4v3.pth" \
    "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth"
download_weight "realesr-general-wdn-x4v3.pth" \
    "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-wdn-x4v3.pth"

# --- Frontend setup ---

log "Setting up frontend..."

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    log "Installing frontend dependencies..."
    cd "$FRONTEND_DIR" && npm install --silent
else
    log "Frontend dependencies already installed."
fi

# --- Create .env files if missing ---

if [ ! -f "$BACKEND_DIR/.env" ]; then
    warn "No backend .env found — using defaults (SQLite, dev JWT secret)."
fi

if [ ! -f "$FRONTEND_DIR/.env" ]; then
    log "Creating frontend .env..."
    echo "VITE_API_BASE=http://127.0.0.1:8000/api" > "$FRONTEND_DIR/.env"
fi

# --- Start backend ---

log "Starting backend on http://127.0.0.1:8000 ..."
cd "$BACKEND_DIR"
"$VENV_DIR/bin/uvicorn" app.main:app --reload --port 8000 --host 127.0.0.1 &
BACKEND_PID=$!

# Wait for backend to be ready
log "Waiting for backend..."
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:8000/health &>/dev/null; then
        log "Backend is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        err "Backend failed to start. Check the logs above."
        exit 1
    fi
    sleep 1
done

# --- Start frontend ---

log "Starting frontend on http://localhost:5173 ..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

sleep 2

echo ""
log "========================================="
log "  ForensicX is running!"
log "  Frontend: http://localhost:5173"
log "  Backend:  http://127.0.0.1:8000"
log "  API docs: http://127.0.0.1:8000/docs"
log "========================================="
log "Press Ctrl+C to stop both servers."
echo ""

wait
