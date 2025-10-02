# -*- coding: utf-8 -*-
"""s1_collect 단계 CLI (UTF-8).

기능 요약
- pykrx 기본 수집 (일봉/시가총액/펀더멘털)
- 선택적으로 DART 재무제표 수집 (우선주→보통주 끝자리 0 매핑, corp_code 자동해결)
- 결과 요약 출력(JSON)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from importlib import import_module
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Mapping, Sequence


def _project_root() -> Path:
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "Python").exists() or (p / "data").exists() or (p / ".env").exists():
            return p
    return here.parents[4]


# 패키지 동적 임포트 (경로 문제 방지)
def _stage_import(name: str):
    try:
        return import_module(f"Python.pipeline.pipelines.s1_collect.{name}")
    except ModuleNotFoundError:
        return import_module(f"python.pipeline.pipelines.s1_collect.{name}")


dart_client = _stage_import("dart_client")
pykrx_loader = _stage_import("pykrx_loader")
kiwoom_api = _stage_import("kiwoom_client")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    # 한글: 시작/종료 기본값 보정
    today_dt = datetime.now()
    today = today_dt.strftime("%Y-%m-%d")
    # 시작일 미지정 시 최근 10년
    _start_date = args.start_date or (today_dt - timedelta(days=365*10)).strftime("%Y-%m-%d")
    # 종료일 미지정 시 오늘
    _end_date = args.end_date or today

    summaries: Dict[str, Mapping[str, list[Path]]] = {}

    # 1) pykrx 기본 수집 (skip_pykrx 미지정 시)
    base_tickers = list(args.tickers or [])
    if not args.skip_pykrx:
        summaries["pykrx"] = pykrx_loader.run(
            tickers=base_tickers,
            start_date=_start_date,
            end_date=_end_date,
            raw_dir=args.raw_dir,
            include_minute=args.include_minute,
            minute_freq=args.minute_freq,
            include_trading_value=args.include_trading_value,
            investors=args.investors,
            index_codes=args.index_codes,
            adjusted=not args.no_adjust,
        )

    # 2) DART 재무제표 수집 (선택)
    auto_dart = (os.getenv("DART_AUTO") == "1") or ((_project_root() / "data" / "dart_corpcode.csv").exists())
    if args.with_dart or auto_dart:
        corp_codes = list(args.corp_codes or [])
        # 전달된 corp_codes가 일부만 있을 수 있으므로 자동 매핑으로 보강
        try:
            extra = _auto_resolve_corp_codes_base(args.tickers)
            if extra:
                corp_codes = list(dict.fromkeys([*(corp_codes or []), *extra]))
        except Exception:
            pass
        if not corp_codes:
            parser.error("--with-dart 사용 시 corp-codes가 없고 자동 매핑도 실패했습니다. data/dart_corpcode.csv 준비 또는 DART_API_KEY 설정이 필요합니다.")

        _reprt = list(args.reprt_codes) if args.reprt_codes else None
        single_accounts = list(args.single_accounts) if args.single_accounts else [
            "당기순이익", "자산총계", "부채총계", "자본총계", "유동자산", "유동부채", "재고자산",
        ]
        summaries["dart"] = dart_client.fetch_filings(
            corp_codes=corp_codes,
            year=args.dart_year or datetime.now().year,
            raw_dir=args.raw_dir,
            reprt_codes=_reprt,
            fs_div=args.fs_div,
            pause=args.dart_pause,
            single_accounts=single_accounts,
        )

    # 3) (옵션) Kiwoom REST 수집
    if args.with_kiwoom:
        kt = list(args.kiwoom_tickers or base_tickers)
        if not kt:
            parser.error("--with-kiwoom 사용 시 조회할 종목이 필요합니다.")
        summaries["kiwoom"] = kiwoom_api.fetch_quotes(
            tickers=kt,
            start_date=_start_date,
            end_date=_end_date,
            raw_dir=args.raw_dir,
            include_intraday=args.include_intraday,
            intraday_freq=args.intraday_freq,
            intraday_count=args.intraday_count,
            include_financials=args.include_kiwoom_financials,
            include_ratios=args.include_kiwoom_ratios,
            use_mock=args.kiwoom_use_mock,
            start_time=args.start_time,
            end_time=args.end_time,
            pause=args.kiwoom_pause,
        )

    _print_summary(summaries)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Stage-1: Collect raw data (pykrx / DART / Kiwoom)")
    # 공통
    p.add_argument("--tickers", nargs="*", default=[])
    p.add_argument("--start-date")
    p.add_argument("--end-date")
    p.add_argument("--raw-dir")

    # pykrx
    p.add_argument("--skip-pykrx", action="store_true")
    p.add_argument("--include-minute", action="store_true")
    p.add_argument("--minute-freq", default="1m")
    p.add_argument("--include-trading-value", action="store_true")
    p.add_argument("--investors", nargs="*")
    p.add_argument("--index-codes", nargs="*")
    p.add_argument("--no-adjust", action="store_true")

    # DART
    p.add_argument("--with-dart", action="store_true")
    p.add_argument("--corp-codes", nargs="*")
    p.add_argument("--dart-year", type=int)
    p.add_argument("--reprt-codes", nargs="*")
    p.add_argument("--fs-div", default="CFS")
    p.add_argument("--dart-pause", type=float, default=0.25)
    p.add_argument("--single-accounts", nargs="*")

    # Kiwoom
    p.add_argument("--with-kiwoom", action="store_true")
    p.add_argument("--kiwoom-tickers", nargs="*")
    p.add_argument("--kiwoom-use-mock", action="store_true")
    p.add_argument("--include-intraday", action="store_true")
    p.add_argument("--intraday-freq", default="1m")
    p.add_argument("--intraday-count", type=int, default=390)
    p.add_argument("--include-kiwoom-financials", action="store_true")
    p.add_argument("--include-kiwoom-ratios", action="store_true")
    p.add_argument("--start-time", default="090000")
    p.add_argument("--end-time", default="153000")
    p.add_argument("--kiwoom-pause", type=float, default=0.2)
    return p


def _print_summary(summary: Mapping[str, Mapping[str, Sequence[Path]]]) -> None:
    output = {}
    for provider, result in summary.items():
        output[provider] = {k: [str(p) for p in v] for k, v in result.items()}
    print("Collection summary:")
    print(json.dumps(output, ensure_ascii=False, indent=2))


def _auto_resolve_corp_codes_base(tickers: Sequence[str] | None) -> list[str]:
    """우선주 코드를 보통주(끝자리 0)로 정규화해 corp_code 매핑.

    우선순위: data/dart_corpcode.csv -> (있고 DART_API_KEY도 있으면) corpCode.xml 다운로드 병합.
    """
    if not tickers:
        return []

    def _base(code: object) -> str:
        raw = str(code or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            return raw.zfill(6)
        d = digits.zfill(6)
        return d[:-1] + '0'

    want = [_base(t) for t in tickers]
    mapping: dict[str, str] = {}
    root = _project_root()
    csv_path = root / "data" / "dart_corpcode.csv"
    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8-sig", errors="ignore") as fp:
            rdr = csv.DictReader(fp)
            headers = { (h or "").strip().lower(): (h or "").strip() for h in (rdr.fieldnames or []) }
            t_col = headers.get("stock_code") or headers.get("ticker") or headers.get("code") or headers.get("symbol")
            c_col = headers.get("corp_code") or headers.get("corpcode") or headers.get("corpcode_id") or headers.get("corp")

            def _pick_stock_code(row: dict) -> str:
                if t_col and row.get(t_col):
                    return _base(row.get(t_col, ""))
                for v in row.values():
                    s = str(v or "").strip()
                    d = "".join(ch for ch in s if ch.isdigit())
                    if len(d) == 6:
                        return _base(d)
                return ""

            def _pick_corp_code(row: dict) -> str:
                if c_col and row.get(c_col):
                    return str(row.get(c_col, "")).strip()
                for v in row.values():
                    s = str(v or "").strip()
                    d = "".join(ch for ch in s if ch.isdigit())
                    if len(d) == 8:
                        return d
                return ""

            for row in rdr:
                try:
                    t = _pick_stock_code(row)
                    c = _pick_corp_code(row)
                    if t and c:
                        mapping[t] = c
                except Exception:
                    continue

    unresolved = [t for t in want if t not in mapping]
    api_key = os.getenv("DART_API_KEY")
    if unresolved and api_key:
        try:
            api_map = _download_corpcode_lookup(api_key)
            for t in unresolved:
                corp = api_map.get(t)
                if corp:
                    mapping[t] = corp
        except Exception:
            pass
    return [mapping[t] for t in want if t in mapping]


def _download_corpcode_lookup(api_key: str) -> dict[str, str]:
    import requests, zipfile, io, xml.etree.ElementTree as ET
    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    resp = requests.get(url, params={"crtfc_key": api_key}, timeout=30)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        name = next((n for n in zf.namelist() if n.lower().endswith(".xml")), None)
        if not name:
            return {}
        xml_bytes = zf.read(name)
    root = ET.fromstring(xml_bytes)
    out: dict[str, str] = {}
    for el in root.findall("list"):
        corp_code = (el.findtext("corp_code") or "").strip()
        stock_code = (el.findtext("stock_code") or "").strip()
        if stock_code and corp_code:
            out[stock_code] = corp_code
    return out


if __name__ == "__main__":
    raise SystemExit(main())
