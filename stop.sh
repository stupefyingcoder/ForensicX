#!/usr/bin/env bash

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log() { echo -e "${GREEN}[ForensicX]${NC} $1"; }

# Kill backend (uvicorn on port 8000)
BACKEND_PIDS=$(lsof -ti :8000 2>/dev/null)
if [ -n "$BACKEND_PIDS" ]; then
    echo "$BACKEND_PIDS" | xargs kill -9 2>/dev/null
    log "Backend stopped."
else
    log "No backend running on :8000."
fi

# Kill frontend (vite on port 5173)
FRONTEND_PIDS=$(lsof -ti :5173 2>/dev/null)
if [ -n "$FRONTEND_PIDS" ]; then
    echo "$FRONTEND_PIDS" | xargs kill -9 2>/dev/null
    log "Frontend stopped."
else
    log "No frontend running on :5173."
fi

log "All stopped."
