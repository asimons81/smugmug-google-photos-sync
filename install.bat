@echo off
:: ============================================================================
:: SmugMug Google Photos Sync - One-Click Installer for Windows
:: ============================================================================
:: Double-click this file to install. That's it.
:: ============================================================================
setlocal enabledelayedexpansion

title SmugMug Google Photos Sync - Installer
color 0B

echo.
echo  ======================================================
echo   SmugMug  -- Google Photos Sync  -  Installer v1.0.0
echo  ======================================================
echo.

:: --- Check for Python --------------------------------------------------------
echo [1/5] Checking for Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Python is not installed or not in PATH.
    echo.
    echo  Please install Python 3.10+ from https://www.python.org/downloads/
    echo  IMPORTANT: Check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Verify Python version >= 3.10
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
    set PYMAJOR=%%a
    set PYMINOR=%%b
)
if %PYMAJOR% lss 3 (
    echo  ERROR: Python 3.10+ required, found %PYVER%
    pause
    exit /b 1
)
if %PYMAJOR%==3 if %PYMINOR% lss 10 (
    echo  ERROR: Python 3.10+ required, found %PYVER%
    pause
    exit /b 1
)
echo  Found Python %PYVER% - OK

:: --- Determine install location ----------------------------------------------
echo.
echo [2/5] Setting up install directory...
set "INSTALL_DIR=%LOCALAPPDATA%\SmugMugGooglePhotosSync"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
echo  Installing to: %INSTALL_DIR%

:: --- Create virtual environment ----------------------------------------------
echo.
echo [3/5] Creating isolated Python environment...
if exist "%INSTALL_DIR%\venv\Scripts\python.exe" (
    echo  Virtual environment already exists - updating...
) else (
    python -m venv "%INSTALL_DIR%\venv"
    if %errorlevel% neq 0 (
        echo  ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)
echo  Virtual environment ready.

:: --- Install the application -------------------------------------------------
echo.
echo [4/5] Installing application and dependencies...
echo  This may take a few minutes on first install...
echo.

:: Get the directory where this script lives (the repo root)
set "SCRIPT_DIR=%~dp0"

"%INSTALL_DIR%\venv\Scripts\pip.exe" install --upgrade pip >nul 2>&1
"%INSTALL_DIR%\venv\Scripts\pip.exe" install -e "%SCRIPT_DIR%." 2>&1 | findstr /i "error" >nul
if %errorlevel%==0 (
    :: pip install reported errors, try again without -e
    "%INSTALL_DIR%\venv\Scripts\pip.exe" install "%SCRIPT_DIR%." 2>&1
)

:: Verify it installed
"%INSTALL_DIR%\venv\Scripts\python.exe" -c "import src.main" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  Trying alternative install method...
    "%INSTALL_DIR%\venv\Scripts\pip.exe" install -r "%SCRIPT_DIR%requirements.txt"
    :: Copy source into install dir
    xcopy /E /I /Y "%SCRIPT_DIR%src" "%INSTALL_DIR%\src" >nul
)

echo  Application installed successfully.

:: --- Create shortcuts and launcher -------------------------------------------
echo.
echo [5/5] Creating shortcuts and launcher...

:: Create launcher batch file
(
echo @echo off
echo title SmugMug Google Photos Sync
echo cd /d "%INSTALL_DIR%"
echo "%INSTALL_DIR%\venv\Scripts\pythonw.exe" -m src.main %%*
) > "%INSTALL_DIR%\SmugMugSync.bat"

:: Create a launcher VBS (to avoid the console window flash)
(
echo Set objShell = CreateObject^("WScript.Shell"^)
echo objShell.CurrentDirectory = "%INSTALL_DIR%"
echo objShell.Run """%INSTALL_DIR%\venv\Scripts\pythonw.exe"" -m src.main", 0, False
) > "%INSTALL_DIR%\SmugMugSync.vbs"

:: Create desktop shortcut using PowerShell
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'SmugMug Google Photos Sync.lnk')); ^
   $s.TargetPath = '%INSTALL_DIR%\SmugMugSync.vbs'; ^
   $s.WorkingDirectory = '%INSTALL_DIR%'; ^
   $s.Description = 'Sync photos from SmugMug to Google Photos'; ^
   $s.Save()" >nul 2>&1

if %errorlevel%==0 (
    echo  Desktop shortcut created.
) else (
    echo  Could not create desktop shortcut - you can run SmugMugSync.bat manually.
)

:: Create Start Menu shortcut
set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut('%STARTMENU%\SmugMug Google Photos Sync.lnk'); ^
   $s.TargetPath = '%INSTALL_DIR%\SmugMugSync.vbs'; ^
   $s.WorkingDirectory = '%INSTALL_DIR%'; ^
   $s.Description = 'Sync photos from SmugMug to Google Photos'; ^
   $s.Save()" >nul 2>&1

if %errorlevel%==0 (
    echo  Start Menu shortcut created.
)

:: --- Done! -------------------------------------------------------------------
echo.
echo  ======================================================
echo   Installation complete!
echo  ======================================================
echo.
echo  The app has been installed to:
echo    %INSTALL_DIR%
echo.
echo  You can launch it from:
echo    - The desktop shortcut
echo    - The Start Menu
echo    - Running: %INSTALL_DIR%\SmugMugSync.bat
echo.
echo  To uninstall, run:
echo    %INSTALL_DIR%\uninstall.bat
echo.

:: Create uninstaller
(
echo @echo off
echo title SmugMug Google Photos Sync - Uninstaller
echo echo.
echo echo  Uninstalling SmugMug Google Photos Sync...
echo echo.
echo set "DESKTOP=%%USERPROFILE%%\Desktop"
echo set "STARTMENU=%%APPDATA%%\Microsoft\Windows\Start Menu\Programs"
echo del "%%DESKTOP%%\SmugMug Google Photos Sync.lnk" 2^>nul
echo del "%%STARTMENU%%\SmugMug Google Photos Sync.lnk" 2^>nul
echo echo  Shortcuts removed.
echo echo.
echo set /p CONFIRM="Remove all app data? [y/N]: "
echo if /i "%%CONFIRM%%"=="y" ^(
echo     rmdir /s /q "%INSTALL_DIR%" 2^>nul
echo     echo  Application removed.
echo ^) else ^(
echo     echo  Keeping app data. You can delete %INSTALL_DIR% manually.
echo ^)
echo echo.
echo pause
) > "%INSTALL_DIR%\uninstall.bat"

:: Ask to launch
echo.
set /p LAUNCH="  Launch the app now? [Y/n]: "
if /i "%LAUNCH%"=="n" goto :done
if /i "%LAUNCH%"=="no" goto :done

echo.
echo  Launching SmugMug Google Photos Sync...
start "" "%INSTALL_DIR%\SmugMugSync.vbs"

:done
echo.
echo  Press any key to close this installer...
pause >nul
