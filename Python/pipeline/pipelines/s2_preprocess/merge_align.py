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
import csv
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
        "market_cap": "market_cap",
        "shares_outstanding": "shares_outstanding",
        # Kiwoom ka10001 alias keys
        "mac": "market_cap",  # market cap (alias provided by gateway)
        "mktcap": "market_cap",
        "tot_mkt_val": "market_cap",
        "list_shrs": "shares_outstanding",
        "shrs_out": "shares_outstanding",
        "shares": "shares_outstanding",
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

    # Try to enrich from optional kiwoom meta (shares_outstanding)
    meta = _latest_file(directory, "meta")
    if meta is not None:
        try:
            meta_payload = _read_json(meta)
            meta_rows = None
            if isinstance(meta_payload, dict):
                # Common containers
                for key in ("response", "data", "body"):
                    if key in meta_payload and isinstance(meta_payload[key], list):
                        meta_rows = meta_payload[key]
                        break
                if meta_rows is None:
                    # flat list under some other key
                    for v in meta_payload.values():
                        if isinstance(v, list):
                            meta_rows = v; break
            elif isinstance(meta_payload, list):
                meta_rows = meta_payload
            if meta_rows:
                mdf = pd.DataFrame(meta_rows)
                # Normalize columns
                # expected keys: date, shares_outstanding (but tolerate variations)
                if "date" not in mdf.columns:
                    cand = next((c for c in ("trd_date","basDt","dt","Date","DATE") if c in mdf.columns), None)
                    if cand:
                        mdf.rename(columns={cand: "date"}, inplace=True)
                so_col = next((c for c in ("shares_outstanding","shrs_out","list_shrs","shares") if c in mdf.columns), None)
                if so_col:
                    if "date" in mdf.columns:
                        mdf["date"] = pd.to_datetime(mdf["date"], errors="coerce")
                        mdf = mdf.dropna(subset=["date"]).copy()
                        mdf.set_index("date", inplace=True)
                        mdf.sort_index(inplace=True)
                        df["shares_outstanding"] = df["shares_outstanding"].combine_first(pd.to_numeric(mdf[so_col], errors="coerce")) if "shares_outstanding" in df.columns else pd.to_numeric(mdf[so_col], errors="coerce").reindex(df.index)
                    else:
                        # no date info: treat as constant snapshot
                        try:
                            const_val = float(pd.to_numeric(mdf[so_col], errors="coerce").dropna().iloc[-1])
                            df["shares_outstanding"] = df.get("shares_outstanding").combine_first(pd.Series(const_val, index=df.index)) if "shares_outstanding" in df.columns else const_val
                        except Exception:
                            pass
        except Exception:
            pass

    # Compute market_cap if possible
    if "market_cap" not in df.columns or df["market_cap"].isna().all():
        try:
            if "close" in df.columns and "shares_outstanding" in df.columns:
                cap = pd.to_numeric(df["close"], errors="coerce") * pd.to_numeric(df["shares_outstanding"], errors="coerce")
                df["market_cap"] = df.get("market_cap").combine_first(cap) if "market_cap" in df.columns else cap
        except Exception:
            pass

    return df


