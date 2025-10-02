# -*- coding: utf-8 -*-
"""pykrx ?섏쭛 ?좏떥由ы떚: ?먯떆(raw) ?곸뿭??JSON ?뚯씪濡????""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Sequence

try:
    from pykrx import stock  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "pykrx媛 ?ㅼ튂?섏뼱 ?덉? ?딆뒿?덈떎. `pip install pykrx pandas`濡?癒쇱? ?ㅼ튂?섏꽭??"
    ) from exc

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "pandas媛 ?ㅼ튂?섏뼱 ?덉? ?딆뒿?덈떎. `pip install pandas`濡?癒쇱? ?ㅼ튂?섏꽭??"
    ) from exc

LOGGER = logging.getLogger(__name__)
DEFAULT_INVESTORS = ("媛쒖씤", "?멸뎅??, "湲곌??⑷퀎")
DEFAULT_INDEX_CODES = ("1001", "2001")  # KOSPI, KOSDAQ
DATE_FMT = "%Y-%m-%d"


def _find_project_root() -> Path:
    """?섍꼍(.env) ?먮뒗 data ?대뜑媛 ?ы븿???꾨줈?앺듃 猷⑦듃瑜?李얜뒗??"""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists():
            return parent
    for parent in current.parents:
        if (parent / "data").exists():
            return parent
    return current.parents[4]


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
    """pykrx?먯꽌 ?쇰퀎/蹂댁“ ?곗씠???섏쭛 ??data/raw?????""

    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if start > end:
        raise ValueError("start_date媛 end_date蹂대떎 鍮좊쫭?덈떎.")

    raw_root = _resolve_raw_dir(raw_dir)
    pykrx_root = raw_root / "pykrx"
    pykrx_root.mkdir(parents=True, exist_ok=True)

    investors = tuple(investors or DEFAULT_INVESTORS)
    index_codes = tuple(index_codes or DEFAULT_INDEX_CODES)

    results: MutableMapping[str, list[Path]] = {
        "daily_ohlcv": [],
        "minute_ohlcv": [],
        "market_cap": [],
        "fundamental": [],
        "trading_value": [],
        "index_ohlcv": [],
    }

    # ?곗빱蹂??섏쭛
    for ticker in tickers:
        ticker_dir = pykrx_root / ticker
        ticker_dir.mkdir(parents=True, exist_ok=True)

        # ?쇰퀎 OHLCV
        daily_path = ticker_dir / _filename("ohlcv_daily", ticker, start, end)
        df_daily = stock.get_market_ohlcv_by_date(start_date, end_date, ticker, adjusted=adjusted)
        results["daily_ohlcv"].append(_save_dataframe(df_daily, daily_path, index_name="date"))

        # 遺꾨큺(?듭뀡)
        if include_minute:
            minute_path = ticker_dir / _filename(f"ohlcv_{minute_freq}", ticker, start, end)
            df_minute = stock.get_market_ohlcv_by_date(start_date, end_date, ticker, freq=minute_freq)
            results["minute_ohlcv"].append(_save_dataframe(df_minute, minute_path, index_name="datetime"))

        # ?쒓?珥앹븸
        cap_path = ticker_dir / _filename("market_cap", ticker, start, end)
        df_cap = stock.get_market_cap_by_date(start_date, end_date, ticker)
        results["market_cap"].append(_save_dataframe(df_cap, cap_path, index_name="date"))

        # ??붾찘??        fundamental_path = ticker_dir / _filename("fundamental", ticker, start, end)
        df_fund = stock.get_market_fundamental(start_date, end_date, ticker)
        results["fundamental"].append(_save_dataframe(df_fund, fundamental_path, index_name="date"))

        # ?ъ옄?먮퀎 嫄곕옒?湲??듭뀡)
        if include_trading_value:
            for investor in investors:
                trading_path = ticker_dir / _filename(
                    f"trading_value_{_sanitize_for_path(investor)}",
                    ticker,
                    start,
                    end,
                )
                df_trade = _fetch_trading_value(start_date, end_date, ticker, investor)
                results["trading_value"].append(_save_dataframe(df_trade, trading_path, index_name="date"))

    # 吏???곗씠???섏쭛
    index_dir = pykrx_root / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    for code in index_codes:
        index_path = index_dir / _filename("ohlcv", code, start, end)
        df_index = stock.get_index_ohlcv_by_date(start_date, end_date, code)
        results["index_ohlcv"].append(_save_dataframe(df_index, index_path, index_name="date"))

    return {key: paths for key, paths in results.items() if paths}


def _resolve_raw_dir(raw_dir: str | Path | None) -> Path:
    """raw ?곗씠??猷⑦듃瑜??댁꽍?섍퀬 ?붾젆?곕━瑜??앹꽦?쒕떎."""
    if raw_dir is None:
        project_root = _find_project_root()
        raw_dir = project_root / "data" / "raws"
    path = Path(raw_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _parse_date(value: str) -> datetime:
    """YYYY-MM-DD 臾몄옄?댁쓣 ?뚯떛??datetime?쇰줈 蹂?섑븳??"""
    return datetime.strptime(value, DATE_FMT)


def _filename(prefix: str, key: str, start: datetime, end: datetime) -> str:
    """?쇨????뚯씪紐낆쓣 ?앹꽦?쒕떎."""
    return f"{prefix}_{key}_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.json"


def _sanitize_for_path(value: str) -> str:
    """寃쎈줈???덉쟾?섍쾶 ?????덈룄濡?臾몄옄?댁쓣 ?뺤젣?쒕떎."""
    return "".join(ch for ch in value if ch.isalnum() or ch in ("-", "_")) or "unknown"


def _save_dataframe(df: "pd.DataFrame", path: Path, *, index_name: str) -> Path:
    """DataFrame??JSON ?섏씠濡쒕뱶(meta+data)濡???ν븳??"""
    if df is None or df.empty:
        LOGGER.warning("pykrx ?곗씠?곌? 鍮꾩뼱 ?덉뼱 ?뚯씪留??앹꽦?⑸땲?? %s", path.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"meta": {}, "data": []}, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    df = df.copy()
    df.reset_index(inplace=True)
    if df.columns.size > 0:
        df.rename(columns={df.columns[0]: index_name}, inplace=True)
    if index_name in df.columns:
        try:
            df[index_name] = pd.to_datetime(df[index_name]).dt.strftime(DATE_FMT)
        except Exception:  # pragma: no cover
            LOGGER.debug("%s 而щ읆 ?좎쭨 ?뺤떇 蹂???ㅽ뙣", index_name, exc_info=True)

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
    LOGGER.info("pykrx 寃곌낵 ??? %s", path)
    return path


def _fetch_trading_value(start_date: str, end_date: str, ticker: str, investor: str):
    """?ъ옄?먮퀎 嫄곕옒?湲?API???몄옄紐낆쓣 ?좎뿰?섍쾶 泥섎━?쒕떎."""
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
    "?쒓?": "open",
    "怨좉?": "high",
    "?媛": "low",
    "醫낃?": "close",
    "嫄곕옒??: "volume",
    "嫄곕옒?湲?: "value",
    "?쒓?珥앹븸": "market_cap",
    "?곸옣二쇱떇??: "shares_outstanding",
    "PER": "per",
    "PBR": "pbr",
    "EPS": "eps",
    "BPS": "bps",
    "DIV": "dividend",
}

