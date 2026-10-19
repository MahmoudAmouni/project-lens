#!/usr/bin/env bash
# Starts the Server (port 8000) and the Client (port 5173) together.
cd "$(dirname "$0")/.."
.venv/bin/python -m uvicorn Server.main:app --reload --port 8000 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null' EXIT
(cd Client && npm run dev)
