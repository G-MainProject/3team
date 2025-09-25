"""Top mover forecast with indicators/fundamentals (KRW units).
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any, Optional
import numpy as np
try:
    import pandas as pd  # type: ignore
except Exception:
    pd = None  # type: ignore
try:
    from pykrx import stock  # type: ignore
except Exception:
    stock = None  # type: ignore

def _format_financials_for_display(fund: dict[str, Any]) -> list[dict[str, Any]]:
    """fundamentals로부터 보기 좋은 문자열 표기를 생성하고,
    동시에 해당 표기를 fundamentals에도 *_display 키로 병합한다.

    - 퍼센트 지표: debt_ratio, current_ratio, quick_ratio, equity_ratio, roe, roa
    - 배수 지표: per, pbr
    """
    def num(v: Any) -> float | None:
        try:
            return float(v)
        except Exception:
            return None

    items: list[tuple[str, str, float | None, str]] = [
        ("debt_ratio", "부채비율", num(fund.get("debt_ratio")), "%"),
        ("current_ratio", "유동비율", num(fund.get("current_ratio")), "%"),
        ("quick_ratio", "당좌비율", num(fund.get("quick_ratio")), "%"),
        ("equity_ratio", "자기자본비율", num(fund.get("equity_ratio")), "%"),
        ("roe", "ROE", num(fund.get("roe")), "%_scaled"),  # 0.12 -> 12.00%
        ("roa", "ROA", num(fund.get("roa")), "%_scaled"),
        ("per", "PER", num(fund.get("per")), "x"),
        ("pbr", "PBR", num(fund.get("pbr")), "x"),
    ]

    out: list[dict[str, Any]] = []
    for key, label, value, kind in items:
        if value is None or (value != value):  # NaN check
            continue
        if kind == "%":
            txt = f"{value:.2f}%"
        elif kind == "%_scaled":
            txt = f"{value*100.0:.2f}%"
        elif kind == "x":
            txt = f"{value:.2f}x"
        else:
            txt = str(value)
        item_dict = {"key": key, "label": label, "value": float(value), "display": txt}
        out.append(item_dict)
        # fundamentals에도 보기용 표기를 병합 (예: roe_display)
        try:
            fund[f"{key}_display"] = txt
        except Exception:
            pass
    return out

def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    opts = parser.parse_args(argv)

    close_snapshot = _load_close_snapshot(opts)
    snapshot_generated_at = None
    snapshot_source = None
    snapshot_prices: dict[str, float] = {}
    if isinstance(close_snapshot, dict):
        snapshot_generated_at = close_snapshot.get("generated_at")
        snapshot_source = close_snapshot.get("source")
        prices_obj = close_snapshot.get("prices")
        if isinstance(prices_obj, dict):
            for k, v in prices_obj.items():
                if _is_number(v):
                    snapshot_prices[str(k)] = float(v)

    top_data = _read_json(opts.top_movers)
    predictions = _read_json(opts.predictions)
    predicted_prices = np.array(predictions.get("prices"), dtype=float)
    predicted_returns = np.array(predictions.get("returns"), dtype=float)
    horizons = [str(h) for h in predictions.get("horizons", [])]
    actual_prices = _load_array(opts.actual_prices)
    if predicted_prices.shape != actual_prices.shape:
        raise ValueError("Predicted and actual price arrays must have the same shape.")

    labels = _load_labels(opts.labels, predicted_prices.shape[0]) if opts.labels else [
        {"ticker": str(i), "index": i} for i in range(predicted_prices.shape[0])
    ]

    # name/details/source
    name_lookup = {str(e.get("ticker")): e.get("name") for e in top_data.get("details", [])}
    details_lookup = {str(e.get("ticker")): e for e in top_data.get("details", [])}
    top_source = top_data.get("source")

    # enrich names via pykrx if possible
    date_for_lookup = str(top_data.get("date") or "").replace("-", "")
    top_tickers = [str(t) for t in top_data.get("tickers", [])]
    if stock is not None and date_for_lookup:
        for t in top_tickers:
            if not name_lookup.get(t):
                try:
                    name_lookup[t] = stock.get_market_ticker_name(t.zfill(6), date=date_for_lookup)
                except Exception:
                    pass

    # map ticker -> sample indices
    index_map: dict[str, list[int]] = {}
    for idx, info in enumerate(labels):
        ticker = str(info.get("ticker", "")).strip()
        if ticker:
            index_map.setdefault(ticker, []).append(idx)

    # optional current close array
    current_close: np.ndarray | None = None
    if opts.close_values and opts.close_values.exists():
        current_close = _load_array(opts.close_values).astype(float)
    elif "current_close" in predictions:
        current_close = np.array(predictions["current_close"], dtype=float)

    entries: list[dict[str, Any]] = []
    for ticker in (top_tickers[: opts.limit] if opts.limit else top_tickers):
        indices = index_map.get(ticker)
        if not indices:
            ind, fund = _load_feature_snapshot(opts.silver_root, ticker, None)
            det = details_lookup.get(ticker) or {}
            # 필드 순서: ticker, name, source, current_price, change_pct, ...
            entry_nf: dict[str, Any] = {}
            entry_nf["ticker"] = ticker
            entry_nf["name"] = name_lookup.get(ticker) or ticker
            entry_nf["source"] = top_source
            entry_nf["current_price"] = float(det.get("current_price")) if _is_number(det.get("current_price")) else None
            entry_nf["change_pct"] = float(det.get("change_pct")) if _is_number(det.get("change_pct")) else None
            entry_nf["status"] = "not_found_in_labels"
            entry_nf["horizons"] = []
            entry_nf["indicators"] = ind or None
            if fund:
                _ = _format_financials_for_display(fund)
                entry_nf["fundamentals"] = fund
            else:
                entry_nf["fundamentals"] = None
            entries.append(entry_nf)
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

        det = details_lookup.get(ticker) or {}
        # 필드 순서: ticker, name, source, current_price, change_pct, ...
        entry: dict[str, Any] = {}
        entry["ticker"] = ticker
        entry["name"] = name_lookup.get(ticker) or ticker
        entry["source"] = top_source
        entry["current_price"] = float(det.get("current_price")) if _is_number(det.get("current_price")) else None
        entry["change_pct"] = float(det.get("change_pct")) if _is_number(det.get("change_pct")) else None
        entry["horizons"] = horizon_rows
        # 레이블 정보는 요청에 따라 출력하지 않음
        entry["indicators"] = ind or None
        if fund:
            _ = _format_financials_for_display(fund)
            entry["fundamentals"] = fund
        else:
            entry["fundamentals"] = None

        # 보기 좋은 재무지표 표기(있을 때만): 비율은 % 표기, 배수는 x 표기
        # financials 리스트는 제거

        # 요청에 따라 current_close / current_close_snapshot는 출력하지 않음

        entries.append(entry)

    # output
    output = {
        "date": top_data.get("date"),
        "market": top_data.get("market"),
        "generated_at": snapshot_generated_at,
        "price_source": snapshot_source,
        "count": len(entries),
        "horizons": horizons,
        "entries": entries,
    }
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate forecast report for top movers.")
    p.add_argument("--top-movers", type=Path, default=Path("data/raw/top_movers_auto.json"))
    p.add_argument("--predictions", type=Path, default=Path("data/outputs/preds.json"))
    p.add_argument("--actual-prices", type=Path, default=Path("data/outputs/actual_prices.npy"))
    p.add_argument("--close-values", type=Path, default=Path("data/live/current_close.npy"))
    p.add_argument("--close-metadata", type=Path, default=Path("data/live/current_close.json"))
    p.add_argument("--labels", type=Path, default=Path("data/gold/test/labels.json"))
    p.add_argument("--silver-root", type=Path, default=Path("data/silver"))
    p.add_argument("--output", type=Path, default=Path("data/outputs/top_mover_forecast.json"))
    p.add_argument("--limit", type=int)
    return p

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

def _load_close_snapshot(opts: argparse.Namespace) -> Optional[dict[str, Any]]:
    candidates: list[Path] = []
    if getattr(opts, "close_metadata", None):
        candidates.append(Path(opts.close_metadata))
    if getattr(opts, "close_values", None):
        close_path = Path(opts.close_values)
        candidates.append(close_path.with_suffix(".json"))
        candidates.append(close_path.parent / "current_close.json")
    seen: set[Path] = set()
    for c in candidates:
        if not c:
            continue
        c = c.resolve()
        if c in seen:
            continue
        seen.add(c)
        if c.exists():
            try:
                data = _read_json(c)
            except Exception:
                continue
            if isinstance(data, dict):
                e = dict(data)
                e.setdefault("path", str(c))
                return e
    return None

def _load_feature_snapshot(silver_root: Path, ticker: str, date_str: Optional[str]) -> tuple[dict[str, float], dict[str, float]]:
    tech_keys = [
        "bb_percent_b", "bb_bandwidth", "bb_upper", "bb_lower", "bb_mid",
        "macd", "macd_signal", "macd_hist", "rsi", "obv", "obv_ema",
    ]
    fund_keys = [
        "per", "pbr", "roe", "roa",
        "debt_ratio", "current_ratio", "quick_ratio", "equity_ratio",
        "market_cap", "shares_outstanding",
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
            except Exception:
                row = df.tail(1).to_dict(orient="records")[0]
        else:
            row = df.tail(1).to_dict(orient="records")[0]
    else:
        row = df.tail(1).to_dict(orient="records")[0]
    indicators = {k: float(row[k]) for k in tech_keys if k in row and _is_number(row[k])}
    fundamentals = {k: float(row[k]) for k in fund_keys if k in row and _is_number(row[k])}

    # Enrich fundamentals on-the-fly if raw DART columns are present in row
    def f(name: str) -> float | None:
        v = row.get(name)
        try:
            return float(v)
        except Exception:
            return None

    # Compute equity_ratio if missing
    if "equity_ratio" not in fundamentals:
        eq = f("fund_equity")
        assets = f("fund_assets")
        if eq is not None and assets not in (None, 0.0):
            fundamentals["equity_ratio"] = float(eq / assets * 100.0)

    # Compute debt_ratio if missing
    if "debt_ratio" not in fundamentals:
        liab = f("fund_liabilities")
        eq = f("fund_equity")
        if liab is not None and eq not in (None, 0.0):
            fundamentals["debt_ratio"] = float(liab / eq * 100.0)

    # Compute current_ratio and quick_ratio if missing
    ca = f("fund_current_assets")
    cl = f("fund_current_liabilities")
    inv = f("fund_inventories")
    if "current_ratio" not in fundamentals and ca is not None and cl not in (None, 0.0):
        fundamentals["current_ratio"] = float(ca / cl * 100.0)
    if "quick_ratio" not in fundamentals and ca is not None and inv is not None and cl not in (None, 0.0):
        fundamentals["quick_ratio"] = float((ca - inv) / cl * 100.0)

    # Compute ROA if missing: prefer net_income_ttm/assets; else ROE * equity_ratio
    if "roa" not in fundamentals:
        ni_ttm = f("fund_net_income_ttm")
        assets = f("fund_assets")
        if ni_ttm is not None and assets not in (None, 0.0):
            fundamentals["roa"] = float(ni_ttm / assets)
        else:
            roe = fundamentals.get("roe")
            eq_ratio = fundamentals.get("equity_ratio")
            if isinstance(roe, float) and isinstance(eq_ratio, float):
                # equity_ratio is %; convert to fraction
                fundamentals["roa"] = float(roe * (eq_ratio / 100.0))
    return indicators, fundamentals

if __name__ == "__main__":
    raise SystemExit(main())


def _format_financials_for_display(fund: dict[str, Any]) -> list[dict[str, Any]]:
    """Create a compact, human-friendly financials list from fundamentals.

    - Percent metrics: debt_ratio, current_ratio, quick_ratio, equity_ratio, roe, roa
    - Multiples: per, pbr
    """
    def num(v: Any) -> float | None:
        try:
            return float(v)
        except Exception:
            return None

    items: list[tuple[str, str, float | None, str]] = [
        ("debt_ratio", "부채비율", num(fund.get("debt_ratio")), "%"),
        ("current_ratio", "유동비율", num(fund.get("current_ratio")), "%"),
        ("quick_ratio", "당좌비율", num(fund.get("quick_ratio")), "%"),
        ("equity_ratio", "자기자본비율", num(fund.get("equity_ratio")), "%"),
        ("roe", "ROE", num(fund.get("roe")), "%_scaled"),  # 0.12 -> 12.00%
        ("roa", "ROA", num(fund.get("roa")), "%_scaled"),
        ("per", "PER", num(fund.get("per")), "x"),
        ("pbr", "PBR", num(fund.get("pbr")), "x"),
    ]

    out: list[dict[str, Any]] = []
    for key, label, value, kind in items:
        if value is None or (value != value):  # NaN check
            continue
        if kind == "%":
            txt = f"{value:.2f}%"
        elif kind == "%_scaled":
            txt = f"{value*100.0:.2f}%"
        elif kind == "x":
            txt = f"{value:.2f}x"
        else:
            txt = str(value)
        out.append({"key": key, "label": label, "value": float(value), "display": txt})
    return out
