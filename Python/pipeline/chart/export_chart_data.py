# -*- coding: utf-8 -*-
"""차트용 시계열 데이터(OHLCV + 지표) 내보내기.

입력(데이터 소스)
- silver 레이어의 종목별 테이블: s2 전처리 산출물(`data/silver`)
- 선택: 상위 변동 종목 JSON(top-movers)로 종목/이름 매핑

출력
- `data/outputs/chart_data/{ticker}.json`: 날짜별 OHLCV + 지표 행 목록
- `data/outputs/chart_data/index.json`: 내보낸 종목 요약 인덱스

메모
- 실시간 아님. 기존 silver 스냅샷만 사용.
- 기간 미지정 시 기본 약 10년(3650일) 범위로 제한.
- silver에 특정 컬럼이 없으면 조용히 건너뜀.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
import importlib
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Optional

import numpy as np

try:  # 선택 의존성(아래에서 지연 보장)
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore


# .env 로더(BOM 안전). 모듈 부재 시 무시
try:
    from Python.pipeline.utils.env import load_dotenv_utf8sig, sanitize_environ_bom
except Exception:  # pragma: no cover
    def load_dotenv_utf8sig() -> None:  # type: ignore
        return None

    def sanitize_environ_bom() -> None:  # type: ignore
        return None


DEFAULT_INDICATORS = [
    # 핵심 OHLCV는 별도로 처리(여기엔 지표만 나열)
    "bb_percent_b",
    "bb_bandwidth",
    "bb_upper",
    "bb_mid",
    "bb_lower",
    "macd",
    "macd_signal",
    "macd_hist",
    "rsi",
    "obv",
    "obv_ema",
]


@dataclass(slots=True)
class Options:
    tickers: list[str]
    top_movers: Optional[Path]
    silver_root: Path
    output_dir: Path
    start_date: Optional[str]
    end_date: Optional[str]
    indicators: list[str]
    days_lookback: int


def _project_root() -> Path:
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / ".env").exists() or (p / "data").exists():
            return p
    return here.parents[3]


def _maybe_install(packages: list[str]) -> bool:
    """pip으로 누락 패키지 설치를 시도합니다. 성공 시 True 반환.

    - 최선 시도(best-effort)만 수행하며, 실패하더라도 호출 측에서 정상 처리해야 합니다.
    """
    try:
        cmd = [sys.executable, "-m", "pip", "install", *packages]
        rc = subprocess.run(cmd, capture_output=True, text=True).returncode
        return rc == 0
    except Exception:
        return False


def _ensure_pandas() -> Any:
    global pd  # type: ignore
    if pd is not None:
        return pd
    try:
        pd = importlib.import_module("pandas")  # type: ignore
        return pd
    except Exception:
        # 1회 자동 설치 시도
        ok = _maybe_install(["pandas", "pyarrow"])  # parquet-friendly default
        if ok:
            try:
                pd = importlib.import_module("pandas")  # type: ignore
                return pd
            except Exception:
                pass
    raise RuntimeError(
        "pandas가 필요합니다. 'pip install pandas pyarrow' 설치 후 다시 시도하세요.")


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    txt = str(s).strip()
    if not txt:
        return None
    # allow YYYY-MM-DD or YYYYMMDD
    if len(txt) == 8 and txt.isdigit():
        txt = f"{txt[:4]}-{txt[4:6]}-{txt[6:]}"
    try:
        return datetime.strptime(txt[:10], "%Y-%m-%d")
    except Exception:
        return None


def _date_bounds(want_start: Optional[str], want_end: Optional[str]) -> tuple[datetime, datetime]:
    end = _parse_date(want_end) or datetime.now()
    start = _parse_date(want_start) or (end - timedelta(days=3650))
    if start > end:
        start, end = end - timedelta(days=3650), end
    return start, end


def _read_json_utf8(path: Path) -> Any:
    # BOM(utf-8-sig) 허용
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return json.loads(path.read_text(encoding="utf-8"))


def _normalize_ticker_base(code: str) -> str:
    raw = str(code or "").strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return raw.zfill(6)
    d = digits.zfill(6)
    # silver가 보통 보통주 기준(마지막 자리 0)으로 저장될 수 있어 보정
    return d[:-1] + "0"


def _load_silver_table(silver_root: Path, ticker: str):
    _pd = _ensure_pandas()
    cands = [silver_root / f"{ticker}.parquet", silver_root / f"{ticker}.pkl"]
    b = _normalize_ticker_base(ticker)
    if b != ticker:
        cands += [silver_root / f"{b}.parquet", silver_root / f"{b}.pkl"]
    for p in cands:
        if p.exists():
            try:
                if p.suffix == ".parquet":
                    # parquet 엔진(pyarrow) 보장
                    try:
                        importlib.import_module("pyarrow")
                    except Exception:
                        _maybe_install(["pyarrow"])  # best-effort
                    return _pd.read_parquet(p)
                return _pd.read_pickle(p)
            except Exception:
                continue
    return None


def _coerce_float(val: Any) -> Optional[float]:
    try:
        f = float(val)
        return None if (isinstance(f, float) and (np.isnan(f) or np.isinf(f))) else f
    except Exception:
        return None


def _resolve_name(ticker: str, top_data: dict | None) -> Optional[str]:
    if not top_data:
        return None
    try:
        for e in (top_data.get("details") or []):
            if str(e.get("ticker")) == str(ticker):
                nm = e.get("name")
                if isinstance(nm, str) and nm.strip():
                    return nm.strip()
    except Exception:
        pass
    return None


def _select_columns(df, indicators: Iterable[str]) -> list[str]:
    cols = []
    for c in ("open", "high", "low", "close", "volume"):
        if c in df.columns:
            cols.append(c)
    for c in indicators:
        if c in df.columns and c not in cols:
            cols.append(c)
    return cols


def _build_annual_summary(df, *, want_cols: list[str]) -> list[dict[str, Any]]:
    """연도별 재무/지표 요약 생성.

    - 각 연도 마지막 거래일 스냅샷을 사용해 지정 컬럼을 추출
    - 존재하는 컬럼만 포함하고 NaN/inf 는 제외
    """
    try:
        _pd = _ensure_pandas()
        frame = df.copy()
        if "date" not in frame.columns:
            return []
        frame["date"] = _pd.to_datetime(frame["date"]).dt.normalize()
        frame["__year"] = frame["date"].dt.year
        cols = [c for c in want_cols if c in frame.columns]
        if not cols:
            return []
        agg = (
            frame.sort_values("date")
                 .groupby("__year", as_index=False)
                 .tail(1)
                 .sort_values("__year")
        )
        out: list[dict[str, Any]] = []
        for _, row in agg.iterrows():
            try:
                year_val = int(row["__year"])  # type: ignore
            except Exception:
                continue
            item: dict[str, Any] = {"year": year_val}
            for c in cols:
                v = _coerce_float(row.get(c))
                if v is not None:
                    item[c] = v
            out.append(item)
        return out
    except Exception:
        return []


def export_for_ticker(opts: Options, ticker: str, top_data: dict | None) -> Optional[dict[str, Any]]:
    tbl = _load_silver_table(opts.silver_root, ticker)
    if tbl is None or len(tbl) == 0:
        return None
    df = tbl.copy()
    # 날짜 컬럼 정규화
    if "date" in df.columns:
        df["date"] = _ensure_pandas().to_datetime(df["date"]).dt.normalize()
    else:
        # 날짜 컬럼이 없으면 가짜 날짜를 만들 수도 있지만, 여기선 건너뜀
        return None

    # 기간 필터링
    start_dt, end_dt = _date_bounds(opts.start_date, opts.end_date)
    mask = (df["date"] >= start_dt) & (df["date"] <= end_dt)
    df = df.loc[mask]
    if df.empty:
        return None

    use_cols = _select_columns(df, opts.indicators)
    out_rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        item: dict[str, Any] = {"date": str(getattr(row["date"], "date", lambda: row["date"])()) if hasattr(row["date"], "date") else str(row["date"]).split("T")[0]}
        for c in use_cols:
            item[c] = _coerce_float(row.get(c))
        out_rows.append(item)

    # 연도별 재무 요약(가능 시)
    annual_cols = [
        "fund_revenue",
        "fund_operating_income",
        "fund_net_income",
        "fund_net_income_ttm",
        "per", "pbr", "roe", "roa", "market_cap",
    ]
    annual = _build_annual_summary(df, want_cols=annual_cols)

    # 메타데이터 구성
    name = _resolve_name(ticker, top_data)
    meta = {
        "ticker": ticker,
        "name": name or ticker,
        "date_start": out_rows[0]["date"],
        "date_end": out_rows[-1]["date"],
        "count": len(out_rows),
        "columns": ["date", *use_cols],
        "indicators": [c for c in use_cols if c not in ("open", "high", "low", "close", "volume")],
        "annual_fields": [c for c in annual_cols if c in df.columns],
    }

    payload = {"meta": meta, "rows": out_rows}
    if annual:
        payload["annual_financials"] = annual
    return payload


def _load_top_movers(path: Optional[Path]) -> dict | None:
    if not path:
        return None
    if not path.exists():
        return None
    try:
        return _read_json_utf8(path)
    except Exception:
        return None


def _resolve_tickers(cli_tickers: list[str], top_data: dict | None) -> list[str]:
    if cli_tickers:
        return [str(t) for t in cli_tickers]
    if top_data and isinstance(top_data.get("tickers"), list):
        return [str(t) for t in top_data["tickers"]]
    return []


def main(argv: Optional[list[str]] = None) -> int:
    load_dotenv_utf8sig(); sanitize_environ_bom()
    p = argparse.ArgumentParser(description="Export OHLCV+indicators to chart-ready JSON per ticker")
    p.add_argument("--tickers", nargs="*", help="Tickers to export (default: from --top-movers)")
    p.add_argument("--top-movers", type=Path, default=Path("data/raws/top_movers_auto.json"))
    p.add_argument("--silver-root", type=Path, default=Path("data/silver"))
    p.add_argument("--output-dir", type=Path, default=Path("data/outputs/chart_data"))
    p.add_argument("--start-date", help="YYYY-MM-DD (default: ~10y ago)")
    p.add_argument("--end-date", help="YYYY-MM-DD (default: today)")
    p.add_argument("--indicators", nargs="*", default=DEFAULT_INDICATORS, help="Extra indicator columns to include")
    p.add_argument("--days-lookback", type=int, default=3650, help="Lookback days when dates absent (unused if dates provided)")
    args = p.parse_args(argv)

    top = _load_top_movers(args.top_movers)
    tickers = _resolve_tickers(list(args.tickers or []), top)
    if not tickers:
        print("No tickers provided. Use --tickers or provide a top-movers JSON.")
        return 2

    opts = Options(
        tickers=tickers,
        top_movers=args.top_movers,
        silver_root=args.silver_root,
        output_dir=args.output_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        indicators=list(args.indicators or []),
        days_lookback=int(args.days_lookback or 3650),
    )

    # export
    top_data = _load_top_movers(opts.top_movers)
    payloads: list[dict[str, Any]] = []
    for tk in opts.tickers:
        payload = export_for_ticker(opts, tk, top_data)
        if payload is None:
            continue
        payloads.append(payload)

    if payloads:
        bundle = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "count": len(payloads),
            "items": payloads,
        }
    target_path = args.output_dir
    if target_path == Path("data/outputs/chart_data"):
        target_path = Path("data/outputs/chart_data.json")
        if target_path.suffix:
            target_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            target_path.mkdir(parents=True, exist_ok=True)
            target_path = target_path / "chart_data.json"
        target_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Exported {len(payloads)} tickers to {target_path}")
        return 0

    print("No chart data exported. Check silver files or date range.")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
