# -*- coding: utf-8 -*-
"""s0(탐색) 스테이지를 간편 실행하는 스크립트.

사용 예시(프로젝트 루트에서 실행):
  python scripts/run_s0.py --source kiwoom --market KOSPI --count 5 --date 20250929 --output data/raws/top_movers_auto.json
  python scripts/run_s0.py --source pykrx  --market KOSPI --count 5 --date 20250929 --output data/raws/top_movers_auto.json
  python scripts/run_s0.py --source auto   --market KOSPI --count 5 --date 20250929 --output data/raws/top_movers_auto.json
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Ensure .env is loaded (UTF-8-SIG) for KIWOOM_* when running scripts directly
try:
    from Python.pipeline.utils.env import load_dotenv_utf8sig, sanitize_environ_bom
except Exception:
    def load_dotenv_utf8sig() -> None:  # type: ignore
        return None
    def sanitize_environ_bom() -> None:  # type: ignore
        return None
try:
    load_dotenv_utf8sig()
    sanitize_environ_bom()
except Exception:
    pass


def run_cmd(cmd: list[str]) -> int:
    return subprocess.call(cmd)


def main(argv: list[str] | None = None) -> int:
    # 한글 도움말 정상화 및 source=auto 허용
    p = argparse.ArgumentParser(description="s0_discover(탐색) 일괄 실행")
    p.add_argument("--source", choices=["pykrx", "kiwoom", "auto"], default="kiwoom", help="탐색 소스(auto/pykrx/kiwoom)")
    p.add_argument("--market", default="KOSPI", help="시장(KOSPI/KOSDAQ/ALL)")
    p.add_argument("--count", type=int, default=5, help="종목 개수")
    p.add_argument("--date", default=datetime.now().strftime("%Y%m%d"), help="기준일(YYYYMMDD)")
    p.add_argument("--output", default="data/raws/top_movers_auto.json", help="출력 JSON 경로")
    # Kiwoom 자격/엔드포인트 전달 옵션(없으면 .env에서 읽음)
    p.add_argument("--kiwoom-base", help="Kiwoom REST base URL (예: https://gw.example)")
    p.add_argument("--kiwoom-appkey", help="Kiwoom APPKEY")
    p.add_argument("--kiwoom-secret", help="Kiwoom SECRETKEY")
    p.add_argument("--kiwoom-rank-path", help="Kiwoom 랭킹 API 경로(ka10027 매핑)")
    p.add_argument("--kiwoom-rank-trid", help="Kiwoom 랭킹 TR ID(기본 ka10027)")
    p.add_argument("--kiwoom-api-id", help="요청 헤더 api-id 강제값")
    p.add_argument("--kiwoom-use-mock", action="store_true", help="Kiwoom 모의 서버 사용(.env 필요)")
    args = p.parse_args(argv)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    base_cmd = [
        sys.executable,
        "-m",
        "Python.pipeline.pipelines.s0_discover.top_movers",
        "--market",
        args.market,
        "--count",
        str(args.count),
        "--date",
        args.date,
        "--output",
        str(out),
    ]

    # 공통: Kiwoom 관련 인자 구성(지정된 경우만 전달)
    def kiwoom_args() -> list[str]:
        args_list: list[str] = []
        if args.kiwoom_base:
            args_list += ["--kiwoom-base", args.kiwoom_base]
        if args.kiwoom_appkey:
            args_list += ["--kiwoom-appkey", args.kiwoom_appkey]
        if args.kiwoom_secret:
            args_list += ["--kiwoom-secret", args.kiwoom_secret]
        if args.kiwoom_rank_path:
            args_list += ["--kiwoom-rank-path", args.kiwoom_rank_path]
        if args.kiwoom_rank_trid:
            args_list += ["--kiwoom-rank-trid", args.kiwoom_rank_trid]
        if args.kiwoom_api_id:
            args_list += ["--kiwoom-api-id", args.kiwoom_api_id]
        if args.kiwoom_use_mock:
            args_list += ["--kiwoom-use-mock"]
        return args_list

    # 소스별 분기: kiwoom → 실패시 pykrx 백업, auto → 그대로 전달(+키움 인자), pykrx → 그대로 실행
    if args.source == "kiwoom":
        code = run_cmd(base_cmd + ["--source", "kiwoom", *kiwoom_args()])
        if code != 0:
            print("[run_s0] Kiwoom 실패 → pykrx로 백업합니다", file=sys.stderr)
            code = run_cmd(base_cmd + ["--source", "pykrx"])
        return code
    if args.source == "auto":
        return run_cmd(base_cmd + ["--source", "auto", *kiwoom_args()])
    return run_cmd(base_cmd + ["--source", "pykrx"])


if __name__ == "__main__":
    raise SystemExit(main())
