@echo off
echo Setting up AI-Powered ATS Application...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Create uploads directory
if not exist "uploads" mkdir uploads

REM Copy environment template
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo Please edit .env file with your configuration
)

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Edit .env file with your Mistral API key and other settings
echo 2. Run: python app.py
echo 3. Open http://localhost:5000 in your browser
echo.
pause
