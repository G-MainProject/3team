# -*- coding: utf-8 -*-
"""s0 결과(top_movers JSON)를 받아 s1~s5 전체를 일괄 실행하는 스크립트.

사용 예시(프로젝트 루트에서 실행):
  python scripts/run_s1_to_s5.py --top-movers data/raws/top_movers_auto.json --close-values data/gold/test/close.npy
  python scripts/run_s1_to_s5.py --top-movers data/raws/top_movers_auto.json --skip-s1
  python scripts/run_s1_to_s5.py --top-movers data/raws/top_movers_auto.json --skip-s3 --infer-model Python/pipeline/artifacts/models/model_best.pth
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
import os
import csv


def run_cmd(cmd: list[str]) -> int:
    # 한글: 하위 프로세스 실행 유틸리티
    return subprocess.call(cmd)


def run_cmd_env(cmd: list[str], extra_env: dict | None = None) -> int:
    # 한글: 환경변수 주입하여 실행
    env = os.environ.copy()
    if extra_env:
        env.update({k: str(v) for k, v in extra_env.items()})
    try:
        proc = subprocess.run(cmd, env=env)
        return int(proc.returncode)
    except Exception:
        return subprocess.call(cmd)


def _has_dart_corp_codes(tickers: list[str]) -> bool:
    # 한글: data/dart_corpcode.csv에서 대상 티커 중 일부라도 매핑 가능한지 확인
    csv_path = Path("data/dart_corpcode.csv")
    if not csv_path.exists():
        return False
    def base(code: str) -> str:
        d = "".join(ch for ch in str(code) if ch.isdigit()).zfill(6)
        return d[:-1] + '0' if d else d
    want = {base(t) for t in tickers}
    try:
        with csv_path.open("r", encoding="utf-8", errors="ignore") as fp:
            rdr = csv.DictReader(fp)
            headers = { (h or "").strip().lower(): h for h in (rdr.fieldnames or []) }
            t_col = headers.get("stock_code") or headers.get("ticker") or headers.get("code") or headers.get("symbol")
            have: set[str] = set()
            for row in rdr:
                sc = (row.get(t_col, "") if t_col else "").strip()
                if sc:
                    have.add(base(sc))
        return any(t in have for t in want)
    except Exception:
        return False


def _load_tickers(path: Path) -> list[str]:
    """top_movers JSON에서 tickers 배열을 최대한 유연하게 로드한다.

    - 정상 JSON(dict) 포맷 우선 시도
    - 실패 시 원문에서 "tickers": [...] 패턴을 정규식으로 추출(깨진 JSON 대응)
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("tickers"), list):
            return [str(t) for t in data["tickers"]]
    except Exception:
        pass
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'"tickers"\s*:\s*\[(.*)\]', raw, flags=re.S)
        if m:
            inner = m.group(1)
            # 한글: 양쪽 따옴표/홑따옴표 제거 후 아이템 정제
            items = [x.strip().strip("\"'") for x in inner.split(',') if x.strip()]
            return [i for i in items if i]
    except Exception:
        pass
    return []


