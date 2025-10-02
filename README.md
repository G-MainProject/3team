<p align="center">
  <img src="logo/logoH.png" alt="3팀 프로젝트 배너" width="50%">
</p>

# 🚀 3팀 프로젝트

## 📜 목차

- [팀원 및 담당 파트](#team)
- [사용 기술 (Tech Stack)](#tech-stack)
- [개발 워크플로우](#workflow)
- [브랜치 전략](#branch-strategy)
- [커밋 메시지 규칙](#commit-rules)
- [재무제표 OCR 분석 (`Python/Analyze`)](#analyze)
- [감성 분석 및 키워드 추출 (`Python/Prediction`)](#prediction)
- [주가 예측 파이프라인 (`Python/pipeline`)](#pipeline)
- [RPA (Britiy RPA)](#rpa)
- [Backend API 서버 (`Spring`)](#spring)
- [프론트엔드 (`React`)](#react)

---

## <a name="team"></a> 👨‍💻 팀원 및 담당 파트

| 담당            | 폴더명              | 이름   |
| :-------------- | :------------------ | :----- |
| Python 분석     | `Python/Analyze`    | 김민수 |
| Python 감성분석 | `Python/Prediction` | 이용범 |
| Python 예측     | `Python/pipeline`   | 이준범 |
| RPA             | `RPA`               | 오주희 |
| Spring          | `Spring`            | 전승원 |
| React           | `React`             | 변진환 |

---

## <a name="tech-stack"></a> 🛠️ 사용 기술 (Tech Stack)

### Frontend (React)

- **Framework**: `React`
- **Build Tool**: `Vite`
- **Routing**: `react-router-dom`
- **State Management**: React Context API
- **Charting**: `recharts`
- **WebSocket**: `@stomp/stompjs`, `sockjs-client`
- **Styling**: `App.css` (기본 CSS), 컴포넌트 기반 스타일링
- **Linting**: `ESLint`
- **Backend Services**: `firebase` (인증 등)
- **Etc**: `@isoterik/react-word-cloud` (워드 클라우드), `html2canvas` (HTML 캡처)

### Backend (Spring)

- **Framework**: `Spring Boot`
- **Build Tool**: `Maven`
- **Database**: `MySQL`, `H2` (개발용)
- **Data Access**: `Spring Data JPA`
- **API**: `Spring Web` (REST API), `Spring WebSocket`
- **Security**: `Spring Security`
- **Asynchronous HTTP**: `Spring WebFlux`
- **Cache**: `Spring Data Redis`
- **Utilities**: `Lombok`, `Jackson` (JSON 처리)

### AI/Analysis (Python)

- **Machine Learning**: `tensorflow`
- **Data Handling**: `pandas`, `numpy`
- **Korean NLP**: `konlpy`
- **OCR**: `easyocr`, `opencv-python`
- **Web Interaction**: `requests`, `beautifulsoup4`
- **Generative AI**: `google-generativeai` (Gemini API)
- **Graph Analysis**: `networkx` (TextRank 키워드 추출)
- **Environment**: `python-dotenv`

---

## <a name="workflow"></a> 🔄 개발 워크플로우

1.  **이슈 생성**: 기능 추가, 버그 수정 등의 작업을 위한 이슈를 생성합니다.
2.  **작업 진행**: 해당 브랜치에서 이슈에 할당된 기능 개발 또는 버그 수정 작업을 진행합니다.
3.  **Pull Request (PR)**: 작업 완료 후, `dev` 브랜치로 PR을 생성합니다.
4.  **코드 리뷰 및 병합**: 팀원들의 코드 리뷰 후 `dev` 브랜치에 병합(Merge)합니다.
5.  **이슈 종료**: PR 본문에 `closes #{issue-number}`를 포함하여 이슈를 자동으로 종료합니다.

---

## <a name="commit-rules"></a> 📝 커밋 메시지 규칙

커밋 메시지는 다음 키워드로 시작하여 변경 내용을 명확하게 전달합니다.

| 키워드     | 설명                                            |
| :--------- | :---------------------------------------------- |
| `feat`     | 새로운 기능 추가                                |
| `fix`      | 버그 수정                                       |
| `docs`     | 문서 수정 (README 등)                           |
| `style`    | 코드 스타일 변경 (포맷팅, 세미콜론 등)          |
| `test`     | 테스트 코드 추가 또는 수정                      |
| `refactor` | 코드 리팩토링                                   |
| `chore`    | 빌드 관련 파일 수정, 패키지 매니저 설정 변경 등 |

<details>
<summary><strong>커밋 메시지 예시 보기</strong></summary>

- `feat: 로그인 페이지 UI 구현`
- `fix: 로그인 API 연동 오류 수정`
- `docs: README.md 프로젝트 구조 업데이트`

</details>

---

## <a name="analyze"></a> 🖼️ 재무제표 OCR 분석 (`Python/Analyze`)

> 담당: 김민수

`Python/Analyze` 폴더는 이미지 형태의 재무제표에서 텍스트를 추출하고, 이를 구조화된 데이터(CSV)로 변환하는 OCR 솔루션입니다.

- **주요 라이브러리**: `easyocr`, `opencv-python`, `numpy`, `pandas`
- **분석 흐름**:
  1.  **이미지 전처리**: `opencv-python`을 사용하여 이미지의 흑백 변환, 샤프닝, 노이즈 제거 등을 수행하여 OCR 인식률을 높입니다.
  2.  **OCR 수행**: `easyocr`을 사용하여 전처리된 이미지에서 텍스트와 좌표를 추출합니다.
  3.  **텍스트 후처리**: 금융 용어 오타 교정 및 숫자 형식 표준화를 진행합니다.
  4.  **테이블 구조화**: `numpy`와 `pandas`를 이용해 텍스트 좌표를 분석하여 원본 표 구조를 복원하고 CSV 파일로 저장합니다.

<details>
<summary><strong>📄 상세 설명 및 실행 방법 보기</strong></summary>

### 주요 파일

1.  **`OCR_M.py`**: 이미지 전처리, OCR, 테이블 구조화 등 전체 프로세스를 관장하고 최종 CSV 파일을 생성하는 메인 스크립트입니다.
2.  **`OCR_D.py`**: '금융' -> '금음'과 같이 자주 발생하는 OCR 한글 오타를 교정하기 위한 단어 딕셔너리를 제공하는 헬퍼 모듈입니다.

### 실행 방법

1.  **의존성 설치**: `pip install -r Python/requirements.txt`
2.  **스크립트 실행**:
    - `OCR_M.py` 파일 내의 `image_file_path`와 `output_csv_path` 변수를 설정합니다.
    - 스크립트를 직접 실행합니다.
      ```shell
      python Python/Analyze/OCR_M.py
      ```

</details>

## <a name="prediction"></a> 📊 감성 분석 및 키워드 추출 (`Python/Prediction`)

> 담당:
> - 변진환: 뉴스 데이터 수집/정제
> - 이용범: 감성 분석/키워드 추출

`Python/Prediction` 폴더는 네이버 뉴스 기사를 수집하고, 텍스트 데이터에 대한 감성 분석과 핵심 키워드 추출을 수행합니다.

- **주요 라이브러리**: `konlpy`, `networkx`, `pandas`, `requests`
- **분석 흐름**:
  1.  **뉴스 수집**: 네이버 뉴스 API를 통해 검색어 관련 기사를 수집합니다.
  2.  **감성 분석**: `konlpy`와 금융 감성 사전을 기반으로 구축된 나이브 베이즈 모델을 사용하여 기사의 긍정/부정/중립을 분석합니다.
  3.  **키워드 추출**: `konlpy`의 `Okt` 형태소 분석기와 `networkx`의 TextRank 알고리즘을 사용하여 핵심 키워드를 추출합니다.
  4.  **리포트 생성**: 분석 결과를 종합하여 `sentiment_report.json` 파일을 생성합니다.

<details>
<summary><strong>📄 상세 설명 및 실행 방법 보기</strong></summary>

### 주요 파일

1.  **`main.py`**: 사용자로부터 검색어를 입력받아 전체 분석 프로세스를 실행하고 최종 리포트를 생성합니다.
2.  **`sentiment_analyzer.py`**: `finance_data.csv` корпу스를 기반으로 텍스트의 감성 점수를 계산합니다.
3.  **`keyword_extractor.py`**: TextRank 알고리즘과 도메인 특화 용어 가중치를 적용하여 핵심 키워드를 추출합니다.

### 실행 방법

1.  **의존성 설치**: `pip install -r Python/requirements.txt`
2.  **환경 변수 설정**: `.env` 파일에 네이버 API 사용을 위한 `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`을 추가합니다.
3.  **스크립트 실행**:
    ```shell
    # 특정 검색어로 분석 실행
    python Python/Prediction/main.py --search-word "삼성전자"
    ```

</details>

---

## <a name="pipeline"></a> 📈 주가 예측 파이프라인 (`Python/pipeline`)

> 담당: 이준범

`Python/pipeline` 폴더는 주가 예측을 위한 전체 머신러닝 파이프라인을 포함합니다. 데이터 수집부터 전처리, 모델 학습, 추론, 최종 리포트 생성까지의 과정을 체계적으로 관리합니다.

- **주요 라이브러리**: `tensorflow`, `pandas`, `pykrx`, `requests`
- **파이프라인 흐름**:
  1.  **S0: Discover**: 변동성 상위 종목 탐색
  2.  **S1: Collect**: 주가, 재무제표 등 원본 데이터 수집
  3.  **S2: Preprocess**: 모델 학습용 데이터 가공 (Bronze → Silver → Gold)
  4.  **S3: Model**: CNN 기반 시계열 예측 모델 학습
  5.  **S4: Infer**: 학습된 모델로 미래 주가 예측
  6.  **S5: Evaluate**: 모델 성능 평가 및 최종 리포트 생성

<details>
<summary><strong>📄 상세 설명 및 실행 방법 보기</strong></summary>

### 파이프라인 흐름

파이프라인은 다음과 같은 단계로 구성됩니다.

1.  **S0: Discover**: `pykrx`를 사용하여 KOSPI, KOSDAQ 시장에서 변동성이 큰 종목을 탐색합니다.
2.  **S1: Collect**: Kiwoom API, DART API, `pykrx`를 통해 원본 데이터를 수집합니다.
3.  **S2: Preprocess**: `pandas`를 활용하여 시계열 데이터를 병합하고 이동평균, RSI, MACD 등 기술적 분석 지표를 특성으로 추가합니다.
4.  **S3: Model**: `tensorflow`를 사용하여 CNN 기반의 예측 모델을 학습합니다.
5.  **S4: Infer**: 학습된 모델 가중치를 불러와 미래 수익률과 예상 주가를 계산합니다.
6.  **S5: Evaluate**: 모든 단계의 결과를 종합하여 최종 분석 리포트(`top_mover_forecast.json`)를 생성합니다.

### 실행 방법

1.  **의존성 설치**: `pip install -r Python/requirements.txt`
2.  **환경 변수 설정**: `.env` 파일에 `DART_API_KEY`, `KIWOOM_API_KEY` 등을 설정합니다.
3.  **전체 파이프라인 실행**:
    ```shell
    python Python/pipeline/scripts/run_s1_to_s5.py --tickers 005930 --start-date 2015-01-01
    ```

</details>

---

## <a name="rpa"></a> 🤖 RPA (Britiy RPA)

> 담당: 오주희

`RPA` 폴더는 **Britiy RPA**를 사용하여 DART(금융감독원 전자공시시스템)에서 기업 공시 정보를 자동으로 수집, 가공, 저장하는 작업을 수행합니다.

- **주요 프로세스**:
  1.  **`T_0_조건설정`**: 자동화 작업을 위한 대상 기업, 기간 등의 조건을 설정합니다.
  2.  **`T_1_1_DART_열기`**: DART 시스템에 접속합니다.
  3.  **`T_1_2_DART_데이터추출`**: 설정된 조건에 따라 공시 데이터를 검색하고 추출합니다.
  4.  **`T_1_3_DART_첨부파일가공`**: 추출된 공시의 첨부 파일을 다운로드하고 필요한 정보를 가공합니다.
  5.  **`T_1_4_DART_엑셀저장`**: 최종적으로 가공된 데이터를 Excel 파일로 저장합니다.

이 자동화 프로세스를 통해 반복적인 데이터 수집 작업을 효율화하고 수작업으로 발생할 수 있는 오류를 최소화합니다。

---

## <a name="spring"></a> 🚀 Backend API 서버 (`Spring`)

> 담당: 전승원

`Spring` 폴더는 프로젝트의 백엔드 API 서버로, **Spring Boot**를 기반으로 구축되었습니다. React 프론트엔드 애플리케이션에 필요한 데이터를 제공하고, 사용자 인증 및 실시간 통신을 처리하는 역할을 담당합니다.

- **주요 기능**:
    - **RESTful API 제공**: 주식 정보(`StockController`), SNS 데이터(`SnsController`), 사용자 정보(`UserController`) 등 다양한 데이터를 처리하는 API 엔드포인트를 제공합니다.
    - **사용자 인증 및 관리**: Spring Security를 활용하여 사용자의 회원가입, 로그인 등 인증/인가 기능을 구현합니다. (`AuthController`, `UserController`, `AdminController`)
    - **실시간 통신**: Spring WebSocket을 사용하여 클라이언트와 실시간으로 데이터를 주고받는 기능을 제공합니다. (`WebSocketController`)
    - **외부 데이터 연동**: WebFlux를 사용하여 Reddit 등 외부 서비스의 데이터를 비동기적으로 가져와 가공하고 제공합니다.
    - **캐싱**: Spring Data Redis를 이용해 자주 사용되는 데이터를 캐싱하여 API 응답 성능을 향상시킵니다.

- **주요 기술 스택**:
    - **Framework**: `Spring Boot`
    - **Language**: `Java 17`
    - **Data Access**: `Spring Data JPA`, `Spring Data Redis`
    - **API**: `Spring Web` (REST API), `Spring WebSocket`
    - **Security**: `Spring Security`
    - **Asynchronous HTTP**: `Spring WebFlux`
    - **Database**: `MySQL` (운영), `H2` (개발)
    - **Utilities**: `Lombok`, `Jackson`

- **아키텍처**:
    - `controller` - `service` - `repository` 계층으로 구성된 표준적인 **Layered Architecture**를 따릅니다.
    - `User`와 같은 핵심 데이터는 `entity`로 정의하고 JPA를 통해 데이터베이스에 저장하며, 외부 데이터는 DTO(`dto`)를 통해 전달받아 처리합니다.

---

## <a name="react"></a> 🖥️ 프론트엔드 (`React`)

> 담당:
> - 변진환: 기능 구현
> - 전승원: 전반적인 스타일

`React` 폴더는 3팀 프로젝트의 프론트엔드 애플리케이션입니다. **Vite**를 빌드 도구로 사용하는 모던 React 프로젝트로, 사용자에게 데이터 시각화, AI 분석 결과 등 다양한 정보를 웹 인터페이스를 통해 제공합니다.

- **주요 기능 및 페이지**:
    - **데이터 시각화**: `recharts` 라이브러리를 활용하여 주가 데이터를 캔들스틱 차트, 통합 주식 차트 등 다양한 형태로 시각화합니다. (`CandleStickChart`, `UnifiedStockChart`, `Dashboard`, `StockAnalysis` 페이지)
    - **AI 기반 인사이트**: 백엔드에서 처리된 AI 분석 결과를 워드 클라우드 등의 형태로 사용자에게 보여줍니다. (`WordCloud` 컴포넌트, `AIInsights` 페이지)
    - **실시간 데이터 연동**: WebSocket(`@stomp/stompjs`)을 사용하여 백엔드 서버와 실시간으로 데이터를 주고받아 동적인 화면을 구성합니다.
    - **사용자 인증**: `firebase`를 연동하여 로그인, 회원가입 기능을 제공하며, `react-router-dom`을 통해 인증 상태에 따른 페이지 접근을 제어합니다. (`Login`, `Signup`, `Mypage` 페이지)
    - **SNS 데이터 연동**: 백엔드 API를 통해 SNS 데이터를 받아와 화면에 표시합니다. (`Sns` 컴포넌트)

- **주요 기술 스택**:
    - **Framework**: `React`
    - **Build Tool**: `Vite`
    - **Routing**: `react-router-dom`
    - **State Management**: React Context API
    - **Charting**: `recharts`
    - **WebSocket**: `@stomp/stompjs`, `sockjs-client`
    - **Styling**: 기본 CSS 및 컴포넌트 기반 스타일링
    - **Linting**: `ESLint`
    - **Authentication**: `firebase`

- **아키텍처**:
    - **Component-Based Architecture**: 기능별로 컴포넌트(`component`)를 분리하고, 이를 조합하여 페이지(`pages`)를 구성합니다.
    - **State Management**: React Context API(`contexts`)를 사용하여 전역적으로 필요한 상태(예: 인증 정보, 주식 데이터)를 관리합니다.
    - **Custom Hooks**: 반복되는 로직을 `hooks`로 추상화하여 코드 재사용성을 높입니다.
    - **Service Layer**: 백엔드 API 통신 로직을 `services` 폴더에서 관리하여 컴포넌트와 분리합니다.