# Starts the Server (port 8000) and the Client (port 5173) together.
Set-Location (Join-Path $PSScriptRoot "..")
$server = Start-Process -PassThru -NoNewWindow .venv\Scripts\python -ArgumentList "-m", "uvicorn", "Server.main:app", "--reload", "--port", "8000"
try {
    Push-Location Client
    npm run dev
} finally {
    Pop-Location
    Stop-Process -Id $server.Id -ErrorAction SilentlyContinue
}
