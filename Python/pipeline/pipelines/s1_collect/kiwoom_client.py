# -*- coding: utf-8 -*-
"""Kiwoom OpenAPI+ REST 클라이언트(UTF-8, BOM 안전 처리).

수집 결과를 data/raws/kiwoom 이하에 JSON으로 저장해 후속 전처리 단계에 제공한다.

환경 변수(.env, UTF-8-SIG 대응):
  - 필수: KIWOOM_BASE, KIWOOM_APPKEY, KIWOOM_SECRETKEY
  - 선택: KIWOOM_API_ID, KIWOOM_TOKEN_API_ID, KIWOOM_RANK_PATH, KIWOOM_RANK_TR_ID
  - 일봉: KIWOOM_DAILY_API_ID, KIWOOM_DAILY_PATH
  - 차트: KIWOOM_DAILY_CHART_API_ID, KIWOOM_DAILY_CHART_PATH
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence
from urllib.parse import urljoin, urlencode

import requests

LOGGER = logging.getLogger(__name__)
DATE_FMT = "%Y-%m-%d"


DEFAULT_DAILY_ENDPOINT = "/api/dostk/stkinfo"
DEFAULT_INTRADAY_ENDPOINT = "/api/dostk/stkinfo"
DEFAULT_FINANCIAL_ENDPOINT = "/api/dostk/stkinfo"
DEFAULT_RATIO_ENDPOINT = "/api/dostk/stkinfo"
DEFAULT_TOP_MOVERS_ENDPOINT = "/api/dostk/rank"
# 선택 메타데이터 엔드포인트(예: 발행주식수 등)
DEFAULT_META_ENDPOINT = "/api/dostk/meta"


def _find_project_root() -> Path:
    """상위 경로에서 .env 또는 data 디렉터리를 찾아 프로젝트 루트를 결정한다."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists() or (parent / "data").exists():
            return parent
    return current.parents[4]


def _normalize_date_input(date: str | None) -> str:
    if not date:
        return datetime.now().strftime(DATE_FMT)
    value = str(date).strip()
    if not value:
        return datetime.now().strftime(DATE_FMT)
    if len(value) == 8 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return value


def _coerce_float(value: object) -> float:
    if value is None:
        return math.nan
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return math.nan
    cleaned = value.strip().replace(",", "")
    if not cleaned:
        return math.nan
    sign = 1.0
    if cleaned[0] in "+-":
        sign = -1.0 if cleaned[0] == "-" else 1.0
        cleaned = cleaned[1:].strip()
    if not cleaned:
        return math.nan
    try:
        return sign * float(cleaned)
    except ValueError:
        filtered = "".join(ch for ch in cleaned if ch.isdigit() or ch == ".")
        if not filtered:
            return math.nan
        try:
            return sign * float(filtered)
        except ValueError:
            return math.nan



def _normalize_ymd(value: object) -> str | None:
    "Normalize various date strings (YYYYMMDD/ISO) to ISO format."
    if value is None:
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    digits = ''.join(ch for ch in text_value if ch.isdigit())
    if len(digits) < 8:
        return None
    try:
        dt = datetime.strptime(digits[:8], "%Y%m%d")
    except ValueError:
        return None
    return dt.strftime("%Y-%m-%d")


def _get_with_variants(mapping: Mapping[str, Any], key: str) -> Any:
    "Lookup helper that tolerates dash/underscore/name casing variations."
    candidates = {
        key,
        key.replace('-', '_'),
        key.replace('_', '-'),
        key.lower(),
        key.upper(),
    }
    for candidate in candidates:
        if candidate in mapping:
            return mapping[candidate]
    lower = key.lower()
    for actual in mapping:
        if isinstance(actual, str) and actual.lower() == lower:
            return mapping[actual]
    return None


def _unwrap_response(payload: Any) -> Mapping[str, Any]:
    "Return the innermost mapping payload (unwraps response containers)."
    if isinstance(payload, Mapping):
        inner = payload.get('response')
        if isinstance(inner, Mapping):
            return inner
        return payload
    return {}


