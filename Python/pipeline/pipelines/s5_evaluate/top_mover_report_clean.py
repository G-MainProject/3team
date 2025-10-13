# -*- coding: utf-8 -*-
"""Top movers 예측 리포트 생성(UTF-8, 간결/안전 버전).

- fundamentals_display 등 파생 필드 제거, 핵심 지표만 유지
- 깨진 한글/인덴트로 인한 파싱 오류 제거, 최소 의존으로 동작
- silver 스냅샷/pykrx 보강은 선택적으로만 수행(기본 비활성)
"""

from __future__ import annotations

import argparse
import json
import os
import math
from pathlib import Path
from typing import Any, Optional
from time import perf_counter
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

import numpy as np

# 선택 의존(없어도 동작)
try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore

# 선택 의존: 종목명 보강용(pykrx)
try:
    from pykrx import stock  # type: ignore
except Exception:  # pragma: no cover
    stock = None  # type: ignore

# 핵심 재무지표 키(리포트 스키마 고정용)
MAIN_RATIO_KEYS = [
    "roe", "roa", "per", "pbr",
    "debt_ratio", "current_ratio", "quick_ratio", "equity_ratio",
]


def _load_overfit_summary() -> dict:
    metrics_path = Path("Python/pipeline/artifacts/models/training_metrics.json")
    if not metrics_path.exists():
        return {"status": "unavailable"}
    try:
        payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    except Exception:
        return {"status": "error"}

    final = payload.get("final") or {}
    train_entry = final.get("train") or {}
    val_entry = final.get("val") or {}
    overfit = final.get("overfit") or {}

    def _clean(value):
        try:
            num = float(value)
        except Exception:
            return None
        return num if math.isfinite(num) else None

    return {
        "status": "ok",
        "category": overfit.get("category") or "unknown",
        "score": _clean(overfit.get("score")),
        "ratio": _clean(overfit.get("ratio")),
        "final_train_loss": _clean(train_entry.get("loss")),
        "final_val_loss": _clean(val_entry.get("loss")),
        "epochs": payload.get("epochs"),
        "best_epoch": (payload.get("best") or {}).get("epoch"),
    }




