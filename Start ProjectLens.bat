@echo off
rem Double-click to run ProjectLens: installs everything on the first run, starts the Server and the Client,
rem and opens the app in the browser when it is ready. Close this window to stop the app.
title ProjectLens
cd /d "%~dp0"

rem Already running (for example a second double-click): just open the browser.
powershell -NoProfile -Command "try { Invoke-WebRequest http://localhost:5173 -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if %errorlevel%==0 (
    echo ProjectLens is already running. Opening it in the browser...
    start "" http://localhost:5173
    exit /b 0
)

rem First run: Python environment, packages, embedding model and Client packages.
if not exist ".venv\Scripts\python.exe" goto setup
if not exist "Client\node_modules" goto setup
goto start

:setup
echo First run: installing everything. This takes a few minutes, only once.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup.ps1
if errorlevel 1 (
    echo.
    echo Setup failed. Read the message above, then double-click this file again.
    pause
    exit /b 1
)

:start
rem Open the browser as soon as the Client answers (checked every second, for up to 2 minutes).
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "for ($i = 0; $i -lt 120; $i++) { try { Invoke-WebRequest http://localhost:5173 -UseBasicParsing -TimeoutSec 2 | Out-Null; Start-Process 'http://localhost:5173'; break } catch { Start-Sleep -Seconds 1 } }"

echo Starting ProjectLens. The browser opens by itself when the app is ready.
echo Keep this window open while you use the app; close it to stop ProjectLens.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start.ps1
pause