def _extract_list(payload: Any, keys: Sequence[str]) -> list[dict[str, Any]]:
    mapping = _unwrap_response(payload)
    for key in keys:
        value = _get_with_variants(mapping, key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
    return []


def _extract_scalar(payload: Any, keys: Sequence[str]) -> Any:
    mapping = _unwrap_response(payload)
    for key in keys:
        value = _get_with_variants(mapping, key)
        if value is not None:
            return value
    return None


def _fetch_daily_chart_series(
    sess,
    base_url: str,
    *,
    endpoint: str,
    tr_id: str,
    authorization: str,
    ticker: str,
    start_date: str,
    end_date: str,
    adjust_type: str,
    pause: float,
    max_pages: int = 64,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    "Fetch daily candle data via Kiwoom chart API (ka10081)."
    start_iso = _normalize_date_input(start_date)
    end_iso = _normalize_date_input(end_date)
    start_digits = start_iso.replace('-', '')
    end_digits = end_iso.replace('-', '')
    base_dt = end_digits
    adjust_flag = (adjust_type or '1').strip() or '1'

    aggregated: list[dict[str, Any]] = []
    continuation: list[dict[str, Any]] = []
    earliest_seen: str | None = None

    cont_flag: str | None = None
    next_key: str | None = None
    base_digits = end_digits

    for _ in range(max_pages):
        body = {
            'stk_cd': ticker,
            'base_dt': base_digits,
            'upd_stkpc_tp': adjust_flag,
        }
        data = _post_kiwoom(
            sess,
            base_url,
            endpoint,
            tr_id=tr_id,
            authorization=authorization,
            body=body,
            cont_yn=cont_flag,
            next_key=next_key,
        )
        rows = _extract_list(data, (
            'stk_dt_pole_chart_qry',
            'output',
            'items',
            'data',
            'body',
        ))
        earliest_batch: str | None = None
        if rows:
            aggregated.extend(rows)
            for row in rows:
                row_iso = _normalize_ymd(
                    row.get('dt')
                    or row.get('date')
                    or row.get('base_dt')
                    or row.get('trade_date')
                )
                if not row_iso:
                    continue
                digits = row_iso.replace('-', '')
                if earliest_seen is None or digits < earliest_seen:
                    earliest_seen = digits
                if earliest_batch is None or digits < earliest_batch:
                    earliest_batch = digits
        cont_resp = _extract_scalar(data, ('cont_yn', 'contYn', 'cont-yn'))
        next_resp = _extract_scalar(data, ('next_key', 'nextKey', 'next-key'))
        continuation.append({
            'cont_yn': cont_resp,
            'next_key': next_resp,
        })
        reached_goal = bool(earliest_seen and earliest_seen <= start_digits)
        if earliest_batch:
            try:
                dt_obj = datetime.strptime(earliest_batch, '%Y%m%d')
                base_digits = (dt_obj - timedelta(days=1)).strftime('%Y%m%d')
            except Exception:
                base_digits = earliest_batch
        if reached_goal:
            break
        if (
            cont_resp is not None
            and str(cont_resp).strip().upper() == 'Y'
            and next_resp not in (None, '')
        ):
            cont_flag = 'Y'
            next_key = str(next_resp)
        else:
            cont_flag = None
            next_key = None
        if not earliest_batch:
            break
        if base_digits <= start_digits:
            break
        time.sleep(max(pause, 0))
        continue

    by_date: dict[str, dict[str, Any]] = {}
    for row in aggregated:
        row_iso = _normalize_ymd(
            row.get('dt')
            or row.get('date')
            or row.get('base_dt')
            or row.get('trade_date')
        )
        if not row_iso:
            continue
        digits = row_iso.replace('-', '')
        if digits < start_digits or digits > end_digits:
            continue

        record: dict[str, Any] = {'date': row_iso}

        def _add_float(target: str, *candidates: str) -> None:
            for candidate in candidates:
                value = row.get(candidate)
                if value is None:
                    continue
                number = _coerce_float(value)
                if math.isnan(number):
                    continue
                record[target] = number
                return

        _add_float('open', 'open_pric', 'open_price', 'open', 'opn_prc')
        _add_float('high', 'high_pric', 'high_price', 'high', 'hg_prc')
        _add_float('low', 'low_pric', 'low_price', 'low', 'lw_prc')
        _add_float('close', 'cur_prc', 'close', 'cl_prc')
        _add_float('volume', 'trde_qty', 'volume', 'tot_trdvol')
        _add_float('tr_value', 'trde_prica', 'trade_price', 'trade_value', 'tot_trdprc')
        _add_float('change', 'pred_pre', 'change', 'cmpprevdd_prc')
        _add_float('turnover_rate', 'trde_tern_rt', 'turnover_rate')

        if digits in by_date:
            existing = by_date[digits]
            existing.update({k: v for k, v in record.items() if k != 'date'})
        else:
            by_date[digits] = record

    normalized = [by_date[key] for key in sorted(by_date.keys())]
    return normalized, aggregated, continuation

def fetch_top_movers(
    *,
    market: str,
    count: int,
    use_mock: bool = False,
    session: requests.Session | None = None,
    pause: float = 0.2,
    direction: str = "both",
) -> list[dict[str, Any]]:
    """Kiwoom REST(ka10027)를 호출해 상위 변동 종목을 조회한다."""
    _ensure_env_loaded()
    base_key = "KIWOOM_MOCK_BASE" if use_mock else "KIWOOM_BASE"
    base_url = os.getenv(base_key)
    if not base_url:
        raise RuntimeError(f"{base_key} is not set in environment")
    base_url = _normalize_base(base_url)

    appkey = os.getenv("KIWOOM_APPKEY")
    secret = os.getenv("KIWOOM_SECRETKEY")
    if not appkey or not secret:
        raise RuntimeError("KIWOOM_APPKEY or KIWOOM_SECRETKEY is missing")

    endpoint = os.getenv("KIWOOM_RANK_PATH", DEFAULT_TOP_MOVERS_ENDPOINT)
    tr_id = os.getenv("KIWOOM_RANK_TR_ID", "ka10027")
    session_obj = session or requests.Session()

    market_map = {"KOSPI": "001", "KOSDAQ": "101", "ALL": "000"}
    market_code = market_map.get((market or "").upper(), "000")

    body = {
        "mrkt_tp": market_code,
        "sort_tp": os.getenv("KIWOOM_RANK_SORT_TP", "1"),
        "trde_qty_cnd": os.getenv("KIWOOM_RANK_TRDE_QTY_CND", "0000"),
        "stk_cnd": os.getenv("KIWOOM_RANK_STK_CND", "0"),
        "crd_cnd": os.getenv("KIWOOM_RANK_CRD_CND", "0"),
        "updown_incls": os.getenv("KIWOOM_RANK_UPDOWN_INCLS", "1"),
        "pric_cnd": os.getenv("KIWOOM_RANK_PRIC_CND", "0"),
        "trde_prica_cnd": os.getenv("KIWOOM_RANK_TRDE_PRICA_CND", "0"),
        "stex_tp": os.getenv("KIWOOM_RANK_STEX_TP", "1"),
    }

    try:
        authorization = _issue_token(session_obj, base_url, appkey, secret)
        # 엔드포인트가 rkinfo로 끝나면 먼저 GET 쿼리를 시도하고, 아니면 POST로 요청한다
        data: Any
        if endpoint.rstrip("/").lower().endswith("rkinfo"):
            url = urljoin(_normalize_base(base_url), endpoint)
            headers = {
                "tr_id": tr_id,
                "api-id": (os.getenv("KIWOOM_API_ID") or os.getenv("KIWOOM_RANK_API_ID") or tr_id),
                "authorization": authorization,
            }
            resp = session_obj.get(url, headers=headers, params=body, timeout=15)
            try:
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                data = _post_kiwoom(
                    session_obj,
                    base_url,
                    endpoint,
                    tr_id=tr_id,
                    authorization=authorization,
                    body=body,
                )
        else:
            data = _post_kiwoom(
                session_obj,
                base_url,
                endpoint,
                tr_id=tr_id,
                authorization=authorization,
                body=body,
            )
        results = _extract_top_movers(data, max_count=count)
    finally:
        if session is None:
            session_obj.close()
    return results[:count]


def fetch_current_prices(
    *,
    tickers: Sequence[str],
    date: str | None = None,
    use_mock: bool = False,
    session: requests.Session | None = None,
    pause: float = 0.2,
) -> dict[str, float]:
    """Kiwoom REST(ka10001)에서 현재가를 조회해 {ticker: price} 형태로 반환한다."""
    target_date = _normalize_date_input(date)
    _ensure_env_loaded()

    base_key = "KIWOOM_BASE"
    base_url = os.getenv(base_key)
    if not base_url:
        raise RuntimeError(f"{base_key} is not set in environment")
    base_url = _normalize_base(base_url)

    appkey = os.getenv("KIWOOM_APPKEY")
    secret = os.getenv("KIWOOM_SECRETKEY")
    if not appkey or not secret:
        raise RuntimeError("KIWOOM_APPKEY or KIWOOM_SECRETKEY is missing")

    endpoint = os.getenv("KIWOOM_DAILY_PATH", DEFAULT_DAILY_ENDPOINT)
    tr_id = os.getenv("KIWOOM_DAILY_API_ID", "ka10001")
    sess = session or requests.Session()
    out: dict[str, float] = {}
    try:
        authorization = _issue_token(sess, base_url, appkey, secret)
        for t in tickers:
            body = {"date": target_date, "ticker": str(t).zfill(6)}
            data = _post_kiwoom(
                sess,
                base_url,
                endpoint,
                tr_id=tr_id,
                authorization=authorization,
                body=body,
            )
            # 가능한 범위에서 가격 필드를 추출한다
            price = None
            if isinstance(data, Mapping):
                for k in ("price", "close", "current_price", "output"):
                    v = data.get(k)
                    if isinstance(v, (int, float)):
                        price = float(v)
                        break
                    if isinstance(v, str):
                        price = _coerce_float(v)
                        break
            out[str(t).zfill(6)] = float(price) if price is not None else math.nan
            time.sleep(max(pause, 0))
    finally:
        if session is None:
            sess.close()
    return out


def fetch_quotes(
    *,
    tickers: Sequence[str],
    start_date: str,
    end_date: str,
    raw_dir: str | Path | None = None,
    session: requests.Session | None = None,
    include_intraday: bool = False,
    intraday_freq: str = "1m",
    intraday_count: int = 390,
    include_financials: bool = False,
    include_ratios: bool = False,
    use_mock: bool = False,
    start_time: str = "090000",
    end_time: str = "153000",
    pause: float = 0.2,
) -> Mapping[str, list[Path]]:
    """Fetch daily (and optional intraday) quotes and save to raw_dir/kiwoom.

    Also optionally fetch raw financials/ratios payloads from the same Kiwoom
    endpoint/TR (ka10001, /api/dostk/stkinfo) and persist the entire responses
    without normalization when include_financials/include_ratios is enabled.
    """
    _ensure_env_loaded()
    base_key = "KIWOOM_BASE"
    base_url = os.getenv(base_key)
    if not base_url:
        raise RuntimeError(f"{base_key} is not set in environment")
    base_url = _normalize_base(base_url)

    appkey = os.getenv("KIWOOM_APPKEY")
    secret = os.getenv("KIWOOM_SECRETKEY")
    if not appkey or not secret:
        raise RuntimeError("KIWOOM_APPKEY or KIWOOM_SECRETKEY is missing")

    raw_root = _resolve_raw_dir(raw_dir) / "kiwoom"
    raw_root.mkdir(parents=True, exist_ok=True)

    daily_endpoint = os.getenv("KIWOOM_DAILY_PATH", DEFAULT_DAILY_ENDPOINT)
    daily_trid = os.getenv("KIWOOM_DAILY_API_ID", "ka10001")

    sess = session or requests.Session()
    saved: MutableMapping[str, list[Path]] = {}
    try:
        authorization = _issue_token(sess, base_url, appkey, secret)
        for ticker in tickers:
            # 일봉 데이터 수집
            _tk = str(ticker).zfill(6)
            _st = _normalize_date_input(start_date)
            _en = _normalize_date_input(end_date)
            daily_body = {
                "ticker": _tk,
                "stk_cd": _tk,
                "stock_code": _tk,
                "start": _st,
                "end": _en,
                "st_dt": _st.replace("-", ""),
                "en_dt": _en.replace("-", ""),
                "from_date": _st,
                "to_date": _en,
            }
            data = _post_kiwoom(
                sess,
                base_url,
                daily_endpoint,
                tr_id=daily_trid,
                authorization=authorization,
                body=daily_body,
            )
            chart_endpoint = os.getenv("KIWOOM_DAILY_CHART_PATH") or "/api/dostk/chart"
            chart_trid = (
                os.getenv("KIWOOM_DAILY_CHART_TR_ID")
                or os.getenv("KIWOOM_DAILY_CHART_API_ID")
                or "ka10081"
            )
            chart_adjust = (
                os.getenv("KIWOOM_DAILY_CHART_ADJUST")
                or os.getenv("KIWOOM_DAILY_UPD_STKPC_TP")
                or "1"
            )
            try:
                chart_output, chart_rows, cont_history = _fetch_daily_chart_series(
                    sess,
                    base_url,
                    endpoint=chart_endpoint,
                    tr_id=chart_trid,
                    authorization=authorization,
                    ticker=_tk,
                    start_date=_st,
                    end_date=_en,
                    adjust_type=chart_adjust,
                    pause=pause,
                )
            except Exception as exc:
                LOGGER.warning("Kiwoom chart fetch failed for %s: %s", _tk, exc)
                chart_output, chart_rows, cont_history = [], [], []

            if isinstance(data, Mapping):
                response_payload: dict[str, Any] = dict(data)
            else:
                response_payload = {"raw": data}
            if chart_rows:
                response_payload["stk_dt_pole_chart_qry"] = chart_rows
            if chart_output:
                response_payload["output"] = chart_output
            if cont_history:
                response_payload["continuation"] = cont_history
                response_payload["chart_tr_id"] = chart_trid
                response_payload["chart_endpoint"] = chart_endpoint
                response_payload["chart_adjust_type"] = chart_adjust

            _dir = raw_root / _tk
            _dir.mkdir(parents=True, exist_ok=True)
            daily_path = _dir / _filename(
                "ka10001",
                _tk,
                datetime.fromisoformat(_normalize_date_input(start_date)),
                datetime.fromisoformat(_normalize_date_input(end_date)),
            )
            request_payload = dict(daily_body)
            request_payload.update(
                {
                    "chart_tr_id": chart_trid,
                    "chart_endpoint": chart_endpoint,
                    "chart_adjust_type": chart_adjust,
                }
            )
            api_id_for_file = chart_trid if chart_output or chart_rows else daily_trid
            _write_json(
                daily_path,
                {
                    "api_id": api_id_for_file,
                    "request": request_payload,
                    "response": response_payload,
                },
            )
            saved.setdefault(str(ticker).zfill(6), []).append(daily_path)
            time.sleep(max(pause, 0))

            # 선택: 일봉과 동일 엔드포인트/TR로 재무 데이터 저장
            if include_financials:
                try:
                    fin_body = {
                        "ticker": _tk,
                        "stk_cd": _tk,
                        "stock_code": _tk,
                        "from_date": _st,
                        "to_date": _en,
                    }
                    fin_data = _post_kiwoom(
                        sess,
                        base_url,
                        daily_endpoint,
                        tr_id=daily_trid,
                        authorization=authorization,
                        body=fin_body,
                    )
                    fin_path = _dir / _filename(
                        "financials",
                        _tk,
                        datetime.fromisoformat(_normalize_date_input(start_date)),
                        datetime.fromisoformat(_normalize_date_input(end_date)),
                    )
                    _write_json(fin_path, {"api_id": daily_trid, "request": fin_body, "response": fin_data})
                    saved[str(ticker).zfill(6)].append(fin_path)
                    time.sleep(max(pause, 0))
                except Exception as exc:
                    LOGGER.warning("Kiwoom financials fetch failed for %s: %s", _tk, exc)

            # 선택: 일봉과 동일 엔드포인트/TR로 재무비율 데이터 저장
            if include_ratios:
                try:
                    ratio_body = {
                        "ticker": _tk,
                        "stk_cd": _tk,
                        "stock_code": _tk,
                        "from_date": _st,
                        "to_date": _en,
                    }
                    ratio_data = _post_kiwoom(
                        sess,
                        base_url,
                        daily_endpoint,
                        tr_id=daily_trid,
                        authorization=authorization,
                        body=ratio_body,
                    )
                    ratio_path = _dir / _filename(
                        "ratios",
                        _tk,
                        datetime.fromisoformat(_normalize_date_input(start_date)),
                        datetime.fromisoformat(_normalize_date_input(end_date)),
                    )
                    _write_json(ratio_path, {"api_id": daily_trid, "request": ratio_body, "response": ratio_data})
                    saved[str(ticker).zfill(6)].append(ratio_path)
                    time.sleep(max(pause, 0))
                except Exception as exc:
                    LOGGER.warning("Kiwoom ratios fetch failed for %s: %s", _tk, exc)

            # 선택: 시가총액 계산을 위한 메타 정보(예: 발행주식수) 저장
            try:
                meta_endpoint = os.getenv("KIWOOM_META_PATH", "").strip()
                meta_trid = os.getenv("KIWOOM_META_TR_ID", "ka_shares").strip()
                if meta_endpoint:
                    meta_body = {
                        "ticker": _tk,
                        "from_date": _st,
                        "to_date": _en,
                    }
                    meta_data = _post_kiwoom(
                        sess,
                        base_url,
                        meta_endpoint,
                        tr_id=meta_trid or "ka_shares",
                        authorization=authorization,
                        body=meta_body,
                    )
                    meta_path = _dir / _filename(
                        "meta",
                        _tk,
                        datetime.fromisoformat(_normalize_date_input(start_date)),
                        datetime.fromisoformat(_normalize_date_input(end_date)),
                    )
                    _write_json(meta_path, {"api_id": meta_trid or "ka_shares", "request": meta_body, "response": meta_data})
                    saved[str(ticker).zfill(6)].append(meta_path)
                    time.sleep(max(pause, 0))
            except Exception:
                pass

            # 선택: 분봉 데이터 수집
            if include_intraday:
                intraday_endpoint = os.getenv("KIWOOM_INTRADAY_PATH", DEFAULT_INTRADAY_ENDPOINT)
                intraday_trid = os.getenv("KIWOOM_INTRADAY_TR_ID", "ka10082")
                body = {
                    "ticker": str(ticker).zfill(6),
                    "start_date": _normalize_date_input(start_date),
                    "end_date": _normalize_date_input(end_date),
                    "start_time": start_time,
                    "end_time": end_time,
                    "freq": intraday_freq,
                    "count": intraday_count,
                }
                data = _post_kiwoom(
                    sess,
                    base_url,
                    intraday_endpoint,
                    tr_id=intraday_trid,
                    authorization=authorization,
                    body=body,
                )
                # 분봉 파일도 동일한 종목 디렉터리에 저장한다
                intraday_path = (_dir if '_dir' in locals() else (raw_root / _tk)) / _filename(
                    "intraday",
                    _tk,
                    datetime.fromisoformat(_normalize_date_input(start_date)),
                    datetime.fromisoformat(_normalize_date_input(end_date)),
                )
                _write_json(intraday_path, {"api_id": intraday_trid, "request": body, "response": data})
                saved[str(ticker).zfill(6)].append(intraday_path)
                time.sleep(max(pause, 0))
    finally:
        if session is None:
            sess.close()
    return saved


def _issue_token(sess: requests.Session, base_url: str, appkey: str, secret: str) -> str:
    """OAuth2 토큰을 발급받아 Authorization 헤더로 사용할 값을 돌려준다."""
    endpoint = "/oauth2/token"
    token_api_id = (os.getenv("KIWOOM_TOKEN_API_ID") or os.getenv("KIWOOM_API_ID") or "au10001").strip()
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "api-id": token_api_id,
    }
    body = {
        "grant_type": "client_credentials",
        "appkey": appkey,
        "secretkey": secret,
    }
    data = _post(sess, base_url, endpoint, headers=headers, body=body)
    if data.get("return_code") not in (0, "0", None):
        raise RuntimeError(f"Token request failed: {data}")
    token = data.get("token") or data.get("access_token") or data.get("accessToken")
    token_type = data.get("token_type") or data.get("tokenType") or "Bearer"
    if not token:
        raise RuntimeError("Token not found in response")
    return f"{token_type} {token}"


def _extract_top_movers(data: Any, *, max_count: int) -> list[dict[str, Any]]:
    """응답 구조가 달라도 상위 변동 종목 목록을 추출한다."""
    if data is None:
        return []
    items_to_process: list[Any] = []
    if isinstance(data, Mapping):
        for key in ("response", "data", "body", "output", "output1", "output2", "movers", "items", "stock_list", "pred_pre_flu_rt_upper"):
            if key in data and isinstance(data[key], list):
                items_to_process = list(data[key])
                break
        if not items_to_process:
            # 단순 리스트 형태의 후보 처리
            if isinstance(data.get("list"), list):
                items_to_process = list(data.get("list"))
    elif isinstance(data, list):
        items_to_process = data
    out: list[dict[str, Any]] = []
    for it in items_to_process[: max_count * 2]:
        if not isinstance(it, Mapping):
            continue
        ticker = it.get("ticker") or it.get("stock_code") or it.get("code") or it.get("isu_cd")
        name = it.get("name") or it.get("stock_name") or it.get("kor_name") or it.get("isu_nm")
        change = it.get("change_rate") or it.get("rate") or it.get("prdy_ctrt") or it.get("chg_rt")
        try:
            change_f = float(change) if isinstance(change, (int, float)) else _coerce_float(str(change or ""))
        except Exception:
            change_f = math.nan
        out.append({
            "ticker": str(ticker or "").zfill(6),
            "name": name,
            "change_rate": change_f,
            "raw": it,
        })
        if len(out) >= max_count:
            break
    return out


def _post_kiwoom(
    sess: requests.Session,
    base_url: str,
    endpoint: str,
    *,
    tr_id: str,
    authorization: str,
    body: Mapping[str, object],
    cont_yn: str | None = None,
    next_key: str | None = None,
    timeout: int = 15,
):
    """필요한 헤더와 오류 처리를 적용해 Kiwoom REST POST 요청을 수행한다."""
    # TR 전용 API ID를 우선 사용하고, 없으면 전역 오버라이드 값을 이용한다.
    fallback_api_id = os.getenv("KIWOOM_API_ID")
    api_id_value = None

    def _norm_tid(x: str | None) -> str | None:
        try:
            return "ka10027" if (x or "").strip().lower() == "ka100027" else x
        except Exception:
            return x

    t = str(tr_id).lower()
    if t in ("ka10027", "rank", "ranking"):
        api_id_value = os.getenv("KIWOOM_RANK_API_ID")
    elif t in ("ka10001", "daily"):
        api_id_value = os.getenv("KIWOOM_DAILY_API_ID")
    elif t in ("ka10081", "day", "daychart", "daily_chart"):
        api_id_value = os.getenv("KIWOOM_DAILY_CHART_API_ID") or os.getenv("KIWOOM_DAILY_API_ID")
    elif t in ("ka10082", "week", "weekly", "chart"):
        api_id_value = os.getenv("KIWOOM_WEEK_CHART_API_ID")

    if not api_id_value:
        api_id_value = fallback_api_id
    api_id_value = _norm_tid(api_id_value)
    if not api_id_value:
        api_id_value = tr_id
    cont_header = 'N' if cont_yn is None else (str(cont_yn).strip().upper() or 'N')
    next_header = '' if next_key is None else str(next_key)
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "tr_id": tr_id,
        "api-id": api_id_value,
        "authorization": authorization,
        "cont-yn": cont_header,
        "next-key": next_header,
    }
    print(f"[kiwoom_client] tr_id={tr_id} api-id={api_id_value} endpoint={endpoint}")
    try:
        data = _post(sess, base_url, endpoint, headers=headers, body=body, timeout=timeout)
    except requests.HTTPError as exc:
        response = getattr(exc, "response", None)
        status = response.status_code if response is not None else "unknown"
        snippet = response.text.strip() if response is not None else str(exc)
        LOGGER.error("Kiwoom %s request failed (HTTP %s): %s", tr_id, status, snippet[:200])
        raise RuntimeError(f"Kiwoom API {tr_id} failed (HTTP {status}). Response: {snippet[:200]}") from exc
    if isinstance(data, Mapping):
        code = data.get("return_code") or data.get("rt_cd")
        if code not in (None, 0, "0"):
            LOGGER.warning("Kiwoom %s abnormal response: %s", tr_id, data)
    return data


