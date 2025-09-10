# -*- coding: utf-8 -*-
"""
Forecast current-year Q3/Q4 revenue from merged JSON.

Uses tf.keras LSTM if TensorFlow is available; otherwise falls back to a
seasonal YoY baseline derived from the last 5 years of quarters.
Prints predictions with a simple confidence score in parentheses.

Usage:
  python -m Python.Sentiment.Apps.forecast_revenue --json data/005930_merged.json
  python -m Python.Sentiment.Apps.forecast_revenue --json data/005930_merged.json --seq 8 --epochs 150
  python -m Python.Sentiment.Apps.forecast_revenue --json data/005930_merged.json --no-tf
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Any, List, Tuple


def _to_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        s = str(v).replace(",", "").strip()
        if s in ("", "-"):
            return None
        if s.startswith("+"):
            s = s[1:]
        return int(s)
    except Exception:
        try:
            return int(float(s))  # type: ignore[name-defined]
        except Exception:
            return None


def _fmt(v: Any) -> str:
    if v is None:
        return "-"
    try:
        return f"{int(v):,}"
    except Exception:
        return str(v)


def _flatten_quarters(dart: dict) -> List[Tuple[int, int, int | None]]:
    """Return list of (year, quarter[1-4], value or None) in chronological order."""
    rows = dart.get("data") or []
    out: List[Tuple[int, int, int | None]] = []
    for row in rows:
        year = row.get("year")
        try:
            year = int(year)
        except Exception:
            continue
        q = (row.get("quarters") or {})
        for qi, key in enumerate(["Q1", "Q2", "Q3", "Q4"], start=1):
            out.append((year, qi, _to_int(q.get(key))))
    return out


def _contiguous_known(series: List[Tuple[int, int, int | None]]) -> List[int]:
    """Collapse to a contiguous list of known ints (skip Nones)."""
    vals: List[int] = []
    for _, _, v in series:
        if v is not None:
            vals.append(int(v))
    return vals


def _windowize(values: List[float], seq: int) -> Tuple[List[List[float]], List[float]]:
    X: List[List[float]] = []
    y: List[float] = []
    for i in range(len(values) - seq):
        X.append(values[i : i + seq])
        y.append(values[i + seq])
    return X, y


def _maybe_tf():
    try:
        import tensorflow as tf  # type: ignore
        return tf
    except Exception:
        return None


def _train_tf_regressor(values: List[int], seq: int, epochs: int = 120, lr: float = 1e-3):
    tf = _maybe_tf()
    if tf is None:
        return None

    # Scale: log1p then standardize
    x = [math.log1p(v) for v in values]
    mean = float(statistics.fmean(x)) if x else 0.0
    stdev = float(statistics.pstdev(x)) if len(x) > 1 else 1.0
    if stdev == 0:
        stdev = 1.0
    xs = [(v - mean) / stdev for v in x]

    X_list, y_list = _windowize(xs, seq)
    if not X_list:
        return None

    X = tf.convert_to_tensor(X_list, dtype=tf.float32)  # (n, seq)
    X = tf.expand_dims(X, -1)  # (n, seq, 1)
    y = tf.convert_to_tensor(y_list, dtype=tf.float32)  # (n,)

    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(seq, 1)),
        tf.keras.layers.LSTM(32, activation="tanh"),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(1),
    ])
    model.compile(optimizer=tf.keras.optimizers.Adam(lr), loss="mse")
    model.fit(X, y, epochs=epochs, batch_size=16, verbose=0)

    def predict_next(next_seq_vals: List[int]) -> int:
        use = next_seq_vals[-seq:]
        if len(use) < seq:
            use = [use[0]] * (seq - len(use)) + use
        px = [((math.log1p(v) - mean) / stdev) for v in use]
        tx = tf.convert_to_tensor([[[p] for p in px]], dtype=tf.float32)  # (1, seq, 1)
        pv = float(model.predict(tx, verbose=0)[0, 0])
        pred = math.expm1(pv * stdev + mean)
        return max(0, int(round(pred)))

    return predict_next


def _seasonal_baseline(series: List[Tuple[int, int, int | None]], current_year: int) -> Tuple[int | None, int | None]:
    """Baseline: use last year's Q3/Q4 adjusted by YoY growth observed in Q1/Q2."""
    table = {(y, q): v for (y, q, v) in series}

    def get(y: int, q: int) -> int | None:
        v = table.get((y, q))
        return None if v is None else int(v)

    growths: List[float] = []
    for q in (1, 2):
        py = get(current_year - 1, q)
        cy = get(current_year, q)
        if py and cy and py > 0:
            growths.append(cy / py - 1.0)
    g = float(statistics.fmean(growths)) if growths else 0.0

    def adj(base: int | None) -> int | None:
        if base is None:
            return None
        return max(0, int(round(base * (1.0 + g))))

    q3 = adj(get(current_year - 1, 3)) or get(current_year - 2, 3) or get(current_year, 2)
    q4 = adj(get(current_year - 1, 4)) or get(current_year - 2, 4) or get(current_year, 2)
    return q3, q4


