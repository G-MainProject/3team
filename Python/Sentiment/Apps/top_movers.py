# -*- coding: utf-8 -*-
"""
Top Movers (급등/급락 상위)

Default: save tab-separated text (TSV) to data/top_movers_{direction}_{YYYYMMDD_HHMMSS}.txt
Fetches per-symbol trade info via Kiwoom REST and computes change metrics.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

# Bootstrap sys.path so this file can be executed directly
_CUR = Path(__file__).resolve()
_PROJECT_ROOT = _CUR.parents[3]  # .../3team
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from Python.Sentiment.Libs.env import load_env
from Python.Sentiment.Libs.kiwoom_client import (
    get_base,
    issue_token,
    get_trade_info,
    get_movers_ka10019,
)
from Python.Sentiment.Libs.io_utils import save_tsv, save_json
from Python.Sentiment.Libs.symbols import load_symbol_map


_CUR = Path(__file__).resolve()
_SENTIMENT_DIR = _CUR.parents[1]          # .../Sentiment
_PROJECT_ROOT = _SENTIMENT_DIR.parents[1] # .../3team
_DATA_DIR = _PROJECT_ROOT / "data"


def _to_float(x: Any) -> float | None:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    try:
        s = str(x).strip()
        if s == "":
            return None
        # remove commas and percent/plus signs
        s = s.replace(",", "")
        s = s.replace("%", "")
        # Some payloads encode sign separately; keep only the numeric sign if present
        return float(s)
    except Exception:
        return None


def _to_int(x: Any) -> int | None:
    f = _to_float(x)
    if f is None:
        return None
    try:
        return int(round(f))
    except Exception:
        return None


def _sign_from(value: Any) -> int:
    """Infer sign from various notations. Returns -1, 0, or 1."""
    if value is None:
        return 0
    s = str(value).strip()
    if s == "":
        return 0
    sl = s.lower()
    # direct tokens
    if sl in ("-", "2", "down", "d"):
        return -1
    if sl in ("+", "1", "up", "u"):
        return 1
    # language/symbol hints
    if any(t in s for t in ["하락", "▼", "↓", "minus"]):
        return -1
    if any(t in s for t in ["상승", "▲", "↑", "plus"]):
        return 1
    try:
        v = float(s.replace("%", "").replace(",", ""))
        if v < 0:
            return -1
        if v > 0:
            return 1
    except Exception:
        pass
    return 0


def _side_from(chg_pct: float | None, chg_abs: int | None) -> str:
    """Return 'UP', 'DOWN', or 'FLAT' from change metrics."""
    try:
        if chg_pct is not None:
            if chg_pct > 0:
                return "UP"
            if chg_pct < 0:
                return "DOWN"
        if chg_abs is not None:
            if chg_abs > 0:
                return "UP"
            if chg_abs < 0:
                return "DOWN"
    except Exception:
        pass
    return "FLAT"


def _extract_metrics(stk: str, payload: Dict[str, Any]) -> Tuple[str, str, int | None, int | None, float | None]:
    """
    Return tuple: (code, name, price, change_abs, change_pct)
    Fallbacks:
      - price: stck_prpr | tp | price | trade_price | (cntr_infr[0].cur_prc)
      - change_abs: prdy_vrss | vs | (price - prdy_clpr)
      - change_pct: prdy_ctrt | chg_rate | fluctuationRate | ((price-prdy_clpr)/prdy_clpr*100)
      - name: stk_nm | name | ""
    """
    code = (payload.get("stk_cd") or payload.get("code") or stk or "").strip()
    name = str(payload.get("stk_nm") or payload.get("name") or "").strip()

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
    price_i = _to_int(price)

    change_abs = payload.get("prdy_vrss") or payload.get("vs")
    change_pct = payload.get("prdy_ctrt") or payload.get("chg_rate") or payload.get("fluctuationRate")

    prdy_clpr = payload.get("prdy_clpr") or payload.get("prev_price")
    prdy_clpr_f = _to_float(prdy_clpr)

    chg_abs_i = _to_int(change_abs)
    chg_pct_f = _to_float(change_pct)

    if (chg_abs_i is None or chg_pct_f is None) and (price_i is not None and prdy_clpr_f and prdy_clpr_f != 0):
        # compute from price and previous close if possible
        diff = float(price_i) - float(prdy_clpr_f)
        if chg_abs_i is None:
            chg_abs_i = int(round(diff))
        if chg_pct_f is None:
            chg_pct_f = (diff / float(prdy_clpr_f)) * 100.0

    return code, name, price_i, chg_abs_i, chg_pct_f


def _iter_codes_from_file(path: Path) -> Iterable[str]:
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        # allow name or code lines; filter 6-digit codes only here
        if len(s) == 6 and s.isdigit():
            yield s


def _default_txt_path(direction: str) -> Path:
    ts = time.strftime("%Y%m%d_%H%M%S")
    return _DATA_DIR / f"top_movers_{direction}_{ts}.txt"


def main() -> None:
    load_env()

    p = argparse.ArgumentParser(description="Top Movers (급등/급락) TSV exporter")
    p.add_argument("--direction", choices=["up", "down", "both"], default="both", help="정렬/필터 기준")
    p.add_argument("--limit", type=int, default=5, help="상위 N개 (기본 5)")
    p.add_argument("--mock", action="store_true", help="모의 서버 사용")
    p.add_argument("--txt-out", default="", help="TSV 저장 경로 (기본: data/top_movers_*.txt)")
    p.add_argument("--universe-file", default="", help="조회할 종목코드 목록 파일 (1행 1코드, 6자리)")
    p.add_argument("--codes", default="", help="콤마/공백 구분 6자리 코드 목록 예) 005930,000660 035420")
    p.add_argument("--source", choices=["ka10019", "percode"], default="ka10019", help="데이터 소스: 랭킹TR(권장) 또는 개별조회")
    # ka10019 required params (defaults follow spec: 전체/포함/분전 등)
    p.add_argument("--mrkt-tp", default="000", help="시장구분(000 전체, 001 코스피, 101 코스닥, 201 코스피200)")
    p.add_argument("--flu-tp", default="", help="등락구분(1 급등, 2 급락). both일 때는 자동으로 1,2 두 번 호출")
    p.add_argument("--tm-tp", default="1", help="시간구분(1 분전, 2 일전). 기본 1")
    p.add_argument("--tm", default="5", help="시간 값(분전/일전). 기본 5")
    p.add_argument("--trde-qty-tp", default="00000", help="거래량구분(00000 전체, 00010 만주이상, ...)")
    p.add_argument("--stk-cnd", default="0", help="종목조건(0 전체, 1 관리제외, 3 우선주제외, 5 증100 제외, 6 증100만, 7 증40만, 8 증30만)")
    p.add_argument("--crd-cnd", default="0", help="신용조건(0 전체, 1 A군, 2 B군, 3 C군, 4 D군, 7 E군, 9 전체)")
    p.add_argument("--pric-cnd", default="0", help="가격조건(0 전체, 1 1천 미만, 2 1천~2천, 3 2천~3천, 4 5천~1만, 5 1만 이상, 8 1천 이상)")
    p.add_argument("--updown-incls", default="1", help="상하한포함(0 미포함, 1 포함). 기본 1")
    p.add_argument("--stex-tp", default="1", help="거래소구분(1 KRX, 2 NXT, 3 통합). 기본 1")
    p.add_argument("--max-workers", type=int, default=16, help="동시 요청 수 (기본 16)")
    p.add_argument("--max-codes", type=int, default=0, help="조회 종목 수 상한(0=무제한)")
    p.add_argument("--no-console", action="store_true", help="콘솔 요약 출력 생략")
    p.add_argument("--debug", action="store_true", help="디버그: 원본 응답 JSON 저장")
    args = p.parse_args()

    base = get_base(args.mock)
    auth = issue_token(base)

    rows: List[Tuple[str, str, int | None, int | None, float | None]] = []

    if args.source == "ka10019":
        # Use ranking TR (no universe needed). Try first page.
        try:
            def call_once(flu_tp: str):
                return get_movers_ka10019(
                    base,
                    auth,
                    cont_yn="N",
                    next_key="",
                    mrkt_tp=args.mrkt_tp,
                    extra_body={
                        "flu_tp": flu_tp,
                        "tm_tp": args.tm_tp,
                        "tm": args.tm,
                        "trde_qty_tp": args.trde_qty_tp,
                        "stk_cnd": args.stk_cnd,
                        "crd_cnd": args.crd_cnd,
                        "pric_cnd": args.pric_cnd,
                        "updown_incls": args.updown_incls,
                        "stex_tp": args.stex_tp,
                    },
                )

            items = []
            # Determine flu_tp based on direction when not provided or when both
            if args.direction == "both":
                r_up = call_once("1")
                r_dn = call_once("2")
                items = ((r_up or {}).get("items") or []) + ((r_dn or {}).get("items") or [])
                resp = {"raw": {"up": r_up.get("raw"), "down": r_dn.get("raw")}}
            else:
                flu_tp = args.flu_tp.strip() or ("1" if args.direction == "up" else "2")
                resp = call_once(flu_tp)
                items = (resp or {}).get("items") or []
            if args.debug:
                ts = time.strftime("%Y%m%d_%H%M%S")
                dbg_path = _DATA_DIR / f"debug_ka10019_{ts}.json"
                try:
                    save_json(resp.get("raw"), dbg_path)
                    if not args.no_console:
                        print(f"[debug] saved raw ka10019 -> {dbg_path}")
                except Exception:
                    pass
            for it in items:
                code = str(it.get("stk_cd") or it.get("code") or "").strip()
                name = str(it.get("stk_nm") or it.get("name") or "").strip()
                price = _to_int(it.get("cur_prc") or it.get("stck_prpr") or it.get("tp"))
                # prefer flu_rt(등락률), fallback to jmp_rt(급등률)
                chg_pct = _to_float(it.get("flu_rt") or it.get("jmp_rt"))
                chg_abs = _to_int(it.get("pred_pre") or it.get("base_pre") or it.get("prdy_vrss"))
                rows.append((code, name, price, chg_abs, chg_pct))
        except Exception:
            rows = []
    else:
        # per-code fallback path (may require symbols CSV or explicit codes)
        # universe: from --codes > file > symbols.csv
        codes: List[str] = []
        code_to_name: Dict[str, str] = {}
        if args.codes:
            tokens = re.split(r"[\s,]+", args.codes.strip())
            for t in tokens:
                if not t:
                    continue
                c = re.sub(r"\D", "", t)
                if len(c) == 6 and c.isdigit():
                    codes.append(c)
            if not codes:
                raise SystemExit("--codes 값에서 6자리 코드를 찾지 못했습니다.")
        elif args.universe_file:
            uf = Path(args.universe_file)
            if not uf.exists():
                raise SystemExit(f"universe 파일을 찾을 수 없습니다: {uf}")
            codes = list(_iter_codes_from_file(uf))
        else:
            try:
                name_to_code = load_symbol_map()  # name -> code
            except FileNotFoundError:
                raise SystemExit(
                    "심볼 파일(data/symbols_krx.csv)이 없습니다. "
                    "--codes '005930,000660' 또는 --universe-file 경로를 지정해 실행하세요."
                )
            for n, c in name_to_code.items():
                if c and len(c) == 6 and c.isdigit():
                    code_to_name.setdefault(c, n)
            codes = list(code_to_name.keys())

        if args.max_codes and args.max_codes > 0:
            codes = codes[: args.max_codes]

        results: List[Tuple[str, str, int | None, int | None, float | None]] = []

        def _task(code: str):
            try:
                data = get_trade_info(base, auth, code)
                if isinstance(data, dict):
                    code_, name, price, chg_abs, chg_pct = _extract_metrics(code, data)
                    if not name:
                        name = code_to_name.get(code_, "")
                    return code_, name, price, chg_abs, chg_pct
                return code, code_to_name.get(code, ""), None, None, None
            except Exception:
                return code, code_to_name.get(code, ""), None, None, None

        with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as ex:
            futs = {ex.submit(_task, c): c for c in codes}
            for f in as_completed(futs):
                r = f.result()
                results.append(r)
        rows = [r for r in results if r[4] is not None]

    # normalize sign: if absolute delta indicates opposite sign, fix percentage sign
    try:
        fixed_rows: List[Tuple[str, str, int | None, int | None, float | None]] = []
        for code, name, price, chg_abs, chg_pct in rows:
            if chg_pct is not None and chg_abs is not None:
                try:
                    if chg_abs < 0 and chg_pct > 0:
                        chg_pct = -abs(float(chg_pct))
                    elif chg_abs > 0 and chg_pct < 0:
                        chg_pct = abs(float(chg_pct))
                except Exception:
                    pass
            fixed_rows.append((code, name, price, chg_abs, chg_pct))
        rows = fixed_rows
    except Exception:
        pass

    # normalize sign again (covers ka10019 branch too)
    try:
        fixed_rows2: List[Tuple[str, str, int | None, int | None, float | None]] = []
        for code, name, price, chg_abs, chg_pct in rows:
            if chg_pct is not None and chg_abs is not None:
                try:
                    if chg_abs < 0 and chg_pct > 0:
                        chg_pct = -abs(float(chg_pct))
                    elif chg_abs > 0 and chg_pct < 0:
                        chg_pct = abs(float(chg_pct))
                except Exception:
                    pass
            fixed_rows2.append((code, name, price, chg_abs, chg_pct))
        rows = fixed_rows2
    except Exception:
        pass

    # sort by direction
    if args.direction == "up":
        rows.sort(key=lambda x: x[4], reverse=True)  # highest positive pct
        rows = [r for r in rows if (r[4] or 0) > 0]
    elif args.direction == "down":
        rows.sort(key=lambda x: x[4])  # most negative first
        rows = [r for r in rows if (r[4] or 0) < 0]
    else:  # both
        rows.sort(key=lambda x: abs(x[4] or 0.0), reverse=True)

    top = rows[: max(1, args.limit)]

    # prepare TSV
    headers = ["code", "name", "side", "price", "change_abs", "change_pct"]
    tsv_rows: List[List[str]] = []
    for code, name, price, chg_abs, chg_pct in top:
        side = _side_from(chg_pct, chg_abs)
        price_s = "" if price is None else str(int(price))
        chg_abs_s = "" if chg_abs is None else str(int(chg_abs))
        chg_pct_s = "" if chg_pct is None else f"{chg_pct:.2f}"
        tsv_rows.append([code, name or "", side, price_s, chg_abs_s, chg_pct_s])

    out_path = Path(args.txt_out) if args.txt_out else _default_txt_path(args.direction)
    saved = save_tsv(tsv_rows, out_path, headers=headers, include_header=True)

    if not args.no_console:
        print(f"[Top Movers 저장 완료] {saved}")
        for idx, (code, name, price, chg_abs, chg_pct) in enumerate(top, start=1):
            side = _side_from(chg_pct, chg_abs)
            price_s = "-" if price is None else f"{price:,}"
            chg_abs_s = "-" if chg_abs is None else f"{chg_abs:,}"
            chg_pct_s = "-" if chg_pct is None else f"{chg_pct:.2f}%"
            print(f"{idx}) {name or ''}({code}) [{side}] {chg_pct_s} ({chg_abs_s}) / {price_s}")


if __name__ == "__main__":
    main()
