# 3Team Backend API

Spring Boot 기반의 백엔드 API 서버입니다.

## 🚀 기술 스택

- **Java 17**
- **Spring Boot 3.2.0**
- **Spring Data JPA**
- **H2 Database** (개발용)
- **MySQL** (운영용)
- **Maven**
- **Lombok**

## 📁 프로젝트 구조

```
Spring/
├── src/
│   ├── main/
│   │   ├── java/com/team3/backendapi/
│   │   │   ├── BackendApiApplication.java    # 메인 애플리케이션
│   │   │   ├── config/                       # 설정 클래스
│   │   │   │   └── WebConfig.java
│   │   │   ├── controller/                   # REST 컨트롤러
│   │   │   │   └── HealthController.java
│   │   │   └── dto/                          # 데이터 전송 객체
│   │   │       └── ApiResponse.java
│   │   └── resources/
│   │       └── application.yml               # 애플리케이션 설정
│   └── test/                                 # 테스트 코드
├── pom.xml                                   # Maven 의존성 관리
├── start-server.bat                          # Windows 배치 파일
├── start-server.ps1                          # PowerShell 스크립트
└── README.md
```

## 🛠️ 개발 환경 설정

### 1. 필수 요구사항
- Java 17 이상
- Maven 3.6 이상
- IDE (IntelliJ IDEA, Eclipse, VS Code 등)

### 2. 프로젝트 실행

#### 방법 1: 배치 파일 사용 (권장)
```cmd
# Spring 폴더에서 배치 파일 실행
start-server.bat
```

#### 방법 2: PowerShell 스크립트 사용
```powershell
# Spring 폴더에서 PowerShell 스크립트 실행
.\start-server.ps1
```

#### 방법 3: 수동 실행
```cmd
# 프로젝트 디렉토리로 이동
cd Spring

# JAR 파일 빌드
mvn clean package -DskipTests

# JAR 파일 실행
java -jar target\backend-api-0.0.1-SNAPSHOT.jar
```

#### 방법 4: Maven 명령어 (문제가 있을 수 있음)
```cmd
# 프로젝트 디렉토리로 이동
cd Spring

# Maven 의존성 설치
mvn clean install

# 애플리케이션 실행
mvn spring-boot:run
```

### 3. 개발 서버 접속
- **API 서버**: http://localhost:8080
- **H2 콘솔**: http://localhost:8080/h2-console
- **Health Check**: http://localhost:8080/api/health

## 🔧 환경별 설정

### 개발 환경 (dev)
- H2 인메모리 데이터베이스 사용
- 자동 테이블 생성/삭제

### 운영 환경 (prod)
- MySQL 데이터베이스 사용
- 환경변수로 DB 연결 정보 설정

## 📋 API 엔드포인트

### Health Check
- **GET** `/api/health` - 서버 상태 확인

## 🗄️ 데이터베이스

### 개발 환경
- H2 인메모리 데이터베이스 사용
- 자동 테이블 생성/삭제

### 운영 환경
- MySQL 데이터베이스 사용
- 환경변수로 DB 연결 정보 설정

## 🚀 배포

### JAR 파일 빌드
```cmd
mvn clean package
```

### 실행
```cmd
java -jar target/backend-api-0.0.1-SNAPSHOT.jar
```

## 📝 개발 가이드

1. **새로운 API 추가**: `controller` 패키지에 컨트롤러 클래스 생성
2. **데이터 모델 추가**: `entity` 패키지에 엔티티 클래스 생성
3. **비즈니스 로직**: `service` 패키지에 서비스 클래스 생성
4. **데이터 접근**: `repository` 패키지에 리포지토리 인터페이스 생성

## 🤝 팀 협업

이 프로젝트는 3Team의 백엔드 API 서버입니다.
- 프론트엔드: React (../React/)
- 데이터 분석: Python (../Python/)
- RPA: UiPath (../RPA/)

## 🔧 문제 해결

### Maven spring-boot:run 명령이 작동하지 않는 경우
이는 Maven 설정 문제일 수 있습니다. 다음 방법들을 시도해보세요:

1. **배치 파일 사용**: `start-server.bat` 실행
2. **PowerShell 스크립트 사용**: `.\start-server.ps1` 실행
3. **JAR 파일 직접 실행**: `java -jar target\backend-api-0.0.1-SNAPSHOT.jar`

### 새 터미널에서 실행하는 방법
1. Spring 폴더로 이동
2. `start-server.bat` 더블클릭 또는 명령어 실행
3. 또는 `.\start-server.ps1` 실행

## 📞 문의

프로젝트 관련 문의사항이 있으시면 팀원들과 상의해주세요.