def _tlog(msg: str) -> None:
    # 한글 주석: 상세 타이밍 로그는 환경변수로 제어
    if os.getenv("PIPELINE_TIMING_VERBOSE") == "1":
        print(msg)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    opts = parser.parse_args(argv)

    t_total = perf_counter()

    # 입력 로드
    t = perf_counter()
    top_data = _read_json(opts.top_movers)
    predictions = _read_json(opts.predictions)
    predicted_prices = np.array(predictions.get("prices"), dtype=float)
    predicted_returns = np.array(predictions.get("returns"), dtype=float)
    horizons = [str(h) for h in predictions.get("horizons", [])]
    if getattr(opts, "horizons", None):
        horizons = [str(h) for h in opts.horizons]
    actual_prices = _load_array(opts.actual_prices)
    _tlog(f"[s5] loaded inputs in {perf_counter() - t:.3f}s")

    if predicted_prices.shape != actual_prices.shape:
        raise ValueError("Predicted and actual price arrays must have the same shape.")

    # labels
    t = perf_counter()
    labels = _load_labels(opts.labels, predicted_prices.shape[0]) if opts.labels else [
        {"ticker": str(i), "index": i} for i in range(predicted_prices.shape[0])
    ]
    _tlog(f"[s5] loaded labels in {perf_counter() - t:.3f}s")

    # name/details/source
    name_lookup = {str(e.get("ticker")): e.get("name") for e in top_data.get("details", [])}
    details_lookup = {str(e.get("ticker")): e for e in top_data.get("details", [])}
    top_source = top_data.get("source")

    # 종목명 보강(pykrx / dart_corpcode.csv)
    try:
        date_for_lookup = str(top_data.get("date") or "").replace("-", "")
        def _normalize_krx_ticker(tk: str) -> str:
            digits = "".join(ch for ch in tk if ch.isdigit())
            return digits.zfill(6) if digits else tk.zfill(6)

        def _looks_mojibake(name: Optional[str]) -> bool:
            if not name:
                return True
            try:
                if "\ufffd" in name or "??" in name:
                    return True
                hangul = sum(1 for ch in name if '\uAC00' <= ch <= '\uD7A3')
                return hangul == 0
            except Exception:
                return False

        if stock is not None and date_for_lookup:
            tickers_for_name = list({*_safe_list(top_data.get("tickers", [])), *name_lookup.keys()})
            for tk in tickers_for_name:
                if _looks_mojibake(name_lookup.get(tk)):
                    try:
                        name_lookup[tk] = stock.get_market_ticker_name(_normalize_krx_ticker(tk), date=date_for_lookup)
                    except Exception:
                        pass
    except Exception:
        pass

    # CSV 기반 보강: data/dart_corpcode.csv에서 이름 맵핑 시도
    try:
        _enrich_names_from_corpcode_csv(Path("data/dart_corpcode.csv"), name_lookup)
    except Exception:
        pass

    # source 보정: local-test는 기본값 'pykrx'로 대체
    try:
        if isinstance(top_source, str) and top_source.strip().lower() == "local-test":
            top_source = "pykrx"
    except Exception:
        pass

    # 현재가 배열(optional)
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

    # 리포트 대상 티커(중복 제거: tickers ∪ details.ticker)
    top_tickers = [str(t) for t in top_data.get("tickers", [])]
    detail_tickers = [str(e.get("ticker")) for e in top_data.get("details", []) if str(e.get("ticker"))]
    seen = set()
    report_tickers: list[str] = []
    for tk in top_tickers + [x for x in detail_tickers if x not in top_tickers]:
        if tk and tk not in seen:
            seen.add(tk)
            report_tickers.append(tk)

    # index map
    index_map: dict[str, list[int]] = {}
    for idx, info in enumerate(labels):
        ticker = str(info.get("ticker", "")).strip()
        if ticker:
            index_map.setdefault(ticker, []).append(idx)

    # 본문 구성
    entries: list[dict[str, Any]] = []
    for ticker in (report_tickers[: opts.limit] if opts.limit else report_tickers):
        indices = index_map.get(ticker)
        if not indices:
            # 라벨에 없는 티커: 스냅샷 생략, 지표/펀더멘털은 '-' 채움
            det = details_lookup.get(ticker) or {}
            try:
                if isinstance(det.get("source"), str) and det.get("source").strip().lower() == "local-test":
                    det["source"] = "pykrx"
            except Exception:
                pass
            ind_snap, fund_snap = _load_feature_snapshot(opts.silver_root, ticker, None)
            entry_nf: dict[str, Any] = {
                "ticker": ticker,
                "name": name_lookup.get(ticker) or ticker,
                "source": det.get("source") or top_source or "pykrx",
                "current_price": _num_or_none(det.get("current_price")),
                "change_pct": _num_or_none(det.get("change_pct")),
                "status": "not_found_in_labels",
                "horizons": [],
                "indicators": ind_snap,
                "fundamentals": _with_main_ratio_keys(fund_snap or {}),
            }
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

        rows: list[dict[str, Any]] = []
        for i, h in enumerate(horizons):
            pred_val = float(pred_row[i])
            act_val = float(actual_row[i])
            err_val = float(price_abs_err[i])
            pred_ret = float(return_row[i])
            lower = max(0.0, pred_val - err_val)
            upper = max(lower, pred_val + err_val)
            row: dict[str, Any] = {
                "horizon": h,
                "predicted_price": pred_val,
                "actual_price": act_val,
                "abs_error": err_val,
                "predicted_interval": [lower, upper],
                "predicted_return": pred_ret,
            }
            if actual_return_row is not None:
                act_ret = float(actual_return_row[i])
                row["actual_return"] = act_ret
                row["return_abs_error"] = abs(pred_ret - act_ret)
            rows.append(row)

        # silver 스냅샷에서 기술지표/기본지표 추출(가능한 경우)
        target_date = None
        try:
            lbl = labels[sample_idx]
            if isinstance(lbl, dict) and lbl.get("date"):
                target_date = str(lbl.get("date"))
        except Exception:
            target_date = None
        ind_snap, fund_snap = _load_feature_snapshot(opts.silver_root, ticker, target_date)

        det = details_lookup.get(ticker) or {}
        try:
            if isinstance(det.get("source"), str) and det.get("source").strip().lower() == "local-test":
                det["source"] = "pykrx"
        except Exception:
            pass
        entry: dict[str, Any] = {
            "ticker": ticker,
            "name": name_lookup.get(ticker) or ticker,
            "source": det.get("source") or top_source or "pykrx",
            # 현재가: details가 없으면 base_close로 대체
            "current_price": _num_or_none(det.get("current_price")) if _num_or_none(det.get("current_price")) is not None else (float(base_close) if base_close is not None else None),
            # 변동률: details 없으면 0.0으로 대체(미정의 방지)
            "change_pct": _num_or_none(det.get("change_pct")) if _num_or_none(det.get("change_pct")) is not None else 0.0,
            "horizons": rows,
            "indicators": ind_snap,
            "fundamentals": _with_main_ratio_keys(fund_snap or {}),
        }
        entries.append(entry)

    # 헤더/메타
    try:
        if ZoneInfo is not None:
            generated_at = datetime.now(ZoneInfo("Asia/Seoul")).isoformat()
        else:
            generated_at = (datetime.utcnow() + timedelta(hours=9)).isoformat()
    except Exception:
        generated_at = None

    meta_fields_ko = {
        "top_level": {
            "date": "탐색 기준일(YYYYMMDD)",
            "market": "시장(KOSPI/KOSDAQ/ALL)",
            "generated_at": "리포트 생성 시각(ISO8601, KST)",
            "timezone": "시간대 정보",
            "count": "종목 개수",
            "horizons": "예측 범위(예: 1d, 1w, 1m, 6m, 1y)",
            "entries": "종목별 예측/지표/펀더멘털",
        },
        "entry": {
            "ticker": "종목 코드(6자리)",
            "name": "종목명",
            "source": "탐색 출처(pykrx/kiwoom/기타)",
            "current_price": "현재가(선택)",
            "change_pct": "변동률(%)",
            "horizons": "기간별 예측 행",
            "indicators": "기술적 지표 스냅샷",
            "fundamentals": "핵심 재무지표 요약('-'은 결측)",
        },
        "horizon_row": {
            "horizon": "예측 기간 라벨",
            "predicted_price": "예측 종가",
            "actual_price": "실제 종가",
            "abs_error": "절대 오차(가격)",
            "predicted_interval": "예측 구간 [하, 상]",
            "predicted_return": "예측 수익률(배수)",
            "actual_return": "실제 수익률(배수)",
            "return_abs_error": "절대 오차(수익률)",
        },
    }

    overfit_summary = _load_overfit_summary()

    output = {
        "date": top_data.get("date"),
        "market": top_data.get("market"),
        "generated_at": generated_at,
        "timezone": "Asia/Seoul (GMT+9)",
        "count": len(entries),
        "horizons": horizons,
        "entries": entries,
        "meta": {
            "fields_ko": meta_fields_ko,
            "overfitting": overfit_summary,
        },
    }

    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    _tlog(f"[s5] total time {perf_counter() - t_total:.3f}s")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate forecast report for top movers.")
    p.add_argument("--top-movers", type=Path, default=Path("data/raws/top_movers_auto.json"))
    p.add_argument("--predictions", type=Path, default=Path("data/outputs/preds.json"))
    p.add_argument("--actual-prices", type=Path, default=Path("data/outputs/actual_prices.npy"))
    p.add_argument("--close-values", type=Path)
    p.add_argument("--labels", type=Path, default=Path("data/gold/test/labels.json"))
    p.add_argument("--silver-root", type=Path, default=Path("data/silver"))  # 미사용(호환용)
    p.add_argument("--output", type=Path, default=Path("data/outputs/top_mover_forecast.json"))
    p.add_argument("--limit", type=int)
    p.add_argument("--time-per-ticker", action="store_true")
    p.add_argument("--horizons", nargs="*", help="Override forecast horizons labels (e.g., 1d 1w 1m)")
    return p


