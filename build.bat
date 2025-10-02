@echo off
chcp 65001 >nul
echo ========================================
echo         3TEAM PROJECT BUILD
echo ========================================
echo.

echo [1/4] Cleaning previous builds...
if exist "React\dist" rmdir /s /q "React\dist"
if exist "Spring\target" rmdir /s /q "Spring\target"
if exist "Spring\src\main\resources\static" rmdir /s /q "Spring\src\main\resources\static"
echo ✓ Cleanup completed
echo.

echo [2/4] Building React frontend...
cd React
echo Installing React dependencies...
call npm install
if %errorlevel% neq 0 (
    echo ❌ npm install failed!
    pause
    exit /b 1
)
echo Building React project...
call npm run build
if %errorlevel% neq 0 (
    echo ❌ React build failed!
    pause
    exit /b 1
)
echo ✓ React build completed
echo.

echo [3/4] Copying React build to Spring...
cd ..
if not exist "Spring\src\main\resources\static" mkdir "Spring\src\main\resources\static"
xcopy "React\dist\*" "Spring\src\main\resources\static\" /E /I /Y
echo ✓ React build copied to Spring
echo.

echo [4/4] Building Spring backend...
cd Spring
call .\mvnw.cmd clean package -DskipTests
if %errorlevel% neq 0 (
    echo ❌ Spring build failed!
    pause
    exit /b 1
)
echo ✓ Spring build completed
echo.

cd ..
echo ========================================
echo           BUILD COMPLETED!
echo ========================================
echo.
echo Next steps:
echo 1. Run 'start.bat' to start the application
echo 2. Open http://localhost:8080 in your browser
echo.
pause