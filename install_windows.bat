@echo off
rem ==========================================================================
rem  Fine Gear Profile Generator - Windows setup
rem
rem  1. Finds Python 3.12+ (newest first). If none is found, or the newest is
rem     older than %TARGET%, offers to install Python %TARGET% with winget.
rem  2. Creates a private environment in .venv and installs the requirements.
rem  3. Runs a quick headless check.
rem
rem  Double-click this file. Set FGPG_NONINTERACTIVE=1 to skip all prompts.
rem ==========================================================================
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title FGPG setup

set "TARGET=3.15"
set "TARGET_MINOR=15"

echo.
echo  Fine Gear Profile Generator - Windows setup
echo  -------------------------------------------
echo.

call :find_python
if defined PY (
    echo  Found Python !PYV!
    echo    !PY!
) else (
    echo  Python 3.12 or newer was not found.
)

set "DO_INSTALL="
if not defined PY set "DO_INSTALL=1"
if defined PY if !PYMINOR! LSS %TARGET_MINOR% (
    if defined FGPG_NONINTERACTIVE (
        echo  Python !PYV! is supported - keeping it.
    ) else (
        echo.
        echo  A newer Python is available: %TARGET%
        choice /c YN /m "  Install Python %TARGET% now (recommended)"
        if !errorlevel! EQU 1 set "DO_INSTALL=1"
    )
)

if defined DO_INSTALL (
    call :install_python
    call :find_python
    if not defined PY goto :no_python
    echo  Using Python !PYV!
)

rem --- private environment ---------------------------------------------------
set "VPY=.venv\Scripts\python.exe"
if exist "%VPY%" (
    set "VMINOR="
    for /f "delims=" %%m in ('call "%VPY%" -c "import sys;print(sys.version_info[1])" 2^>nul') do set "VMINOR=%%m"
    if not "!VMINOR!"=="!PYMINOR!" (
        echo  Re-creating .venv for Python !PYV! ...
        rmdir /s /q .venv
    )
)
if not exist "%VPY%" (
    echo  Creating .venv ...
    "%PY%" -m venv .venv || goto :fail
)

echo  Installing packages (first run can take a few minutes) ...
"%VPY%" -m pip install --upgrade pip --quiet || goto :fail
"%VPY%" -m pip install -r fine_gear_profile_generator\requirements.txt --quiet || goto :fail

"%VPY%" -c "import tkinter" 2>nul
if errorlevel 1 (
    echo.
    echo  WARNING: Tkinter is missing from this Python, so the GUI cannot start.
    echo  Re-run the Python installer, choose Modify and tick "tcl/tk and IDLE".
)

echo  Checking the installation ...
"%VPY%" -m fine_gear_profile_generator.main --headless --output-dir result || goto :fail

echo.
echo  Setup complete. Start FGPG by double-clicking run_fgpg.bat
echo.
if not defined FGPG_NONINTERACTIVE pause
exit /b 0

rem --------------------------------------------------------------------------
:find_python
rem Sets PY (path), PYV (version) and PYMINOR for the newest Python 3.12+.
set "PY="
set "PYV="
set "PYMINOR="
for %%V in (15 14 13 12) do (
    if not defined PY (
        for /f "delims=" %%P in ('py -3.%%V -c "import sys;print(sys.executable)" 2^>nul') do set "PY=%%P"
        if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python3%%V\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python3%%V\python.exe"
        if not defined PY if exist "%ProgramFiles%\Python3%%V\python.exe" set "PY=%ProgramFiles%\Python3%%V\python.exe"
        if defined PY set "PYMINOR=%%V"
    )
)
if not defined PY (
    rem Last resort: "python" on PATH, if it is 3.12 or newer.
    for /f "delims=" %%P in ('python -c "import sys;sys.version_info>=(3,12) and print(sys.executable)" 2^>nul') do set "PY=%%P"
    if defined PY for /f "delims=" %%m in ('python -c "import sys;print(sys.version_info[1])"') do set "PYMINOR=%%m"
)
if defined PY for /f "delims=" %%v in ('call "%PY%" -c "import platform;print(platform.python_version())"') do set "PYV=%%v"
exit /b 0

:install_python
where winget >nul 2>nul
if errorlevel 1 (
    echo  winget is not available on this PC.
    goto :eof
)
echo  Installing Python %TARGET% with winget ...
winget install -e --id Python.Python.%TARGET% --scope user --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo  Python %TARGET% could not be installed with winget - trying Python 3.14 ...
    winget install -e --id Python.Python.3.14 --scope user --accept-package-agreements --accept-source-agreements
)
goto :eof

:no_python
echo.
echo  Python could not be installed automatically.
echo  Please install it from https://www.python.org/downloads/
echo  (tick "Add python.exe to PATH" and "tcl/tk and IDLE"), then run this file again.
if not defined FGPG_NONINTERACTIVE pause
exit /b 1

:fail
echo.
echo  Setup failed - see the messages above.
if not defined FGPG_NONINTERACTIVE pause
exit /b 1
