# -*- coding: utf-8 -*-
"""Kiwoom OpenAPI+ REST client (UTF-8, BOM-safe).

Stores raw JSON responses under data/raws/kiwoom for downstream preprocessing.

Environment variables (.env, UTF-8-SIG friendly):
  - KIWOOM_BASE, KIWOOM_APPKEY, KIWOOM_SECRETKEY
  - Optional: KIWOOM_API_ID, KIWOOM_TOKEN_API_ID, KIWOOM_RANK_PATH, KIWOOM_RANK_TR_ID
  - Optional: KIWOOM_KA10001_PATH, KIWOOM_DAILY_TR_ID
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from datetime import datetime
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


def _find_project_root() -> Path:
    """Find project root containing .env or data directory."""
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


def fetch_top_movers(
    *,
    market: str,
    count: int,
    use_mock: bool = False,
    session: requests.Session | None = None,
    pause: float = 0.2,
    direction: str = "both",
) -> list[dict[str, Any]]:
    """Fetch top movers via Kiwoom REST (ka10027)."""
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
        # Try GET with query first if endpoint endswith rkinfo, else POST
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
    """Fetch current prices (ka10001) and return {ticker: price}."""
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

    endpoint = os.getenv("KIWOOM_KA10001_PATH", DEFAULT_DAILY_ENDPOINT)
    tr_id = os.getenv("KIWOOM_DAILY_TR_ID", "ka10001")
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
            # Best-effort extraction of price
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
    """Fetch daily (and optional intraday) quotes and save to raw_dir/kiwoom."""
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

    daily_endpoint = os.getenv("KIWOOM_KA10001_PATH", DEFAULT_DAILY_ENDPOINT)
    daily_trid = os.getenv("KIWOOM_DAILY_TR_ID", "ka10001")

    sess = session or requests.Session()
    saved: MutableMapping[str, list[Path]] = {}
    try:
        authorization = _issue_token(sess, base_url, appkey, secret)
        for ticker in tickers:
            # Daily
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
            # Save under per-ticker directory with ka10001 prefix to match s2 loader
            _dir = raw_root / _tk
            _dir.mkdir(parents=True, exist_ok=True)
            daily_path = _dir / _filename(
                "ka10001",
                _tk,
                datetime.fromisoformat(_normalize_date_input(start_date)),
                datetime.fromisoformat(_normalize_date_input(end_date)),
            )
            _write_json(daily_path, {"api_id": daily_trid, "request": daily_body, "response": data})
            saved.setdefault(str(ticker).zfill(6), []).append(daily_path)
            time.sleep(max(pause, 0))

            # Intraday (optional)
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
                # Save intraday under the same per-ticker directory
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
    """Issue OAuth2 token and return Authorization header value."""
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
    """Extract top movers list from various possible payload shapes."""
    if data is None:
        return []
    items_to_process: list[Any] = []
    if isinstance(data, Mapping):
        for key in ("response", "data", "body", "output", "output1", "output2", "movers", "items", "stock_list", "pred_pre_flu_rt_upper"):
            if key in data and isinstance(data[key], list):
                items_to_process = list(data[key])
                break
        if not items_to_process:
            # flat list candidate
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
    timeout: int = 15,
):
    """Perform Kiwoom REST POST with proper headers and error handling."""
    # api-id header priority: KIWOOM_API_ID -> TR-specific -> tr_id
    api_id_value = os.getenv("KIWOOM_API_ID")
    def _norm_tid(x: str | None) -> str | None:
        try:
            return "ka10027" if (x or "").strip().lower() == "ka100027" else x
        except Exception:
            return x
    if not api_id_value:
        t = str(tr_id).lower()
        if t in ("ka10027", "rank", "ranking"):
            api_id_value = os.getenv("KIWOOM_RANK_API_ID")
        elif t in ("ka10001", "daily"):
            api_id_value = os.getenv("KIWOOM_DAILY_API_ID")
        elif t in ("ka10082", "week", "weekly", "chart"):
            api_id_value = os.getenv("KIWOOM_WEEK_CHART_API_ID")
    api_id_value = _norm_tid(api_id_value)
    if not api_id_value:
        api_id_value = tr_id
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "tr_id": tr_id,
        "api-id": api_id_value,
        "authorization": authorization,
        "cont-yn": "N",
        "next-key": "",
    }
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
    """Plain POST helper."""
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
    """Legacy loader (kept for compatibility)."""
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
    """Load .env with UTF-8-SIG and sanitize BOM (idempotent)."""
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
        raw_dir = project_root / "data" / "raws"
    path = Path(raw_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _normalize_base(url: str) -> str:
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        raise RuntimeError(f"Kiwoom BASE URL invalid: {url}")
    return url.rstrip("/")

