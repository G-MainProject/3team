# 3Team Backend API Server 시작 스크립트
Write-Host "Starting 3Team Backend API Server..." -ForegroundColor Green
Write-Host ""

# 현재 디렉토리를 Spring 폴더로 설정
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# JAR 파일이 있는지 확인
if (-not (Test-Path "target\backend-api-0.0.1-SNAPSHOT.jar")) {
    Write-Host "JAR file not found. Building project..." -ForegroundColor Yellow
    Write-Host ""
    mvn clean package -DskipTests
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Build failed!" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host ""
}

# 서버 시작
Write-Host "Starting server..." -ForegroundColor Green
Write-Host ""
Write-Host "Server will be available at:" -ForegroundColor Cyan
Write-Host "  - API Server: http://localhost:8080" -ForegroundColor Cyan
Write-Host "  - Health Check: http://localhost:8080/api/health" -ForegroundColor Cyan
Write-Host "  - H2 Console: http://localhost:8080/h2-console" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

java -jar target\backend-api-0.0.1-SNAPSHOT.jar
