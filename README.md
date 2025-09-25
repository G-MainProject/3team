# 🚀 3팀 프로젝트

## 👨‍💻 팀원 및 담당 파트

| 담당 | 폴더명 | 이름 |
|:---:|:---:|:---:|
| Python 분석 | `Python/Analyze` | 김민수 |
| Python 감성분석 | `Python/Prediction` | 이용범 |
| Python 예측 | `Python/Sentiment` | 이준범 |
| RPA | `RPA` | 오주희 |
| Spring | `Spring` | 전승원 |
| React | `React` | 변진환 |

---

## 🛠️ 개발 워크플로우

1.  **이슈 생성**: 기능 추가, 버그 수정 등의 작업을 위한 이슈를 생성합니다.
2.  **브랜치 생성**: 생성된 이슈 번호를 기반으로 새로운 브랜치를 생성합니다.
    -   `feature/{issue-number}-{description}`
    -   `fix/{issue-number}-{description}`
3.  **작업 진행**: 해당 브랜치에서 이슈에 할당된 기능 개발 또는 버그 수정 작업을 진행합니다.
4.  **Pull Request (PR)**: 작업 완료 후, `dev` 브랜치로 PR을 생성합니다.
5.  **코드 리뷰 및 병합**: 팀원들의 코드 리뷰 후 `dev` 브랜치에 병합(Merge)합니다.
6.  **이슈 종료**: PR 본문에 `closes #{issue-number}`를 포함하여 이슈를 자동으로 종료합니다.

---

## 🌿 브랜치 전략

-   **`main`**: 제품으로 출시될 수 있는 안정적인 버전의 브랜치입니다.
-   **`dev`**: 개발용 메인 브랜치입니다. 모든 기능 브랜치는 `dev`를 기준으로 생성하고 병합합니다.

### 브랜치 이름 규칙

| 종류 | 형식 | 예시 |
|:---:|:---:|:---:|
| 기능 개발 | `feature/#{이슈번호}-{기능}` | `feature/#10-login-page` |
| 버그 수정 | `fix/#{이슈번호}-{내용}` | `fix/#25-auth-error` |
| 문서 작업 | `docs/#{이슈번호}-{내용}` | `docs/#3-readme-update` |

---

## 📝 커밋 메시지 규칙

커밋 메시지는 다음 키워드로 시작하여 변경 내용을 명확하게 전달합니다.

| 키워드 | 설명 |
|:---:|:---|
| `feat` | 새로운 기능 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서 수정 (README 등) |
| `style`| 코드 스타일 변경 (포맷팅, 세미콜론 등) |
| `test` | 테스트 코드 추가 또는 수정 |
| `refactor` | 코드 리팩토링 |
| `chore` | 빌드 관련 파일 수정, 패키지 매니저 설정 변경 등 |

### 커밋 메시지 예시

-   `feat: 로그인 페이지 UI 구현`
-   `fix: 로그인 API 연동 오류 수정`
-   `docs: README.md 프로젝트 구조 업데이트`

## 🐍 Python: 주식 시세 API 호출

이 스크립트는 키움증권 API를 사용하여 특정 종목의 현재 시세를 조회하고, 결과를 JSON 파일로 저장합니다.

### 📁 폴더 구조

```
3team/
├─ data/                       # JSON 파일 및 종목 정보(CSV) 저장
└─ Python/
   └─ Sentiment/
      ├─ Apps/price_to_json.py # 메인 실행 스크립트
      └─ Libs/
         ├─ kiwoom_client.py   # API 요청 처리
         ├─ env.py             # 환경변수 관리 (API 키 등)
         ├─ io_utils.py        # 파일 입출력 유틸리티
         └─ symbols.py         # 종목 코드 <-> 종목명 변환
```

### ⚙️ 사전 준비

프로젝트에 필요한 라이브러리를 설치합니다.

```bash
pip install requests python-dotenv
```

### ▶️ 실행 방법

