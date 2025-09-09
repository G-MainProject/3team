# -*- coding: utf-8 -*-
"""
price_to_json.py
- 실행 시 Kiwoom(체결/주가) + DART(최근 N년 분기 매출액)를 수집하여
  하나의 JSON 파일(data/{종목코드}_merged.json)로 저장한다.
- 선택적으로 --no-kiwoom, --no-dart 로 한쪽을 제외할 수 있다(기본: 둘 다 포함).
"""

import argparse
import os
import time
from pathlib import Path
from urllib.parse import urljoin
import requests

# 환경/유틸/클라이언트
from Python.Sentiment.Libs.env import load_env
from Python.Sentiment.Libs.kiwoom_client import get_base, issue_token, get_trade_info
from Python.Sentiment.Libs.io_utils import save_json
from Python.Sentiment.Libs.symbols import load_symbol_map, resolve_code_by_name
from Python.Sentiment.Libs.revenue import collect_recent_years

# 요약(콘솔 출력) 모듈
from Python.Sentiment.Libs.summaries import (
    print_summary_kiwoom,
    print_summary_dart,
    print_summary_merged,
)

# ─────────────────────────────────────────
# 경로 계산
# ─────────────────────────────────────────
_CUR = Path(__file__).resolve()
_SENTIMENT_DIR = _CUR.parents[1]          # .../Sentiment
_PROJECT_ROOT = _SENTIMENT_DIR.parents[2] # .../3team
_DATA_DIR = _PROJECT_ROOT / "data"

# ─────────────────────────────────────────
# (보조) 이름→코드 조회 (Kiwoom TR 보조용; 내부 CSV 매핑이 우선)
# ─────────────────────────────────────────
def _get_code_by_name_via_api(base: str, auth: str, name: str) -> str | None:
    """키움 REST로 종목명→코드 보조 조회(필요시). 보통은 symbols.csv 매핑으로 해결."""
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
    # 필드 방어적 파싱
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

# ─────────────────────────────────────────
# 수집 함수 (얇게 유지)
# ─────────────────────────────────────────
def fetch_kiwoom(stk: str, mock: bool) -> dict:
    base = get_base(mock)
    auth = issue_token(base)
    return get_trade_info(base, auth, stk)

def fetch_dart(stk: str, years_n: int, fs_div: str) -> dict:
    return collect_recent_years(
        project_root=str(_PROJECT_ROOT),
        stock_code=stk,
        years=years_n,
        fs_div=fs_div
    )

def _default_merged_path(stk: str) -> Path:
    return _DATA_DIR / f"{stk}_merged.json"

# ─────────────────────────────────────────
# 메인
# ─────────────────────────────────────────
def main():
    load_env()

    p = argparse.ArgumentParser(description="Sentiment Apps: (기본) Kiwoom + DART 병합 JSON 저장")
    # 공통 입력
    p.add_argument("stk", nargs="?", help="종목코드(6자리) 예: 005930")
    p.add_argument("--name", help="종목명 예: 삼성전자")

    # 출력 경로 (병합 파일)
    p.add_argument("--out", default="", help="병합 JSON 저장 경로 (기본: data/{종목코드}_merged.json)")

    # 선택 제외 옵션 (기본: 둘 다 포함)
    p.add_argument("--no-kiwoom", action="store_true", help="Kiwoom 데이터 제외")
    p.add_argument("--no-dart",   action="store_true", help="DART 데이터 제외")

    # Kiwoom 옵션
    p.add_argument("--mock", action="store_true", help="(kiwoom) 모의투자 도메인 사용")

    # DART 옵션
    p.add_argument("--years", type=int, default=3, help="(dart) 최근 N년 (기본 3)")
    p.add_argument("--fs", default="CFS", choices=["CFS", "OFS"], help="(dart) 연결/개별 재무제표 (기본 CFS)")

    args = p.parse_args()

    # 1) 종목코드 확정
    if not args.stk and not args.name:
        raise SystemExit("종목코드(stk) 또는 --name 중 하나는 반드시 입력하세요.")
    if args.stk and args.name:
        raise SystemExit("종목코드와 --name은 동시에 사용할 수 없습니다.")

    if args.name:
        # 내부 CSV 매핑 우선
        m = load_symbol_map()
        code, cands = resolve_code_by_name(args.name, m)
        if not code:
            # 필요시 API 보조 조회 (주석 해제하여 사용 가능)
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

    # 2) 데이터 수집 (기본: 둘 다)
    kiwoom_data = None
    dart_data = None

    if not args.no_kiwoom:
        kiwoom_data = fetch_kiwoom(stk, args.mock)

    if not args.no_dart:
        dart_data = fetch_dart(stk, args.years, args.fs)

    if kiwoom_data is None and dart_data is None:
        raise SystemExit("둘 다 제외되어 저장할 데이터가 없습니다. (--no-kiwoom, --no-dart 둘 다 사용됨)")

    # 3) 병합 JSON 구성
    merged = {
        "stock_code": stk,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if kiwoom_data is not None:
        merged["kiwoom"] = {
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "data": kiwoom_data
        }
    if dart_data is not None:
        merged["dart"] = dart_data  # (fs_div, collected_years, data[...] 포함)

    # 4) 저장
    out_path = Path(args.out) if args.out else _default_merged_path(stk)
    os.makedirs(out_path.parent, exist_ok=True)
    saved = save_json(merged, out_path)
    print(f"[병합 저장 완료] {saved}")

    # 5) 요약 출력 (프로젝트 목적 맞춘 요약)
    print_summary_merged(merged)

if __name__ == "__main__":
    main()
