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
    # 토큰 필드 호환 처리
    token = data.get("token") or data.get("access_token") or data.get("accessToken")
    token_type = data.get("token_type") or data.get("tokenType") or "Bearer"
    if not token:
        raise RuntimeError(f"토큰 필드 확인 필요: {data}")
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
    data = r.json()
    # Normalize common wrappers: { data: {...} } or list payloads
    if isinstance(data, dict):
        for key in ("data", "output", "result", "response"):
            v = data.get(key)
            if isinstance(v, dict):
                return v
            if isinstance(v, list) and v:
                first = v[0]
                if isinstance(first, dict):
                    return first
    return data


def get_movers_ka10019(
    base: str,
    authorization: str,
    cont_yn: str = "N",
    next_key: str = "",
    mrkt_tp: str | None = None,
    extra_body: dict | None = None,
) -> dict:
    """
    TR: ka10019 (가격급등락 랭킹)

    Headers:
      - api-id: ka10019
      - authorization: Bearer ...
      - cont-yn: 'Y' or 'N'
      - next-key: paging key

    Body: usually empty for ranking queries.

    Returns dict { 'items': list, 'next_key': str }
    """
    # Allow endpoint override via env to match actual deployment path
    try:
        endpoint = env("KIWOOM_KA10019_PATH", default="/api/dostk/stkinfo")
    except TypeError:
        # Backward compatibility if env(default=...) signature differs
        endpoint = env("KIWOOM_KA10019_PATH", "/api/dostk/stkinfo")
    url = urljoin(base, endpoint)
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "api-id": "ka10019",
        "authorization": authorization,
        "cont-yn": cont_yn,
        "next-key": next_key or "",
    }
    body: dict = {}
    if mrkt_tp is not None and str(mrkt_tp).strip() != "":
        body["mrkt_tp"] = mrkt_tp
    if isinstance(extra_body, dict):
        body.update({k: v for k, v in extra_body.items() if v is not None})
    r = requests.post(url, headers=headers, json=body, timeout=10)
    r.raise_for_status()
    data = r.json()

    def _find_list_recursive(obj):
        # Prefer known key 'pric_jmpflu'; otherwise return first list of dicts
        if isinstance(obj, dict):
            # direct known key
            v = obj.get("pric_jmpflu")
            if isinstance(v, list):
                return v
            # try common wrappers
            for key in ("output", "data", "result", "response", "payload", "body", "items", "list"):
                vv = obj.get(key)
                if isinstance(vv, list):
                    return vv
                if isinstance(vv, dict):
                    found = _find_list_recursive(vv)
                    if isinstance(found, list):
                        return found
            # fallback: scan values
            for vv in obj.values():
                if isinstance(vv, list):
                    return vv
                if isinstance(vv, dict):
                    found = _find_list_recursive(vv)
                    if isinstance(found, list):
                        return found
        elif isinstance(obj, list):
            return obj
        return []

    items = _find_list_recursive(data)

    resp_next_key = ""
    try:
        resp_next_key = r.headers.get("next-key") or ""
    except Exception:
        pass
    if isinstance(data, dict):
        resp_next_key = (
            resp_next_key
            or data.get("next_key")
            or data.get("nextKey")
            or ""
        )
    return {"items": items, "next_key": resp_next_key, "raw": data}
