# -*- coding: utf-8 -*-
"""Top movers 탐색(pykrx 또는 Kiwoom 기반).

- 기본: Kiwoom 먼저 시도 → 실패 시 pykrx로 폴백
- pykrx: 해당 일자 OHLCV로 변동성 상위, 현재가/변동률(근사) 포함
- 출력: tickers + details[{ticker,name,change_pct,current_price,base_price?}]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
import csv as _csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Mapping

try:  # Python 3.9 이상
    from zoneinfo import ZoneInfo  # type: ignore
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

import requests
from urllib.parse import urljoin


def _project_root() -> Path:
    """프로젝트 루트를 추정.

    - 1순위: .env가 존재하는 디렉터리
    - 2순위: Python 또는 data 디렉터리가 존재하는 상위 디렉터리
    """
    here = Path(__file__).resolve()
    # 실제 .env 파일이 있는 디렉터리를 우선 사용한다
    for p in here.parents:
        if (p / ".env").exists():
            return p
    # 프로젝트 루트로 보이는 디렉터리를 예비 후보로 사용한다
    for p in here.parents:
        if (p / "Python").exists() or (p / "data").exists():
            return p
    return here.parents[4]


def _load_env_fallback() -> None:
    """.env 값을 강제로 os.environ에 주입하고 일부 별칭 보정."""
    try:
        env_path = _project_root() / ".env"
        if not env_path.exists():
            return
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")
        # 별칭 보정
        if os.getenv("KIWOOM_RANK_TR_ID") is None and os.getenv("KIWOOM_RANK_API_ID") is not None:
            os.environ["KIWOOM_RANK_TR_ID"] = os.getenv("KIWOOM_RANK_API_ID") or ""
        if os.getenv("KIWOOM_DAILY_PATH") is None and os.getenv("KIWOOM_KA10001_PATH") is not None:
            os.environ["KIWOOM_DAILY_PATH"] = os.getenv("KIWOOM_KA10001_PATH") or ""
    except Exception:
        pass


def _debug_enabled() -> bool:
    return (os.getenv("KIWOOM_DEBUG") or "").strip() == "1"


# -------- pykrx 관련 보조 함수 --------
try:  # pykrx 라이브러리
    from pykrx import stock  # type: ignore
except Exception:  # pragma: no cover
    stock = None  # type: ignore

_ETF_CACHE: set[str] | None = None


def _load_etf_set() -> set[str]:
    """Return a cached set of ETF/ETN tickers (zero-padded)."""
    global _ETF_CACHE
    if _ETF_CACHE is not None:
        return _ETF_CACHE
    tickers: set[str] = set()
    if stock is not None:
        def _collect(name: str) -> None:
            getter = getattr(stock, name, None)
            if callable(getter):
                try:
                    tickers.update(str(t).strip().zfill(6) for t in getter())
                except Exception:
                    pass

        _collect("get_etf_ticker_list")
        _collect("get_etn_ticker_list")
    _ETF_CACHE = tickers
    return _ETF_CACHE


def _is_etf_ticker(ticker: str) -> bool:
    tk = str(ticker or "").strip().zfill(6)
    if not tk:
        return False
    return tk in _load_etf_set()


def _is_structured_product(entry: Mapping[str, Any], etf_set: set[str]) -> bool:
    """Return True if entry looks like ETF/ETN based on ticker or name."""
    tk = str(entry.get("ticker") or "").strip().zfill(6)
    if tk and tk in etf_set:
        return True
    name = entry.get("name")
    if isinstance(name, str):
        upper = name.upper()
        if "ETF" in upper or "ETN" in upper:
            return True
    category = entry.get("category")
    if isinstance(category, str) and category.upper() in {"ETF", "ETN"}:
        return True
    return False


def _find_latest_trading_date(date_str: str) -> str:
    """기준일로부터 최근 거래일(YYYYMMDD) 반환(pykrx 필요)."""
    if stock is None:
        raise ImportError("pykrx가 필요합니다. `pip install pykrx`를 설치하세요")
    base = datetime.strptime(date_str.replace("-", ""), "%Y%m%d")
    for i in range(14):
        target = (base - timedelta(days=i)).strftime("%Y%m%d")
        try:
            frame = stock.get_market_cap_by_ticker(target)
            if frame is not None and not frame.empty:
                return target
        except Exception:
            continue
    raise RuntimeError(f"최근 2주내 거래일을 찾지 못했습니다: {date_str}")


def _fetch_top_movers_pykrx(date: str, market: str, count: int) -> List[dict[str, Any]]:
    if stock is None:
        raise ImportError("pykrx가 필요합니다. `pip install pykrx`를 설치하세요")
    frame = stock.get_market_ohlcv_by_ticker(date, market=market)
    if frame is None or frame.empty:
        raise RuntimeError(f"pykrx에서 데이터를 찾지 못했습니다: {date}, {market}")
    if "ticker" not in frame.columns:
        try:
            frame = frame.copy(); frame["ticker"] = frame.index.astype(str)
        except Exception:
            frame["ticker"] = frame.index
    frame = frame.reset_index(drop=True)

    def pick(*cands: str) -> str:
        for c in cands:
            if c in frame.columns:
                return c
        raise KeyError("필수 컬럼을 찾지 못했습니다")

    c_open = pick("open", "시가"); c_high = pick("high", "고가"); c_low = pick("low", "저가"); c_close = pick("close", "종가")
    frame["volatility"] = (frame[c_high] - frame[c_low]).abs() / frame[c_open].replace(0, float("nan"))
    frame = frame.dropna(subset=["volatility"]).sort_values("volatility", ascending=False)
    etf_set = _load_etf_set()
    out: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        try:
            cur = float(row[c_close])
        except Exception:
            cur = None
        try:
            opn = float(row[c_open])
            chg = ((cur / opn) - 1.0) * 100.0 if (cur is not None and opn not in (None, 0.0)) else None
        except Exception:
            chg = None
        ticker_str = str(row["ticker"]).strip()
        if ticker_str.zfill(6) in etf_set:
            continue
        out.append({
            "ticker": ticker_str,
            "volatility": float(row["volatility"]),
            "current_price": cur,
            "change_pct": chg,
        })
        if len(out) >= count:
            break
    return out


def _lookup_name(ticker: str, date: str) -> str | None:
    if stock is None:
        return None
    try:
        return stock.get_market_ticker_name(ticker, date=date)
    except Exception:
        return None


def _annotate_names(entries: list[dict[str, Any]], date_for_lookup: str) -> None:
    for e in entries:
        tk = str(e.get("ticker") or "").strip()
        if not tk:
            continue
        if not e.get("name"):
            nm = _lookup_name(tk, date_for_lookup)
            if nm:
                e["name"] = nm


def _enrich_names_from_csv(entries: list[dict[str, Any]], csv_path: Path) -> None:
    if not csv_path.exists():
        return
    try:
        with csv_path.open("r", encoding="utf-8-sig", errors="ignore") as fp:
            rdr = _csv.DictReader(fp)
            headers = { (h or "").strip().lower(): h for h in (rdr.fieldnames or []) }
            t_col = headers.get("ticker") or headers.get("stock_code") or headers.get("code") or headers.get("symbol")
            n_col = headers.get("corp_name") or headers.get("corpname") or headers.get("corp_nm") or headers.get("corp")
            mapping: dict[str, str] = {}
            for row in rdr:
                try:
                    tk = str(row.get(t_col, "")).strip().zfill(6) if t_col else str(list(row.values())[0]).strip().zfill(6)
                    nm = str(row.get(n_col, "")).strip() if n_col else str(list(row.values())[-1]).strip()
                    if tk and nm:
                        mapping[tk] = nm
                except Exception:
                    continue
        for e in entries:
            tk = str(e.get("ticker") or "").strip().zfill(6)
            if tk and (not e.get("name") or str(e.get("name")).strip() == tk):
                if tk in mapping:
                    e["name"] = mapping[tk]
    except Exception:
        pass


# -------- Kiwoom 직접 호출 관련 --------

def _post(sess: requests.Session, base: str, endpoint: str, *, headers: Mapping[str, str], body: Mapping[str, object], timeout: int = 15):
    url = urljoin(base.rstrip("/"), endpoint)
    r = sess.post(url, headers=headers, json=body, timeout=timeout)
    r.raise_for_status(); return r.json()


def _issue_token(sess: requests.Session, base: str, appkey: str, secret: str) -> str:
    token_api_id = (os.getenv("KIWOOM_TOKEN_API_ID") or os.getenv("KIWOOM_API_ID") or "au10001").strip()
    headers = {"Content-Type": "application/json;charset=UTF-8", "api-id": token_api_id}
    body = {"grant_type": "client_credentials", "appkey": appkey, "secretkey": secret}
    data = _post(sess, base, "/oauth2/token", headers=headers, body=body)
    token = data.get("token") or data.get("access_token") or data.get("accessToken")
    token_type = data.get("token_type") or data.get("tokenType") or "Bearer"
    if not token:
        raise RuntimeError("토큰 응답이 없습니다.")
    return f"{token_type} {token}"


def _extract_rank_items(data: Any, *, max_count: int, exclude: set[str] | None = None) -> list[dict[str, Any]]:
    items: list[Any] = []
    if isinstance(data, Mapping):
        for key in ("response", "data", "body", "output", "output1", "output2", "movers", "items", "stock_list", "pred_pre_flu_rt_upper"):
            v = data.get(key)
            if isinstance(v, list):
                items = v; break
    elif isinstance(data, list):
        items = data
    out: list[dict[str, Any]] = []
    for it in items:
        if not isinstance(it, Mapping):
            continue
        tk_raw = it.get("ticker") or it.get("stk_cd") or it.get("symbol") or it.get("code") or it.get("isu_cd")
        if not tk_raw:
            continue
        tk = str(tk_raw).strip()
        if exclude and tk.zfill(6) in exclude:
            continue
        def fnum(x):
            try:
                from math import isnan
                v = float(x)
                return None if isnan(v) else v
            except Exception:
                return None
        out.append({
            "ticker": tk,
            "name": it.get("stk_nm") or it.get("name"),
            "change_pct": fnum(it.get("flu_rt") or it.get("change_pct")),
            "current_price": fnum(it.get("cur_prc") or it.get("price")),
            "base_price": fnum(it.get("base_pric")),
        })
        if len(out) >= max_count:
            break
    return out


def _fetch_top_movers_kiwoom(market: str, count: int, *, use_mock: bool = False) -> list[dict[str, Any]]:
    _load_env_fallback()
    base_key = "KIWOOM_MOCK_BASE" if use_mock else "KIWOOM_BASE"
    base = os.getenv(base_key)
    if not base:
        raise RuntimeError(f"{base_key} 환경변수가 필요합니다")
    appkey = os.getenv("KIWOOM_APPKEY"); secret = os.getenv("KIWOOM_SECRETKEY")
    if not appkey or not secret:
        raise RuntimeError("KIWOOM_APPKEY/KIWOOM_SECRETKEY 환경변수가 필요합니다")
    endpoint = os.getenv("KIWOOM_RANK_PATH", "/api/dostk/rank")
    tr_id = os.getenv("KIWOOM_RANK_TR_ID", "ka10027")
    # TR ID/API ID 오타 보정: ka100027 -> ka10027
    def _norm_tid(x: str | None) -> str | None:
        try:
            return "ka10027" if (x or "").strip().lower() == "ka100027" else x
        except Exception:
            return x
    tr_id = _norm_tid(tr_id) or "ka10027"
    market_map = {"KOSPI": "001", "KOSDAQ": "101", "ALL": "000"}
    mrkt_code = market_map.get(market.upper(), "000")
    body_snake = {
        "mrkt_tp": mrkt_code,
        "sort_tp": os.getenv("KIWOOM_RANK_SORT_TP", "1"),
        "trde_qty_cnd": os.getenv("KIWOOM_RANK_TRDE_QTY_CND", "0000"),
        "stk_cnd": os.getenv("KIWOOM_RANK_STK_CND", "0"),
        "crd_cnd": os.getenv("KIWOOM_RANK_CRD_CND", "0"),
        "updown_incls": os.getenv("KIWOOM_RANK_UPDOWN_INCLS", "1"),
        "pric_cnd": os.getenv("KIWOOM_RANK_PRIC_CND", "0"),
        "trde_prica_cnd": os.getenv("KIWOOM_RANK_TRDE_PRICA_CND", "0"),
        "stex_tp": os.getenv("KIWOOM_RANK_STEX_TP", "1"),
    }
    def cam(k: str) -> str:
        parts = k.split("_"); return parts[0] + "".join(p.capitalize() for p in parts[1:])
    body_camel = { cam(k): v for k, v in body_snake.items() }
    sess = requests.Session()
    try:
        authz = _issue_token(sess, base, appkey, secret)
        def try_get(params):
            try:
                url = urljoin(base.rstrip("/"), endpoint)
                api_id = os.getenv("KIWOOM_API_ID") or os.getenv("KIWOOM_RANK_API_ID") or tr_id
                api_id = _norm_tid(api_id) or api_id
                h = {"tr_id": tr_id, "api-id": api_id, "authorization": authz}
                r = sess.get(url, headers=h, params=params, timeout=15)
                r.raise_for_status(); return r.json()
            except Exception:
                return None
        def try_post(payload):
            try:
                api_id = os.getenv("KIWOOM_API_ID") or os.getenv("KIWOOM_RANK_API_ID") or tr_id
                api_id = _norm_tid(api_id) or api_id
                h = {"Content-Type": "application/json;charset=UTF-8", "tr_id": tr_id, "api-id": api_id, "authorization": authz}
                return _post(sess, base, endpoint, headers=h, body=payload, timeout=15)
            except Exception:
                return None
        data = (
            try_get(body_snake) or try_get(body_camel) or try_post(body_snake) or try_post(body_camel) or try_post({"rq": body_snake}) or try_post({"rq": body_camel})
        )
        # 디버그 로깅 및 원본 저장
        if _debug_enabled():
            try:
                keys = list(data.keys()) if isinstance(data, dict) else type(data).__name__
                rc = data.get("return_code") if isinstance(data, dict) else None
                rm = data.get("return_msg") if isinstance(data, dict) else None
                print(f"[s0:kiwoom] keys={keys} return_code={rc} return_msg={rm}")
                raw_path = _project_root() / "data" / "raws" / "kiwoom_rank_raw.json"
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"[s0:kiwoom] raw saved -> {raw_path}")
            except Exception:
                pass
        return _extract_rank_items(data, max_count=count, exclude=_load_etf_set())
    finally:
        sess.close()


# -------- 메인 실행부 --------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Select top movers via pykrx or Kiwoom")
    p.add_argument("--source", choices=["pykrx", "kiwoom", "auto"], default="kiwoom", help="Top mover source (auto/pykrx/kiwoom)")
    p.add_argument("--date", default=datetime.now().strftime("%Y%m%d"), help="기준일 (YYYYMMDD)")
    p.add_argument("--market", default="ALL", help="시장 (KOSPI, KOSDAQ, ALL)")
    p.add_argument("--count", type=int, default=5, help="선정 종목 수")
    p.add_argument("--kiwoom-use-mock", action="store_true")
    p.add_argument("--output", type=Path)
    # CLI에서 Kiwoom 환경을 직접 주입할 수 있도록(옵션)
    p.add_argument("--kiwoom-base"); p.add_argument("--kiwoom-appkey"); p.add_argument("--kiwoom-secret")
    p.add_argument("--kiwoom-rank-path"); p.add_argument("--kiwoom-rank-trid"); p.add_argument("--kiwoom-api-id")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    today = datetime.now().strftime("%Y%m%d")
    try:
        date_for_pykrx = _find_latest_trading_date(args.date)
    except Exception:
        date_for_pykrx = args.date

    # .env 주입(필요 시) + CLI->env 반영
    _load_env_fallback()
    if args.kiwoom_base: os.environ["KIWOOM_BASE"] = args.kiwoom_base
    if args.kiwoom_appkey: os.environ["KIWOOM_APPKEY"] = args.kiwoom_appkey
    if args.kiwoom_secret: os.environ["KIWOOM_SECRETKEY"] = args.kiwoom_secret
    if args.kiwoom_rank_path: os.environ["KIWOOM_RANK_PATH"] = args.kiwoom_rank_path
    if args.kiwoom_rank_trid: os.environ["KIWOOM_RANK_TR_ID"] = args.kiwoom_rank_trid
    if args.kiwoom_api_id: os.environ["KIWOOM_API_ID"] = args.kiwoom_api_id

    use_source = args.source
    if args.source != "pykrx":
        try:
            entries = _fetch_top_movers_kiwoom(args.market, args.count, use_mock=args.kiwoom_use_mock)
            asof = today
            use_source = "kiwoom"
        except Exception as exc:
            print(f"Error fetching from Kiwoom direct API: {exc}", file=sys.stderr)
            try:
                entries = _fetch_top_movers_pykrx(date_for_pykrx, args.market, args.count)
                asof = date_for_pykrx
                use_source = "pykrx"
                print("[s0_discover] Fallback to pykrx succeeded.")
            except Exception as exc2:
                print(f"Error fetching from pykrx (fallback): {exc2}", file=sys.stderr)
                return 1
        # Kiwoom 응답이 비어있는 경우에도 pykrx로 폴백 시도
        if not entries:
            if _debug_enabled():
                print("[s0:kiwoom] empty list; trying pykrx fallback")
            try:
                entries = _fetch_top_movers_pykrx(date_for_pykrx, args.market, args.count)
                asof = date_for_pykrx
                use_source = "pykrx"
                print("[s0_discover] Fallback to pykrx succeeded (empty kiwoom).")
            except Exception as exc2:
                print(f"Error fetching from pykrx (fallback after empty kiwoom): {exc2}", file=sys.stderr)
                # 비어있지만 최소한 스키마는 유지해 저장
    else:
        try:
            entries = _fetch_top_movers_pykrx(date_for_pykrx, args.market, args.count)
            asof = date_for_pykrx
            use_source = "pykrx"
        except Exception as exc:
            print(f"Error fetching from pykrx: {exc}", file=sys.stderr)
            return 1

    # 이름 보강(pykrx + CSV)
    _annotate_names(entries, date_for_pykrx)
    _enrich_names_from_csv(entries, _project_root() / "data" / "dart_corpcode.csv")

    # details 스키마 정규화
    for e in entries:
        for k in ("change_pct", "current_price", "base_price"):
            e.setdefault(k, None)

    etf_set_final = _load_etf_set()
    entries = [e for e in entries if not _is_structured_product(e, etf_set_final)]
    entries = entries[: args.count]

    tickers = [str(e.get("ticker")) for e in entries if e.get("ticker")]
    output_path = Path(args.output) if args.output else (_project_root() / "data" / "raw" / f"top_movers_{today}.json")
    try:
        generated_at = datetime.now(ZoneInfo("Asia/Seoul")).isoformat() if ZoneInfo else datetime.now(timezone.utc).isoformat()
    except Exception:
        generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "date": today,
        "market": args.market,
        "count": len(tickers),
        "tickers": tickers,
        "source": use_source,
        "generated_at": generated_at,
        "details": entries,
        "meta": {"description": "Top mover discovery results across the requested market."},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"Top movers saved to {output_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print("An unexpected error occurred in top_movers.py:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise SystemExit(1)