def _load_fundamentals(ticker: str, cfg: MergeConfig) -> Optional[pd.DataFrame]:
    """Load fundamentals from DART raws if available, with robust fallbacks.

    Strategy
    - Prefer DART multi-account (balance sheet) latest values per corp_code.
      Extract: equity, assets, liabilities, current assets/liabilities, inventories.
    - If DART missing, derive minimal fundamentals from pykrx:
        fund_equity ≈ market_cap / pbr (if pbr>0)
        fund_net_income_ttm ≈ market_cap / per (if per>0)
    - Align to price trading-day index by repeating last-known snapshot.
    """

    # Ensure price index to align outputs
    try:
        price_df = _load_price_frame(ticker, cfg)
        idx = price_df.index
    except Exception:
        return pd.DataFrame()

    values: dict[str, float] = {}

    # Helper: base ticker (common stock) for corp_code lookup
    def _base(code: object) -> str:
        raw = str(code or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            return raw.zfill(6)
        d = digits.zfill(6)
        return d[:-1] + "0"

    # Helper: parse numbers like "1,234" or "-" safely
    def _num(x: object) -> float:
        try:
            if x is None:
                return float("nan")
            if isinstance(x, (int, float)):
                return float(x)
            s = str(x).strip()
            if not s or s in ("-", "--"):
                return float("nan")
            # Handle parentheses negatives and commas
            neg = False
            if s.startswith("(") and s.endswith(")"):
                neg = True
                s = s[1:-1]
            s = s.replace(",", "")
            val = float(s)
            return -val if neg else val
        except Exception:
            return float("nan")

    # Map ticker -> corp_code via data/dart_corpcode.csv
    corp_code: str | None = None
    try:
        root = _find_project_root()
        csv_path = root / "data" / "dart_corpcode.csv"
        if csv_path.exists():
            base = _base(ticker)
            with csv_path.open("r", encoding="utf-8-sig", errors="ignore") as fp:
                rdr = csv.DictReader(fp)
                headers = { (h or "").strip().lower(): h for h in (rdr.fieldnames or []) }
                t_col = headers.get("ticker") or headers.get("stock_code") or headers.get("code") or headers.get("symbol")
                c_col = headers.get("corp_code") or headers.get("corpcode") or headers.get("corpcode_id") or headers.get("corp")
                for row in rdr:
                    tk = str(row.get(t_col, "") if t_col else next(iter(row.values()), "")).strip()
                    tk = ("".join(ch for ch in tk if ch.isdigit())).zfill(6) if tk else ""
                    if tk and tk[:-1] + "0" == base:
                        corp_code = str(row.get(c_col, "") if c_col else "").strip()
                        if corp_code:
                            break
    except Exception:
        corp_code = None

    # Fallback: scan dart raws to discover corp_code by stock_code
    if corp_code is None:
        try:
            dart_root = cfg.raw_root / "dart"
            base = _base(ticker)
            if dart_root.exists():
                for corp_dir in dart_root.iterdir():
                    if not corp_dir.is_dir():
                        continue
                    sample = _latest_file(corp_dir, "fnlttMultiAcnt_")
                    if not sample:
                        continue
                    try:
                        pl = _read_json(sample)
                        found = False
                        for rec in (pl or []):
                            for row in (rec.get("rows") or []):
                                sc = str(row.get("stock_code") or "").strip()
                                if sc and sc.zfill(6)[:-1] + "0" == base:
                                    corp_code = corp_dir.name
                                    found = True
                                    break
                            if found:
                                break
                        if found:
                            break
                    except Exception:
                        continue
        except Exception:
            pass

    # Try DART multi-account snapshot
    try:
        if corp_code:
            dart_dir = cfg.raw_root / "dart" / corp_code
            multi = _latest_file(dart_dir, "fnlttMultiAcnt_") if dart_dir.exists() else None
        else:
            multi = None
    except Exception:
        multi = None

    if multi is not None and multi.exists():
        try:
            # Load all available multi-account files for current and previous years
            dart_dir = multi.parent
            multi_files = sorted(dart_dir.glob("fnlttMultiAcnt_*.json"))
            prefer = {"11014": 0, "11013": 1, "11012": 2, "11011": 3}

            # Collect BS accounts (latest first by reprt_code preference)
            # Accept common synonyms/variants per account
            mapping_variants: dict[str, list[str]] = {
                "fund_equity": ["자본총계", "총자본", "자본 총계"],
                "fund_assets": ["자산총계", "총자산", "자산 총계"],
                "fund_liabilities": ["부채총계", "총부채", "부채 총계"],
                "fund_current_assets": ["유동자산", "유동 자산", "유동자산총계"],
                "fund_current_liabilities": ["유동부채", "유동 부채", "유동부채총계"],
                "fund_inventories": ["재고자산", "재고 자산"],
            }
            def _match_account(name: str) -> str | None:
                nm0 = (name or "").strip()
                nm = nm0.replace(" ", "")
                for dest, keys in mapping_variants.items():
                    for k in keys:
                        kk = k.replace(" ", "")
                        if nm == kk or nm.startswith(kk) or kk in nm:
                            return dest
                return None
            seen_bs: set[str] = set()

            # For TTM: gather YTD net income by (year, reprt_code)
            net_ytd: dict[tuple[int, str], float] = {}

            def _is_net_income(name: str) -> bool:
                n = (name or "").replace(" ", "").strip()
                return ("당기" in n and "이익" in n)  # handles '당기순이익(손실)'

            for mf in multi_files:
                try:
                    payload = _read_json(mf)
                except Exception:
                    continue
                # payload: list of {reprt_code, year, rows:[...]}
                for rec in (payload or []):
                    try:
                        y = int(rec.get("year") or rec.get("bsns_year") or 0)
                    except Exception:
                        y = 0
                    rc = str(rec.get("reprt_code", ""))
                    pri = prefer.get(rc, 9)
                    for row in (rec.get("rows") or []):
                        nm = str(row.get("account_nm", "")).strip()
                        val = _num(row.get("thstrm_amount"))
                        # Balance sheet snapshots (latest preferred)
                        if pri <= 3 and nm:
                            dest = _match_account(nm)
                            if dest and dest not in seen_bs and pd.notna(val):
                                values[dest] = float(val)
                                seen_bs.add(dest)
                        # Net income YTD for TTM
                        if _is_net_income(nm) and pd.notna(val) and y:
                            # Store highest precedence (lowest pri) per (year, rc)
                            key = (y, rc)
                            if key not in net_ytd or pri < prefer.get(key[1], 9):
                                net_ytd[key] = float(val)

            # Fallback: if equity missing but assets and liabilities present
            if ("fund_equity" not in values) and ("fund_assets" in values) and ("fund_liabilities" in values):
                try:
                    ae = float(values.get("fund_assets", float("nan")))
                    lb = float(values.get("fund_liabilities", float("nan")))
                    if pd.notna(ae) and pd.notna(lb):
                        values["fund_equity"] = ae - lb
                except Exception:
                    pass

            # Derive quarterly net income and TTM from YTD and FY
            def _quarters_from_ytd(year: int) -> dict[int, float]:
                q: dict[int, float] = {}
                ytd_q1 = net_ytd.get((year, "11011"))
                ytd_q2 = net_ytd.get((year, "11012"))
                ytd_q3 = net_ytd.get((year, "11013"))
                fy = net_ytd.get((year, "11014"))
                if ytd_q1 is not None:
                    q[1] = ytd_q1
                if ytd_q2 is not None:
                    base = ytd_q1 if ytd_q1 is not None else 0.0
                    q[2] = ytd_q2 - base
                if ytd_q3 is not None:
                    base = ytd_q2 if ytd_q2 is not None else (ytd_q1 or 0.0)
                    q[3] = ytd_q3 - base
                if fy is not None:
                    base = ytd_q3 if ytd_q3 is not None else (ytd_q2 or ytd_q1 or 0.0)
                    q[4] = fy - base
                return q

            years = sorted({y for (y, _rc) in net_ytd.keys()})
            if years:
                latest_year = max(years)
                q_latest = _quarters_from_ytd(latest_year)
                q_prev = _quarters_from_ytd(latest_year - 1) if (latest_year - 1) in years else {}
                # Determine latest reported quarter available this year
                latest_q = max(q_latest.keys()) if q_latest else None
                if latest_q is None and (latest_year in years) and (latest_year, "11014") in net_ytd:
                    # Annual only
                    values["fund_net_income_ttm"] = float(net_ytd[(latest_year, "11014")])
                elif latest_q is not None:
                    seq = [(latest_year - 1, 2), (latest_year - 1, 3), (latest_year - 1, 4),
                           (latest_year, 1), (latest_year, 2), (latest_year, 3), (latest_year, 4)]
                    # up to latest_q of latest_year
                    upto = [(y, q) for (y, q) in seq if (y < latest_year) or (y == latest_year and q <= latest_q)]
                    quarters: list[float] = []
                    for y, q in upto:
                        v = (q_latest if y == latest_year else q_prev).get(q)
                        if v is not None and pd.notna(v):
                            quarters.append(float(v))
                    if len(quarters) >= 4:
                        values["fund_net_income_ttm"] = sum(quarters[-4:])
        except Exception:
            pass

    # Fallbacks from pykrx-derived fields (per/pbr/market_cap)
    try:
        mc = float(price_df["market_cap"].dropna().iloc[-1]) if "market_cap" in price_df.columns else float("nan")
    except Exception:
        mc = float("nan")
    try:
        pbr = float(price_df["pbr"].dropna().iloc[-1]) if "pbr" in price_df.columns else float("nan")
    except Exception:
        pbr = float("nan")
    try:
        per = float(price_df["per"].dropna().iloc[-1]) if "per" in price_df.columns else float("nan")
    except Exception:
        per = float("nan")

    if ("fund_equity" not in values) and pd.notna(mc) and pd.notna(pbr) and pbr not in (0.0,):
        try:
            values["fund_equity"] = float(mc) / float(pbr)
        except Exception:
            pass
    if ("fund_net_income_ttm" not in values) and pd.notna(mc) and pd.notna(per) and per not in (0.0,):
        try:
            values["fund_net_income_ttm"] = float(mc) / float(per)
        except Exception:
            pass

    if not values:
        return pd.DataFrame()

    out = pd.DataFrame(index=idx)
    for k, v in values.items():
        try:
            out[k] = float(v)
        except Exception:
            out[k] = np.nan
    return out


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
