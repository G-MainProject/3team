# -*- coding: utf-8 -*-
# Libs/dart_client.py
import csv
import io
import os
import time
import zipfile
import requests
import xml.etree.ElementTree as ET

# ✅ 키움과 동일한 방식: env()로 환경변수 읽기
from Python.Sentiment.Libs.env import env

BASE = "https://opendart.fss.or.kr/api"
REPRT = {
    "Q1": "11013",   # 1분기
    "H1": "11012",   # 반기(누적 6개월)
    "Q3": "11014",   # 3분기(누적 9개월)
    "FY": "11011",   # 사업보고서(누적 12개월)
}

def _to_int(s):
    if s is None:
        return None
    s = str(s).replace(",", "").strip()
    if s in ("", "-"):
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except Exception:
            return None

def _get_api_key() -> str:
    """
    ✅ 매 호출 시 env에서 읽어와 최신 값을 사용 (키움 방식과 동일)
    - price_to_json.py에서 load_env()가 먼저 호출되어 있어야 함
    """
    key = env("DART_API_KEY", required=True)
    if not key or len(key) < 10:
        raise RuntimeError("DART_API_KEY가 설정되지 않았습니다. env.py/.env 에 설정하세요.")
    return key

def corpcode_cache_path(project_root: str) -> str:
    return os.path.join(project_root, "data", "dart_corpcode.csv")

def fetch_and_cache_corpcode(project_root: str) -> dict:
    """DART CORPCODE.xml 받아 CSV로 캐시 후 dict 반환 (stock_code -> corp_code)"""
    api_key = _get_api_key()
    url = f"{BASE}/corpCode.xml?crtfc_key={api_key}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    xml_bytes = z.read("CORPCODE.xml")
    root = ET.fromstring(xml_bytes)

    path = corpcode_cache_path(project_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    mapping = {}
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["corp_code", "corp_name", "stock_code"])
        for el in root.findall("list"):
            corp_code = (el.findtext("corp_code") or "").strip()
            corp_name = (el.findtext("corp_name") or "").strip()
            stock_code = (el.findtext("stock_code") or "").strip()
            if stock_code:
                mapping[stock_code] = corp_code
                w.writerow([corp_code, corp_name, stock_code])
    return mapping

def load_corpcode_cache(project_root: str) -> dict:
    path = corpcode_cache_path(project_root)
    if not os.path.exists(path):
        return {}
    mapping = {}
    with open(path, "r", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for row in rd:
            if row.get("stock_code"):
                mapping[row["stock_code"]] = row["corp_code"]
    return mapping

def get_corp_code(project_root: str, stock_code: str) -> str:
    """캐시 → 없으면 다운로드"""
    mapping = load_corpcode_cache(project_root)
    corp_code = mapping.get(stock_code)
    if corp_code:
        return corp_code
    mapping = fetch_and_cache_corpcode(project_root)
    return mapping.get(stock_code)

def fetch_fnltt_singl_acnt_all(corp_code: str, year: int, reprt_code: str, fs_div="CFS", pause=0.2) -> list:
    """단일회사 전체계정 (표준계정ID 포함)"""
    api_key = _get_api_key()
    url = f"{BASE}/fnlttSinglAcntAll.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": str(year),
        "reprt_code": reprt_code,
        "fs_div": fs_div,
    }
    r = requests.get(url, params=params, timeout=30)
    data = r.json()
    if data.get("status") != "000":
        # 013(데이터 없음) 등은 상위에서 처리할 수 있게 예외 메시지 유지
        raise RuntimeError(f"[{year}/{reprt_code}] DART 오류: {data.get('status')} {data.get('message')}")
    time.sleep(pause)
    return data.get("list", []) or []

def pick_revenue_amounts(rows: list):
    """
    rows에서 매출액(Revenue) 행을 찾아 (당기금액 amt, 당기누적 add) 튜플 반환.
    우선순위: account_id == 'ifrs-full_Revenue' → account_nm에 '매출' 포함
    """
    target = None
    for row in rows:
        if (row.get("account_id") or "").lower() == "ifrs-full_revenue":
            target = row
            break
    if target is None:
        for row in rows:
            if "매출" in (row.get("account_nm") or ""):
                target = row
                break
    if target is None:
        return None, None
    amt = _to_int(target.get("thstrm_amount"))
    add = _to_int(target.get("thstrm_add_amount"))
    return amt, add

def get_year_report_revenue(corp_code: str, year: int, fs_div="CFS") -> dict:
    """
    한 해의 Q1/H1/Q3/FY 각각에서 매출액 (당기금액/누적금액) 수집
    return: {"Q1": {"amount": int|None, "add": int|None}, ...}
    """
    out = {}
    for k, rc in REPRT.items():
        try:
            rows = fetch_fnltt_singl_acnt_all(corp_code, year, rc, fs_div=fs_div)
            amt, add = pick_revenue_amounts(rows)
            out[k] = {"amount": amt, "add": add}
        except RuntimeError:
            # 없는 경우도 정상흐름으로 None 처리
            out[k] = {"amount": None, "add": None}
    return out
