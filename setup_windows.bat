@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo  FaceAttend AI — Windows Local Setup
echo ============================================================

:: Check Python
python --version 2>nul || (
    echo [ERROR] Python not found. Please install Python 3.10 or 3.11 from python.org.
    pause
    exit /b
)

:: Create virtual environment
echo.
echo [1/4] Creating virtual environment (venv)...
python -m venv venv
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to create venv. 
    pause
    exit /b
)

call venv\Scripts\activate.bat

:: Upgrade pip
echo.
echo [2/4] Upgrading pip...
python -m pip install --upgrade pip wheel setuptools

:: Install dependencies
echo.
echo [3/4] Installing dependencies...
:: Install cmake and dlib first (dlib takes time)
pip install cmake
pip install dlib

:: Install all requirements
pip install -r requirements.txt

:: Copy env file
if not exist backend\.env (
    echo.
    echo [4/4] Creating default configuration...
    copy .env.example backend\.env
)

echo.
echo ============================================================
echo  Setup complete!
echo.
echo  To start the application, just double-click:
echo    run_app.bat
echo.
echo  The dashboard will open at: http://localhost:8000
echo  Login: admin / admin123
echo ============================================================
pause
endlocal
