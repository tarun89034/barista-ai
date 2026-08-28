#!/usr/bin/env bash
# =============================================================================
# Barista AI – Quick Start Script
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }

# ── Check Python ─────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    echo "Error: Python 3 is required. Install from https://python.org" >&2
    exit 1
fi
SYS_PY=$(command -v python3 || command -v python)

# ── Install Python deps ─────────────────────────────────────────────────────
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    info "Creating Python virtual environment..."
    "$SYS_PY" -m venv "$SCRIPT_DIR/.venv"
fi

# Resolve the venv interpreter explicitly. Activating alone is not enough:
# $SYS_PY holds an absolute path to the system python, so using it after
# activation installs into the venv but runs the server outside it.
if [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
    PY="$SCRIPT_DIR/.venv/bin/python"          # POSIX
elif [ -x "$SCRIPT_DIR/.venv/Scripts/python.exe" ]; then
    PY="$SCRIPT_DIR/.venv/Scripts/python.exe"  # Windows
else
    echo "Error: no interpreter found in $SCRIPT_DIR/.venv" >&2
    exit 1
fi

# shellcheck disable=SC1091
source "$SCRIPT_DIR/.venv/bin/activate" 2>/dev/null \n    || source "$SCRIPT_DIR/.venv/Scripts/activate" 2>/dev/null \n    || true

info "Installing Python dependencies..."
"$PY" -m pip install -q --upgrade pip
"$PY" -m pip install -q -r "$SCRIPT_DIR/requirements.txt"

# ── .env file ────────────────────────────────────────────────────────────────
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    warn "No .env file found. Copying .env.example → .env"
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    warn "Please edit .env and set GEMINI_API_KEY before using LLM features."
fi

# ── Build frontend (if Node.js available) ────────────────────────────────────
if command -v node &>/dev/null; then
    if [ ! -d "$SCRIPT_DIR/frontend/out" ]; then
        info "Building frontend..."
        (cd "$SCRIPT_DIR/frontend" && npm ci --no-audit --no-fund && npm run build)
    else
        info "Frontend already built (frontend/out/ exists). Skipping."
    fi
else
    warn "Node.js not found. Frontend won't be served. Install from https://nodejs.org"
fi

# ── Start server ─────────────────────────────────────────────────────────────
HOST="${API_HOST:-0.0.0.0}"
PORT="${API_PORT:-8000}"

info "Starting Barista AI on http://$HOST:$PORT ..."
"$PY" "$SCRIPT_DIR/main.py" serve --host "$HOST" --port "$PORT"
