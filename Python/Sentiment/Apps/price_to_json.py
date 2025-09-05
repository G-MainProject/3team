# -*- coding: utf-8 -*-
import argparse, time
from pathlib import Path
from urllib.parse import urljoin         # ★ 추가
import requests                          # ★ 추가

from Python.Sentiment.Libs.env import load_env
from Python.Sentiment.Libs.kiwoom_client import get_base, issue_token, get_trade_info
from Python.Sentiment.Libs.io_utils import default_json_path, save_json
from Python.Sentiment.Libs.symbols import load_symbol_map, resolve_code_by_name

def get_code_by_name(base: str, auth: str, name: str) -> dict:
    """
    종목명 → 코드 조회 (TR: ka10001 가정, 문서에 따라 필드명이 다를 수 있어 방어적으로 파싱)
    """
    url = urljoin(base, "/api/dostk/stkinfo")
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "api-id": "ka10001",   # 종목기본정보/검색 TR (문서 기준)
        "authorization": auth,
        "cont-yn": "N",
        "next-key": "",
    }
    body = {"stk_nm": name}
    r = requests.post(url, headers=headers, json=body, timeout=10)
    r.raise_for_status()
    return r.json()

def extract_code_from_response(resp: dict) -> str | None:
    """
    ka10001 응답에서 stk_cd를 뽑아낸다.
    - 단일 객체: resp["stk_cd"]
    - 리스트 형태: resp["stk_list"][0]["stk_cd"] 또는 resp["list"][0]["stk_cd"]
    실제 문서 필드명에 따라 분기 처리.
    """
    # 1) 단일 필드
    if isinstance(resp, dict) and resp.get("stk_cd"):
        return str(resp["stk_cd"]).strip()

    # 2) 리스트 케이스
    for key in ("stk_list", "list", "items", "data"):
        arr = resp.get(key)
        if isinstance(arr, list) and arr:
            cand = arr[0]
            code = cand.get("stk_cd") or cand.get("code") or cand.get("stkCode")
            if code:
                return str(code).strip()

    # 3) 못 찾으면 None
    return None

def print_summary(data: dict) -> None:
    # ka10003 체결정보 요약
    arr = data.get("cntr_infr")
    if isinstance(arr, list) and arr:
        x = arr[0]
        print(f"- 체결시각: {x.get('tm')}  현재가: {x.get('cur_prc')}  전일대비: {x.get('pred_pre')}  등락률: {x.get('pre_rt')}")
        return
    # ka10001 등 기본정보 형식(필드 추정)
    if "cur_prc" in data:
        print(f"- 현재가: {data.get('cur_prc')}  전일대비: {data.get('pred_pre')}  등락률: {data.get('flu_rt')}")
        return
    rc = data.get("return_code")
    if rc not in (None, 0, "0"):
        print(f"- 호출 실패: return_code={rc}, return_msg={data.get('return_msg')}")
    else:
        print("- 요약 가능한 필드를 찾지 못했어. 저장된 JSON을 확인해주세요.")

def main():
    load_env()

    p = argparse.ArgumentParser(description="Kiwoom: 종목 체결/주가 정보 → data/*.json 저장")
    # 코드 또는 이름 중 하나 받기
    p.add_argument("stk", nargs="?", help="종목코드(6자리) 예: 005930")
    p.add_argument("--name", help="종목명 예: 삼성전자")
    p.add_argument("--mock", action="store_true", help="모의투자 도메인 사용")
    p.add_argument("--out", default="", help="저장 경로(기본: data/stock_...json)")
    args = p.parse_args()

    if not args.stk and not args.name:
        raise SystemExit("종목코드(stk) 또는 --name 중 하나는 반드시 입력하세요. 예: 005930 또는 --name 삼성전자")
    if args.stk and args.name:
        raise SystemExit("종목코드와 --name은 동시에 사용할 수 없습니다. 둘 중 하나만 입력하세요.")

    base = get_base(args.mock)
    auth = issue_token(base)

    # 종목명으로 받은 경우 → 코드로 변환
    if args.name:
        m = load_symbol_map()
        code, cands = resolve_code_by_name(args.name, m)
        if not code:
            if cands:
                print("여러 후보가 있어요:")
                for n, c in cands:
                    print(f"- {n} ({c})")
                raise SystemExit("정확한 이름으로 다시 시도하거나 위 코드 중 하나를 사용하세요.")
            raise SystemExit(f"'{args.name}' 에 해당하는 종목을 찾지 못했습니다. CSV를 확인하세요.")
        stk = code
    else:
        stk = args.stk.strip()

    # 코드 형식 검증(6자리)
    if not (len(stk) == 6 and stk.isdigit()):
        raise SystemExit(f"종목코드 형식이 잘못됐어요: {stk} (예: 005930)")

    # 체결/주가 정보 조회
    data = get_trade_info(base, auth, stk)

    # 저장
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = Path(args.out) if args.out else default_json_path(stk, ts)
    saved = save_json(data, out_path)

    print(f"[저장 완료] {saved}")
    print_summary(data)

if __name__ == "__main__":
    main()
