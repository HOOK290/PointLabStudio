@echo off
chcp 65001 >nul
rem PointLab Studio launcher - double click to start (no console window)
setlocal
cd /d "%~dp0"
title PointLab Studio

set "PYW=.venv\Scripts\pythonw.exe"
set "PY=.venv\Scripts\python.exe"

if not exist "%PYW%" goto no_venv

rem Dependency self-check: keep the console visible with a reason instead of failing silently.
"%PY%" -c "import PySide6, open3d, numpy, scipy" >nul 2>nul
if errorlevel 1 goto bad_deps

start "" "%PYW%" run.py %*
exit /b 0

:no_venv
echo.
echo [PointLab Studio] 没有找到虚拟环境 .venv
echo.
echo 首次运行请在同一目录执行：
echo     python -m venv .venv
echo     .venv\Scripts\python.exe -m pip install -r requirements-lock.txt
echo.
pause
exit /b 1

:bad_deps
echo.
echo [PointLab Studio] 依赖缺失或损坏，正在显示详细信息...
echo.
"%PY%" -c "import PySide6, open3d, numpy, scipy"
echo.
echo 修复方法：
echo     .venv\Scripts\python.exe -m pip install -r requirements.txt
echo.
pause
exit /b 1
