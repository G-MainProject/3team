@echo off
chcp 65001 >nul

echo ========================================
echo  Starting Server and ngrok Tunnel...
echo ========================================
echo.

echo [1/3] Starting Spring server in a new window...
start "Spring Server (Port 8080)" java -jar Spring/target/backend-api-0.0.1-SNAPSHOT.jar

echo [2/3] Waiting for the server to initialize (15 seconds)...
timeout /t 15 >nul

echo [3/3] Starting ngrok tunnel in a new window...
start "ngrok Tunnel" ngrok http 8080

echo.
echo ========================================
echo      ✅ Both processes are running!
echo ========================================
echo.
echo You can now close this window.
echo To stop the servers, close the two new windows that opened.
echo.
pause