@echo off
setlocal enabledelayedexpansion

echo ========================================
echo AI Research Assistant - Dependency Manager
echo ========================================
echo.

REM Get current directory
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"
echo Working directory: %CD%
echo.

REM Check if .venv_config exists
if not exist ".venv_config" (
    echo ERROR: .venv_config file not found!
    echo.
    echo This means the setup has not been completed yet.
    echo Please run simple_setup.bat first to install dependencies.
    echo.
    pause
    exit /b 1
)

REM Read virtual environment path from .venv_config
for /f "tokens=2 delims==" %%a in ('findstr "VENV_PATH" .venv_config') do set "VENV_PATH=%%a"
for /f "tokens=2 delims==" %%a in ('findstr "VENV_ACTIVATE" .venv_config') do set "VENV_ACTIVATE=%%a"

REM Remove quotes if present
set "VENV_PATH=%VENV_PATH:"=%"
set "VENV_ACTIVATE=%VENV_ACTIVATE:"=%"

echo Virtual environment path: %VENV_PATH%
echo Virtual environment activate: %VENV_ACTIVATE%
echo.

REM Check if virtual environment exists
if not exist "%VENV_PATH%" (
    echo ERROR: Virtual environment not found at: %VENV_PATH%
    echo.
    echo The virtual environment may have been deleted or moved.
    echo Please run simple_setup.bat again to recreate it.
    echo.
    pause
    exit /b 1
)

REM Check if activate script exists
if not exist "%VENV_ACTIVATE%" (
    echo ERROR: Virtual environment activate script not found at: %VENV_ACTIVATE%
    echo.
    echo The virtual environment may be corrupted.
    echo Please run simple_setup.bat again to recreate it.
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call "%VENV_ACTIVATE%"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    echo.
    echo The virtual environment may be corrupted.
    echo Please run simple_setup.bat again to recreate it.
    echo.
    pause
    exit /b 1
)
echo Virtual environment activated successfully!
echo.

REM Check if dependency_manager.py exists
if not exist "dependency_manager.py" (
    echo ERROR: dependency_manager.py not found!
    echo.
    echo This file should be in the project root directory.
    echo Please check if the file exists or download it again.
    echo.
    pause
    exit /b 1
)

REM Run dependency manager
echo Running dependency manager...
echo.
python dependency_manager.py
set "EXIT_CODE=%ERRORLEVEL%"
echo.

REM Check exit code
if %EXIT_CODE% EQU 0 (
    echo ========================================
    echo Dependency check completed successfully!
    echo ========================================
    echo.
    echo All dependencies are ready.
    echo You can now start the AI Research Assistant.
    echo.
) else (
    echo ========================================
    echo Dependency check found issues!
    echo ========================================
    echo.
    echo Some dependencies may be missing or corrupted.
    echo Consider running simple_setup.bat again to fix issues.
    echo.
)

echo Press any key to exit...
pause >nul
exit /b %EXIT_CODE%
