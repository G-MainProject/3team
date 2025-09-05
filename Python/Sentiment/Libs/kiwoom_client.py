# -*- coding: utf-8 -*-
import requests
from urllib.parse import urljoin
from Python.Sentiment.Libs.env import env  # ← 우리가 만든 env() 사용

def _normalize_base(url: str) -> str:
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise RuntimeError(f"KIWOOM_BASE URL 형식 확인: {url}")
    if url.endswith("/"):
        url = url[:-1]
    return url

def get_base(use_mock: bool) -> str:
    base = env("KIWOOM_MOCK_BASE" if use_mock else "KIWOOM_BASE", required=True)
    return _normalize_base(base)

def issue_token(base: str) -> str:
    """
    TR: au10001 (토큰발급)
    """
    url = urljoin(base, "/oauth2/token")
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "api-id": "au10001",
    }
    body = {
        "grant_type": "client_credentials",
        "appkey": env("KIWOOM_APPKEY", required=True),
        "secretkey": env("KIWOOM_SECRETKEY", required=True),
    }
    r = requests.post(url, headers=headers, json=body, timeout=10)
    r.raise_for_status()
    data = r.json()
    # 성공 코드가 0 또는 미제공인 경우가 있어, 방어적으로 체크
    if data.get("return_code") not in (0, "0", None):
        raise RuntimeError(f"토큰 발급 실패: {data}")
    token_type = data.get("token_type", "bearer")
    token = data["token"]
    return f"{token_type} {token}"

def get_trade_info(base: str, authorization: str, stk_cd: str) -> dict:
    """
    TR: ka10003 (체결정보)
    """
    url = urljoin(base, "/api/dostk/stkinfo")
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "api-id": "ka10003",
        "authorization": authorization,
        "cont-yn": "N",
        "next-key": "",
    }
    body = {"stk_cd": stk_cd}
    r = requests.post(url, headers=headers, json=body, timeout=10)
    r.raise_for_status()
    return r.json()
