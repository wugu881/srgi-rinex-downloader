@echo off
setlocal
cd /d "%~dp0"

set "PY=python"
where python >nul 2>nul
if errorlevel 1 set "PY=py -3"
%PY% -c "import sys" >nul 2>nul
if errorlevel 1 (
  echo 没有找到 Python，请先安装 Python 3.8 或更高版本（安装时勾选 Add Python to PATH）
  pause
  exit /b 1
)

echo 正在打开 Chrome 窗口，请在窗口里登录 SRGI（只需登录一次）
echo.
%PY% srgi_login.py
echo.
pause
