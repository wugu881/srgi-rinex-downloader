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

echo ============================================
echo    SRGI RINEX 下载工具
echo ============================================
echo    1 = 按页码选站（每页 20 个站）
echo    2 = 按站号范围选站
echo.
set /p MODE=请选择 1 或 2:
if "%MODE%"=="1" goto PAGE
if "%MODE%"=="2" goto STAT
goto END

:PAGE
echo.
set /p VAL=页码范围（数字，例如 17-24）:
set "SEL=--pages"
goto ASK_YEAR

:STAT
echo.
set /p VAL=站号范围（4 位站号，例如 crjs-csbl）:
set "SEL=--stations"

:ASK_YEAR
echo.
set /p Y=年份（4 位数字，例如 2026）:
if "%Y%"=="" (
  echo 年份不能为空，请重新输入
  goto ASK_YEAR
)

:ASK_DOY
echo.
set /p D=年积日范围（3 位年积日，例如 001-100）:
if "%D%"=="" (
  echo 年积日不能为空，请重新输入
  goto ASK_DOY
)

echo.
set /p M=下载方式（1 或 2，回车 = 2）:
if "%M%"=="" set "M=2"

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

echo.
echo 完成。报告: %O%\report.csv
echo 补下缺失数据: %PY% srgi_tool.py run --retry "%O%\report.csv" --out "%O%"
pause
goto :eof

:END
exit /b
