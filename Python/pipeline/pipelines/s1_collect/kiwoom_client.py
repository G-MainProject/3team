"""Kiwoom OpenAPI+ REST 래퍼: data/raw에 JSON 응답 저장 및 실시간 조회 유틸.

주의: 이 파일은 환경변수(.env)를 읽어 REST 게이트웨이에 접근합니다.
필수 .env 키: KIWOOM_BASE, KIWOOM_APPKEY, KIWOOM_SECRETKEY
선택 .env 키: KIWOOM_API_ID, KIWOOM_TOKEN_API_ID, KIWOOM_RANK_PATH, KIWOOM_RANK_TR_ID 등
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
from urllib.parse import urljoin

import requests

LOGGER = logging.getLogger(__name__)
DATE_FMT = "%Y-%m-%d"


def _find_project_root() -> Path:
    """환경(.env) 또는 data 폴더가 있는 최상위 프로젝트 루트 탐색."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists() or (parent / "data").exists():
            return parent
    return current.parents[4]


DEFAULT_DAILY_ENDPOINT = "/api/dostk/stkinfo"
DEFAULT_INTRADAY_ENDPOINT = "/api/dostk/stkinfo"
DEFAULT_FINANCIAL_ENDPOINT = "/api/dostk/stkinfo"
DEFAULT_RATIO_ENDPOINT = "/api/dostk/stkinfo"
DEFAULT_TOP_MOVERS_ENDPOINT = "/api/dostk/rank"


