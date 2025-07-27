@echo off
cd /d "%~dp0"

REM Activate the virtual environment
call venv\Scripts\activate.bat

REM Run uvicorn server
uvicorn backend.main:app --reload --host 0.0.0.0

REM Optional: Pause to see output after it ends
pause
