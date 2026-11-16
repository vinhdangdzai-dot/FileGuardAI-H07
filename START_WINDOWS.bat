@echo off
cd /d "%~dp0"
echo [H07] FileGuard AI - setup and run on localhost
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
if not exist "artifacts\model.joblib" (
    ".venv\Scripts\python.exe" -m ml.train_model
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" run.py
exit /b %errorlevel%
:failed
echo Setup failed. Check Python and internet access.
pause
exit /b 1