def _normalize_date_input(date: str | None) -> str:
    if not date:
        return datetime.now().strftime("%Y-%m-%d")
    value = str(date).strip()
    if not value:
        return datetime.now().strftime("%Y-%m-%d")
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
    """실시간(랭킹) 상하위 종목을 Kiwoom REST API(ka10027)로 조회합니다.

    기본 정렬은 상승률 상위이며(.env로 조정 가능), 서버 스펙에 따라
    TR ID/경로를 환경변수로 재정의할 수 있습니다.
    """
    _load_env_cache()
    base_key = "KIWOOM_MOCK_BASE" if use_mock else "KIWOOM_BASE"
    base_url = os.getenv(base_key)
    if not base_url:
        raise RuntimeError(f"{base_key} 환경변수가 설정되지 않았습니다.")
    base_url = _normalize_base(base_url)

    appkey = os.getenv("KIWOOM_APPKEY")
    secret = os.getenv("KIWOOM_SECRETKEY")
    if not appkey or not secret:
        raise RuntimeError("KIWOOM_APPKEY 또는 KIWOOM_SECRETKEY가 설정되지 않았습니다.")

    endpoint = os.getenv("KIWOOM_RANK_PATH", DEFAULT_TOP_MOVERS_ENDPOINT)
    # 전일대비 등락률 상위 요청 기본 TR ID: ka10027
    tr_id = os.getenv("KIWOOM_RANK_TR_ID", "ka10027")

    session_obj = session or requests.Session()

    market_map = {"KOSPI": "001", "KOSDAQ": "101", "ALL": "000"}
    market_code = market_map.get(market.upper(), "000")

    # ka10027 스펙 기준 요청 바디(기본값은 .env로 오버라이드 가능)
    base_body = {
        "mrkt_tp": market_code,  # 000 전체, 001 코스피, 101 코스닥
        "sort_tp": os.getenv("KIWOOM_RANK_SORT_TP", "1"),  # 1 상승률, 2 상승폭, 3 하락률, 4 하락폭, 5 보합
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
        body = dict(base_body)
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


fetch_top_movers_direct = fetch_top_movers


def fetch_current_prices(
    *,
    tickers: Sequence[str],
    date: str | None = None,
    use_mock: bool = False,
    session: requests.Session | None = None,
    pause: float = 0.2,
) -> dict[str, float]:
    """현재가 스냅샷을 조회(ka10001 기반)하여 {ticker: price} 매핑 반환."""
    target_date = _normalize_date_input(date)
    _load_env_cache()

    base_key = "KIWOOM_MOCK_BASE" if use_mock else "KIWOOM_BASE"
    base_url = os.getenv(base_key)
    if not base_url:
        raise RuntimeError(f"{base_key} 환경변수가 설정되지 않았습니다.")
    base_url = _normalize_base(base_url)

    appkey = os.getenv("KIWOOM_APPKEY")
    secret = os.getenv("KIWOOM_SECRETKEY")
    if not appkey or not secret:
        raise RuntimeError("KIWOOM_APPKEY 또는 KIWOOM_SECRETKEY 환경 변수를 확인하세요.")

    endpoint = os.getenv("KIWOOM_KA10001_PATH", DEFAULT_DAILY_ENDPOINT)
    tr_id = os.getenv("KIWOOM_DAILY_TR_ID", "ka10001")

    session_obj = session or requests.Session()
    prices: dict[str, float] = {}
    try:
        authorization = _issue_token(session_obj, base_url, appkey, secret)
        for idx, ticker in enumerate(tickers):
            body = {
                "stk_cd": ticker,
                "start_date": target_date,
                "end_date": target_date,
                "adjusted": True,
            }
            try:
                data = _post_kiwoom(
                    session_obj,
                    base_url,
                    endpoint,
                    tr_id=tr_id,
                    authorization=authorization,
                    body=body,
                )
            except RuntimeError:
                continue

            base_price = _coerce_float(data.get("base_pric"))
            current_price = _coerce_float(data.get("cur_prc"))
            change_pct = _coerce_float(data.get("flu_rt"))
            price = math.nan
            if not math.isnan(current_price):
                price = current_price
            elif not math.isnan(base_price) and not math.isnan(change_pct):
                price = base_price * (1.0 + change_pct / 100.0)
            elif not math.isnan(base_price):
                price = base_price
            if not math.isnan(price):
                prices[str(ticker)] = float(price)
            if pause > 0 and idx < len(tickers) - 1:
                time.sleep(pause)
    finally:
        if session is None:
            session_obj.close()
    return prices


def fetch_quotes(
    *,
    tickers: Sequence[str],
    start_date: str,
    end_date: str,
    raw_dir: str | Path | None = None,
    include_intraday: bool = False,
    intraday_freq: str = "1m",
    intraday_count: int = 390,
    include_financials: bool = False,
    include_ratios: bool = False,
    use_mock: bool = False,
    start_time: str = "090000",
    end_time: str = "153000",
    pause: float = 0.2,
    session: requests.Session | None = None,
) -> MutableMapping[str, list[Path]]:
    """REST 엔드포인트를 호출하고 data/raw 아래에 JSON을 저장."""
    start = datetime.strptime(_normalize_date_input(start_date), DATE_FMT)
    end = datetime.strptime(_normalize_date_input(end_date), DATE_FMT)
    if start > end:
        raise ValueError("start_date가 end_date보다 큽니다.")

    _load_env_cache()
    base_key = "KIWOOM_MOCK_BASE" if use_mock else "KIWOOM_BASE"
    base_url = os.getenv(base_key)
    if not base_url:
        raise RuntimeError(f"{base_key} 환경변수가 설정되지 않았습니다.")
    base_url = _normalize_base(base_url)

    appkey = os.getenv("KIWOOM_APPKEY")
    secret = os.getenv("KIWOOM_SECRETKEY")
    if not appkey or not secret:
        raise RuntimeError("KIWOOM_APPKEY 또는 KIWOOM_SECRETKEY가 설정되지 않았습니다.")

    raw_root = _resolve_raw_dir(raw_dir) / "kiwoom"
    raw_root.mkdir(parents=True, exist_ok=True)

    session_obj = session or requests.Session()
    saved: MutableMapping[str, list[Path]] = {}
    try:
        authorization = _issue_token(session_obj, base_url, appkey, secret)
        daily_endpoint = os.getenv("KIWOOM_KA10001_PATH", DEFAULT_DAILY_ENDPOINT)
        for ticker in tickers:
            ticker_dir = raw_root / ticker
            ticker_dir.mkdir(parents=True, exist_ok=True)
            daily_body = {
                "stk_cd": ticker,
                "start_date": start.strftime("%Y-%m-%d"),
                "end_date": end.strftime("%Y-%m-%d"),
                "adjusted": True,
            }
            daily_path = ticker_dir / _filename("ka10001", ticker, start, end)
            data = _post_kiwoom(
                session_obj,
                base_url,
                daily_endpoint,
                tr_id="ka10001",
                authorization=authorization,
                body=daily_body,
            )
            _write_json(daily_path, {"api_id": "ka10001", "request": daily_body, "response": data})
            saved.setdefault(ticker, []).append(daily_path)
            time.sleep(max(pause, 0))
    finally:
        if session is None:
            session_obj.close()
    return saved


def _issue_token(sess: requests.Session, base_url: str, appkey: str, secret: str) -> str:
    """OAuth2 토큰을 발급받아 Authorization 값을 구성한다."""
    endpoint = "/oauth2/token"
    # 토큰 호출용 api-id: 기본값은 "au10001"
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
        raise RuntimeError(f"토큰 발급 실패: {data}")
    token = data.get("token") or data.get("access_token") or data.get("accessToken")
    token_type = data.get("token_type") or data.get("tokenType") or "Bearer"
    if not token:
        raise RuntimeError("토큰이 응답에 없습니다.")
    return f"{token_type} {token}"


def _extract_top_movers(data: Any, *, max_count: int) -> list[dict[str, Any]]:
    """Kiwoom 응답 구조에서 공통 필드만 추려 상하위 결과 리스트로 변환."""
    if data is None:
        return []
    items_to_process: list[Any] = []
    if isinstance(data, Mapping):
        for key in ("response", "data", "body", "output", "output1", "output2", "movers", "items", "stock_list", "pred_pre_flu_rt_upper"):
            if key in data and isinstance(data[key], list):
                items_to_process = data[key]
                break
    elif isinstance(data, list):
        items_to_process = data

    results: list[dict[str, Any]] = []
    for item in items_to_process:
        if not isinstance(item, Mapping):
            continue
        ticker = item.get("ticker") or item.get("stk_cd") or item.get("symbol") or item.get("code") or item.get("isu_cd")
        if not ticker:
            continue
        change_pct = _coerce_float(item.get("flu_rt") or item.get("change_pct"))
        current_price = _coerce_float(item.get("cur_prc") or item.get("price"))
        base_price = _coerce_float(item.get("base_pric"))
        entry = {
            "ticker": str(ticker),
            "name": item.get("stk_nm") or item.get("name"),
            "change_pct": None if math.isnan(change_pct) else change_pct,
            "current_price": None if math.isnan(current_price) else current_price,
            "base_price": None if math.isnan(base_price) else base_price,
        }
        results.append(entry)
        if len(results) >= max_count:
            break
    return results


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
    """Kiwoom REST POST 호출을 수행하고 응답 코드를 로깅한다."""
    # 데이터 호출에도 api-id가 필요한 서버 구성이 있어 포함
    api_id_value = (os.getenv("KIWOOM_API_ID") or tr_id)
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
        LOGGER.error("Kiwoom %s 요청 실패 (HTTP %s): %s", tr_id, status, snippet[:200])
        raise RuntimeError(f"Kiwoom API {tr_id} 요청 실패 (HTTP {status}). 응답 요약: {snippet[:200]}") from exc
    if isinstance(data, Mapping):
        code = data.get("return_code") or data.get("rt_cd")
        if code not in (None, 0, "0"):
            LOGGER.warning("Kiwoom %s 응답코드 경고: %s", tr_id, data)
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
    """단순 POST 호출."""
    url = urljoin(base_url, endpoint)
    response = sess.post(url, headers=headers, json=body, timeout=timeout)
    response.raise_for_status()
    try:
        return response.json()
    except json.JSONDecodeError:
        LOGGER.error("Kiwoom 응답 JSON 파싱 실패: %s", response.text[:200])
        raise


def _filename(prefix: str, ticker: str, start: datetime, end: datetime) -> str:
    return f"{prefix}_{ticker}_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.json"


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)
    LOGGER.info("Kiwoom 응답 저장: %s", path)


_ENV_LOADED = False


def _load_env_cache() -> None:
    """.env를 한 번만 읽어 os.environ에 주입."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    project_root = _find_project_root()
    env_path = project_root / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    _ENV_LOADED = True


def _resolve_raw_dir(raw_dir: str | Path | None) -> Path:
    if raw_dir is None:
        project_root = _find_project_root()
        raw_dir = project_root / "data" / "raw"
    path = Path(raw_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _normalize_base(url: str) -> str:
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        raise RuntimeError(f"Kiwoom BASE URL 형식 오류: {url}")
    return url.rstrip("/")
