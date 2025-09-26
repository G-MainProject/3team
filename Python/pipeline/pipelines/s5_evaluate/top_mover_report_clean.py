# -*- coding: utf-8 -*-
"""Generate forecast report for top movers (clean UTF-8 version).

- No *_display fields are injected into fundamentals dict
- fundamentals_display is not used (omit entirely)
- Key financial ratios are always present in fundamentals (fill with '-' if missing)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional, Iterable

import numpy as np
from time import perf_counter
import os

def _tlog(msg: str) -> None:
    if os.getenv("PIPELINE_TIMING_VERBOSE") == "1":
        print(msg)
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore

try:  # optional, used to enrich names
    from pykrx import stock  # type: ignore
except Exception:  # pragma: no cover
    stock = None  # type: ignore


MAIN_RATIO_KEYS = [
    "roe", "roa", "per", "pbr",
    "debt_ratio", "current_ratio", "quick_ratio", "equity_ratio",
]


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    opts = parser.parse_args(argv)

    t_total = perf_counter()

    t = perf_counter()
    top_data = _read_json(opts.top_movers)
    predictions = _read_json(opts.predictions)
    _tlog(f"[s5] loaded inputs in {perf_counter() - t:.3f}s")

    t = perf_counter()
    predicted_prices = np.array(predictions.get("prices"), dtype=float)
    predicted_returns = np.array(predictions.get("returns"), dtype=float)
    horizons = [str(h) for h in predictions.get("horizons", [])]
    actual_prices = _load_array(opts.actual_prices)
    _tlog(f"[s5] prepared arrays in {perf_counter() - t:.3f}s")
    if predicted_prices.shape != actual_prices.shape:
        raise ValueError("Predicted and actual price arrays must have the same shape.")

    t = perf_counter()
    labels = _load_labels(opts.labels, predicted_prices.shape[0]) if opts.labels else [
        {"ticker": str(i), "index": i} for i in range(predicted_prices.shape[0])
    ]
    _tlog(f"[s5] loaded labels in {perf_counter() - t:.3f}s")

    # name/details/source
    name_lookup = {str(e.get("ticker")): e.get("name") for e in top_data.get("details", [])}
    details_lookup = {str(e.get("ticker")): e for e in top_data.get("details", [])}
    top_source = top_data.get("source")

    # enrich names via pykrx if possible
    date_for_lookup = str(top_data.get("date") or "").replace("-", "")
    top_tickers = [str(t) for t in top_data.get("tickers", [])]
    t = perf_counter()
    if stock is not None and date_for_lookup:
        for tk in top_tickers:  # 변수명 충돌 방지(타이머 t와 구분)  # 한글 주석
            if not name_lookup.get(tk):
                try:
                    name_lookup[tk] = stock.get_market_ticker_name(tk.zfill(6), date=date_for_lookup)
                except Exception:
                    pass
    _tlog(f"[s5] enriched names in {perf_counter() - t:.3f}s")

    # map ticker -> sample indices
    t = perf_counter()
    index_map: dict[str, list[int]] = {}
    for idx, info in enumerate(labels):
        ticker = str(info.get("ticker", "")).strip()
        if ticker:
            index_map.setdefault(ticker, []).append(idx)
    _tlog(f"[s5] built index map in {perf_counter() - t:.3f}s")

    # current close handling — only accept arrays matching N
    current_close: np.ndarray | None = None
    if opts.close_values and opts.close_values.exists():
        try:
            arr = _load_array(opts.close_values).astype(float)
            if arr.shape[0] == predicted_prices.shape[0]:
                current_close = arr
        except Exception:
            current_close = None
    if current_close is None and "current_close" in predictions:
        try:
            arr = np.array(predictions["current_close"], dtype=float)
            if arr.shape[0] == predicted_prices.shape[0]:
                current_close = arr
        except Exception:
            current_close = None

    # union of tickers from tickers[] and details[] to avoid omissions
    t = perf_counter()
    detail_tickers = [str(e.get("ticker")) for e in top_data.get("details", []) if str(e.get("ticker"))]
    seen = set()
    report_tickers: list[str] = []
    for tk in top_tickers + [x for x in detail_tickers if x not in top_tickers]:
        if tk and tk not in seen:
            seen.add(tk)
            report_tickers.append(tk)
    _tlog(f"[s5] prepared {len(report_tickers)} tickers in {perf_counter() - t:.3f}s")

    t_entries = perf_counter()
    entries: list[dict[str, Any]] = []
    for ticker in (report_tickers[: opts.limit] if opts.limit else report_tickers):
        t_one = perf_counter()
        indices = index_map.get(ticker)
        if not indices:
            ind, fund = _load_feature_snapshot(opts.silver_root, ticker, None)
            _ensure_main_ratio_keys(fund)
            det = details_lookup.get(ticker) or {}
            entry_nf: dict[str, Any] = {
                "ticker": ticker,
                "name": name_lookup.get(ticker) or ticker,
                "source": top_source,
                "current_price": float(det.get("current_price")) if _is_number(det.get("current_price")) else None,
                "change_pct": float(det.get("change_pct")) if _is_number(det.get("change_pct")) else None,
                "status": "not_found_in_labels",
                "horizons": [],
                "indicators": ind or None,
                "fundamentals": fund or None,
            }
            entries.append(entry_nf)
            if opts.time_per_ticker:
                _tlog(f"[s5] ticker {ticker} (no-label) in {perf_counter() - t_one:.3f}s")
            continue

        sample_idx = indices[-1]
        pred_row = predicted_prices[sample_idx]
        return_row = predicted_returns[sample_idx]
        actual_row = actual_prices[sample_idx]
        price_abs_err = np.abs(pred_row - actual_row)
        base_close = float(current_close[sample_idx]) if current_close is not None else None
        actual_return_row = None
        if base_close is not None and base_close != 0:
            actual_return_row = (actual_row / base_close) - 1.0

        horizon_rows: list[dict[str, Any]] = []
        for i, h in enumerate(horizons):
            pred_val = float(pred_row[i])
            act_val = float(actual_row[i])
            err_val = float(price_abs_err[i])
            pred_ret = float(return_row[i])
            row: dict[str, Any] = {
                "horizon": h,
                "predicted_price": pred_val,
                "actual_price": act_val,
                "abs_error": err_val,
                "predicted_interval": [pred_val - err_val, pred_val + err_val],
                "predicted_return": pred_ret,
            }
            if actual_return_row is not None:
                act_ret = float(actual_return_row[i])
                row["actual_return"] = act_ret
                row["return_abs_error"] = abs(pred_ret - act_ret)
            horizon_rows.append(row)

        target_date = None
        try:
            lbl = labels[sample_idx]
            if isinstance(lbl, dict) and lbl.get("date"):
                target_date = str(lbl.get("date"))
        except Exception:
            target_date = None
        ind, fund = _load_feature_snapshot(opts.silver_root, ticker, target_date)
        _ensure_main_ratio_keys(fund)

        det = details_lookup.get(ticker) or {}
        entry: dict[str, Any] = {
            "ticker": ticker,
            "name": name_lookup.get(ticker) or ticker,
            "source": top_source,
            "current_price": float(det.get("current_price")) if _is_number(det.get("current_price")) else None,
            "change_pct": float(det.get("change_pct")) if _is_number(det.get("change_pct")) else None,
            "horizons": horizon_rows,
            "indicators": ind or None,
            "fundamentals": fund or None,
        }
        entries.append(entry)
        if opts.time_per_ticker:
            _tlog(f"[s5] ticker {ticker} in {perf_counter() - t_one:.3f}s")

    _tlog(f"[s5] built entries in {perf_counter() - t_entries:.3f}s")

    # Generated-at (KST/GMT+9)  # 한글 주석
    try:
        if ZoneInfo is not None:
            kst_now = datetime.now(ZoneInfo("Asia/Seoul"))
        else:
            kst_now = datetime.utcnow() + timedelta(hours=9)
        generated_at = kst_now.isoformat()
    except Exception:
        generated_at = None

    output = {
        "date": top_data.get("date"),
        "market": top_data.get("market"),
        "generated_at": generated_at,
        "timezone": "Asia/Seoul (GMT+9)",
        "count": len(entries),
        "horizons": horizons,
        "entries": entries,
    }
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    _tlog(f"[s5] total time {perf_counter() - t_total:.3f}s")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate forecast report for top movers.")
    p.add_argument("--top-movers", type=Path, default=Path("data/raw/top_movers_auto.json"))
    p.add_argument("--predictions", type=Path, default=Path("data/outputs/preds.json"))
    p.add_argument("--actual-prices", type=Path, default=Path("data/outputs/actual_prices.npy"))
    p.add_argument("--close-values", type=Path)  # optional
    p.add_argument("--labels", type=Path, default=Path("data/gold/test/labels.json"))
    p.add_argument("--silver-root", type=Path, default=Path("data/silver"))
    p.add_argument("--output", type=Path, default=Path("data/outputs/top_mover_forecast.json"))
    p.add_argument("--limit", type=int)
    p.add_argument("--time-per-ticker", action="store_true", help="Print per-ticker processing time")
    return p


def _load_feature_snapshot(silver_root: Path, ticker: str, date_str: Optional[str]) -> tuple[dict[str, float], dict[str, Any]]:
    # 기술지표 요약(리포트 표시용으로 소수만 유지)  # 한글 주석
    tech_keys = [
        "bb_percent_b", "macd", "rsi", "obv",
        "news_sentiment_mean", "news_count",
    ]
    if pd is None:
        return {}, {}
    p_parquet = silver_root / f"{ticker}.parquet"
    p_pkl = silver_root / f"{ticker}.pkl"
    try:
        if p_parquet.exists():
            df = pd.read_parquet(p_parquet)
        elif p_pkl.exists():
            df = pd.read_pickle(p_pkl)
        else:
            return {}, {}
    except Exception:
        return {}, {}
    if df is None or df.empty:
        return {}, {}
    if "date" in df.columns:
        try:
            df["date"] = pd.to_datetime(df["date"]).dt.normalize()
        except Exception:
            pass
        if date_str:
            try:
                target = pd.to_datetime(str(date_str)).normalize()
                sel = df.loc[df["date"] == target]
                if sel.empty:
                    sel = df.loc[df["date"] <= target].tail(1)
                row = sel.tail(1).to_dict(orient="records")[0] if not sel.empty else {}
                # fallback: fundamentals missing at target, use nearest future row
                if row:
                    fund_keys = [
                        "fund_net_income_ttm", "fund_net_income", "fund_equity", "fund_assets",
                        "fund_liabilities", "fund_current_assets", "fund_current_liabilities",
                    ]
                    def _all_missing(d: dict) -> bool:
                        import math
                        seen = False
                        for k in fund_keys:
                            if k in d:
                                seen = True
                                v = d.get(k)
                                if v is None:
                                    continue
                                try:
                                    fv = float(v)
                                    if not math.isnan(fv) and fv != 0.0:
                                        return False
                                except Exception:
                                    return False
                        return True if seen else False
                    if _all_missing(row):
                        sel2 = df.loc[df["date"] >= target].head(1)
                        if not sel2.empty:
                            cand = sel2.head(1).to_dict(orient="records")[0]
                            if not _all_missing(cand):
                                row = cand
            except Exception:
                row = df.tail(1).to_dict(orient="records")[0]
        else:
            row = df.tail(1).to_dict(orient="records")[0]
    else:
        row = df.tail(1).to_dict(orient="records")[0]

    # 우선주 펀더멘털 보정: 보통주 코드(끝자리 0) 기준 행을 추가 로드  # 한글 주석
    row_base = None
    try:
        raw = str(ticker or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        base = (digits.zfill(6)[:-1] + '0') if digits else raw.zfill(6)
        if base and base != ticker and pd is not None:
            bpq = silver_root / f"{base}.parquet"
            bpk = silver_root / f"{base}.pkl"
            if bpq.exists():
                bdf = pd.read_parquet(bpq)
            elif bpk.exists():
                bdf = pd.read_pickle(bpk)
            else:
                bdf = None
            if bdf is not None and not bdf.empty:
                if "date" in bdf.columns:
                    try:
                        bdf["date"] = pd.to_datetime(bdf["date"]).dt.normalize()
                    except Exception:
                        pass
                    if date_str:
                        try:
                            target = pd.to_datetime(str(date_str)).normalize()
                            sel = bdf.loc[bdf["date"] == target]
                            if sel.empty:
                                sel = bdf.loc[bdf["date"] <= target].tail(1)
                            row_base = sel.tail(1).to_dict(orient="records")[0] if not sel.empty else None
                        except Exception:
                            row_base = bdf.tail(1).to_dict(orient="records")[0]
                    else:
                        row_base = bdf.tail(1).to_dict(orient="records")[0]
                else:
                    row_base = bdf.tail(1).to_dict(orient="records")[0]
    except Exception:
        row_base = None

    indicators = {k: float(row[k]) for k in tech_keys if k in row and _is_number(row[k])}

    # fundamentals 원본 및 보정 계산  # 한글 주석
    fund: dict[str, Any] = {}
    def f(name: str) -> Optional[float]:
        v = row.get(name)
        try:
            return float(v)
        except Exception:
            return None

    # 보통주 기준 펀더멘털 값을 사용하기 위한 헬퍼  # 한글 주석
    def fb(name: str) -> Optional[float]:
        try:
            if row_base is None:
                return None
            v = row_base.get(name)
            return float(v)
        except Exception:
            return None

    # 원천 값
    mcap = f("market_cap")
    shares = f("shares_outstanding")
    eq = f("fund_equity")
    assets = f("fund_assets")
    liab = f("fund_liabilities")
    ca = f("fund_current_assets")
    cl = f("fund_current_liabilities")
    inv = f("fund_inventories")
    ni_ttm = f("fund_net_income_ttm")

    # 보통주 값으로 대체(가능 시)  # 한글 주석
    try:
        mcap = fb("market_cap") or mcap
        shares = fb("shares_outstanding") or shares
        eq = fb("fund_equity") or eq
        assets = fb("fund_assets") or assets
        liab = fb("fund_liabilities") or liab
        ca = fb("fund_current_assets") or ca
        cl = fb("fund_current_liabilities") or cl
        inv = fb("fund_inventories") or inv
        ni_ttm = fb("fund_net_income_ttm") or ni_ttm
    except Exception:
        pass

    # 보조: price, eps, bps
    price_est = (mcap / shares) if (mcap is not None and shares not in (None, 0.0)) else None
    eps = (ni_ttm / shares) if (ni_ttm is not None and shares not in (None, 0.0)) else None
    bps = (eq / shares) if (eq is not None and shares not in (None, 0.0)) else None

    # 직접/보정 계산
    def nget(key: str) -> Optional[float]:
        v = f(key)
        return v if (v is not None and not np.isnan(v)) else None

    fund["per"] = nget("per") if nget("per") is not None else (
        (price_est / eps) if (price_est is not None and eps not in (None, 0.0)) else None
    )
    fund["pbr"] = nget("pbr") if nget("pbr") is not None else (
        (price_est / bps) if (price_est is not None and bps not in (None, 0.0)) else None
    )
    fund["roe"] = nget("roe")
    # roa 우선 net_income_ttm / assets, 없으면 roe*equity_ratio
    eq_ratio = nget("equity_ratio")
    roa_calc = (ni_ttm / assets) if (ni_ttm is not None and assets not in (None, 0.0)) else None
    if roa_calc is None and (fund["roe"] is not None and eq_ratio is not None):
        roa_calc = float(fund["roe"] * (eq_ratio / 100.0))
    fund["roa"] = nget("roa") if nget("roa") is not None else roa_calc

    fund["debt_ratio"] = nget("debt_ratio") if nget("debt_ratio") is not None else (
        (liab / eq * 100.0) if (liab is not None and eq not in (None, 0.0)) else None
    )
    fund["current_ratio"] = nget("current_ratio") if nget("current_ratio") is not None else (
        (ca / cl * 100.0) if (ca is not None and cl not in (None, 0.0)) else None
    )
    fund["quick_ratio"] = nget("quick_ratio") if nget("quick_ratio") is not None else (
        ((ca - inv) / cl * 100.0) if (ca is not None and inv is not None and cl not in (None, 0.0)) else None
    )
    fund["equity_ratio"] = nget("equity_ratio") if nget("equity_ratio") is not None else (
        (eq / assets * 100.0) if (eq is not None and assets not in (None, 0.0)) else None
    )

    # 지표가 없으면 '-'로 채우도록 메인 키를 보장  # 한글 주석
    # ---- 0.0 값을 결측으로 간주하여 펀더멘털 재보정(필요 시 덮어쓰기) ----  # 한글 주석
    def _nz(v: Optional[float]) -> Optional[float]:
        try:
            if v is None or (isinstance(v, float) and (np.isnan(v) or v == 0.0)):
                return None
            return float(v)
        except Exception:
            return None

    # per/pbr 재계산
    per0 = _nz(fund.get("per"))
    pbr0 = _nz(fund.get("pbr"))
    if per0 is None:
        fund["per"] = (price_est / eps) if (price_est is not None and eps not in (None, 0.0)) else None
    if pbr0 is None:
        fund["pbr"] = (price_est / bps) if (price_est is not None and bps not in (None, 0.0)) else None

    # roe 재계산(가능 시)
    roe0 = _nz(fund.get("roe"))
    if roe0 is None and (ni_ttm is not None and eq not in (None, 0.0)):
        try:
            fund["roe"] = float(ni_ttm / eq)
        except Exception:
            pass

    # roa 재계산: 우선 net_income_ttm / assets, 아니면 roe*equity_ratio
    roa0 = _nz(fund.get("roa"))
    if roa0 is None:
        eqr0 = _nz(fund.get("equity_ratio"))
        cand = (ni_ttm / assets) if (ni_ttm is not None and assets not in (None, 0.0)) else None
        if cand is None and (_nz(fund.get("roe")) is not None and eqr0 is not None):
            try:
                cand = float(_nz(fund.get("roe")) * (eqr0 / 100.0))
            except Exception:
                cand = None
        fund["roa"] = cand

    # 기타 비율 재계산
    if _nz(fund.get("debt_ratio")) is None and (liab is not None and eq not in (None, 0.0)):
        fund["debt_ratio"] = float(liab / eq * 100.0)
    if _nz(fund.get("current_ratio")) is None and (ca is not None and cl not in (None, 0.0)):
        fund["current_ratio"] = float(ca / cl * 100.0)
    if _nz(fund.get("quick_ratio")) is None and (ca is not None and inv is not None and cl not in (None, 0.0)):
        fund["quick_ratio"] = float((ca - inv) / cl * 100.0)
    if _nz(fund.get("equity_ratio")) is None and (eq is not None and assets not in (None, 0.0)):
        fund["equity_ratio"] = float(eq / assets * 100.0)

    _ensure_main_ratio_keys(fund)
    return indicators, fund


def _ensure_main_ratio_keys(fund: dict[str, Any]) -> None:
    for k in MAIN_RATIO_KEYS:
        if k not in fund or (fund[k] is None or (isinstance(fund[k], float) and np.isnan(fund[k]))):
            fund[k] = "-"  # 값이 없으면 대시로 표기  # 한글 주석


def _is_number(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _load_array(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(path)
    return np.load(path)


def _load_labels(path: Path, expected: int) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("labels file must contain a list")
    labels: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict):
            labels.append(dict(item))
        else:
            labels.append({"ticker": str(item)})
    if len(labels) < expected:
        labels.extend({"ticker": f"#{i}"} for i in range(len(labels), expected))
    return labels[:expected]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
