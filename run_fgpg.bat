@echo off
rem Start the Fine Gear Profile Generator GUI (run install_windows.bat once first).
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo FGPG is not installed yet - running install_windows.bat first.
    call install_windows.bat || exit /b 1
)

".venv\Scripts\python.exe" -c "import tkinter" 2>nul
if errorlevel 1 (
    echo Tkinter is missing from this Python installation, so the GUI cannot start.
    echo Re-run the Python installer, choose Modify and tick "tcl/tk and IDLE",
    echo then run install_windows.bat again.
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" -m fine_gear_profile_generator.main
