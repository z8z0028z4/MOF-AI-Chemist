@echo off
echo ========================================
echo AI Research Assistant - Master Installer
echo ========================================
echo.
echo This script will run the full setup process and verify dependencies.
echo.

call scripts\setup.bat

echo.
echo ========================================
echo Running Dependency Manager Verification
echo ========================================
echo.

call scripts\dependency_manager.bat

echo.
echo Use scripts\run_backend.bat or scripts\start_react.bat to start the application.
pause
