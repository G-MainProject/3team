"""Kiwoom OpenAPI+ REST wrappers to persist raw responses into data/raw."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Mapping, MutableMapping, Sequence
from urllib.parse import urljoin

import requests

LOGGER = logging.getLogger(__name__)
DATE_FMT = "%Y-%m-%d"


def _find_project_root() -> Path:
    """환경파일(.env) 또는 data 디렉터리를 이용해 루트를 추적한다."""

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists() or (parent / "data").exists():
            return parent
    return current.parents[4]

DEFAULT_DAILY_ENDPOINT = "/api/dostk/stkinfo"
DEFAULT_INTRADAY_ENDPOINT = "/api/dostk/stkinfo"
DEFAULT_FINANCIAL_ENDPOINT = "/api/dostk/stkinfo"
DEFAULT_RATIO_ENDPOINT = "/api/dostk/stkinfo"


# 키움 OpenAPI REST 게이트웨이를 호출해 data/raw/kiwoom 하위에 JSON으로 적재

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
) -> Mapping[str, list[Path]]:
    """Call Kiwoom REST endpoints and write JSON payloads under ``data/raw``."""

    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if start > end:
        raise ValueError("start_date가 end_date보다 늦습니다.")

    _load_env_cache()
    base_key = "KIWOOM_MOCK_BASE" if use_mock else "KIWOOM_BASE"
    base_url = os.getenv(base_key)
    if not base_url:
        raise RuntimeError(f"{base_key} 환경변수가 설정되어 있지 않습니다.")
    base_url = _normalize_base(base_url)

    appkey = os.getenv("KIWOOM_APPKEY")
    secret = os.getenv("KIWOOM_SECRETKEY")
    if not appkey or not secret:
        raise RuntimeError("KIWOOM_APPKEY 또는 KIWOOM_SECRETKEY가 설정되어 있지 않습니다.")

    raw_root = _resolve_raw_dir(raw_dir) / "kiwoom"
    raw_root.mkdir(parents=True, exist_ok=True)

    session_obj = session or requests.Session()
    saved: MutableMapping[str, list[Path]] = {}

    try:
        authorization = _issue_token(session_obj, base_url, appkey, secret)

        daily_endpoint = os.getenv("KIWOOM_KA10001_PATH", DEFAULT_DAILY_ENDPOINT)
        intraday_endpoint = os.getenv("KIWOOM_KA10002_PATH", DEFAULT_INTRADAY_ENDPOINT)
        financial_endpoint = os.getenv("KIWOOM_KA20001_PATH", DEFAULT_FINANCIAL_ENDPOINT)
        ratio_endpoint = os.getenv("KIWOOM_KA20002_PATH", DEFAULT_RATIO_ENDPOINT)

        for ticker in tickers:
            ticker_dir = raw_root / ticker
            ticker_dir.mkdir(parents=True, exist_ok=True)

            # 일봉 호출
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
                api_id="ka10001",
                authorization=authorization,
                body=daily_body,
            )
            _write_json(daily_path, {"api_id": "ka10001", "request": daily_body, "response": data})
            saved.setdefault(ticker, []).append(daily_path)
            time.sleep(max(pause, 0))

            # 분봉/체결 데이터 옵션 처리
            if include_intraday:
                intraday_body = {
                    "stk_cd": ticker,
                    "start_time": start_time,
                    "end_time": end_time,
                    "freq": intraday_freq,
                    "count": intraday_count,
                }
                intraday_path = ticker_dir / _filename("ka10002", ticker, start, end)
                data = _post_kiwoom(
                    session_obj,
                    base_url,
                    intraday_endpoint,
                    api_id="ka10002",
                    authorization=authorization,
                    body=intraday_body,
                )
                _write_json(intraday_path, {"api_id": "ka10002", "request": intraday_body, "response": data})
                saved[ticker].append(intraday_path)
                time.sleep(max(pause, 0))

            # 재무제표 요약
            if include_financials:
                from_year = start.year
                to_year = end.year
                financial_body = {
                    "stk_cd": ticker,
                    "consolidated": True,
                    "from_year": from_year,
                    "to_year": to_year,
                }
                financial_path = ticker_dir / _filename("ka20001", ticker, start, end)
                data = _post_kiwoom(
                    session_obj,
                    base_url,
                    financial_endpoint,
                    api_id="ka20001",
                    authorization=authorization,
                    body=financial_body,
                )
                _write_json(financial_path, {"api_id": "ka20001", "request": financial_body, "response": data})
                saved[ticker].append(financial_path)
                time.sleep(max(pause, 0))

            # 재무비율 요약
            if include_ratios:
                ratio_body = {
                    "stk_cd": ticker,
                    "from_year": start.year,
                    "to_year": end.year,
                }
                ratio_path = ticker_dir / _filename("ka20002", ticker, start, end)
                data = _post_kiwoom(
                    session_obj,
                    base_url,
                    ratio_endpoint,
                    api_id="ka20002",
                    authorization=authorization,
                    body=ratio_body,
                )
                _write_json(ratio_path, {"api_id": "ka20002", "request": ratio_body, "response": data})
                saved[ticker].append(ratio_path)
                time.sleep(max(pause, 0))
    finally:
        if session is None:
            session_obj.close()

    return saved


def _issue_token(sess: requests.Session, base_url: str, appkey: str, secret: str) -> str:
    """OAuth2 토큰을 발급받아 Authorization 헤더에 사용한다."""

    endpoint = "/oauth2/token"
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "api-id": "au10001",
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


def _post_kiwoom(
    sess: requests.Session,
    base_url: str,
    endpoint: str,
    *,
    api_id: str,
    authorization: str,
    body: Mapping[str, object],
    timeout: int = 15,
):
    """Kiwoom REST POST 호출을 수행하고 반환 코드를 로깅한다."""

    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "api-id": api_id,
        "authorization": authorization,
        "cont-yn": "N",
        "next-key": "",
    }
    data = _post(sess, base_url, endpoint, headers=headers, body=body, timeout=timeout)
    if isinstance(data, Mapping):
        code = data.get("return_code") or data.get("rt_cd")
        if code not in (None, 0, "0"):
            LOGGER.warning("Kiwoom %s 반환코드 경고: %s", api_id, data)
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
    """공통 POST 래퍼."""

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
    LOGGER.info("Kiwoom 데이터 저장: %s", path)


_ENV_LOADED = False


def _load_env_cache() -> None:
    """환경변수를 한 번만 로딩한다."""

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


def _parse_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, DATE_FMT)
    except ValueError as exc:
        raise ValueError(f"날짜 형식이 YYYY-MM-DD가 아닙니다: {value}") from exc


def _normalize_base(url: str) -> str:
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        raise RuntimeError(f"Kiwoom BASE URL 형식 오류: {url}")
    return url.rstrip("/")
