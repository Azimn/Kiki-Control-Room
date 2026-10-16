@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-airi\Scripts\python.exe" (
  py -3 -m venv .venv-airi
  if errorlevel 1 goto failed
)
.venv-airi\Scripts\python.exe -m pip install -r runtime\airi\requirements.txt
if errorlevel 1 goto failed
.venv-airi\Scripts\python.exe runtime\airi\bridge.py
if errorlevel 1 goto failed
exit /b 0
:failed
 echo Kiki could not start. Check that Python 3.10 or newer is installed and review the error above.
 pause
 exit /b 1
