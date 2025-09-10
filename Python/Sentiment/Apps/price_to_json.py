# -*- coding: utf-8 -*-
"""
price_to_json.py
- Run Kiwoom (trade/price, optional) and DART (quarterly revenue) collectors
  and save a merged JSON to data/{stock_code}_merged.json.
"""

import argparse
import os
import time
from pathlib import Path
from urllib.parse import urljoin
import requests

# env/utils/clients
from Python.Sentiment.Libs.env import load_env
from Python.Sentiment.Libs.kiwoom_client import get_base, issue_token, get_trade_info
from Python.Sentiment.Libs.io_utils import save_json
from Python.Sentiment.Libs.symbols import load_symbol_map, resolve_code_by_name
from Python.Sentiment.Libs.revenue import collect_recent_financials

# console summaries
from Python.Sentiment.Libs.summaries import (
    print_summary_kiwoom,
    print_summary_dart,
    print_summary_merged,
)

# paths
_CUR = Path(__file__).resolve()
_SENTIMENT_DIR = _CUR.parents[1]          # .../Sentiment
_PROJECT_ROOT = _SENTIMENT_DIR.parents[1] # .../3team
_DATA_DIR = _PROJECT_ROOT / "data"


def _get_code_by_name_via_api(base: str, auth: str, name: str) -> str | None:
    """Aux lookup: name -> code via Kiwoom REST (rarely needed)."""
    url = urljoin(base, "/api/dostk/stkinfo")
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "api-id": "ka10001",
        "authorization": auth,
        "cont-yn": "N",
        "next-key": "",
    }
    body = {"stk_nm": name}
    r = requests.post(url, headers=headers, json=body, timeout=10)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("stk_cd"):
        return str(data["stk_cd"]).strip()
    for key in ("stk_list", "list", "items", "data"):
        arr = data.get(key)
        if isinstance(arr, list) and arr:
            cand = arr[0]
            code = cand.get("stk_cd") or cand.get("code") or cand.get("stkCode")
            if code:
                return str(code).strip()
    return None


def _normalize_kiwoom_payload(stk: str, data: dict | list | None) -> dict | list | None:
    """Make Kiwoom payload friendlier for summary printing.
    - Ensure stk_cd exists
    - Ensure tp (price) exists by probing common keys or first cntr_infr item
    """
    if not isinstance(data, dict):
        return data
    payload = dict(data)
    payload.setdefault("stk_cd", stk)
    price = (
        payload.get("stck_prpr")
        or payload.get("tp")
        or payload.get("price")
        or payload.get("trade_price")
    )
    if price is None:
        cn = payload.get("cntr_infr")
        if isinstance(cn, list) and cn and isinstance(cn[0], dict):
            price = cn[0].get("cur_prc")
    if price is not None and payload.get("tp") is None:
        payload["tp"] = price
    return payload


def fetch_kiwoom(stk: str, mock: bool) -> dict:
    base = get_base(mock)
    auth = issue_token(base)
    return get_trade_info(base, auth, stk)


def fetch_dart(stk: str, years_n: int, fs_div: str) -> dict:
    # Extended financials: revenue/op_profit/net_profit/ratios
    return collect_recent_financials(
        project_root=str(_PROJECT_ROOT),
        stock_code=stk,
        years=years_n,
        fs_div=fs_div,
    )


def _default_merged_path(stk: str) -> Path:
    return _DATA_DIR / f"{stk}_merged.json"


def main():
    load_env()

    p = argparse.ArgumentParser(description="Sentiment Apps: Kiwoom+DART 병합 JSON 저장")
    # common inputs
    p.add_argument("stk", nargs="?", help="종목코드(6자리) 예: 005930")
    p.add_argument("--name", help="종목명 예: 삼성전자")

    # output path
    p.add_argument("--out", default="", help="병합 JSON 저장 경로 (기본: data/{종목코드}_merged.json)")

    # selective toggles (default: include both)
    p.add_argument("--no-kiwoom", action="store_true", help="Kiwoom 데이터 제외")
    p.add_argument("--no-dart", action="store_true", help="DART 데이터 제외")

    # Kiwoom options
    p.add_argument("--mock", action="store_true", help="(kiwoom) 모의투자 도메인 사용")

    # DART options
    p.add_argument("--years", type=int, default=8, help="(dart) 최근 N년 (기본 8)")
    p.add_argument("--fs", default="CFS", choices=["CFS", "OFS"], help="(dart) 연결/개별 재무제표 (기본 CFS)")

    args = p.parse_args()

    # 1) resolve stock code
    if not args.stk and not args.name:
        raise SystemExit("종목코드(stk) 또는 --name 중 하나는 반드시 입력하세요.")
    if args.stk and args.name:
        raise SystemExit("종목코드와 --name은 동시에 사용할 수 없습니다.")

    if args.name:
        m = load_symbol_map()
        code, cands = resolve_code_by_name(args.name, m)
        if not code:
            # Optional: REST fallback (disabled by default)
            # base = get_base(args.mock); auth = issue_token(base)
            # code = _get_code_by_name_via_api(base, auth, args.name)
            if cands:
                print("여러 후보가 있어요:")
                for n, c in cands:
                    print(f"- {n} ({c})")
                raise SystemExit("정확한 이름으로 다시 시도하거나 위 코드 중 하나를 사용하세요.")
            raise SystemExit(f"'{args.name}' 에 해당하는 종목을 찾지 못했습니다.")
        stk = code
    else:
        stk = args.stk.strip()

    if not (len(stk) == 6 and stk.isdigit()):
        raise SystemExit(f"종목코드 형식이 잘못됐어요: {stk} (예: 005930)")

    # 2) fetch (default: both)
    kiwoom_data = None
    dart_data = None
    errors: list[str] = []

    if not args.no_kiwoom:
        try:
            kiwoom_data = fetch_kiwoom(stk, args.mock)
            kiwoom_data = _normalize_kiwoom_payload(stk, kiwoom_data)
            if args.name and isinstance(kiwoom_data, dict) and not kiwoom_data.get("stk_nm"):
                kiwoom_data["stk_nm"] = args.name
        except Exception as e:
            msg = f"Kiwoom 오류: {e}"
            print(f"[{msg}]")
            errors.append(msg)
            kiwoom_data = None

    if not args.no_dart:
        try:
            dart_data = fetch_dart(stk, args.years, args.fs)
        except Exception as e:
            msg = f"DART 오류: {e}"
            print(f"[{msg}]")
            errors.append(msg)
            dart_data = None

    if kiwoom_data is None and dart_data is None:
        # Save skeleton JSON even when both failed
        merged = {
            "stock_code": stk,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "errors": errors,
        }
        out_path = Path(args.out) if args.out else _default_merged_path(stk)
        os.makedirs(out_path.parent, exist_ok=True)
        saved = save_json(merged, out_path)
        print(f"[병합 저장 완료] {saved}")
        print_summary_merged(merged)
        return

    # 3) merge JSON structure
    merged = {
        "stock_code": stk,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if kiwoom_data is not None:
        merged["kiwoom"] = {
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "data": kiwoom_data,
        }
    if dart_data is not None:
        merged["dart"] = dart_data

    # 4) save
    out_path = Path(args.out) if args.out else _default_merged_path(stk)
    os.makedirs(out_path.parent, exist_ok=True)
    saved = save_json(merged, out_path)
    print(f"[병합 저장 완료] {saved}")

    # 5) summaries
    print_summary_merged(merged)


if __name__ == "__main__":
    main()
