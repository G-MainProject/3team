"""Evaluate multi-horizon predictions against actual prices."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Optional

import numpy as np



def _load_labels(path: Path, expected: int) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() in {".json", ".jsonl"}:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            values = list(data.values())
        else:
            values = list(data)
    else:
        values = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    labels = [str(v) for v in values]
    if len(labels) < expected:
        labels += [f"#{i}" for i in range(len(labels), expected)]
    return labels[:expected]

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

    horizon_summary = []
    for idx, label in enumerate(horizons):
        pred_column = predicted_prices[:, idx]
        actual_column = actual_prices[:, idx]
        price_mean = float(np.mean(pred_column))
        actual_mean = float(np.mean(actual_column))
        mae_val = float(mae[idx])
        horizon_summary.append(
            {
                "horizon": label,
                "predicted_mean_price": price_mean,
                "actual_mean_price": actual_mean,
                "price_mae": mae_val,
                "predicted_price_interval": [price_mean - mae_val, price_mean + mae_val],
                "return_mae": float(return_mae[idx])
            }
        )


    per_sample_report = None
    labels: list[str] | None = None
    if opts.per_sample:
        if opts.sample_labels:
            labels = _load_labels(opts.sample_labels, predicted_prices.shape[0])
        else:
            labels = [str(i) for i in range(predicted_prices.shape[0])]
        sample_errors = np.abs(predicted_prices - actual_prices).mean(axis=1)
        order = np.argsort(sample_errors)[::-1]
        limit = min(max(opts.per_sample_limit, 1), predicted_prices.shape[0])
        entries = []
        for idx in order[:limit]:
            entry = {
                "index": int(idx),
                "label": labels[idx] if labels else str(idx),
                "predicted_prices": predicted_prices[idx].tolist(),
                "actual_prices": actual_prices[idx].tolist(),
                "price_abs_error": np.abs(predicted_prices[idx] - actual_prices[idx]).tolist(),
                "return_abs_error": np.abs(predicted_returns[idx] - actual_returns[idx]).tolist(),
                "price_mae": float(sample_errors[idx])
            }
            entries.append(entry)
        per_sample_report = {
            "sorted_by": "price_mae_desc",
            "limit": limit,
            "entries": entries
        }

    output = {
        "predictions": str(opts.predictions),
        "actual_prices": str(opts.actual_prices),
        "horizons": horizons,
        "price_mae": mae.tolist(),
        "price_mape": mape.tolist(),
        "return_mae": return_mae.tolist(),
        "summary": {
            "notes": "predicted_price_interval = [predicted_mean_price - price_mae, predicted_mean_price + price_mae]",
            "notes_ko": "predicted_price_interval 값은 예측 평균 가격 ± 가격 MAE 구간을 의미합니다.",
            "per_horizon": horizon_summary
        },
        "meta": {
            "description": "Evaluation summary comparing predicted prices/returns with actuals.",
            "description_ko": "예측된 가격·수익률과 실제 값을 비교한 평가 요약",
            "fields": {
                "predictions": "Path to the s4 predictions JSON.",
                "actual_prices": "Path to the numpy array of actual prices.",
                "horizons": "List of horizon labels.",
                "price_mae": "Per-horizon mean absolute error (price).",
                "price_mape": "Per-horizon mean absolute percentage error (price).",
                "return_mae": "Per-horizon mean absolute error (returns).",
                "summary": "Aggregate statistics per horizon (mean price and intervals).",
                "per_sample": "Optional: per-sample report (top-N largest price errors)."
            },
            "fields_ko": {
                "predictions": "s4 단계에서 생성된 예측 JSON 파일 경로",
                "actual_prices": "실제 가격 numpy 배열 경로",
                "horizons": "평가에 사용된 기간 레이블 목록",
                "price_mae": "기간별 가격 MAE(평균 절대 오차)",
                "price_mape": "기간별 가격 MAPE(평균 절대 백분율 오차)",
                "return_mae": "기간별 수익률 MAE",
                "summary": "기간별 평균 가격 및 오차 구간 요약",
                "per_sample": "선택 사항: 샘플별 상세 에러 리포트"
            },
            "summary_fields_ko": {
                "horizon": "평가 대상 기간 레이블",
                "predicted_mean_price": "해당 기간 예측 평균 가격",
                "actual_mean_price": "해당 기간 실제 평균 가격",
                "price_mae": "해당 기간 가격 MAE",
                "predicted_price_interval": "예측 평균 가격 ± 가격 MAE 구간",
                "return_mae": "해당 기간 수익률 MAE"
            },
            "per_sample_fields_ko": {
                "index": "샘플 인덱스",
                "label": "샘플 구분용 라벨(옵션)",
                "predicted_prices": "해당 샘플의 기간별 예측 가격",
                "actual_prices": "해당 샘플의 기간별 실제 가격",
                "price_abs_error": "기간별 가격 절대 오차",
                "return_abs_error": "기간별 수익률 절대 오차",
                "price_mae": "샘플 단위 평균 가격 절대 오차"
            }
        }
    }


    if per_sample_report is not None:
        output["per_sample"] = per_sample_report

    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate predicted prices vs actual prices")
    parser.add_argument("--predictions", type=Path, required=True, help="s4 예측 결과 JSON 경로")
    parser.add_argument("--actual-prices", type=Path, required=True, help="실제 가격 numpy (N, len(horizons))")
    parser.add_argument("--horizons", nargs="*", type=int, default=[1, 5, 20, 120, 250], help="평가할 호라이즌 목록")
    parser.add_argument("--output", type=Path, default=Path("outputs/eval.json"))
    parser.add_argument("--per-sample", action="store_true", help="샘플별 상세 리포트를 포함")
    parser.add_argument("--per-sample-limit", type=int, default=20, help="상세 리포트로 출력할 샘플 수")
    parser.add_argument("--sample-labels", type=Path, help="샘플 인덱스에 매핑할 레이블 목록 (json/txt)")
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
