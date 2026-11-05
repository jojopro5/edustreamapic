@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
  py -3 server.py --port 8765
  goto :end
)

where python >nul 2>&1
if %errorlevel%==0 (
  python server.py --port 8765
  goto :end
)

echo Python was not found. Install Python 3.11 or newer and run this file again.
pause

:end
endlocal
