"""CLI entrypoint for the stage-00 data collection pipeline."""

from __future__ import annotations

import argparse
import os  # 환경변수 사용을 위해 os 모듈 추가
import json
import sys
from datetime import datetime
import csv
from importlib import import_module
from pathlib import Path
from typing import Dict, Mapping, Sequence

# 모듈 단독 실행 시에도 패키지 임포트가 가능하도록 경로를 보정한다
if __package__ in (None, ""):
    start = Path(__file__).resolve()
    project_root = next((parent for parent in start.parents if (parent / "Python").exists()), start.parents[4])
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    def _stage_import(name: str):
        try:
            return import_module(f"Python.pipeline.pipelines.s1_collect.{name}")
        except ModuleNotFoundError:
            return import_module(f"python.pipeline.pipelines.s1_collect.{name}")

    dart_client = _stage_import("dart_client")
    pykrx_loader = _stage_import("pykrx_loader")
    # 공통 유틸리티 임포트
    kiwoom_api = _stage_import("kiwoom_client")
else:
    from . import dart_client, pykrx_loader
    from . import kiwoom_client as kiwoom_api


# CLI 진입점 ---------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    summaries: Dict[str, Mapping[str, list[Path]]] = {}

    # 기본 pykrx 수집
    pykrx_ticks = args.tickers if args.tickers else []
    if not args.skip_pykrx:
        summaries["pykrx"] = pykrx_loader.run(
            tickers=pykrx_ticks,
            start_date=args.start_date,
            end_date=args.end_date,
            raw_dir=args.raw_dir,
            include_minute=args.include_minute,
            minute_freq=args.minute_freq,
            include_trading_value=args.include_trading_value,
            investors=args.investors,
            index_codes=args.index_codes,
            adjusted=not args.no_adjust,
        )

    # DART 재무제표 수집 옵션
    if args.with_dart:
        corp_codes = list(args.corp_codes or [])
        if not corp_codes:
            # 제공된 ticker 목록을 기반으로 DART corp_code 자동 매핑
            # (data/dart_corpcode.csv 또는 DART corpCode.xml을 사용)
            corp_codes = _auto_resolve_corp_codes_base(args.tickers)
        if not corp_codes:
            parser.error("--with-dart 사용 시 corp-codes를 지정하거나 data/dart_corpcode.csv에 매핑을 준비해 주세요.")
        # 최신 보고서만 기본 사용. --reprt-codes로 명시되면 우선.
        _reprt = list(args.reprt_codes) if args.reprt_codes else None
        if not args.single_accounts:
            args.single_accounts = [
                "당기순이익",
                "자산총계",
                "부채총계",
                "자본총계",
                "유동자산",
                "유동부채",
                "재고자산",
            ]
        # Force standard single-accounts (ensure UTF-8 correctness)
        args.single_accounts = [
            "당기순이익",
            "자산총계",
            "부채총계",
            "자본총계",
            "유동자산",
            "유동부채",
            "재고자산",
        ]
        summaries["dart"] = dart_client.fetch_filings(
            corp_codes=corp_codes,
            year=args.dart_year or datetime.now().year,
            raw_dir=args.raw_dir,
            reprt_codes=_reprt,
            fs_div=args.fs_div,
            pause=args.dart_pause,
            single_accounts=args.single_accounts,
        )

    # 키움 REST 수집 옵션
    if args.with_kiwoom:
        kiwoom_tickers = args.kiwoom_tickers or pykrx_ticks
        if not kiwoom_tickers:
            parser.error("Kiwoom 호출에 사용할 티커가 없습니다. --tickers 또는 --kiwoom-tickers 를 확인하세요.")
        summaries["kiwoom"] = kiwoom_api.fetch_quotes(
            tickers=kiwoom_tickers,
            start_date=args.start_date,
            end_date=args.end_date,
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


# 인자 정의 ---------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage-00 data collection (pykrx / DART / Kiwoom)",
    )
    parser.add_argument("--tickers", nargs="*", default=[], help="기본으로 사용할 종목 코드 목록")
    parser.add_argument("--start-date", required=True, help="조회 시작일 (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="조회 종료일 (YYYY-MM-DD)")
    parser.add_argument("--raw-dir", type=Path, default=None, help="저장 루트 (기본: data/raw)")

    parser.add_argument("--include-minute", action="store_true", help="pykrx 분봉 수집 여부")
    parser.add_argument("--minute-freq", default="1m", help="pykrx 분봉 주기")
    parser.add_argument("--include-trading-value", action="store_true", help="투자주체 매매대금 수집")
    parser.add_argument("--investors", nargs="*", help="투자주체 목록 (미지정 시 기본값 사용)")
    parser.add_argument("--index-codes", nargs="*", help="지수 코드 (미지정 시 KOSPI/KOSDAQ)")
    parser.add_argument("--no-adjust", action="store_true", help="일봉 조회 시 조정주가 미사용")
    parser.add_argument("--skip-pykrx", action="store_true", help="pykrx 수집 생략")

    parser.add_argument("--with-dart", action="store_true", help="DART 데이터 수집 실행")
    parser.add_argument("--corp-codes", nargs="*", help="DART 법인번호 목록")
    parser.add_argument("--dart-year", type=int, help="DART 조회 연도 (기본: 올해)")
    parser.add_argument("--reprt-codes", nargs="*", help="DART 보고서 코드 목록")
    parser.add_argument("--fs-div", default="CFS", help="연결/별도 구분 (CFS/OFS)")
    parser.add_argument("--dart-pause", type=float, default=0.25, help="DART 호출 대기 시간")
    parser.add_argument("--single-accounts", nargs="*", help="fnlttSinglAcntAll 계정명 목록")

    parser.add_argument("--with-kiwoom", action="store_true", help="Kiwoom REST 호출 실행")
    parser.add_argument("--kiwoom-tickers", nargs="*", help="Kiwoom 조회용 종목 코드 (미지정 시 tickers 재사용)")
    parser.add_argument("--kiwoom-use-mock", action="store_true", help="Mock 게이트웨이 사용")
    parser.add_argument("--include-intraday", action="store_true", help="Kiwoom 분봉 수집")
    parser.add_argument("--intraday-freq", default="1m", help="Kiwoom 분봉 주기")
    parser.add_argument("--intraday-count", type=int, default=390, help="Kiwoom 분봉 개수")
    parser.add_argument("--include-kiwoom-financials", action="store_true", help="Kiwoom 재무제표 수집")
    parser.add_argument("--include-kiwoom-ratios", action="store_true", help="Kiwoom 재무비율 수집")
    parser.add_argument("--start-time", default="090000", help="Kiwoom 분봉 시작 시각")
    parser.add_argument("--end-time", default="153000", help="Kiwoom 분봉 종료 시각")
    parser.add_argument("--kiwoom-pause", type=float, default=0.2, help="Kiwoom 호출 대기 시간")

    return parser


# 실행 결과를 사람이 읽기 쉬운 JSON으로 출력 ------------------------------------------------


def _print_summary(summary: Mapping[str, Mapping[str, Sequence[Path]]]) -> None:
    output = {}
    for provider, result in summary.items():
        output[provider] = {
            key: [str(path) for path in paths]
            for key, paths in result.items()
        }
    if not output:
        print("No collectors executed. Check your flags.")
        return
    print("Collection summary:")
    print(json.dumps(output, ensure_ascii=False, indent=2))


def _auto_resolve_corp_codes(tickers: Sequence[str] | None) -> list[str]:
    """data/dart_corpcode.csv에서 ticker(=stock_code)로 corp_code를 찾는다.

    가능한 헤더명: ticker, code, stock_code, symbol, corp_code, corpcode 등.
    제공된 tickers에 해당하는 corp_code 리스트를 반환하며, 매칭 실패는 건너뛴다.
    """
    try:
        start = Path(__file__).resolve()
        project_root = next((p for p in start.parents if (p / "data").exists()), start.parents[4])
        path = project_root / "data" / "dart_corpcode.csv"
        if not path.exists() or not tickers:
            return []
        def _norm(code: object) -> str:
            raw = str(code or "").strip()
            digits = "".join(ch for ch in raw if ch.isdigit())
            return digits.zfill(6) if digits else raw.zfill(6)

        want = [_norm(t) for t in tickers]
        mapping: dict[str, str] = {}
        with path.open("r", encoding="utf-8") as fp:
            reader = csv.DictReader(fp)
            headers = {h.lower(): h for h in (reader.fieldnames or [])}
            t_col = headers.get("ticker") or headers.get("stock_code") or headers.get("code") or headers.get("symbol")
            c_col = headers.get("corp_code") or headers.get("corpcode") or headers.get("corpcode_id") or headers.get("corp")
            if not t_col or not c_col:
                for row in reader:
                    vals = list(row.values())
                    if len(vals) >= 2:
                        t = _norm(vals[0])
                        c = str(vals[1]).strip()
                        if t and c:
                            mapping[t] = c
            else:
                for row in reader:
                    t = _norm(row.get(t_col, ""))
                    c = str(row.get(c_col, "")).strip()
                    if t and c:
                        mapping[t] = c
        return [mapping[t] for t in want if t in mapping]
    except Exception:
        return []


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


def _auto_resolve_corp_codes_base(tickers: Sequence[str] | None) -> list[str]:
    """Resolve corp_code by normalizing any ticker to base stock_code (last digit '0').

    - Extract digits, pad to 6, then force last digit to '0' (common stock).
    - Look up in data/dart_corpcode.csv first; if missing and DART_API_KEY exists,
      download corpCode.xml and build stock_code->corp_code map.
    """
    if not tickers:
        return []
    def base(code: object) -> str:
        raw = str(code or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            return raw.zfill(6)
        d = digits.zfill(6)
        return d[:-1] + '0'
    want = [base(t) for t in tickers]
    mapping: dict[str, str] = {}
    try:
        start = Path(__file__).resolve()
        project_root = next((p for p in start.parents if (p / "data").exists()), start.parents[4])
        csv_path = project_root / "data" / "dart_corpcode.csv"
        if csv_path.exists():
            with csv_path.open("r", encoding="utf-8") as fp:
                reader = csv.DictReader(fp)
                headers = {h.lower(): h for h in (reader.fieldnames or [])}
                t_col = headers.get("ticker") or headers.get("stock_code") or headers.get("code") or headers.get("symbol")
                c_col = headers.get("corp_code") or headers.get("corpcode") or headers.get("corpcode_id") or headers.get("corp")
                if not t_col or not c_col:
                    for row in reader:
                        vals = list(row.values())
                        if len(vals) >= 2:
                            t = base(vals[0])
                            c = str(vals[1]).strip()
                            if t and c:
                                mapping[t] = c
                else:
                    for row in reader:
                        t = base(row.get(t_col, ""))
                        c = str(row.get(c_col, "")).strip()
                        if t and c:
                            mapping[t] = c
    except Exception:
        pass
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

def _auto_resolve_corp_codes_v2(tickers: Sequence[str] | None) -> list[str]:
    """ticker(=stock_code) -> corp_code 매핑을 CSV 또는 DART API로 자동 해석.

    우선순위: data/dart_corpcode.csv -> DART corpCode.xml(네트워크)
    - 지원 컬럼명: ticker, code, stock_code, symbol / corp_code, corpcode, corpcode_id, corp
    - 우선주 등 영문 포함 티커는 숫자만 추출해 6자리로 정규화
    """
    if not tickers:
        return []

    def _base(code: object) -> str:
        raw = str(code or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            return raw.zfill(6)
        d = digits.zfill(6)
        # DART 매핑 전용 규칙: 보통주 stock_code로 검색하기 위해 끝자리를 0으로 정규화  # 한글 주석
        return d[:-1] + '0'

    want = [_base(t) for t in tickers]
    mapping: dict[str, str] = {}
    try:
        start = Path(__file__).resolve()
        project_root = next((p for p in start.parents if (p / "data").exists()), start.parents[4])
        path = project_root / "data" / "dart_corpcode.csv"
        if path.exists():
            with path.open("r", encoding="utf-8") as fp:
                reader = csv.DictReader(fp)
                headers = {h.lower(): h for h in (reader.fieldnames or [])}
                t_col = headers.get("ticker") or headers.get("stock_code") or headers.get("code") or headers.get("symbol")
                c_col = headers.get("corp_code") or headers.get("corpcode") or headers.get("corpcode_id") or headers.get("corp")
                if not t_col or not c_col:
                    for row in reader:
                        vals = list(row.values())
                        if len(vals) >= 2:
                            t = _base(vals[0])
                            c = str(vals[1]).strip()
                            if t and c:
                                mapping[t] = c
                else:
                    for row in reader:
                        t = _base(row.get(t_col, ""))
                        c = str(row.get(c_col, "")).strip()
                        if t and c:
                            mapping[t] = c
    except Exception:
        pass

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
    """DART corpCode.xml(Zip)을 내려받아 stock_code -> corp_code 매핑을 만든다."""
    import requests  # lazy import
    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    resp = requests.get(url, params={"crtfc_key": api_key}, timeout=30)
    resp.raise_for_status()
    import zipfile, io, xml.etree.ElementTree as ET
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

