@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo 没有找到 python，请先安装 Python 3.8 或更高版本（安装时勾选 Add Python to PATH）
  pause
  exit /b
)
echo ============================================
echo    SRGI RINEX 下载工具
echo ============================================
echo   1 = 按页码选站（每页 20 个）
echo   2 = 按站号范围选站
echo.
set /p MODE=请选择 1 或 2:
if "%MODE%"=="1" goto PAGE
if "%MODE%"=="2" goto STAT
goto END

:PAGE
set /p VAL=页码范围（例如 17-24）:
set SEL=--pages
goto ASK_YEAR

:STAT
set /p VAL=站号范围（例如 crjs-csbl）:
set SEL=--stations

:ASK_YEAR
echo.
set /p Y=年份（直接回车 = 2026）:
if "%Y%"=="" set Y=2026
set /p D=年积日范围（例如 212-320）:
set /p O=保存目录（直接回车 = 本目录下的 output）:
if "%O%"=="" set O=%~dp0output

echo.
echo 即将执行:
echo   python srgi_tool.py run %SEL% %VAL% --year %Y% --doy %D% --out "%O%"
echo.
pause
python srgi_tool.py run %SEL% %VAL% --year %Y% --doy %D% --out "%O%"

echo.
echo 完成。报告: %O%\report.csv
echo 想补下缺失的数据: python srgi_tool.py run --retry "%O%\report.csv" --out "%O%"
pause
goto :eof

:END
exit /b
