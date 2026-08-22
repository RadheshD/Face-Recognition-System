@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo  FaceAttend AI — Starting Application...
echo ============================================================

:: Find virtual environment
set VENV_PATH=
if exist venv_310\Scripts\activate.bat (
    set VENV_PATH=venv_310
) else if exist venv\Scripts\activate.bat (
    set VENV_PATH=venv
)

if "%VENV_PATH%"=="" (
    echo [ERROR] Virtual environment not found. 
    echo Please run setup_windows.bat first to install dependencies.
    pause
    exit /b
)

echo [1/3] Activating virtual environment (%VENV_PATH%)...
call %VENV_PATH%\Scripts\activate.bat

echo [2/3] Opening dashboard in browser...
:: Small delay to let the server start
start http://127.0.0.1:8000

echo [3/3] Starting backend server...
cd backend
python main.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Failed to start the server. 
    echo Make sure you have installed all requirements.
    pause
)

endlocal
