#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "[ERROR] .venv directory not found. Please create it and install requirements."
    exit 1
fi

echo "Starting backend service..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend --log-level info
