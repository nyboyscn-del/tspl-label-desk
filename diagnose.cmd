@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -c "import importlib.util; names=('PIL','barcode','qrcode','win32print'); print('Project venv: PASS'); [print(n+': '+('AVAILABLE' if importlib.util.find_spec(n) else 'NOT INSTALLED')) for n in names]"
) else (
    py -3 -c "import importlib.util; names=('PIL','barcode','qrcode','win32print'); print('System Python: PASS'); [print(n+': '+('AVAILABLE' if importlib.util.find_spec(n) else 'NOT INSTALLED')) for n in names]"
)
powershell -NoProfile -Command "$c=Get-NetTCPConnection -LocalPort 8630 -State Listen -ErrorAction SilentlyContinue; if($c){'Port 8630: LISTENING'}else{'Port 8630: not listening'}"
endlocal