def _post(
    sess: requests.Session,
    base_url: str,
    endpoint: str,
    *,
    headers: Mapping[str, str],
    body: Mapping[str, object],
    timeout: int = 15,
):
    """단순 POST 요청을 처리하는 보조 함수."""
    url = urljoin(base_url, endpoint)
    response = sess.post(url, headers=headers, json=body, timeout=timeout)
    response.raise_for_status()
    try:
        return response.json()
    except json.JSONDecodeError:
        LOGGER.error("Kiwoom JSON decode failed: %s", response.text[:200])
        raise


def _filename(prefix: str, ticker: str, start: datetime, end: datetime) -> str:
    return f"{prefix}_{ticker}_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.json"


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)
    LOGGER.info("Kiwoom file saved: %s", path)


_ENV_LOADED = False


def _load_env_cache() -> None:
    """호환성을 위해 유지하는 레거시 로더."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    project_root = _find_project_root()
    env_path = project_root / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    _ENV_LOADED = True


def _ensure_env_loaded() -> None:
    """UTF-8-SIG로 .env를 읽어 BOM을 제거한다(여러 번 호출해도 안전하다)."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    try:
        from Python.pipeline.utils.env import load_dotenv_utf8sig, sanitize_environ_bom
    except Exception:
        def load_dotenv_utf8sig() -> None:  # type: ignore
            return None
        def sanitize_environ_bom() -> None:  # type: ignore
            return None
    try:
        load_dotenv_utf8sig()
        sanitize_environ_bom()
    except Exception:
        pass
    _ENV_LOADED = True


def _resolve_raw_dir(raw_dir: str | Path | None) -> Path:
    if raw_dir is None:
        project_root = _find_project_root()
        path = project_root / "data" / "raws"
    else:
        path = Path(raw_dir)
        # 과거 경로인 'data/raw'를 'data/raws'로 정규화한다
        try:
            if path.name == "raw":
                path = path.with_name("raws")
        except Exception:
            pass
    path.mkdir(parents=True, exist_ok=True)
    return path


def _normalize_base(url: str) -> str:
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        raise RuntimeError(f"Kiwoom BASE URL invalid: {url}")
    return url.rstrip("/")
