@echo off
chcp 65001 >nul
set JAVA_TOOL_OPTIONS=-Dfile.encoding=UTF-8
set MAVEN_OPTS=-Dfile.encoding=UTF-8
echo ========================================
echo        3TEAM PROJECT START
echo ========================================
echo.

echo [1/4] Checking if ports are already in use...
netstat -an | find "8080" >nul
if %errorlevel% equ 0 (
    echo ⚠️  Port 8080 is already in use. Stopping existing processes...
    taskkill /f /im java.exe >nul 2>&1
    timeout /t 2 >nul
)

netstat -an | find "5173" >nul
if %errorlevel% equ 0 (
    echo ⚠️  Port 5173 is already in use. Stopping existing processes...
    taskkill /f /im node.exe >nul 2>&1
    timeout /t 2 >nul
)

echo [2/4] Starting Spring backend server...
cd Spring
start "Spring Backend" cmd /k ".\mvnw.cmd spring-boot:run"
echo ✓ Spring backend starting on http://localhost:8080
cd..

echo [3/4] Starting React frontend server...
cd React
start "React Frontend" cmd /k "npm run dev"
echo ✓ React frontend starting on http://localhost:5173
cd..

echo [4/4] Waiting for servers to start...
timeout /t 15 >nul

echo ========================================
echo        APPLICATION STARTED!
echo ========================================
echo.
echo 🌐 Frontend URL: http://localhost:5173
echo 🔧 Backend API: http://localhost:8080/api
echo 📊 Dashboard: http://localhost:5173 (React)
echo.
echo Press Ctrl+C in the Spring console to stop the backend
echo Press Ctrl+C in the React console to stop the frontend
echo Or close this window to keep them running
echo.
echo 🌐 To access the application, open your browser and go to:
echo    http://localhost:5173
echo.
pause
