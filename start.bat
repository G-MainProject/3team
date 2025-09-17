@echo off
chcp 65001 >nul
echo ========================================
echo        3TEAM PROJECT START
echo ========================================
echo.

echo [1/3] Checking if Spring is already running...
netstat -an | find "8080" >nul
if %errorlevel% equ 0 (
    echo ⚠️  Port 8080 is already in use. Stopping existing processes...
    taskkill /f /im java.exe >nul 2>&1
    timeout /t 2 >nul
)

echo [2/3] Starting Spring backend server...
cd Spring
start "Spring Backend" cmd /k "mvn spring-boot:run"
echo ✓ Spring backend starting on http://localhost:8080
echo.

echo [3/3] Waiting for Spring to start...
timeout /t 10 >nul

echo ========================================
echo        APPLICATION STARTED!
echo ========================================
echo.
echo 🌐 Application URL: http://localhost:8080
echo 📊 Dashboard: http://localhost:8080/dashboard
echo 🔧 API: http://localhost:8080/api
echo.
echo Press Ctrl+C in the Spring console to stop the server
echo Or close this window to keep it running
echo.
echo Opening browser...
start http://localhost:8080
echo.
pause
