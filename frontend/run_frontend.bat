@echo off
echo Starting AI Research Assistant Frontend...
cd /d "%~dp0"
echo Current directory: %CD%
echo.

echo Node.js version:
node --version 2>&1
echo.

if exist "package.json" (
    echo package.json found
) else (
    echo ERROR: package.json not found
    pause
    exit /b 1
)

if exist "node_modules" (
    echo Dependencies already installed
) else (
    echo Installing dependencies...
    npm install
)

if exist "vite.config.js" (
    echo Vite project detected
)

echo.
echo Starting development server...
npm run dev
