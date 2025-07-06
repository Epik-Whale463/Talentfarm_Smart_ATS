@echo off
echo Starting AI-Powered ATS Application...
echo.

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

REM Check if .env exists
if not exist ".env" (
    echo .env file not found. Please copy .env.example to .env and configure it.
    pause
    exit /b 1
)

REM Start the application
echo Starting Flask application...
python app.py
