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
        echo [错误] 未检测到 Python，请先安装 Python 3 并加入 PATH。
        pause
        exit /b 1
    )
)

echo [信息] 正在安装或检查依赖...
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败。
    pause
    exit /b 1
)

echo [信息] 正在启动自动赚钱脚本面板...
%PYTHON_CMD% auto_money_gui.py

if errorlevel 1 (
    echo [错误] 程序启动失败。
    pause
    exit /b 1
)

endlocal
