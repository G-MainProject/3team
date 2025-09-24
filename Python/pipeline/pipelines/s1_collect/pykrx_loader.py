"""Utilities to pull market data from pykrx and persist it under the raw data lake."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Sequence

# pykrx 모듈은 외부 의존성이므로 사전 설치 여부를 확인한다
try:
    from pykrx import stock  # type: ignore
except ImportError as exc:  # pragma: no cover - import guard
    raise ImportError(
        "pykrx가 설치되어 있지 않습니다. `pip install pykrx pandas`로 선 설치해 주세요."
    ) from exc

# 데이터 병합을 위해 pandas가 반드시 필요하다
try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover - import guard
    raise ImportError(
        "pandas가 설치되어 있지 않습니다. `pip install pandas`로 선 설치해 주세요."
    ) from exc

LOGGER = logging.getLogger(__name__)
DEFAULT_INVESTORS = ("개인", "외국인", "기관합계")
DEFAULT_INDEX_CODES = ("1001", "2001")  # KOSPI, KOSDAQ
DATE_FMT = "%Y-%m-%d"


def _find_project_root() -> Path:
    """���� ���� ��ġ�� �������� ������Ʈ ��Ʈ�� Ž���Ѵ�."""

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists():
            return parent
    for parent in current.parents:
        if (parent / "data").exists():
            return parent
    # Fallback: assume repository structure .../Python/pipeline/...
    return current.parents[4]

# pykrx API 호출부터 파일 저장까지 한 번에 처리하는 진입점

def run(
    *,
    tickers: Sequence[str],
    start_date: str,
    end_date: str,
    raw_dir: str | Path | None = None,
    include_minute: bool = False,
    minute_freq: str = "1m",
    include_trading_value: bool = False,
    investors: Iterable[str] | None = None,
    index_codes: Iterable[str] | None = None,
    adjusted: bool = True,
) -> Mapping[str, list[Path]]:
    """Collect daily/auxiliary datasets from pykrx and persist them to ``data/raw``."""

    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if start > end:
        raise ValueError("start_date가 end_date보다 늦습니다.")

    raw_root = _resolve_raw_dir(raw_dir)
    pykrx_root = raw_root / "pykrx"
    pykrx_root.mkdir(parents=True, exist_ok=True)

    investors = tuple(investors or DEFAULT_INVESTORS)
    index_codes = tuple(index_codes or DEFAULT_INDEX_CODES)

    # 수집된 데이터 종류별로 생성된 파일 경로를 정리한다
    results: MutableMapping[str, list[Path]] = {
        "daily_ohlcv": [],
        "minute_ohlcv": [],
        "market_cap": [],
        "fundamental": [],
        "trading_value": [],
        "index_ohlcv": [],
    }

    # 티커 단위로 pykrx API 호출 및 파일 저장 수행
    for ticker in tickers:
        ticker_dir = pykrx_root / ticker
        ticker_dir.mkdir(parents=True, exist_ok=True)

        daily_path = ticker_dir / _filename("ohlcv_daily", ticker, start, end)
        df_daily = stock.get_market_ohlcv_by_date(start_date, end_date, ticker, adjusted=adjusted)
        results["daily_ohlcv"].append(_save_dataframe(df_daily, daily_path, index_name="date"))

        if include_minute:
            minute_path = ticker_dir / _filename(f"ohlcv_{minute_freq}", ticker, start, end)
            df_minute = stock.get_market_ohlcv_by_date(
                start_date,
                end_date,
                ticker,
                freq=minute_freq,
            )
            results["minute_ohlcv"].append(_save_dataframe(df_minute, minute_path, index_name="datetime"))

        cap_path = ticker_dir / _filename("market_cap", ticker, start, end)
        df_cap = stock.get_market_cap_by_date(start_date, end_date, ticker)
        results["market_cap"].append(_save_dataframe(df_cap, cap_path, index_name="date"))

        fundamental_path = ticker_dir / _filename("fundamental", ticker, start, end)
        df_fund = stock.get_market_fundamental(start_date, end_date, ticker)
        results["fundamental"].append(_save_dataframe(df_fund, fundamental_path, index_name="date"))

        if include_trading_value:
            for investor in investors:
                trading_path = ticker_dir / _filename(
                    f"trading_value_{_sanitize_for_path(investor)}",
                    ticker,
                    start,
                    end,
                )
                df_trade = _fetch_trading_value(start_date, end_date, ticker, investor)
                results["trading_value"].append(
                    _save_dataframe(df_trade, trading_path, index_name="date")
                )

    # 지수 데이터도 동일한 규칙으로 적재
    index_dir = pykrx_root / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    for code in index_codes:
        index_path = index_dir / _filename("ohlcv", code, start, end)
        df_index = stock.get_index_ohlcv_by_date(start_date, end_date, code)
        results["index_ohlcv"].append(_save_dataframe(df_index, index_path, index_name="date"))

    return {key: paths for key, paths in results.items() if paths}


def _resolve_raw_dir(raw_dir: str | Path | None) -> Path:
    """raw 디렉터리 경로를 보정하고 존재하지 않으면 생성한다."""

    if raw_dir is None:
        project_root = _find_project_root()
        raw_dir = project_root / "data" / "raw"
    path = Path(raw_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _parse_date(value: str) -> datetime:
    """YYYY-MM-DD 형식을 검증하여 datetime으로 변환한다."""

    try:
        return datetime.strptime(value, DATE_FMT)
    except ValueError as exc:  # pragma: no cover - 단순 검증
        raise ValueError(f"날짜 형식이 YYYY-MM-DD가 아닙니다: {value}") from exc


def _filename(prefix: str, key: str, start: datetime, end: datetime) -> str:
    """저장 파일명을 통일된 패턴으로 생성한다."""

    return f"{prefix}_{key}_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.json"


def _sanitize_for_path(value: str) -> str:
    """파일 경로에 사용할 수 있도록 문자열을 정제한다."""

    return "".join(ch for ch in value if ch.isalnum() or ch in ("-", "_")) or "unknown"


def _save_dataframe(df: "pd.DataFrame", path: Path, *, index_name: str) -> Path:
    """DataFrame을 JSON 구조(meta+data)로 저장한다."""

    if df is None or df.empty:
        LOGGER.warning("pykrx 데이터가 비어 있어 저장을 건너뜁니다: %s", path.name)
        return path

    df = df.copy()
    df.reset_index(inplace=True)
    if df.columns.size > 0:
        df.rename(columns={df.columns[0]: index_name}, inplace=True)
    if index_name in df.columns:
        try:
            df[index_name] = pd.to_datetime(df[index_name]).dt.strftime(DATE_FMT)
        except Exception:  # pragma: no cover - 변환 실패 시 기록만 남김
            LOGGER.debug("%s 컬럼 날짜 형식 변환 실패", index_name, exc_info=True)

    df.rename(columns=_COLUMN_MAP, inplace=True)

    payload = {
        "meta": {
            "index": index_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "pykrx",
        },
        "data": df.to_dict(orient="records"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)
    LOGGER.info("pykrx 데이터 저장: %s", path)
    return path


def _fetch_trading_value(start_date: str, end_date: str, ticker: str, investor: str):
    """투자주체별 매매대금 API 시그니처 변화에 대응한다."""

    candidates = (
        {"ticker": ticker, "investor": investor},
        {"ticker": ticker, "invst": investor},
        {"investor": investor},
        {"invst": investor},
    )
    for kwargs in candidates:
        try:
            return stock.get_market_trading_value_by_date(start_date, end_date, **kwargs)
        except TypeError:
            continue
    return stock.get_market_trading_value_by_date(start_date, end_date, market="ALL", investor=investor)


_COLUMN_MAP: Mapping[str, str] = {
    "시가": "open",
    "고가": "high",
    "저가": "low",
    "종가": "close",
    "거래량": "volume",
    "거래대금": "value",
    "시가총액": "market_cap",
    "상장주식수": "shares_outstanding",
    "PER": "per",
    "PBR": "pbr",
    "EPS": "eps",
    "BPS": "bps",
    "DIV": "dividend",
}
