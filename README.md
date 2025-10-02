<p align="center">
  <img src="logo/logoH.png" alt="3팀 프로젝트 배너" width="50%">
</p>

# 🚀 3팀 프로젝트

## 📜 목차

- [팀원 및 담당 파트](#team)
- [개발 워크플로우](#workflow)
- [브랜치 전략](#branch-strategy)
- [커밋 메시지 규칙](#commit-rules)
- [주가 예측 파이프라인 (`Python/pipeline`)](#pipeline)
  - [파이프라인 흐름](#pipeline-flow)
  - [폴더 구조](#pipeline-structure)
  - [주요 파일 설명](#pipeline-files)
  - [실행 방법](#pipeline-run)
- [감성 분석 및 키워드 추출 (`Python/Prediction`)](#prediction)
  - [폴더 구조](#prediction-structure)
  - [주요 파일 설명](#prediction-files)
  - [실행 방법](#prediction-run)

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

## <a name="workflow"></a> 🛠️ 개발 워크플로우

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

## <a name="pipeline"></a> 📈 주가 예측 파이프라인 (`Python/pipeline`)

> 담당: 이준범

`Python/pipeline` 폴더는 주가 예측을 위한 전체 머신러닝 파이프라인을 포함합니다. 데이터 수집부터 전처리, 모델 학습, 추론, 최종 리포트 생성까지의 과정을 체계적으로 관리합니다. 파이프라인은 여러 단계(Stage)로 구성되어 있으며, 각 단계는 독립적으로 실행하거나 `scripts/run_s1_to_s5.py` 스크립트를 통해 전체 과정을 한 번에 실행할 수 있습니다.

### <a name="pipeline-flow"></a> 🌊 파이프라인 흐름

파이프라인은 다음과 같은 단계로 구성됩니다.

1.  **S0: Discover**: 변동성 상위 종목을 탐색하여 분석 대상을 선정합니다.
2.  **S1: Collect**: 주가, 재무제표 등 필요한 원본 데이터를 수집합니다.
3.  **S2: Preprocess**: 수집된 데이터를 모델 학습에 적합한 형태로 가공합니다. (Bronze → Silver → Gold)
4.  **S3: Model**: 전처리된 데이터를 사용하여 예측 모델을 학습합니다.
5.  **S4: Infer**: 학습된 모델을 사용하여 미래 주가를 예측합니다.
6.  **S5: Evaluate**: 모델의 예측 결과와 실제 값을 비교하여 최종 리포트를 생성합니다.

<details>
<summary><strong><a name="pipeline-structure"></a> 📂 폴더 구조 보기</strong></summary>

```
Python/pipeline/
├── run_pipeline.py           # (Deprecated) 이전 버전 실행 스크립트
├── pipelines/
│   ├── s0_discover/          # 변동성 상위 종목 탐색
│   ├── s1_collect/           # 원본 데이터 수집 (Kiwoom, DART, pykrx)
│   ├── s2_preprocess/        # 데이터 전처리 (Bronze/Silver/Gold)
│   ├── s3_model/             # 모델 학습
│   ├── s4_infer/             # 모델 추론
│   └── s5_evaluate/          # 최종 리포트 생성
├── scripts/
│   └── run_s1_to_s5.py       # 전체 파이프라인 실행 스크립트
├── artifacts/
│   └── models/               # 학습된 모델 가중치 저장 (model_best.pth)
├── config/
│   └── settings.yaml         # 파이프라인 설정 파일
└── utils/
    └── env.py                # 환경 변수 로딩 유틸리티
```

</details>

<details>
<summary><strong><a name="pipeline-files"></a> 📄 주요 파일 설명 보기</strong></summary>

1.  **`s0_discover/top_movers.py`**
    - Kiwoom API 또는 `pykrx` 라이브러리를 사용하여 KOSPI, KOSDAQ 시장에서 변동성이 큰 종목을 탐색합니다.
    - 결과를 `top_movers_auto.json` 파일로 저장하여 S1 단계의 입력으로 사용합니다.

2.  **`s1_collect/__main__.py`**
    - 여러 소스에서 원본 데이터를 수집하는 단계입니다.
    - **`kiwoom_client`**: Kiwoom REST API를 통해 일봉, 분봉, 재무 데이터를 수집합니다.
    - **`dart_client`**: DART API를 통해 기업의 재무제표, 공시 정보를 수집합니다.
    - **`pykrx_loader`**: `pykrx`를 통해 과거 시세(OHLCV) 데이터를 수집합니다.

3.  **`s2_preprocess/__main__.py`**
    - 수집된 원본 데이터를 Bronze → Silver → Gold 단계에 걸쳐 가공합니다.
    - **Bronze (`merge_align`)**: 각기 다른 소스에서 수집된 데이터를 종목별 시계열 테이블로 병합합니다.
    - **Silver (`features`)**: 이동평균, RSI, MACD 등 기술적 분석 지표를 계산하여 특성을 추가합니다.
    - **Gold (`build_datasets`)**: 모델 학습에 사용할 최종 데이터셋(`X.npy`, `y.npy`)을 생성하고, 정규화를 위한 `scaler.pkl`을 저장합니다.

4.  **`s3_model/__main__.py`**
    - 예측 모델을 정의하고 학습을 수행합니다.
    - **모델 구조**: CNN 기반의 `price_branch`와 `fusion_head`를 결합한 시계열 예측 모델을 사용합니다.
    - **학습**: S2에서 생성된 Gold 데이터셋을 사용하여 다중 예측 기간(1d, 1w, 1m, 6m, 1y)에 대한 미래 수익률을 예측하도록 학습합니다.
    - 학습 결과로 검증 손실이 가장 낮은 모델(`model_best.pth`)과 마지막 에포크의 모델(`model_last.pth`)을 `artifacts/models`에 저장합니다.

5.  **`s4_infer/predict.py`**
    - S3에서 학습된 모델 가중치(`.pth`)를 불러와 예측을 수행합니다.
    - 테스트 데이터셋(`data/gold/test/X.npy`)을 입력으로 받아, 각 예측 기간에 대한 수익률과 예상 주가를 계산합니다.
    - 예측 결과를 `preds.json` 파일로 저장합니다.

6.  **`s5_evaluate/top_mover_report_clean.py`**
    - 모든 단계의 결과를 종합하여 최종 분석 리포트를 생성합니다.
    - S0의 대상 종목, S4의 예측 결과, 실제 주가, 기술/기본 지표 등을 취합합니다.
    - 사용자가 쉽게 이해할 수 있는 형태의 최종 JSON 리포트(`top_mover_forecast.json`)를 생성하여 프론트엔드에 제공할 수 있도록 합니다.

</details>

### <a name="pipeline-run"></a> 🚀 실행 방법

1.  **의존성 설치**
    ```shell
    pip install -r Python/requirements.txt
    ```

2.  **환경 변수 설정**
    - 프로젝트 루트에 `.env` 파일을 생성하고, 데이터 수집에 필요한 API 키를 설정합니다.
    ```
    # DART API 키
    DART_API_KEY=YOUR_DART_API_KEY

    # Kiwoom API 키 (필요 시)
    KIWOOM_APPKEY=YOUR_KIWOOM_APPKEY
    KIWOOM_SECRETKEY=YOUR_KIWOOM_SECRETKEY
    KIWOOM_BASE=https://openapi.kiwoom.com:9443
    ```

3.  **전체 파이프라인 실행**
    - `scripts/run_s1_to_s5.py` 스크립트를 사용하여 전체 파이프라인을 실행할 수 있습니다.
    - **특정 종목 분석**:
      ```shell
      python Python/pipeline/scripts/run_s1_to_s5.py --tickers 005930 000660 --start-date 2015-01-01 --end-date 2024-10-01
      ```
    - **S0 결과 기반 분석**:
      ```shell
      # 먼저 S0 실행
      python -m Python.pipeline.pipelines.s0_discover --output data/raw/top_movers_auto.json
      # S1-S5 실행
      python Python/pipeline/scripts/run_s1_to_s5.py --top-movers data/raw/top_movers_auto.json
      ```
    - 각 단계는 `--skip-s1`, `--skip-s2` 등의 플래그를 통해 건너뛸 수 있습니다.

---

## <a name="prediction"></a> 📊 감성 분석 및 키워드 추출 (`Python/Prediction`)

> 담당: 이용범

`Python/Prediction` 폴더는 네이버 뉴스 기사를 수집하고, 텍스트 데이터에 대한 감성 분석과 핵심 키워드 추출을 수행하여 종합적인 분석 리포트를 생성하는 역할을 담당합니다.

<details>
<summary><strong><a name="prediction-structure"></a> 📂 폴더 구조 보기</strong></summary>

```
Python/Prediction/
├── finance_data.csv
├── keyword_extractor.py
├── main.py
├── SemiREADME.txt
├── sentiment_analyzer.py
└── scripts/
    ├── build_sentiment_lexicon.py
    └── collect_corpus.py
```

</details>

<details>
<summary><strong><a name="prediction-files"></a> 📄 주요 파일 설명 보기</strong></summary>

1.  **`main.py`**
    - 프로젝트의 메인 실행 스크립트입니다.
    - 사용자로부터 검색어(기업명 등)를 입력받거나, `data/row/top_movers_auto.json` 파일에서 검색어 목록을 자동으로 가져옵니다.
    - 네이버 뉴스 API를 호출하여 관련 기사를 수집합니다. (`fetch_recent_news`)
    - `sentiment_analyzer`와 `keyword_extractor`를 사용하여 수집된 기사를 분석합니다.
    - 최종 분석 결과를 `sentiment_report.json` 형식의 종합 리포트로 생성합니다. (`generate_comprehensive_report`)

2.  **`sentiment_analyzer.py`**
    - 뉴스 기사의 감성을 분석하는 `SentimentAnalyzer` 클래스를 포함합니다.
    - `finance_data.csv` (금융 분야 감성 어휘 корпу스)를 기반으로 나이브 베이즈 모델을 구축하여 텍스트의 긍정/부정/중립을 판단하고 감성 점수를 계산합니다.
    - 긍정/부정 키워드 뭉치(Chunk)를 활용하여 점수를 보정합니다.

3.  **`keyword_extractor.py`**
    - 뉴스 기사에서 핵심 키워드를 추출하는 `KeywordExtractor` 클래스를 포함합니다.
    - `konlpy`의 `Okt` 형태소 분석기와 TextRank 알고리즘을 사용하여 키워드와 그 중요도를 계산합니다.
    - 재무, 투자, 거시경제 관련 도메인 특화 용어에 가중치를 부여하여 정확도를 높입니다.

</details>

### <a name="prediction-run"></a> 🚀 실행 방법

1.  **의존성 설치**
    ```shell
    pip install -r Python/requirements.txt
    ```

2.  **환경 변수 설정**
    - 프로젝트 루트 디렉터리에 `.env` 파일을 생성하고, 네이버 API 이용을 위한 `NAVER_CLIENT_ID`와 `NAVER_CLIENT_SECRET` 값을 추가해야 합니다.
    ```
    NAVER_CLIENT_ID=YOUR_CLIENT_ID
    NAVER_CLIENT_SECRET=YOUR_CLIENT_SECRET
    ```

3.  **스크립트 실행**
    - 특정 검색어로 분석을 실행하려면:
      ```shell
      python Python/Prediction/main.py --search-word "삼성전자"
      ```
    - 검색어 없이 실행하면 `data/row/top_movers_auto.json`에 정의된 기업 목록을 순차적으로 분석합니다.
      ```shell
      python Python/Prediction/main.py
      ```
    - 분석 결과는 기본적으로 `data/raw/sentiment_report.json` 파일로 저장됩니다.
