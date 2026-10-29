@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\python.exe" (
    start "TSPL Label Desk" /D "%~dp0" "%~dp0.venv\Scripts\python.exe" "%~dp0src\app.py" %*
) else (
    start "TSPL Label Desk" /D "%~dp0" py -3 "%~dp0src\app.py" %*
)
endlocal
