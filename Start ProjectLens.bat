@echo off
cd /d "%~dp0"
start "ProjectLens Server" .venv\Scripts\python -m uvicorn Server.main:app --port 8000
cd Client
npm run dev -- --open
