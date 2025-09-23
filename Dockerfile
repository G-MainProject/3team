# --- Stage 1: React Frontend 빌드 ---
# Node.js 버전을 18에서 20으로 업그레이드하여 경고를 해결합니다.
FROM node:20-alpine AS frontend-builder

WORKDIR /app/React

# package.json과 package-lock.json 복사 및 의존성 설치
COPY React/package.json React/package-lock.json ./
RUN npm install

# 나머지 React 소스 코드 복사
COPY React/src ./src
COPY React/public ./public
COPY React/index.html ./
COPY React/vite.config.js ./
COPY React/eslint.config.js ./

# 빌드에 필요한 data 폴더를 복사합니다.
COPY data ./data 

# React 앱 빌드
RUN npm run build

# --- Stage 2: Spring Backend 빌드 ---
FROM maven:3-openjdk-17 AS backend-builder

WORKDIR /app/Spring

# Maven 프로젝트 파일 복사
COPY Spring/pom.xml ./
COPY Spring/.mvn ./.mvn
COPY Spring/mvnw ./
COPY Spring/mvnw.cmd ./

# mvnw 스크립트의 실행 권한 부여 및 줄 끝 문자 변환 (sed 사용)
RUN chmod +x mvnw \
    && sed -i 's/\r$//' mvnw

# Maven 의존성 다운로드 (캐싱을 위해 먼저 실행)
RUN --mount=type=cache,target=/root/.m2 ./mvnw dependency:go-offline -DskipTests

# 나머지 Spring 소스 코드 복사
COPY Spring/src ./src

# React 빌드 결과물을 Spring의 static 리소스 폴더로 복사
COPY --from=frontend-builder /app/React/dist ./src/main/resources/static

# Spring 애플리케이션 빌드
RUN ./mvnw clean package -DskipTests

# --- Stage 3: 최종 실행 이미지 ---
FROM openjdk:17-slim-buster

WORKDIR /app

# Spring Boot JAR 파일 복사
COPY --from=backend-builder /app/Spring/target/*.jar app.jar

# 애플리케이션 실행
ENTRYPOINT ["java", "-jar", "app.jar"]
