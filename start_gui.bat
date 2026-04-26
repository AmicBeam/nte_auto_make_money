@echo off
setlocal

cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PYTHON_CMD=python"
    ) else (
        echo [ERROR] Python was not found. Please install Python 3 and add it to PATH.
        pause
        exit /b 1
    )
)

echo [INFO] Installing or checking dependencies...
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [INFO] Launching GUI panel...
%PYTHON_CMD% auto_money_gui.py

if errorlevel 1 (
    echo [ERROR] Failed to launch the program.
    pause
    exit /b 1
)

endlocal
