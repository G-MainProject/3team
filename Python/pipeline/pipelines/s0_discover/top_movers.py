"""Top movers 탐색기 (pykrx 또는 Kiwoom 기반).

- 기본 동작: Kiwoom(ka10027)으로 실시간/장후 랭킹 조회
- 대안: pykrx 일별 변동성 기준 상위 종목

CLI 옵션으로 .env 없이도 Kiwoom 설정을 주입할 수 있도록 지원합니다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

try:  # Python 3.9+
    from zoneinfo import ZoneInfo  # type: ignore
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


# 실행 경로에 따라 프로젝트 루트를 PYTHONPATH에 추가
def _ensure_project_root_on_sys_path() -> None:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists() or (parent / "Python").exists() or (parent / "kiwoom_api.py").exists():
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))
            break


_ensure_project_root_on_sys_path()

# Kiwoom REST 클라이언트 모듈
try:
    from Python.pipeline.pipelines.s1_collect.kiwoom_client import (
        fetch_top_movers as fetch_top_movers_direct,
        _load_env_cache,
    )
    kiwoom_api_available = True
except Exception:  # pragma: no cover
    kiwoom_api_available = False

# pykrx 일별 데이터
try:
    from pykrx import stock  # type: ignore
except Exception:  # pragma: no cover
    stock = None  # type: ignore


# ---------- 유틸 함수들 ----------

def _decide_source_by_time() -> str:
    """KST 기준 평일 09:00~15:30이면 'kiwoom', 그 외에는 'pykrx'."""
    try:
        now = datetime.now(ZoneInfo("Asia/Seoul")) if ZoneInfo else datetime.now()
    except Exception:
        now = datetime.now()
    if now.weekday() > 4:  # 토/일
        return "pykrx"
    t = now.time()
    if (
        t >= datetime.strptime("09:00:00", "%H:%M:%S").time()
        and t <= datetime.strptime("15:30:59", "%H:%M:%S").time()
    ):
        return "kiwoom"
    return "pykrx"


def _find_latest_trading_date(date_str: str) -> str:
    """입력 날짜를 기준으로 최근 거래일 YYYYMMDD 반환(pykrx 필요)."""
    if stock is None:
        raise ImportError("pykrx가 필요합니다. `pip install pykrx`로 설치하세요.")
    base = datetime.strptime(date_str.replace("-", ""), "%Y%m%d")
    for i in range(14):
        target = (base - timedelta(days=i)).strftime("%Y%m%d")
        try:
            frame = stock.get_market_cap_by_ticker(target)
            if frame is not None and not frame.empty:
                return target
        except Exception:
            continue
    raise RuntimeError(f"최근 2주 내 거래일을 찾지 못했습니다: {date_str}")


def _fetch_top_movers_pykrx_dynamic(date: str, market: str, count: int) -> List[dict[str, float]]:
    """pykrx 일별 OHLCV에서 (고가-저가)/시가 변동성 상위 추출.

    - 컬럼명이 국문 또는 영문일 수 있으므로 동적 매핑
    - 티커는 인덱스로 제공되는 경우가 있어 컬럼으로 승격
    """
    if stock is None:
        raise ImportError("pykrx가 필요합니다. `pip install pykrx`로 설치하세요.")

    frame = stock.get_market_ohlcv_by_ticker(date, market=market)
    if frame is None or frame.empty:
        raise RuntimeError(f"pykrx에서 데이터를 찾지 못했습니다: {date}, {market}")

    if "ticker" not in frame.columns:
        try:
            frame = frame.copy()
            frame["ticker"] = frame.index.astype(str)
        except Exception:
            frame["ticker"] = frame.index
    frame = frame.reset_index(drop=True)

    def pick(*cands: str) -> str | None:
        for c in cands:
            if c in frame.columns:
                return c
        return None

    c_open = pick("open", "시가")
    c_high = pick("high", "고가")
    c_low = pick("low", "저가")
    c_ticker = "ticker" if "ticker" in frame.columns else None
    if not all([c_open, c_high, c_low]) or c_ticker is None:
        cols = ", ".join(map(str, frame.columns))
        raise RuntimeError(f"pykrx 컬럼 구조를 해석할 수 없습니다. 현재 컬럼: {cols}")

    denom = frame[c_open].replace(0, float("nan"))
    frame["volatility"] = (frame[c_high] - frame[c_low]).abs() / denom
    frame = frame.dropna(subset=["volatility"]).sort_values("volatility", ascending=False)
    top = frame.head(count)
    return [
        {"ticker": str(row[c_ticker]), "volatility": float(row["volatility"])}
        for _, row in top.iterrows()
    ]


# 이름 보강(pykrx)
_NAME_CACHE: dict[str, str | None] = {}
_NAME_DATE: str = ""


def _lookup_name(ticker: str, date: str) -> str | None:
    global _NAME_DATE
    if stock is None:
        return None
    if date != _NAME_DATE:
        _NAME_CACHE.clear()
        _NAME_DATE = date
    if ticker in _NAME_CACHE:
        return _NAME_CACHE[ticker]
    try:
        name = stock.get_market_ticker_name(ticker, date=date)
    except Exception:
        name = None
    _NAME_CACHE[ticker] = name
    return name


def _annotate_entries(entries: list[dict[str, object]], date_for_lookup: str) -> list[dict[str, object]]:
    annotated: list[dict[str, object]] = []
    for entry in entries:
        tk = entry.get("ticker")
        name = _lookup_name(str(tk), date_for_lookup) if tk else None
        enriched = dict(entry)
        if name:
            enriched["name"] = name
        annotated.append(enriched)
    return annotated


def _default_output(date: str) -> Path:
    root = _find_project_root()
    return root / "data" / "raw" / f"top_movers_{date}.json"


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists() or (parent / "Python").exists():
            return parent
    for parent in current.parents:
        if (parent / "data").exists():
            return parent
    return current.parents[4]


# ---------- 메인/파서 ----------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Select top movers via pykrx or Kiwoom")
    # 기본은 Kiwoom 사용(ka10027은 장 마감 후에도 호출 가능)
    parser.add_argument("--source", choices=["pykrx", "kiwoom", "auto"], default="kiwoom", help="Top mover source (auto/pykrx/kiwoom)")
    parser.add_argument("--date", default=datetime.now().strftime("%Y%m%d"), help="기준 일자 (YYYYMMDD)")
    parser.add_argument("--market", default="KOSPI", help="시장 (KOSPI, KOSDAQ, ALL)")
    parser.add_argument("--count", type=int, default=5, help="선정 종목 수")
    parser.add_argument("--kiwoom-use-mock", action="store_true", help="Use Kiwoom mock environment for queries")
    parser.add_argument("--output", type=Path, help="저장 경로 (json)")
    # .env 없이도 Kiwoom 설정을 주입하기 위한 선택 인자
    parser.add_argument("--kiwoom-base", help="Kiwoom REST base URL (예: https://gw.example)")
    parser.add_argument("--kiwoom-appkey", help="Kiwoom appkey")
    parser.add_argument("--kiwoom-secret", help="Kiwoom secretkey")
    parser.add_argument("--kiwoom-rank-path", help="Kiwoom rank API path (ka10027 매핑 경로)")
    parser.add_argument("--kiwoom-rank-trid", help="Kiwoom rank TR ID (기본 ka10027)")
    parser.add_argument("--kiwoom-api-id", help="요청 헤더 api-id 강제 지정")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    today = datetime.now().strftime("%Y%m%d")

    # pykrx 사용 시 최근 거래일 산출(annotate용)
    try:
        date_for_pykrx = _find_latest_trading_date(args.date)
    except Exception:
        date_for_pykrx = args.date

    # auto면 시간대로 소스 선택
    use_source = args.source
    if args.source == "auto":
        use_source = _decide_source_by_time()

    # Kiwoom 분기
    if use_source == "kiwoom":
        if not kiwoom_api_available:
            print("Error: Kiwoom client is not available.", file=sys.stderr)
            return 1
        try:
            # CLI로 전달된 Kiwoom 설정을 환경변수에 주입(.env 무변경)
            if getattr(args, "kiwoom_base", None):
                os.environ["KIWOOM_BASE"] = args.kiwoom_base
            if getattr(args, "kiwoom_appkey", None):
                os.environ["KIWOOM_APPKEY"] = args.kiwoom_appkey
            if getattr(args, "kiwoom_secret", None):
                os.environ["KIWOOM_SECRETKEY"] = args.kiwoom_secret
            if getattr(args, "kiwoom_rank_path", None):
                os.environ["KIWOOM_RANK_PATH"] = args.kiwoom_rank_path
            if getattr(args, "kiwoom_rank_trid", None):
                os.environ["KIWOOM_RANK_TR_ID"] = args.kiwoom_rank_trid
            if getattr(args, "kiwoom_api_id", None):
                os.environ["KIWOOM_API_ID"] = args.kiwoom_api_id
            _load_env_cache()
            entries = fetch_top_movers_direct(
                market=args.market, count=args.count, use_mock=args.kiwoom_use_mock
            )
            asof = today
        except Exception as exc:
            print(f"Error fetching from Kiwoom direct API: {exc}", file=sys.stderr)
            return 1
    else:
        # pykrx 분기
        try:
            entries = _fetch_top_movers_pykrx_dynamic(date_for_pykrx, args.market, args.count)
        except Exception as exc:
            print(f"Error fetching from pykrx: {exc}", file=sys.stderr)
            return 1
        asof = date_for_pykrx

    # 이름 보강(pykrx) 시도
    entries = _annotate_entries(entries, date_for_pykrx)
    tickers = [str(e.get("ticker")) for e in entries if e.get("ticker")]

    output_path = Path(args.output) if args.output else _default_output(asof)
    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "date": asof,
        "market": args.market,
        "count": len(tickers),
        "tickers": tickers,
        "source": use_source,
        "generated_at": generated_at,
        "details": entries,
        "meta": {
            "description": "Top mover discovery results across the requested market.",
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"Top movers saved to {output_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print("An unexpected error occurred in top_movers.py:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise SystemExit(1)
