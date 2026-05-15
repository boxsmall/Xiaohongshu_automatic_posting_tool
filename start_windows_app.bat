@echo off
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python launch_windows.py
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        py -3 launch_windows.py
    ) else (
        echo 没有找到 Python。请先安装 Python 3.12 或更高版本。
    )
)

echo.
echo 按任意键关闭窗口...
pause >nul
