"""Top mover forecast aggregator in won (KRW) units.

상위 변동 종목(top movers)에 대한 예측 결과를 가격 단위로 집계하여
보고서(JSON)를 생성합니다.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional

import numpy as np

try:
    # 종목명 보강용(설치되어 있으면 사용)
    from pykrx import stock  # type: ignore
except Exception:  # pragma: no cover
    stock = None  # type: ignore


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
            for key, value in prices_obj.items():
                if _is_number(value):
                    snapshot_prices[str(key)] = float(value)

    top_data = _read_json(opts.top_movers)
    predictions = _read_json(opts.predictions)
    predicted_prices = np.array(predictions.get("prices"), dtype=float)
    predicted_returns = np.array(predictions.get("returns"), dtype=float)
    horizons = [str(h) for h in predictions.get("horizons", [])]
    actual_prices = _load_array(opts.actual_prices)
    if predicted_prices.shape != actual_prices.shape:
        raise ValueError("Predicted and actual price arrays must have the same shape.")

    labels = _load_labels(opts.labels, predicted_prices.shape[0]) if opts.labels else [
        {"ticker": str(i), "index": i}
        for i in range(predicted_prices.shape[0])
    ]
    current_close: np.ndarray | None = None
    if opts.close_values and opts.close_values.exists():
        current_close = _load_array(opts.close_values).astype(float)
    elif "current_close" in predictions:
        current_close = np.array(predictions["current_close"], dtype=float)

    top_tickers = [str(t) for t in top_data.get("tickers", [])]
    if opts.limit is not None:
        top_tickers = top_tickers[: opts.limit]

    # top movers의 details에서 종목명을 우선 사용
    name_lookup = {
        str(entry.get("ticker")): entry.get("name")
        for entry in top_data.get("details", [])
    }
    # 종목명 누락 보강: pykrx 사용 가능하면 top_data.date 기준으로 조회
    date_for_lookup = str(top_data.get("date") or "").replace("-", "")
    if stock is not None and date_for_lookup:
        for t in top_tickers:
            if not name_lookup.get(t):
                try:
                    lookup_t = t.zfill(6)
                    name_lookup[t] = stock.get_market_ticker_name(lookup_t, date=date_for_lookup)
                except Exception:
                    pass

    # 라벨 파일에 이름 정보가 있으면 보강 (키 후보 몇 가지 시도)
    label_name_keys = ("name", "company", "corp_name", "corp", "종목명", "한글명")
    for info in labels:
        t = str(info.get("ticker", "")).strip()
        if not t:
            continue
        if not name_lookup.get(t):
            for k in label_name_keys:
                v = info.get(k)
                if v:
                    name_lookup[t] = str(v)
                    break

    # 여전히 누락인 경우 ticker 자체를 이름으로 설정해 null을 피함
    for t in top_tickers:
        if not name_lookup.get(t):
            name_lookup[t] = t

    # labels 기준으로 ticker → sample index 목록 매핑
    index_map: dict[str, list[int]] = {}
    for idx, info in enumerate(labels):
        ticker = str(info.get("ticker", "")).strip()
        if ticker:
            index_map.setdefault(ticker, []).append(idx)

    entries: list[dict[str, Any]] = []
    for ticker in top_tickers:
        indices = index_map.get(ticker)
        if not indices:
            # 라벨에 없어도 보고서에는 표기(요청: 5개 종목 모두 표시)
            entries.append({
                "ticker": ticker,
                "name": name_lookup.get(ticker),
                "status": "not_found_in_labels",
                "horizons": [],
            })
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
        for idx_h, label in enumerate(horizons):
            pred_val = float(pred_row[idx_h])
            act_val = float(actual_row[idx_h])
            err_val = float(price_abs_err[idx_h])
            pred_ret = float(return_row[idx_h])
            horizon_entry: dict[str, Any] = {
                "horizon": label,
                "predicted_price": pred_val,
                "actual_price": act_val,
                "abs_error": err_val,
                "predicted_interval": [pred_val - err_val, pred_val + err_val],
                "predicted_return": pred_ret,
            }
            if actual_return_row is not None:
                act_ret = float(actual_return_row[idx_h])
                horizon_entry["actual_return"] = act_ret
                horizon_entry["return_abs_error"] = abs(pred_ret - act_ret)
            horizon_rows.append(horizon_entry)

        entry: dict[str, Any] = {
            "ticker": ticker,
            "name": name_lookup.get(ticker),
            "horizons": horizon_rows,
            "label": labels[sample_idx],
        }
        # 정상 매칭된 경우 상태를 명시적으로 부여
        entry["status"] = "ok"

        current_close_value: float | None = None
        if current_close is not None:
            current_close_value = float(current_close[sample_idx])
        elif ticker in snapshot_prices:
            current_close_value = float(snapshot_prices[ticker])

        if current_close_value is not None:
            entry["current_close"] = current_close_value
            if snapshot_generated_at or snapshot_source:
                entry["current_close_snapshot"] = {
                    "generated_at": snapshot_generated_at,
                    "source": snapshot_source,
                }
                if ticker in snapshot_prices:
                    entry["current_close_snapshot"]["reported_price"] = float(snapshot_prices[ticker])
                if close_snapshot and isinstance(close_snapshot, dict):
                    entry["current_close_snapshot"].setdefault("path", close_snapshot.get("path"))

        entries.append(entry)

    close_snapshot_output: dict[str, Any] | None = None
    if snapshot_generated_at or snapshot_source or snapshot_prices:
        close_snapshot_output = {
            "generated_at": snapshot_generated_at,
            "source": snapshot_source,
        }
        if snapshot_prices:
            close_snapshot_output["prices"] = snapshot_prices
        if isinstance(close_snapshot, dict) and close_snapshot.get("path"):
            close_snapshot_output["path"] = close_snapshot.get("path")
        if isinstance(close_snapshot, dict) and close_snapshot.get("tickers"):
            close_snapshot_output["tickers"] = close_snapshot.get("tickers")

    output = {
        "date": top_data.get("date"),
        "market": top_data.get("market"),
        "generated_at": snapshot_generated_at,
        "price_source": snapshot_source,
        "count": len(entries),
        "horizons": horizons,
        "entries": entries,
        "meta": {
            "description": "Forecast summary for top mover tickers (prices in KRW).",
            "description_ko": "상위 변동 종목 예측 집계 보고서 (단위: 원)",
            "fields": {
                "date": "Reference date (YYYYMMDD).",
                "market": "Market identifier provided by discovery stage.",
                "generated_at": "Timestamp (UTC) when the baseline prices were fetched.",
                "price_source": "Source of the baseline price data (e.g., pykrx).",
                "count": "Number of entries contained in this report.",
                "horizons": "List of horizon labels shared across entries.",
                "entries": "Forecast detail objects per ticker.",
                "entries.horizons": "Per-horizon prediction details (price, error, return).",
                "close_snapshot": "Metadata describing the baseline close prices used when generating this report.",
            },
            "fields_ko": {
                "date": "기준 일자 (YYYYMMDD)",
                "market": "발견 단계에서 제공한 시장 구분",
                "generated_at": "기준 가격을 조회한 시각 (UTC)",
                "price_source": "기준 가격 데이터 출처 (예: pykrx)",
                "count": "보고서에 포함된 항목 수",
                "horizons": "모든 항목에 공통으로 적용된 기간 라벨 목록",
                "entries": "종목별 상세 예측 결과",
                "entries.horizons": "기간별 예측 가격/오차/수익률"
            },
            "entry_fields_ko": {
                "ticker": "종목 코드",
                "name": "종목명 (확인 가능한 경우)",
                "current_close": "예측 기준이 된 현재 종가",
                "label": "레이블셋의 부가 정보 (예: 섹터, 구분 코드)",
                "status": "라벨 매칭 실패 등 예외 상황 표시 (있는 경우)",
                "horizons": "기간별 상세 지표"
            },
            "entry_horizon_fields_ko": {
                "horizon": "기간 라벨",
                "predicted_price": "예측된 해당 기간 종가",
                "actual_price": "실제 관측된 해당 기간 종가",
                "abs_error": "예측 가격과 실제 가격의 절대 오차",
                "predicted_interval": "예측 값 ± 절대 오차 구간",
                "predicted_return": "예측 수익률",
                "actual_return": "실제 수익률 (현재가 기준으로 계산, 존재하는 경우)",
                "return_abs_error": "예측/실제 수익률의 절대 오차 (존재하는 경우)"
            }
        }
    }

    if close_snapshot_output:
        output["close_snapshot"] = close_snapshot_output
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate forecast report for top movers.")
    parser.add_argument("--top-movers", type=Path, default=Path("data/raw/top_movers_auto.json"), help="top movers JSON 경로")
    parser.add_argument("--predictions", type=Path, default=Path("outputs/preds.json"), help="s4 예측 JSON 경로")
    parser.add_argument("--actual-prices", type=Path, default=Path("outputs/actual_prices.npy"), help="실제 가격 numpy 경로")
    parser.add_argument("--close-values", type=Path, default=Path("data/live/current_close.npy"), help="현재 종가 numpy 경로")
    parser.add_argument("--close-metadata", type=Path, default=Path("data/live/current_close.json"), help="현재가 스냅샷 JSON 경로")
    parser.add_argument("--labels", type=Path, default=Path("data/gold/test/labels.json"), help="샘플 레이블 JSON 경로")
    parser.add_argument("--output", type=Path, default=Path("outputs/top_mover_forecast.json"), help="결과 JSON 경로")
    parser.add_argument("--limit", type=int, help="탑무버 상위 N개만 출력")
    return parser


def _load_close_snapshot(opts: argparse.Namespace) -> Optional[dict[str, Any]]:
    candidates: list[Path] = []
    if getattr(opts, "close_metadata", None):
        candidates.append(Path(opts.close_metadata))
    if getattr(opts, "close_values", None):
        close_path = Path(opts.close_values)
        candidates.append(close_path.with_suffix(".json"))
        candidates.append(close_path.parent / "current_close.json")
    seen: set[Path] = set()
    for candidate in candidates:
        if not candidate:
            continue
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists():
            try:
                data = _read_json(candidate)
            except Exception:
                continue
            if isinstance(data, dict):
                enriched = dict(data)
                enriched.setdefault("path", str(candidate))
                return enriched
    return None


# Helper utilities ---------------------------------------------------------
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


if __name__ == "__main__":
    raise SystemExit(main())
