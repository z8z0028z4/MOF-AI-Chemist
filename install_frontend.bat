@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Frontend Dependencies Installation
echo ========================================
echo.

REM Check if frontend directory exists
if not exist "frontend" (
    echo ERROR: frontend directory not found
    pause
    exit /b 1
)

echo Installing frontend dependencies...
cd frontend

REM Check if package.json exists
if not exist "package.json" (
    echo ERROR: package.json not found in frontend directory
    cd ..
    pause
    exit /b 1
)

REM Install dependencies
echo Running npm install...
npm install

if errorlevel 1 (
    echo ERROR: npm install failed
    cd ..
    pause
    exit /b 1
)

echo Frontend dependencies installed successfully!

REM Check and fix security vulnerabilities
echo Checking and fixing security vulnerabilities...
npm audit fix
if errorlevel 1 (
    echo WARNING: Some vulnerabilities could not be automatically fixed
    echo You may need to manually update packages or check for breaking changes
)

REM Return to project root
cd ..
echo Returned to project root: %CD%

echo.
echo ========================================
echo Frontend installation completed!
echo ========================================
echo.
pause
