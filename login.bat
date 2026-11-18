@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo 没有找到 python，请先安装 Python 3.8 或更高版本（安装时勾选 Add Python to PATH）
  pause
  exit /b
)
echo 正在打开 Chrome 窗口，请在窗口里登录 SRGI（只需登录一次）
echo.
python srgi_login.py
echo.
pause
