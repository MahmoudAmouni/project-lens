# One command setup for Windows: Python venv, packages, embedding model, Client packages.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

# Windows PowerShell does not stop when a program (pip, npm) fails, so every step checks its exit code.
function Invoke-Step([string]$Name, [scriptblock]$Command) {
    Write-Host "== $Name"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Setup failed at: $Name (exit code $LASTEXITCODE)" -ForegroundColor Red
        exit 1
    }
}

# Some packages have deep folders; Windows refuses paths over 260 characters unless long paths are on.
if ((Get-Location).Path.Length -gt 60) {
    Write-Host "Warning: this folder path is long. If pip fails with 'No such file or directory'," -ForegroundColor Yellow
    Write-Host "clone the project into a short folder such as C:\projects\project-lens." -ForegroundColor Yellow
}

if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
    Invoke-Step "Install Python 3.12" { winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements }
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Invoke-Step "Install Node.js LTS" { winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements }
}

if (-not (Test-Path ".venv")) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        Invoke-Step "Create Python environment" { py -3 -m venv .venv }
    } else {
        Invoke-Step "Create Python environment" { python -m venv .venv }
    }
}
Invoke-Step "Upgrade pip" { .venv\Scripts\python -m pip install --upgrade pip }
Invoke-Step "Install Python packages" { .venv\Scripts\python -m pip install -r requirements.txt }
Invoke-Step "Download the embedding model" { .venv\Scripts\python scripts\warm_up_model.py }

if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "Created .env - add your GROQ_API_KEY to it."
}

Push-Location Client
Invoke-Step "Install Client packages" { npm install }
Pop-Location

Write-Host "Setup done. Run scripts\start.ps1 to start ProjectLens." -ForegroundColor Green
