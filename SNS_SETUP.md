# SNS 실시간 여론 기능 설정 가이드

## 📋 개요
이 프로젝트는 주식 관련 SNS 데이터를 실시간으로 수집하고 분석하는 기능을 제공합니다.

## 🔧 설정 방법

### 1. API 토큰 발급

#### Twitter API 토큰 발급
1. [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)에 접속
2. 새 앱 생성 또는 기존 앱 선택
3. "Keys and tokens" 탭에서 Bearer Token 복사
4. `Spring/env.example` 파일을 `Spring/.env`로 복사하고 토큰 설정

#### Threads API 토큰 발급
1. [Facebook Developers](https://developers.facebook.com/tools/explorer/)에 접속
2. Threads API 앱 생성
3. Access Token 발급
4. `Spring/.env` 파일에 토큰 설정

### 2. 환경 변수 설정

```bash
# Spring/.env 파일 생성
cp Spring/env.example Spring/.env

# 파일 편집하여 실제 토큰 입력
TWITTER_BEARER_TOKEN=실제_트위터_토큰
THREADS_ACCESS_TOKEN=실제_스레드_토큰
```

### 3. 애플리케이션 실행

```bash
# Spring 백엔드 실행
cd Spring
mvn spring-boot:run

# React 프론트엔드 실행 (새 터미널)
cd React
npm run dev
```

## 🚀 주요 기능

### 실시간 데이터 수집
- **10분마다** 인기 주식들의 SNS 데이터 자동 수집
- **15분 캐시** 시스템으로 API 호출 최적화
- **5분마다** 프론트엔드 자동 새로고침

### 지원 플랫폼
- **Twitter (X)**: 트윗, 리트윗, 좋아요 수집
- **Threads**: 스레드, 댓글, 좋아요 수집

### 지원 주식
- 삼성전자 (005930)
- SK하이닉스 (000660)
- 네이버 (035420)
- 삼성바이오로직스 (207940)
- 삼성SDI (006400)

## 🔍 API 엔드포인트

### SNS 데이터 조회
```
GET /api/sns/{symbol}
```

**예시:**
```bash
curl http://localhost:8080/api/sns/005930
```

**응답:**
```json
{
  "tweets": [
    {
      "id": "1",
      "author": "@SamsungNews",
      "content": "삼성전자, 3분기 실적 발표...",
      "time": "2시간 전",
      "likes": 1240,
      "retweets": 89,
      "replies": 0,
      "platform": "twitter"
    }
  ],
  "threads": [
    {
      "id": "1", 
      "author": "@SamsungTech",
      "content": "삼성전자의 새로운 AI 반도체 기술...",
      "time": "1시간 전",
      "likes": 3420,
      "retweets": 0,
      "replies": 156,
      "platform": "threads"
    }
  ],
  "stockName": "삼성전자",
  "symbol": "005930"
}
```

## ⚠️ 주의사항

### API 제한
- **Twitter API**: 15분당 15개 요청 제한
- **Threads API**: 시간당 요청 제한 있음
- 토큰이 없거나 제한에 걸리면 더미 데이터 표시

### 에러 처리
- API 실패 시 자동으로 더미 데이터로 대체
- 사용자에게 에러 상황을 명확히 알림
- 네트워크 오류 시 재시도 메커니즘

## 🛠️ 개발자 정보

### 백엔드 (Spring Boot)
- **SnsController**: API 엔드포인트 제공
- **SnsService**: 비즈니스 로직 처리
- **TwitterApiService**: Twitter API 연동
- **ThreadsApiService**: Threads API 연동
- **SnsSchedulerService**: 자동 데이터 수집

### 프론트엔드 (React)
- **Sns.jsx**: SNS 컴포넌트
- **Sns.css**: 스타일링
- 자동 새로고침 및 에러 처리

## 📈 향후 개선 계획

1. **실시간 WebSocket** 연결로 즉시 업데이트
2. **감정 분석** 기능 추가
3. **키워드 추출** 및 트렌드 분석
4. **알림 시스템** 구현
5. **더 많은 SNS 플랫폼** 지원 (Instagram, LinkedIn 등)