def main(argv: list[str] | None = None) -> int:
    # 한글: 인자 파서 생성
    p = argparse.ArgumentParser(description="기존 s0 결과 JSON으로 s1~s5 일괄 실행")
    p.add_argument(
        "--top-movers",
        dest="top_movers",
        type=Path,
        default=Path("data/raws/top_movers_auto.json"),
        help="s0 출력 JSON 경로 (기본: data/raws/top_movers_auto.json)",
    )
    p.add_argument("--skip-s1", action="store_true", help="s1 수집 단계 생략")
    p.add_argument("--skip-s3", action="store_true", help="s3 학습 단계 생략(기학모델 사용)")
    p.add_argument("--skip-s2", action="store_true", help="s2 전처리 단계 생략")
    p.add_argument("--skip-s4", action="store_true", help="s4 추론 단계 생략")
    p.add_argument("--skip-s5", action="store_true", help="s5 리포트 단계 생략")
    p.add_argument("--infer-model", type=Path, help="--skip-s3 시 사용할 학습된 모델 경로")
    p.add_argument(
        "--close-values",
        type=Path,
        default=Path("data/gold/test/close.npy"),
        help="추론/평가에 사용할 close.npy 경로",
    )
    p.add_argument("--preds", type=Path, default=Path("data/outputs/preds.json"), help="s4 추론 결과 경로")
    p.add_argument(
        "--actual-prices",
        type=Path,
        default=Path("data/outputs/actual_prices.npy"),
        help="s5 실제 가격 결과 경로",
    )
    p.add_argument(
        "--report",
        type=Path,
        default=Path("data/outputs/top_mover_forecast.json"),
        help="s5 리포트 출력 경로",
    )
    # 한글: 공통 수집/기간 옵션
    p.add_argument("--start-date")
    # 한글: 기본값은 오늘 날짜(YYYY-MM-DD). 명시 입력 시 그 값을 사용.
    p.add_argument("--end-date")
    # 한글: Kiwoom 옵션 (s1에 그대로 전달)
    p.add_argument("--with-kiwoom", action="store_true", help="s1에서 Kiwoom 수집 수행")
    p.add_argument("--include-kiwoom-financials", action="store_true")
    p.add_argument("--include-kiwoom-ratios", action="store_true")
    p.add_argument("--kiwoom-use-mock", action="store_true")
    p.add_argument("--include-intraday", action="store_true")
    p.add_argument("--intraday-freq", default="1m")
    p.add_argument("--intraday-count", type=int, default=390)
    # 한글: DART 옵션 전달(자동 corp_code 매핑 사용)
    p.add_argument("--with-dart", action="store_true")
    args = p.parse_args(argv)

    if not args.top_movers.exists():
        # 한글: 입력 파일 부재 안내 후 종료
        print(f"[run_s1_to_s5] top_movers 파일을 찾을 수 없습니다: {args.top_movers}", file=sys.stderr)
        return 1

    tickers = _load_tickers(args.top_movers)
    if not tickers:
        print(f"[run_s1_to_s5] tickers 목록이 비어 있습니다: {args.top_movers}", file=sys.stderr)
        return 1
    print("[run_s1_to_s5] Tickers:", ", ".join(tickers))

    # s1: 수집
    today_dt = datetime.now()
    today = today_dt.strftime("%Y-%m-%d")
    # 시작일 미지정 시 최근 10년, 종료일 미지정 시 오늘
    start_date = args.start_date or (today_dt - timedelta(days=365*10)).strftime("%Y-%m-%d")
    end_date = args.end_date or today
    if not args.skip_s1:
        s1 = [
            sys.executable,
            "-m",
            "Python.pipeline.pipelines.s1_collect.cli",
            "--tickers",
            *tickers,
            "--start-date", start_date,
            "--end-date", end_date,
        ]
        if args.with_kiwoom:
            s1.append("--with-kiwoom")
            if args.include_kiwoom_financials:
                s1.append("--include-kiwoom-financials")
            if args.include_kiwoom_ratios:
                s1.append("--include-kiwoom-ratios")
            if args.kiwoom_use_mock:
                s1.append("--kiwoom-use-mock")
            if args.include_intraday:
                s1 += ["--include-intraday", "--intraday-freq", args.intraday_freq, "--intraday-count", str(args.intraday_count)]
        # 자동 DART: .env DART_AUTO=1 또는 data/dart_corpcode.csv 존재 시 기본 ON
        auto_dart = (os.getenv("DART_AUTO") == "1") or (Path("data/dart_corpcode.csv").exists())
        use_dart = bool(args.with_dart or auto_dart)
        print("[run_s1_to_s5] s1 수집:", " ".join(s1))
        # 선택: DART 수집 (사전 매핑 가능 여부 확인)
        can_dart = _has_dart_corp_codes(tickers)
        if use_dart and not can_dart:
            print("[run_s1_to_s5] corpcode CSV에 매핑을 찾지 못해 DART 자동 비활성화", file=sys.stderr)
        use_dart = use_dart and can_dart
        env_ctrl = {"DART_AUTO": "1" if use_dart else "0"}
        if use_dart:
            s1_dart = s1 + ["--with-dart"]
            print("[run_s1_to_s5] s1 DART:", " ".join(s1_dart))
            rc = run_cmd_env(s1_dart, env_ctrl)
        else:
            rc = run_cmd_env(s1, env_ctrl)
        if rc != 0:
            print(f"[run_s1_to_s5] s1 실패(code={rc})", file=sys.stderr)
            return rc

    # s2: 전처리(병합/특징/데이터셋) – 반드시 tickers 전달
    if not args.skip_s2:
        s2 = [
            sys.executable,
            "-m",
            "Python.pipeline.pipelines.s2_preprocess",
            "--tickers",
            *tickers,
        ]
        print("[run_s1_to_s5] s2 전처리:", " ".join(s2))
        rc = run_cmd(s2)
        if rc != 0:
            print(f"[run_s1_to_s5] s2 실패(code={rc})", file=sys.stderr)
            return rc

    # s3: 학습(선택)
    if not args.skip_s3:
        s3 = [
            sys.executable,
            "-m",
            "Python.pipeline.pipelines.s3_model",
            "--train",
        ]
        if args.infer_model:
            # 이미 모델이 있으면 학습 생략을 권장하지만, 명시 시 무시
            pass
        print("[run_s1_to_s5] s3 학습:", " ".join(s3))
        rc = run_cmd(s3)
        if rc != 0:
            print(f"[run_s1_to_s5] s3 실패(code={rc})", file=sys.stderr)
            return rc

    # s4: 추론
    if not args.skip_s4:
        s4 = [
            sys.executable,
            "-m",
            "Python.pipeline.pipelines.s4_infer.predict",
            "--model",
            str(args.infer_model or Path("Python/pipeline/artifacts/models/model_best.pth")),
            "--input",
            str(Path("data/gold/test/X.npy")),
            "--output",
            str(args.preds),
        ]
        if args.close_values:
            s4 += ["--close-values", str(args.close_values)]
        print("[run_s1_to_s5] s4 추론:", " ".join(s4))
        rc = run_cmd(s4)
        if rc != 0:
            print(f"[run_s1_to_s5] s4 실패(code={rc})", file=sys.stderr)
            return rc

    # s5 입력 준비: actual_prices가 없으면 close.npy와 y.npy로 생성
    try:
        if not args.actual_prices.exists():
            import numpy as np  # 한글: 의존성 최소 – 가벼운 연산에만 사용
            close_path = args.close_values
            y_path = Path("data/gold/test/y.npy")
            if not y_path.exists():
                cand = close_path.parent / "y.npy"
                y_path = cand if cand.exists() else y_path
            close_vals = np.load(close_path).astype(float)
            returns = np.load(y_path).astype(float)
            if returns.ndim == 1:
                returns = returns[:, None]
            if close_vals.ndim != 1:
                close_vals = close_vals.reshape(-1)
            if close_vals.shape[0] != returns.shape[0]:
                print(f"[run_s1_to_s5] close({close_vals.shape}) vs returns({returns.shape}) 길이 불일치", file=sys.stderr)
            actual_prices = close_vals[:, None] * (1.0 + returns)
            args.actual_prices.parent.mkdir(parents=True, exist_ok=True)
            import numpy as _np
            _np.save(args.actual_prices, actual_prices)
            print(f"[run_s1_to_s5] actual_prices 생성: {args.actual_prices}")
    except Exception as e:
        print(f"[run_s1_to_s5] actual_prices 생성 실패: {e}", file=sys.stderr)

    # s5: top_mover_report_clean (stdout 중복 방지를 위해 캡처)
    if not args.skip_s5:
        s5 = [
            sys.executable,
            "-m",
            "Python.pipeline.pipelines.s5_evaluate.top_mover_report_clean",
            "--top-movers",
            str(args.top_movers),
            "--predictions",
            str(args.preds),
            "--actual-prices",
            str(args.actual_prices),
            "--close-values",
            str(args.close_values),
            "--output",
            str(args.report),
        ]
        print("[run_s1_to_s5] s5 보고서:", " ".join(s5))
        try:
            # 한글: s5는 결과 JSON을 파일로도 쓰므로 표준출력은 억제
            proc = subprocess.run(s5, stdout=subprocess.DEVNULL, stderr=None)
            rc = proc.returncode
        except Exception:
            rc = run_cmd(s5)
        return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
