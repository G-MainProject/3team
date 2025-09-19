"""Evaluate multi-horizon predictions against actual prices."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np


def main(args: list[str] | None = None) -> int:
    parser = _build_parser()
    opts = parser.parse_args(args)

    preds = _load_json(opts.predictions)
    horizons = preds.get("horizons") or _format_horizon_labels(opts.horizons)
    predicted_prices = np.array(preds["prices"], dtype=float)
    current_close = np.array(preds["current_close"], dtype=float)
    predicted_returns = np.array(preds["returns"], dtype=float)

    actual_prices = _load_array(opts.actual_prices)
    actual_returns = (actual_prices - current_close[:, None]) / current_close[:, None]

    if actual_prices.shape != predicted_prices.shape:
        raise ValueError("예측 가격과 실제 가격의 shape이 다릅니다.")

    diff = predicted_prices - actual_prices
    mae = np.abs(diff).mean(axis=0)
    mape = (np.abs(diff) / np.maximum(actual_prices, 1e-8)).mean(axis=0)

    return_mae = np.abs(predicted_returns - actual_returns).mean(axis=0)

    output = {
        "predictions": str(opts.predictions),
        "actual_prices": str(opts.actual_prices),
        "horizons": horizons,
        "price_mae": mae.tolist(),
        "price_mape": mape.tolist(),
        "return_mae": return_mae.tolist(),
    }

    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate predicted prices vs actual prices")
    parser.add_argument("--predictions", type=Path, required=True, help="s4 추론 결과 JSON 경로")
    parser.add_argument("--actual-prices", type=Path, required=True, help="실제 종가 numpy (N, len(horizons))")
    parser.add_argument("--horizons", nargs="*", type=int, default=[1, 5, 20, 120, 250], help="기간 리스트")
    parser.add_argument("--output", type=Path, default=Path("outputs/eval.json"))
    return parser


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_array(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(path)
    return np.load(path)


def _format_horizon_labels(horizons: Iterable[int]) -> list[str]:
    mapping = {1: "1d", 5: "1w", 20: "1m", 120: "6m", 250: "1y"}
    return [mapping.get(int(h), f"{h}d") for h in horizons]


if __name__ == "__main__":
    raise SystemExit(main())
