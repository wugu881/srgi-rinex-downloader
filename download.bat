@echo off
setlocal enableextensions
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

echo ============================================
echo    SRGI RINEX 下载工具
echo ============================================
echo    1 = 按页码选站（每页 20 个站）
echo    2 = 按站号范围选站
echo    3 = 查看测站顺序表（不确定谁在前就先看这个）
echo.
set /p MODE=请选择 1 / 2 / 3:
if "%MODE%"=="1" goto PAGE
if "%MODE%"=="2" goto STAT
if "%MODE%"=="3" goto ORDER
echo 只能输入 1、2 或 3
pause
goto :eof

:PAGE
echo.
set /p VAL=页码范围（数字，例如 17-24；单页可写 17）:
echo(%VAL%| findstr /r "^[0-9][0-9]*-[0-9][0-9]*$" >nul && goto PAGE_OK
echo(%VAL%| findstr /r "^[0-9][0-9]*$" >nul && goto PAGE_OK
echo 页码格式不对：要写成“起始页-结束页”，例如 17-24
goto PAGE
:PAGE_OK
set "SEL=--pages"
goto ASK_YEAR

:STAT
echo.
set /p VAL=站号范围（4 位站号，例如 crjs-csbl；单站可写 crjs）:
echo(%VAL%| findstr /i /r "^[a-z0-9][a-z0-9][a-z0-9][a-z0-9]-[a-z0-9][a-z0-9][a-z0-9][a-z0-9]$" >nul && goto STAT_OK
echo(%VAL%| findstr /i /r "^[a-z0-9][a-z0-9][a-z0-9][a-z0-9]$" >nul && goto STAT_OK
echo 站号格式不对：要写成“起始站-结束站”，例如 crjs-csbl（站号是 4 位）
goto STAT
:STAT_OK
set "SEL=--stations"

:ASK_YEAR
echo.
set /p Y=年份（4 位数字，例如 2026）:
echo(%Y%| findstr /r "^[0-9][0-9][0-9][0-9]$" >nul
if errorlevel 1 (
  echo 年份必须是 4 位数字，例如 2026
  goto ASK_YEAR
)

:ASK_DOY
echo.
set /p D=年积日范围（1-3 位数字，例如 001-100 或 212-320）:
echo(%D%| findstr /r "^[0-9][0-9]*-[0-9][0-9]*$" >nul
if errorlevel 1 (
  echo 年积日格式不对：要写成“起始-结束”，例如 001-100
  goto ASK_DOY
)

:ASK_MODE
echo.
set /p M=下载方式（1 或 2，回车 = 2）:
if "%M%"=="" set "M=2"
if "%M%"=="1" goto ASK_OUT
if "%M%"=="2" goto ASK_OUT
echo 只能输入 1 或 2
goto ASK_MODE

:ASK_OUT
set /p O=保存目录（回车 = 本目录下的 output）:
if "%O%"=="" set "O=%~dp0output"

set "FLAG="
if "%M%"=="2" set "FLAG=--no-check"

echo.
echo 即将执行:
echo   %PY% srgi_tool.py run %FLAG% %SEL% %VAL% --year %Y% --doy %D% --out "%O%"
echo.
pause

%PY% srgi_tool.py run %FLAG% %SEL% %VAL% --year %Y% --doy %D% --out "%O%"
if errorlevel 1 (
  echo.
  echo 运行失败：请看上面的提示（输入有误 / 未登录 / 网络问题）
  pause
  goto :eof
)

echo.
echo 完成。报告: %O%\report.csv
echo 补下缺失数据: %PY% srgi_tool.py run --retry "%O%\report.csv" --out "%O%"
pause
goto :eof

:ORDER
echo.
set /p O=保存目录（回车 = 本目录下的 output）:
if "%O%"=="" set "O=%~dp0output"
%PY% srgi_tool.py stations --out "%O%"
if errorlevel 1 echo 生成失败：请看上面的提示（可能是未登录或网络问题）
pause
goto :eof
