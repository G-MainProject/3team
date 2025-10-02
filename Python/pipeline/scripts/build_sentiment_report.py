# -*- coding: utf-8 -*-
"""
CSV/JSON 원본을 표준 감성 집계 포맷(data/raws/sentiment_report.json)으로 변환하는 스크립트.

입력 예시 1) CSV 파일(헤더 필요)
  ticker,date,score
  005930,2025-09-16,0.42
  005930,2025-09-16,-0.1
  000660,2025-09-15,0.05

입력 예시 2) JSON 리스트
  [
    {"ticker": "005930", "date": "2025-09-16", "score": 0.42},
    {"ticker": "005930", "date": "2025-09-16", "score": -0.10}
  ]

출력 포맷(merge_align.py에서 자동 인식):
  {
    "items": [
      {
        "stockCode": "005930",
        "analysisDate": "2025-09-16",
        "sentimentAnalysis": {"averageScore": 0.42}
      },
      ...
    ]
  }

참고: s2_preprocess 단계의 merge_align가 아래 위치에서 해당 파일을 자동으로 탐색/병합합니다.
  - Python/pipeline/pipelines/s2_preprocess/merge_align.py:713 (report_path = raw_root / "sentiment_report.json")

사용법(프로젝트 루트에서 실행):
  python scripts/build_sentiment_report.py --input data/raws/my_news_scores.csv --output data/raws/sentiment_report.json

주의사항:
  - ticker는 숫자만 추출되어 6자리로 zero-pad 됩니다(005930 형태).
  - date는 YYYY-MM-DD 형태로 정규화됩니다.
  - score는 -1~1 범위로 클램프되어 저장됩니다(파이프라인 기준에 맞춤).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Iterable


def _zfill6(code: Any) -> str:
    """종목코드를 6자리 숫자 문자열로 정규화.
    - 영문/기타 문자가 섞여 있어도 숫자만 추출
    - 자리수 부족 시 좌측 0 패딩
    """

    raw = str(code or "").strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits.zfill(6) if digits else raw.zfill(6)


def _normalize_date(value: Any) -> str | None:
    """YYYY-MM-DD 형태로 변환 시도. 실패 시 None 반환."""

    text = str(value or "").strip().split(" ")[0].replace(".", "-").replace("/", "-")
    parts = text.split("-")
    try:
        if len(parts) == 3:
            y = int(parts[0])
            m = int(parts[1])
            d = int(parts[2])
            return f"{y:04d}-{m:02d}-{d:02d}"
    except Exception:
        pass
    return None


def _iter_csv_rows(path: Path) -> Iterable[dict[str, Any]]:
    """CSV에서 기본 컬럼(ticker/date/score)을 읽어 표준 행으로 변환."""

    with path.open("r", encoding="utf-8", errors="ignore") as fp:
        rdr = csv.DictReader(fp)
        # 컬럼명 대소문자/언더스코어/하이픈 변형 허용
        headers = {h.lower().replace("-", "_").strip(): h for h in (rdr.fieldnames or [])}
        t_col = headers.get("ticker") or headers.get("stock_code") or headers.get("code") or headers.get("symbol")
        d_col = headers.get("date") or headers.get("analysis_date") or headers.get("published_at")
        s_col = headers.get("score") or headers.get("sentiment") or headers.get("avg_score")
        if not (t_col and d_col and s_col):
            raise SystemExit("CSV 헤더에 ticker/date/score 컬럼이 필요합니다.")
        for row in rdr:
            code = _zfill6(row.get(t_col, ""))
            day = _normalize_date(row.get(d_col))
            try:
                score = float(str(row.get(s_col, "")).strip())
            except Exception:
                score = None
            if code and day and (score is not None):
                # 점수는 -1~1로 클램프  # 한글 주석
                score = max(-1.0, min(1.0, float(score)))
                yield {"ticker": code, "date": day, "score": score}


def _iter_json_rows(path: Path) -> Iterable[dict[str, Any]]:
    """JSON 리스트 또는 {items:[...]} 구조에서 표준 행 산출."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]]
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = (
            payload.get("items")
            or payload.get("data")
            or payload.get("rows")
            or payload.get("result")
            or []
        )
    else:
        rows = []
    for item in rows:
        code = _zfill6(item.get("ticker") or item.get("stockCode") or item.get("code"))
        day = _normalize_date(item.get("date") or item.get("analysisDate"))
        score_val = item.get("score") or (
            # 이미 표준 포맷인 경우 averageScore를 사용  # 한글 주석
            (item.get("sentimentAnalysis") or {}).get("averageScore") if isinstance(item, dict) else None
        )
        try:
            score = float(score_val)
        except Exception:
            score = None
        if code and day and (score is not None):
            # 점수는 -1~1로 클램프  # 한글 주석
            score = max(-1.0, min(1.0, float(score)))
            yield {"ticker": code, "date": day, "score": score}


def convert_to_sentiment_report(input_path: Path, output_path: Path) -> None:
    """표준 감성 집계 JSON으로 변환 및 저장.
    - merge_align이 요구하는 최소 스키마를 만족
    - 평균 점수는 -1~1 범위로 클램프하여 저장(파이프라인 분류 기준과 일치)
    - 일자별 평균은 s2_preprocess(merge_align.py)에서 재집계
    """

    ext = input_path.suffix.lower()
    if ext == ".csv":
        rows = list(_iter_csv_rows(input_path))
    else:
        rows = list(_iter_json_rows(input_path))

    items = []
    for r in rows:
        items.append(
            {
                # s2_preprocess/merge_align.py가 인식하는 키 이름에 맞춘다
                "stockCode": r["ticker"],
                "analysisDate": r["date"],
                # 평균 점수는 이미 -1~1로 클램프됨  # 한글 주석
                "sentimentAnalysis": {"averageScore": float(r["score"])},
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"items": items}
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="감성 점수 CSV/JSON을 sentiment_report.json 포맷으로 변환")
    parser.add_argument("--input", required=True, type=Path, help="입력 CSV 또는 JSON 경로")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/raws/sentiment_report.json"),
        help="출력 JSON 경로(기본: data/raws/sentiment_report.json)",
    )
    args = parser.parse_args(argv)

    try:
        convert_to_sentiment_report(args.input, args.output)
    except SystemExit:
        raise
    except Exception as e:
        print(f"[build_sentiment_report] 변환 중 오류: {e}", file=sys.stderr)
        return 1
    print(f"[build_sentiment_report] 완료: {args.output}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

