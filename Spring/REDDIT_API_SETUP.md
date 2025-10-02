# Reddit API 설정 가이드

## 📋 개요
Reddit API는 **완전 무료**로 사용할 수 있으며, 무제한 요청이 가능합니다. 주식 관련 서브레딧에서 실제 데이터를 수집할 수 있습니다.

## 🔧 설정 방법

### 1. Reddit 앱 생성

#### 1.1 Reddit 계정 로그인
1. [Reddit Preferences](https://www.reddit.com/prefs/apps)에 접속
2. Reddit 계정으로 로그인

#### 1.2 앱 생성
1. "Create App" 또는 "Create Another App" 클릭
2. 앱 정보 입력:
   - **Name**: `StockAnalysisApp` (또는 원하는 이름)
   - **App type**: `script` 선택
   - **Description**: `주식 분석을 위한 데이터 수집 앱`
   - **About URL**: `http://localhost:3000` (개발용)
   - **Redirect URI**: `http://localhost:3000` (개발용)
3. "Create app" 클릭

#### 1.3 Client ID와 Secret 확인
1. 생성된 앱에서 **Client ID** 복사 (19자리 문자열)
2. **Secret** 복사 (27자리 문자열)

### 2. 환경 변수 설정

#### 2.1 Spring/env 파일 수정
```bash
# Reddit API 설정 (무료 - 권장!)
REDDIT_CLIENT_ID=실제_클라이언트_ID
REDDIT_CLIENT_SECRET=실제_시크릿
```

#### 2.2 환경 변수 로드 (Windows)
```cmd
# Spring 디렉토리에서 실행
set REDDIT_CLIENT_ID=실제_클라이언트_ID
set REDDIT_CLIENT_SECRET=실제_시크릿
```

#### 2.3 환경 변수 로드 (Linux/Mac)
```bash
# Spring 디렉토리에서 실행
export REDDIT_CLIENT_ID=실제_클라이언트_ID
export REDDIT_CLIENT_SECRET=실제_시크릿
```

## 🚀 테스트 방법

### 3.1 백엔드 테스트
```bash
# Spring 애플리케이션 실행
cd Spring
mvn spring-boot:run

# API 테스트
curl http://localhost:8080/api/sns/005930
```

### 3.2 프론트엔드 테스트
```bash
# React 애플리케이션 실행
cd React
npm run dev

# 브라우저에서 http://localhost:5173 접속
# Dashboard에서 SNS 탭 확인
```

## 📊 수집되는 데이터

### 4.1 검색 대상 서브레딧
- `r/stocks` - 주식 일반
- `r/investing` - 투자 관련
- `r/SecurityAnalysis` - 증권 분석
- `r/wallstreetbets` - 주식 투자 커뮤니티

### 4.2 수집 데이터
- **제목**: 게시물 제목
- **내용**: 게시물 본문 (축약됨)
- **작성자**: Reddit 사용자명
- **업보트**: 좋아요 수
- **댓글**: 댓글 수
- **시간**: 게시 시간

## 🔍 API 엔드포인트

### 5.1 Reddit API 엔드포인트
- `GET /search.json` - 게시물 검색
- `GET /api/v1/access_token` - 액세스 토큰 발급

### 5.2 우리 API 엔드포인트
```
GET /api/sns/{symbol}
```

**예시:**
```bash
curl http://localhost:8080/api/sns/005930
```

## ⚙️ 설정 옵션

### 6.1 검색 쿼리 커스터마이징
`RedditApiService.java`에서 검색 쿼리를 수정할 수 있습니다:

```java
private String buildQuery(String symbol, String stockName) {
    return String.format("(%s OR %s) subreddit:stocks OR subreddit:investing OR subreddit:SecurityAnalysis", 
        symbol, stockName);
}
```

### 6.2 수집 게시물 수 조정
```java
.queryParam("limit", 5)  // 5개 게시물 수집
```

## 🛠️ 문제 해결

### 7.1 일반적인 오류
- **401 Unauthorized**: Client ID 또는 Secret이 잘못됨
- **403 Forbidden**: 앱 권한 부족
- **429 Too Many Requests**: 요청 제한 초과 (Reddit은 매우 관대함)

### 7.2 로그 확인
```bash
# Spring 애플리케이션 로그에서 확인
# "Reddit API 호출 시작" 메시지 확인
# "Reddit 데이터 수집 완료" 메시지 확인
```

## 📈 장점

### 8.1 Reddit API의 장점
- ✅ **완전 무료** (무제한 사용)
- ✅ **실제 데이터** (사용자 생성 콘텐츠)
- ✅ **다양한 의견** (개인 투자자부터 전문가까지)
- ✅ **실시간 업데이트** (최신 게시물)
- ✅ **높은 신뢰성** (커뮤니티 기반)

### 8.2 수집되는 정보
- 주식에 대한 실제 투자자 의견
- 시장 분석 및 전망
- 뉴스 및 이벤트 반응
- 감정 분석 데이터

## 🔒 보안 주의사항

### 9.1 토큰 보안
- Client ID와 Secret을 코드에 하드코딩하지 마세요
- 환경 변수를 통해 관리하세요
- Git에 토큰이 커밋되지 않도록 주의하세요

### 9.2 .gitignore 설정
```gitignore
# 환경 변수 파일 제외
Spring/env
Spring/.env
```

## 📝 참고사항

### 10.1 Reddit API 정책
- Reddit API는 매우 관대한 사용 정책을 가지고 있습니다
- 개인 사용 목적으로는 제한이 거의 없습니다
- 상업적 사용도 허용됩니다

### 10.2 데이터 사용 가이드라인
- Reddit의 개인정보 보호 정책을 준수하세요
- 수집된 데이터를 적절히 처리하세요
- 사용자 개인정보를 보호하세요
