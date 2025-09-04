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

## Python 폴더구조 구축 및 APi 호출

- 폴더구조
3team/
├─ data/                       # JSON, 심볼 CSV 저장
└─ Python/
   ├─ Apps/price_to_json.py    # 실행 스크립트
   └─ Libs/
      ├─ kiwoom_client.py
      ├─ env.py                # 환경변수 파일(API 키)
      ├─ io_utils.py
      └─ symbols.py            # (종목명→코드 매핑용, CSV 읽음)

- 설치 라이브러리: pip install requests python-dotenv

- 사용법(프로젝트 루트에서 실행: …/3team)
1. 종목코드로 조회
(bash) python -m Python.Apps.price_to_json 005930
2. 종목명으로 조회
(bash) python -m Python.Apps.price_to_json --name 삼성전자
  내부에서 data/symbols_krx.csv를 읽어 종목명 → 코드(6자리) 로 변환 후 조회
  다중 후보일 경우 후보 리스트를 출력하고 종료
3. 실행결과: 
    터미널: [저장 완료] data/stock_005930_YYYYMMDD_HHMMSS.json
            - 체결시각: 09:12:03  현재가: 78900  전일대비: +1200  등락률: +1.54
    파일: data/stock_종목코드_날짜시간.json 생성