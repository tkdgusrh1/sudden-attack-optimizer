@echo off
REM ===========================================================
REM  Sudden Attack optimizer (Windows) - double-click this file.
REM  Keep this file ASCII + CRLF: cmd.exe breaks on UTF-8 and LF.
REM  All Korean messages are printed by optimizer.py instead.
REM  (No Python? Use SuddenAttack-Optimizer.exe from the Releases page.)
REM ===========================================================
cd /d "%~dp0"

if not exist "optimizer.py" goto nozip

REM --- ask for administrator rights, once -----------------------------
REM  Power plan / network / MMCSS items live under HKLM and need it.
REM  The "elevated" argument makes sure we never ask twice in a loop.
REM  The path goes through an environment variable so that folder names
REM  with quotes or brackets cannot break the command.
if "%~1"=="elevated" goto haveadmin
net session >nul 2>&1
if not errorlevel 1 goto haveadmin

echo.
echo   Asking Windows for administrator rights...
set "SELF=%~f0"
powershell -NoProfile -Command "Start-Process -FilePath $env:SELF -ArgumentList 'elevated' -Verb RunAs" >nul 2>&1
if errorlevel 1 goto noadmin
exit /b

:noadmin
echo   Continuing as a normal user - some items will stay locked.

:haveadmin
call :findpython
if not defined LAUNCHER goto nopython
%LAUNCHER% optimizer.py
if errorlevel 1 pause
goto end

:findpython
REM  "python" may be the Microsoft Store stub that only opens the Store.
REM  So we really run it and check the version instead of trusting "where".
set LAUNCHER=
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if not errorlevel 1 set LAUNCHER=py -3
if defined LAUNCHER exit /b
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if not errorlevel 1 set LAUNCHER=python
exit /b

:nopython
echo.
echo   [!] Python 3.8 or newer is required but was not found.
echo.
echo   Easiest: download SuddenAttack-Optimizer.exe from the Releases page
echo   of this project instead - it needs nothing installed.
echo.
echo   Or install Python: the download page opens now. During setup,
echo   check the "Add Python to PATH" box at the bottom of the screen.
echo.
start https://www.python.org/downloads/
pause
goto end

:nozip
echo.
echo   [!] optimizer.py is not next to this file.
echo   Unzip (extract) the whole folder first, then run this file again.
echo.
pause

:end
