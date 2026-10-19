#!/usr/bin/env bash
# One command setup for Mac/Linux: Python venv, packages, embedding model, Client packages.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v python3 >/dev/null; then
  echo "Installing Python..." && brew install python@3.12
fi
if ! command -v node >/dev/null; then
  echo "Installing Node.js..." && brew install node
fi

[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/warm_up_model.py

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env - add your GROQ_API_KEY to it."
fi

(cd Client && npm install)
echo "Setup done. Run scripts/start.sh to start ProjectLens."
