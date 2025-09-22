@echo off
chcp 65001 >nul

echo ========================================
echo   Starting the Integrated Spring Server
echo ========================================
echo.

java -jar Spring/target/backend-api-0.0.1-SNAPSHOT.jar

echo.
echo Server has been stopped.
pause