def _num_or_none(v: Any) -> Optional[float]:
    try:
        f = float(v)
        if np.isnan(f):
            return None
        return f
    except Exception:
        return None


def _with_main_ratio_keys(fund: dict[str, Any]) -> dict[str, Any]:
    # 한글 주석: 필수 키를 '-'로 채워 리포트 스키마를 일정하게 유지
    for k in MAIN_RATIO_KEYS:
        if k not in fund or fund[k] in (None, ""):
            fund[k] = "-"
        else:
            try:
                if isinstance(fund[k], float) and np.isnan(fund[k]):
                    fund[k] = "-"
            except Exception:
                fund[k] = "-"
    return fund


def _safe_list(v: Any) -> list[str]:
    try:
        return [str(x) for x in v]
    except Exception:
        return []


def _load_feature_snapshot(silver_root: Path, ticker: str, date_str: Optional[str]) -> tuple[Optional[dict[str, float]], Optional[dict[str, Any]]]:
    """silver 저장소에서 기술지표/핵심 지표를 일부 로드(존재 시).

    - 파일: data/silver/<ticker>.parquet | .pkl | 대체(보통주 0 매핑)
    - date 컬럼이 있으면 해당 날짜 또는 직전 날짜 선택
    """
    if pd is None:
        return None, None
    def _base(code: str) -> str:
        raw = str(code or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            return raw.zfill(6)
        return (digits + '0') if (raw and not raw[-1].isdigit()) else (digits.zfill(6)[:-1] + '0')

    cands = [silver_root / f"{ticker}.parquet", silver_root / f"{ticker}.pkl"]
    b = _base(ticker)
    if b != ticker:
        cands += [silver_root / f"{b}.parquet", silver_root / f"{b}.pkl"]
    df = None
    for p in cands:
        if p.exists():
            try:
                df = pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_pickle(p)
                break
            except Exception:
                continue
    if df is None or df.empty:
        return None, None
    try:
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.normalize()
            if date_str:
                target = pd.to_datetime(str(date_str)).normalize()
                sel = df.loc[df["date"] == target]
                if sel.empty:
                    sel = df.loc[df["date"] <= target].tail(1)
                row = sel.tail(1).to_dict(orient="records")[0] if not sel.empty else df.tail(1).to_dict(orient="records")[0]
            else:
                row = df.tail(1).to_dict(orient="records")[0]
        else:
            row = df.tail(1).to_dict(orient="records")[0]
    except Exception:
        return None, None

    tech_keys = [
        "bb_percent_b", "bb_bandwidth", "bb_upper", "bb_mid", "bb_lower",
        "macd", "macd_signal", "macd_hist", "rsi",
        "obv", "obv_ema",
        "news_sentiment_mean", "news_count",
    ]
    indicators = {}
    for k in tech_keys:
        try:
            if k in row and row[k] is not None and not (isinstance(row[k], float) and np.isnan(row[k])):
                indicators[k] = float(row[k])
        except Exception:
            pass

    fund_keys = MAIN_RATIO_KEYS
    fund = {}
    for k in fund_keys:
        try:
            v = row.get(k)
            if v is None:
                continue
            fv = float(v)
            if not np.isnan(fv):
                fund[k] = fv
        except Exception:
            continue
    return (indicators or None), (fund or None)


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(path)
    # BOM 이 포함된 JSON도 허용(utf-8-sig 우선)
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
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


def _enrich_names_from_corpcode_csv(csv_path: Path, name_lookup: dict[str, Optional[str]]) -> None:
    """data/dart_corpcode.csv에서 ticker->회사명 보강.

    지원 컬럼(대소문자 무시):
      - ticker/stock_code/code/symbol
      - corp_name/corp_name_eng/corp/corp_nm
    """
    if not csv_path.exists():
        return
    import csv as _csv
    with csv_path.open("r", encoding="utf-8-sig", errors="ignore") as fp:
        rdr = _csv.DictReader(fp)
        headers = { (h or "").strip().lower(): h for h in (rdr.fieldnames or []) }
        t_col = headers.get("ticker") or headers.get("stock_code") or headers.get("code") or headers.get("symbol")
        n_col = headers.get("corp_name") or headers.get("corp_name_eng") or headers.get("corp") or headers.get("corp_nm")
        for row in rdr:
            try:
                tk = str(row.get(t_col, "")).strip().zfill(6) if t_col else str(list(row.values())[0]).strip().zfill(6)
                nm = str(row.get(n_col, "")).strip() if n_col else str(list(row.values())[2]).strip()
                if tk and nm and (not name_lookup.get(tk) or name_lookup.get(tk) == tk):
                    name_lookup[tk] = nm
            except Exception:
                continue


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