프로젝트 최상위 폴더(`c:/코드/3team`)에서 아래 명령어를 실행하세요.

**1. 종목 코드로 조회**

```bash
python -m Python.Sentiment.Apps.price_to_json 005930
```

**2. 종목명으로 조회**

`--name` 또는 `-n` 옵션을 사용합니다.

```bash
python -m Python.Sentiment.Apps.price_to_json --name 삼성전자
```

> **참고**: 종목명으로 조회 시 `data/symbols_krx.csv` 파일을 참조하여 코드로 변환합니다. 만약 검색된 종목이 여러 개일 경우, 후보 목록을 보여주고 프로그램을 종료합니다.

### ✅ 실행 결과

**1. 터미널 출력**

실행 완료 시 저장된 파일 경로와 함께 주요 시세 정보가 출력됩니다.

```
[저장 완료] data/stock_005930_20250905_142228.json
- 체결시각: 14:22:28  현재가: 85,000  전일대비: +1,200  등락률: +1.43%
```

**2. JSON 파일 생성**

`data` 폴더에 `stock_{종목코드}_{현재시간}.json` 형식의 파일이 생성됩니다.

```json
{
  "stck_cntg_hour": "142228",
  "stck_prpr": "85000",
  "prdy_vrss": "1200",
  "prdy_ctrt": "1.43"
}
```

**Top Movers 실행 가이드**

- 기본 실행: `python Python/Sentiment/Apps/top_movers.py --source ka10019 --direction both`
- 저장 포맷: TSV(탭). 경로 `data/top_movers_{direction}_{YYYYMMDD_HHMMSS}.txt`
- 컬럼: `code  name  side  price  change_abs  change_pct`
- 모의/운영: `--mock` 사용 시 모의(일부 TR만 지원), 미사용 시 운영 도메인
- 디버그: `--debug` 추가 시 원본 응답 JSON을 `data/debug_ka10019_*.json`으로 저장

**ka10019 필수 옵션(기본값 포함)**

- `--mrkt-tp`: 시장구분. 기본 `000`(전체). 예: `001` 코스피, `101` 코스닥, `201` 코스피200
- `--tm-tp`: 시간구분. 기본 `1`(분전). `2`(일전)
- `--tm`: 시간 값. 기본 `5`(분/일)
- `--trde-qty-tp`: 거래량 구분. 기본 `00000`(전체)
- `--stk-cnd`: 종목조건. 기본 `0`(전체)
- `--crd-cnd`: 신용조건. 기본 `0`(전체)
- `--pric-cnd`: 가격조건. 기본 `0`(전체)
- `--updown-incls`: 상하한 포함. 기본 `1`(포함)
- `--stex-tp`: 거래소구분. 기본 `1`(KRX)
- `--direction`: 정렬/필터. 기본 `both`(급등·급락을 각각 호출해 합산 후 절대등락률로 정렬)
- `--flu-tp`: 등락구분(1 급등, 2 급락). 기본 공백이면 자동 설정. `both`일 때는 무시되고 1/2 두 번 호출

**환경 변수(.env)**

- `KIWOOM_BASE`: 운영 도메인. 예 `https://api.kiwoom.com`
- `KIWOOM_APPKEY`, `KIWOOM_SECRETKEY`: 인증키
- `KIWOOM_KA10019_PATH`(선택): 문서 경로와 다를 경우 지정. 기본 `/api/dostk/stkinfo`

**percode 폴백(개별 종목 수집)**

- 실행: `python Python/Sentiment/Apps/top_movers.py --source percode --codes "005930,000660 035420" --direction both`
- 또는: `--universe-file data/my_codes.txt`(한 줄당 6자리 코드)
- 대량 수집: `--max-workers`와 `--max-codes`로 동시성·상한 조절

**심볼 CSV 생성(선택)**

- 실행: `python Python/Sentiment/Apps/build_symbols_from_dart.py`
- 필요: `.env`에 `DART_API_KEY`
- 결과: `data/symbols_krx.csv`(이름↔코드 매핑)
