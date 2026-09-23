@echo off
REM ===========================================================
REM  Undo the last optimization (Windows).
REM  Only needed when the screen will not open - the screen has
REM  the same button. ASCII + CRLF only.
REM ===========================================================
cd /d "%~dp0"

if not exist "optimizer.py" goto nozip

if "%~1"=="elevated" goto haveadmin
net session >nul 2>&1
if not errorlevel 1 goto haveadmin
set "SELF=%~f0"
powershell -NoProfile -Command "Start-Process -FilePath $env:SELF -ArgumentList 'elevated' -Verb RunAs" >nul 2>&1
if errorlevel 1 goto haveadmin
exit /b

:haveadmin
set LAUNCHER=
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if not errorlevel 1 set LAUNCHER=py -3
if defined LAUNCHER goto run
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if not errorlevel 1 set LAUNCHER=python
if defined LAUNCHER goto run

echo.
echo   [!] Python 3.8 or newer is required but was not found.
echo   (The .exe version has the same undo button on its screen.)
echo.
pause
goto end

:run
%LAUNCHER% optimizer.py revert
echo.
pause
goto end

:nozip
echo.
echo   [!] optimizer.py is not next to this file.
echo   Unzip (extract) the whole folder first, then run this file again.
echo.
pause

:end