def forecast_q3_q4(merged_path: Path, seq: int, epochs: int, no_tf: bool) -> dict:
    obj = json.loads(merged_path.read_text(encoding="utf-8"))
    stk = obj.get("stock_code") or merged_path.stem.split("_")[0]
    dart = obj.get("dart") or {}
    series = _flatten_quarters(dart)
    values = _contiguous_known(series)
    if not values:
        raise RuntimeError("No numeric revenue series found in merged JSON")

    # Current year is the max year present
    current_year = max((y for (y, _, _) in series), default=None)
    if current_year is None:
        raise RuntimeError("Unable to determine current year from DART data")

    q3_ml = q4_ml = None
    pred_fn = None if no_tf else _train_tf_regressor(values, seq=seq, epochs=epochs)
    if pred_fn is not None and len(values) >= max(4, seq):
        base = values[-seq:]
        q3_ml = pred_fn(base)
        base2 = (base + [q3_ml])[-seq:]
        q4_ml = pred_fn(base2)

    q3_bl, q4_bl = _seasonal_baseline(series, current_year=current_year)

    q3 = q3_ml or q3_bl
    q4 = q4_ml or q4_bl

    # Heuristic confidence via backtested baseline MAPE on past years
    def _lookup(y: int, q: int) -> int | None:
        for yy, qq, vv in series:
            if yy == y and qq == q:
                return None if vv is None else int(vv)
        return None

    years = sorted({y for (y, _, _) in series})
    q3_errs: List[float] = []
    q4_errs: List[float] = []
    for y in years:
        # need previous year to predict, and exclude current_year
        if y <= min(years) or y >= current_year:
            continue
        p3, p4 = _seasonal_baseline(series, current_year=y)
        a3 = _lookup(y, 3)
        a4 = _lookup(y, 4)
        if a3 is not None and a3 != 0 and p3 is not None:
            q3_errs.append(abs(a3 - p3) / abs(a3))
        if a4 is not None and a4 != 0 and p4 is not None:
            q4_errs.append(abs(a4 - p4) / abs(a4))

    def _conf(errs: List[float]) -> float:
        if not errs:
            return 0.5
        mape = float(statistics.fmean(errs))
        c = 1.0 - mape
        # clamp to [0.1, 0.95] and round to 2 decimals
        if c < 0.1:
            c = 0.1
        if c > 0.95:
            c = 0.95
        return round(c, 2)

    q3_conf = _conf(q3_errs)
    q4_conf = _conf(q4_errs)

    return {
        "stock_code": stk,
        "current_year": current_year,
        "q3_pred": q3,
        "q4_pred": q4,
        "method": "tf.keras" if q3_ml and q4_ml else "baseline",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": str(merged_path),
        "seq": seq,
        "epochs": epochs,
        "q3_confidence": q3_conf,
        "q4_confidence": q4_conf,
    }


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Forecast current-year Q3/Q4 revenue from merged JSON")
    p.add_argument("--json", required=True, help="Path to {code}_merged.json")
    p.add_argument("--seq", type=int, default=8, help="Sequence length in quarters (default 8)")
    p.add_argument("--epochs", type=int, default=120, help="Training epochs (default 120)")
    p.add_argument("--no-tf", action="store_true", help="Disable TensorFlow and use baseline only")
    p.add_argument("--out", default="", help="Output path (default: data/{code}_revenue_forecast.json)")
    args = p.parse_args(argv)

    merged_path = Path(args.json)
    if not merged_path.exists():
        raise SystemExit(f"File not found: {merged_path}")

    result = forecast_q3_q4(merged_path, seq=args.seq, epochs=args.epochs, no_tf=args.no_tf)

    code = result.get("stock_code") or merged_path.stem.split("_")[0]
    out_path = Path(args.out) if args.out else merged_path.parent / f"{code}_revenue_forecast.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[Revenue Forecast]")
    print(f"- stock: {code}")
    print(f"- year: {result['current_year']}  method: {result['method']}")
    q3c = result.get('q3_confidence')
    q4c = result.get('q4_confidence')
    print(f"- Q3: {_fmt(result['q3_pred'])} ({q3c if q3c is not None else '-'})")
    print(f"- Q4: {_fmt(result['q4_pred'])} ({q4c if q4c is not None else '-'})")
    print(f"- saved: {out_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
