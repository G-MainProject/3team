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

# 파이프라인 가이드 (Appendix)

본 문서는 기존 README 내용을 유지한 채, 파이프라인 관련 설명을 추가로 정리한 부록입니다. 

## 폴더 구조(요약)

- `Python/pipeline`
  - `pipelines/s0_discover`: 상/하위 변동 종목(top_movers) 탐색
  - `pipelines/s1_collect`: 데이터 수집(Kiwoom/DART/pykrx 백업), RAW 저장 규약 유지
  - `pipelines/s2_preprocess`: 병합/정렬(merge_align), 특성(features), 데이터셋(build_datasets)
  - `pipelines/s3_model`: 학습 엔트리(`__main__.py`), CNN price-branch, fusion head
  - `pipelines/s4_infer`: 추론 스크립트(`predict.py`) – 멀티 호라이즌 예측(1d/1w/1m/6m/1y)
  - `pipelines/s5_evaluate`: 리포트 생성(`top_mover_report_clean.py`)
  - `artifacts/models`: 모델 가중치(`model_best.pth`, `model_last.pth`) 및 `scaler.pkl`
  - `utils`: `.env`(UTF‑8‑SIG) 로더 등 공통 유틸
- `data`
  - `raws/kiwoom/<종목>/ka10001_YYYYMMDD_YYYYMMDD.json`: 일별 시세 RAW
  - `raws/dart/<corp_code>/fnltt*.json`: 재무제표 RAW
  - `bronze/<ticker>.parquet`: 일별 병합 테이블
  - `silver/<ticker>.parquet`: 정제/특성 일부 반영 테이블
  - `gold/train|val|test/{X.npy,y.npy,close.npy}`: 학습용 시퀀스/라벨/종가, `gold/horizons.json`
  - `outputs/{preds.json, top_mover_forecast.json}`: 예측/리포트
- `scripts`
  - `run_s1_to_s5.py`: s1→s5 원샷 실행, 단계별 시간 요약 출력
- `.vscode`: 워크스페이스 설정

## 예측 모델(개요)

- 구조: CNN 기반 `price_branch`(1D 합성곱) + 선택적 `text_branch` → `FusionClassifier`(fusion head)
- 출력: 멀티-호라이즌 수익률(H=5: 1d/1w/1m/6m/1y). 가격은 `close*(1+return)`으로 환산
- 손실/지표: MSE(호라이즌 평균, 선택적 가중치), MAE 및 호라이즌별 MAE
- 전처리: `StandardScaler`를 train split으로 fit 후 전체 split 적용
- 안정성: 추론 시 체크포인트 출력 차원을 자동 감지해 모델과 정합(4/5 타깃 혼용 로딩 안전)

## 동작 플로우

1) s0: 상·하위 변동 종목 탐색(`top_movers_auto.json`)
2) s1: 수집
- Kiwoom RAW 저장 경로 표준화: `raws/kiwoom/<종목>/ka10001_*.json`
- DART 재무 데이터(미존재 status:013은 정상 경고)
3) s2: 전처리(merge → features → gold)
- `horizons.json` 기록. 러너에서 s2 실행 시 1y(250d)를 항상 포함하도록 강제 주입되어 5개 고정
4) s3: 학습 – `model_best.pth`/`model_last.pth` 저장, test MAE 및 per-horizon MAE 출력
5) s4: 추론 – `preds.json`에 `returns/prices/horizons/current_close` 저장
6) s5: 리포트 – `top_mover_forecast.json` 생성, 콘솔에 s5 로그 및 전체 타임 서머리 출력

## 사용법

- 전체 실행 예시
  - `python scripts/run_s1_to_s5.py --tickers 005930 000660 --start-date 2015-01-01 --end-date 2025-10-02`
  - 또는 `python scripts/run_s1_to_s5.py --top-movers data/raws/top_movers_auto.json`
- 단계 제어
  - `--skip-s1|--skip-s2|--skip-s3|--skip-s4|--skip-s5`: 단계별 생략
  - `--no-kiwoom`, `--no-dart`: 수집 소스 비활성화
  - `--infer-model <pth>`: s3 생략 시 사용할 체크포인트 지정
- 출력/검증
  - 예측: `data/outputs/preds.json`의 `horizons`에 "1d","1w","1m","6m","1y"
  - 리포트: `data/outputs/top_mover_forecast.json`
  - 실행 요약: 콘솔 `[run_s1_to_s5] time summary (seconds)`

## 사용 라이브러리(핵심)

- 러너/파이프라인: Python 3.10+ (개발 환경 3.13)
- 수치/데이터: numpy, pandas, pyarrow(Parquet), pickle, json
- 학습/추론: torch(PyTorch)
- 수집: requests(Kiwoom/DART), pykrx(백업)
- 유틸/CLI: argparse, pathlib, logging
- 인코딩/환경: UTF‑8/UTF‑8‑SIG(.env), Windows 콘솔 PYTHONIOENCODING=utf-8 적용

## 트러블슈팅 요약

- s2 “Price directory not found” → RAW 경로가 `raws/kiwoom/<종목>/ka10001_*.json`인지 확인
- DART status:013 → 데이터 미존재 안내로 정상(파이프라인 진행)
- 체크포인트 차원 불일치 → s4가 자동 정합 처리(추론 오류 없이 로딩)