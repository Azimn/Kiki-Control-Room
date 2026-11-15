@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
  echo Python launcher not found. Install Python 3.10 or later from python.org.
  pause
  exit /b 1
)
py -3 -c "from zoneinfo import ZoneInfo; ZoneInfo('America/Chicago')" >nul 2>&1
if errorlevel 1 (
  echo Installing the small Windows timezone database once...
  py -3 -m pip install --user tzdata
  if errorlevel 1 (
    echo Timezone installation failed. See docs\LOCAL_INSTALL.md.
    pause
    exit /b 1
  )
)
echo Kiki will store data in your local user profile.
echo Open http://localhost:8765 in your browser.
py -3 runtime\local\kiki_local.py
if errorlevel 1 pause
