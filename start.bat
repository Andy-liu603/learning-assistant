@echo off
chcp 65001 >nul
echo ==========================================
echo   AI Learning Assistant v2.0
echo ==========================================

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

:: Activate virtual environment
call .venv\Scripts\activate.bat
if exist ".venv\Scripts\python.exe" (
    echo [INFO] Using virtual environment Python
) else (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv .venv
    echo Then: .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: Install dependencies (first run only)
if not exist "backend\__init__.py" (
    echo [INFO] Installing dependencies...
    set PYTHONUTF8=1
    pip install -r requirements.txt -q
)

:: Check .env
if not exist ".env" (
    echo [WARN] .env not found, copying from template...
    copy .env.example .env
    echo [WARN] Please edit .env and add your LLM API Key!
    notepad .env
)

:: HuggingFace offline mode
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1

echo.
echo [INFO] Starting Flask backend + frontend...
echo.

python backend\app.py

pause
