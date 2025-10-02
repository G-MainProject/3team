# -*- coding: utf-8 -*-
"""Merge raw inputs into bronze-level daily datasets (clean ASCII version).

This module loads price data (Kiwoom preferred, then pykrx), optional
fundamentals and news features, joins them on date, fills gaps, and writes a
per-ticker bronze table under data/bronze.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class MergeConfig:
    tickers: Iterable[str]
    raw_root: Path
    bronze_root: Path
    price_source: str = "pykrx"
    news_dir: Optional[Path] = None
    fundamentals_dir: Optional[Path] = None


def run(
    *,
    tickers: Iterable[str] | None = None,
    raw_root: str | Path | None = None,
    bronze_root: str | Path | None = None,
    price_source: str = "pykrx",
    news_dir: str | Path | None = None,
    fundamentals_dir: str | Path | None = None,
) -> list[Path]:
    """Process all tickers and return written bronze file paths."""

    resolved_raw = _resolve_raw_root(raw_root)
    selected = list(tickers) if tickers else _discover_raw_tickers(resolved_raw, price_source)
    if not selected:
        raise RuntimeError("No tickers found under raw root.")
    cfg = MergeConfig(
        tickers=selected,
        raw_root=resolved_raw,
        bronze_root=_resolve_bronze_root(bronze_root),
        price_source=price_source.lower(),
        news_dir=Path(news_dir) if news_dir else None,
        fundamentals_dir=Path(fundamentals_dir) if fundamentals_dir else None,
    )
    outputs: list[Path] = []
    for tk in cfg.tickers:
        try:
            outputs.append(_build_single_bronze(tk, cfg))
        except FileNotFoundError as exc:
            LOGGER.warning("Skipping %s: %s", tk, exc)
    return outputs


def merge_sources(
    *,
    ticker: str,
    raw_root: str | Path | None = None,
    bronze_root: str | Path | None = None,
    price_source: str = "pykrx",
    news_dir: str | Path | None = None,
    fundamentals_dir: str | Path | None = None,
) -> Path:
    cfg = MergeConfig(
        tickers=[ticker],
        raw_root=_resolve_raw_root(raw_root),
        bronze_root=_resolve_bronze_root(bronze_root),
        price_source=price_source.lower(),
        news_dir=Path(news_dir) if news_dir else None,
        fundamentals_dir=Path(fundamentals_dir) if fundamentals_dir else None,
    )
    return _build_single_bronze(ticker, cfg)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _build_single_bronze(ticker: str, cfg: MergeConfig) -> Path:
    price_df = _load_price_frame(ticker, cfg)
    fund_df = _load_fundamentals(ticker, cfg)
    news_df = _load_news_features(ticker, cfg)

    frames = [price_df]
    if fund_df is not None and not fund_df.empty:
        frames.append(fund_df)
    if news_df is not None and not news_df.empty:
        try:
            news_df = _align_news_to_trading_days(news_df, price_df.index)
        except Exception:
            pass
        frames.append(news_df)

    merged = frames[0]
    for f in frames[1:]:
        merged = merged.join(f, how="left")

    merged = _fill_calendar_and_missing(merged)

    # Basic ratios
    def safe_ratio(a: str, b: str, out: str, factor: float = 1.0) -> None:
        if a in merged.columns and b in merged.columns:
            merged[out] = (merged[a] / merged[b]) * factor
            merged[out] = merged[out].replace([np.inf, -np.inf], np.nan)

    safe_ratio("fund_net_income_ttm", "fund_equity", "roe", 1.0)
    safe_ratio("fund_net_income_ttm", "fund_assets", "roa", 1.0)
    if "market_cap" in merged.columns and "fund_net_income_ttm" in merged.columns:
        merged["per"] = (merged["market_cap"] / merged["fund_net_income_ttm"]).replace([np.inf, -np.inf], np.nan)
    if "market_cap" in merged.columns and "fund_equity" in merged.columns:
        merged["pbr"] = (merged["market_cap"] / merged["fund_equity"]).replace([np.inf, -np.inf], np.nan)
    safe_ratio("fund_liabilities", "fund_equity", "debt_ratio", 100.0)
    safe_ratio("fund_current_assets", "fund_current_liabilities", "current_ratio", 100.0)
    if "fund_current_assets" in merged.columns and "fund_current_liabilities" in merged.columns and "fund_inventories" in merged.columns:
        merged["quick_ratio"] = ((merged["fund_current_assets"] - merged["fund_inventories"]) / merged["fund_current_liabilities"]) * 100.0
        merged["quick_ratio"] = merged["quick_ratio"].replace([np.inf, -np.inf], np.nan)
    safe_ratio("fund_equity", "fund_assets", "equity_ratio", 100.0)

    merged["ticker"] = ticker
    cfg.bronze_root.mkdir(parents=True, exist_ok=True)
    out_path = cfg.bronze_root / f"{ticker}.parquet"
    path = _write_table(merged.reset_index().rename(columns={"index": "date"}), out_path)
    LOGGER.info("Bronze dataset saved: %s", path)
    return path


def _load_price_frame(ticker: str, cfg: MergeConfig) -> pd.DataFrame:
    """Load price from Kiwoom (preferred) or pykrx into a daily index frame."""

    k_dir = cfg.raw_root / "kiwoom" / ticker
    p_dir = cfg.raw_root / "pykrx" / ticker

    if k_dir.exists():
        try:
            return _load_kiwoom_price(k_dir)
        except FileNotFoundError:
            pass
    if p_dir.exists():
        return _load_pykrx_price(p_dir)
    raise FileNotFoundError(f"Price directory not found: {k_dir} or {p_dir}")


def _load_pykrx_price(directory: Path) -> pd.DataFrame:
    ohlcv = _latest_file(directory, "ohlcv_daily")
    if ohlcv is None:
        raise FileNotFoundError(f"No pykrx ohlcv file in {directory}")
    df = _read_json_table(ohlcv)
    df.rename(columns={"value": "tr_value"}, inplace=True)

    for prefix in ("market_cap", "fundamental"):
        extra = _latest_file(directory, prefix)
        if extra is None:
            continue
        ex = _read_json_table(extra)
        # ensure date present
        if ex.empty or "date" not in ex.columns:
            continue
        ex["date"] = pd.to_datetime(ex["date"], errors="coerce")
        ex = ex.dropna(subset=["date"]).copy()
        df = df.merge(ex, on="date", how="left")

    if "volume" not in df.columns:
        candidates = [c for c in ("volume", "volume_x", "volume_y") if c in df.columns]
        if candidates:
            vol = None
            for c in candidates:
                s = pd.to_numeric(df[c], errors="coerce")
                vol = s if vol is None else vol.fillna(s)
            df["volume"] = vol
    for c in ("volume_x", "volume_y"):
        if c in df.columns:
            df.drop(columns=[c], inplace=True)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    df.set_index("date", inplace=True)
    df.sort_index(inplace=True)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _load_kiwoom_price(directory: Path) -> pd.DataFrame:
    daily = _latest_file(directory, "ka10001")
    if daily is None:
        raise FileNotFoundError(f"No kiwoom ka10001 file in {directory}")
    payload = _read_json(daily)
    response = payload.get("response", {}) if isinstance(payload, dict) else {}
    rows = response.get("output") or response.get("items") or response.get("data") or response.get("body")
    if not rows:
        raise FileNotFoundError(f"Kiwoom ka10001 response empty: {daily}")
    df = pd.DataFrame(rows)
    rename_map = {
        "trd_date": "date",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
        "tr_value": "tr_value",
    }
    df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)
    if "date" not in df.columns:
        df["date"] = df.get("trd_date")
    # support yyyymmdd or ISO
    try:
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
    except Exception:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    df.set_index("date", inplace=True)
    df.sort_index(inplace=True)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _load_fundamentals(ticker: str, cfg: MergeConfig) -> Optional[pd.DataFrame]:
    # Placeholder: rely on DART-derived features already in pykrx fundamental file if any
    # Here we simply return an empty DataFrame to keep pipeline consistent
    return pd.DataFrame()


def _load_news_features(ticker: str, cfg: MergeConfig) -> Optional[pd.DataFrame]:
    # Optional: load precomputed news features from cfg.news_dir if present
    if not cfg.news_dir:
        return pd.DataFrame()
    # Look for <news_dir>/<ticker>.json or .parquet
    j = cfg.news_dir / f"{ticker}.json"
    if j.exists():
        try:
            df = _read_json_table(j)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date"]).copy()
                df.set_index("date", inplace=True)
                df.sort_index(inplace=True)
                for c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce")
                return df
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def _align_news_to_trading_days(df: pd.DataFrame, trading_index: pd.Index) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    idx = pd.to_datetime(df.index).astype("datetime64[ns]").values
    trading = pd.to_datetime(pd.Index(trading_index)).astype("datetime64[ns]")
    trading = trading.sort_values().unique()
    if trading.size == 0:
        return df
    pos = trading.searchsorted(idx, side="right") - 1
    valid = pos >= 0
    if not valid.any():
        return df.iloc[0:0]
    aligned_dates = trading[pos]
    sfr = df.copy().iloc[valid, :]
    sfr["_aligned_date"] = aligned_dates[valid]
    agg: dict[str, str] = {}
    for c in ("news_sentiment_mean",):
        if c in sfr.columns:
            agg[c] = "mean"
    for c in ("news_count", "news_pos", "news_neu", "news_neg"):
        if c in sfr.columns:
            agg[c] = "sum"
    grouped = sfr.groupby("_aligned_date").agg(agg) if agg else sfr
    grouped.index.name = None
    ti = pd.to_datetime(pd.Index(trading_index))
    out = grouped.reindex(ti)
    for col in list(out.columns):
        if str(col).startswith("news_"):
            out[col] = out[col].fillna(0.0)
    return out.sort_index()


def _fill_calendar_and_missing(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.sort_index()
    # forward fill price columns where appropriate
    for c in df.columns:
        if c in ("open", "high", "low", "close", "volume", "tr_value"):
            df[c] = df[c].astype(float)
    return df


def _latest_file(directory: Path, prefix: str) -> Optional[Path]:
    cands = sorted(directory.glob(f"{prefix}*.json"))
    return cands[-1] if cands else None


def _read_json_table(path: Path) -> pd.DataFrame:
    payload = _read_json(path)
    data = None
    if isinstance(payload, dict):
        for key in ("data", "rows", "items", "result", "response"):
            if key in payload and isinstance(payload[key], list):
                data = payload[key]
                break
        if data is None:
            for val in payload.values():
                if isinstance(val, list):
                    data = val
                    break
    else:
        data = payload
    if data is None:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    # Normalize a date-like column if available
    if df.columns.size:
        if "date" not in df.columns:
            candidates = ["date", "trd_date", "trd_dd", "basDt", "dt", "Date", "DATE"]
            found = next((c for c in candidates if c in df.columns), None)
            if found and found != "date":
                df.rename(columns={found: "date"}, inplace=True)
        if "date" not in df.columns:
            first = df.columns[0]
            df.rename(columns={first: "date"}, inplace=True)
    return df


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _resolve_raw_root(raw_root: str | Path | None) -> Path:
    if raw_root is not None:
        return Path(raw_root)
    return _find_project_root() / "data" / "raws"


def _resolve_bronze_root(bronze_root: str | Path | None) -> Path:
    if bronze_root is not None:
        return Path(bronze_root)
    return _find_project_root() / "data" / "bronze"


def _find_project_root() -> Path:
    cur = Path(__file__).resolve()
    for p in cur.parents:
        if (p / ".env").exists() or (p / "data").exists():
            return p
    return cur.parents[4]


def _discover_raw_tickers(raw_root: Path, price_source: str) -> list[str]:
    price_source = price_source.lower()
    cands: set[str] = set()
    sources: list[Path] = []
    if price_source in ("pykrx", "both") or price_source not in ("pykrx", "kiwoom"):
        sources.append(raw_root / "pykrx")
    if price_source in ("kiwoom", "both"):
        sources.append(raw_root / "kiwoom")
    for src in sources:
        if src.exists():
            for child in src.iterdir():
                if child.is_dir():
                    cands.add(child.name)
    return sorted(cands)


def _write_table(df: pd.DataFrame, path: Path) -> Path:
    try:
        df.to_parquet(path, index=False)
        return path
    except (ImportError, ValueError):
        fb = path.with_suffix(".pkl")
        df.to_pickle(fb)
        LOGGER.warning("Parquet unavailable; wrote pickle: %s", fb)
        return fb

