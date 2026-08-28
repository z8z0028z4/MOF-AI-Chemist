#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "[ERROR] .venv directory not found. Please create it and install requirements."
    exit 1
fi

# Preserve the configured enterprise CA for the backend and fail before
# startup when it points at a missing file. Otherwise use system trust.
for CA_VAR in REQUESTS_CA_BUNDLE SSL_CERT_FILE; do
    CA_VALUE="${!CA_VAR:-}"
    if [ -n "$CA_VALUE" ] && [ ! -f "$CA_VALUE" ]; then
        echo "[ERROR] $CA_VAR points to a missing CA bundle: $CA_VALUE"
        exit 1
    fi
    if [ -n "$CA_VALUE" ]; then
        export "$CA_VAR"
    fi
done

echo "Starting backend service..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend --log-level info
