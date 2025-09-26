"""CLI to execute the entire data-to-inference pipeline."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable
import csv

import numpy as np
from time import perf_counter  # 단계별 소요시간 측정용  # 한글 주석

COLLECT_MODULE = "Python.pipeline.pipelines.s1_collect"
PREPROCESS_MODULE = "Python.pipeline.pipelines.s2_preprocess"
MODEL_MODULE = "Python.pipeline.pipelines.s3_model"
INFER_MODULE = "Python.pipeline.pipelines.s4_infer.predict"
DISCOVER_MODULE = "Python.pipeline.pipelines.s0_discover.top_movers"


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    # 하위 호환을 위해 기본 출력 경로를 data/outputs로 정규화
    try:
        if str(getattr(args, "s5_output", "")).replace("\\", "/") == "outputs/eval.json":
            args.s5_output = Path("data/outputs/eval.json")
    except Exception:
        pass

    project_root = _find_project_root()
    env = _build_env(project_root)
    stage_times: dict[str, float] = {}

    tickers = list(args.tickers)

    # 자동 티커 탐색
    if args.auto_tickers:
        discovery_output = args.auto_output or (project_root / "data" / "raw" / "top_movers_auto.json")
        discover_cmd = [
            "python",
            "-m",
            DISCOVER_MODULE,
            "--date",
            args.auto_date,
            "--market",
            args.auto_market,
            "--count",
            str(args.auto_count),
            "--output",
            str(discovery_output),
            "--source",
            args.auto_source,
        ]
        stage_times["s0_discover"] = _run_stage("s0_discover", discover_cmd, env)
        auto_tickers = _load_tickers(discovery_output)
        if not auto_tickers:
            raise RuntimeError("Top movers 탐색 실패: 자동 티커 목록이 비었습니다.")
        tickers = sorted({*tickers, *auto_tickers}) if tickers else auto_tickers

    if not tickers and not args.skip_s1:
        raise ValueError("수집에 사용할 티커가 없습니다. --tickers 또는 --auto-tickers를 지정하세요.")

    # Stage 1: 수집
    if not args.skip_s1:
        s1_cmd = [
            "python",
            "-m",
            COLLECT_MODULE,
            "--tickers",
            *tickers,
            "--start-date",
            args.start_date,
            "--end-date",
            args.end_date,
        ]
        # .env에 DART_API_KEY가 있고 data/dart_corpcode.csv가 있으면 DART 수집 자동 활성화
        try:
            data_root = next((p for p in [project_root / "data", Path("data")] if p.exists()), project_root / "data")
            corp_map = data_root / "dart_corpcode.csv"
            # 개선: CSV 유무와 무관하게 API 키가 있으면 DART 단계 활성화
            want_dart = bool(os.getenv("DART_API_KEY"))
        except Exception:
            want_dart = False
        if want_dart:
            s1_cmd.append("--with-dart")
        # DART 자동 보정: CSV 매핑에서 corp_code 추가 또는 플래그 제거
        try:
            corp_codes = _load_corp_codes_from_csv(project_root, tickers)
        except Exception:
            corp_codes = []
        if "--with-dart" in s1_cmd:
            if corp_codes:
                s1_cmd += ["--corp-codes", *corp_codes]
            s1_cmd += [
                "--single-accounts",
                "당기순이익",
                "자산총계",
                "부채총계",
                "자본총계",
                "유동자산",
                "유동부채",
                "재고자산",
            ]
            # corp_codes가 없으면 s1 내부의 자동 매핑(API/CSV)을 사용하도록 그대로 둔다
        stage_times["s1_collect"] = _run_stage("s1_collect", s1_cmd, env)

    # Stage 2: 전처리
    if not args.skip_s2:
        s2_cmd = ["python", "-m", PREPROCESS_MODULE]
        if tickers:
            s2_cmd += ["--tickers", *tickers]
        if args.skip_merge:
            s2_cmd.append("--skip-merge")
        if args.skip_features:
            s2_cmd.append("--skip-features")
        if args.skip_datasets:
            s2_cmd.append("--skip-datasets")
        stage_times["s2_preprocess"] = _run_stage("s2_preprocess", s2_cmd, env)

    # Stage 3: 모델 학습
    if not args.skip_s3:
        s3_cmd = ["python", "-m", MODEL_MODULE, "--train"]
        if args.settings:
            s3_cmd += ["--settings", str(args.settings)]
        if args.gold_root:
            s3_cmd += ["--gold-root", str(args.gold_root)]
        if args.artifacts_root:
            s3_cmd += ["--artifacts-root", str(args.artifacts_root)]
        if args.epochs is not None:
            s3_cmd += ["--epochs", str(args.epochs)]
        if args.batch_size is not None:
            s3_cmd += ["--batch-size", str(args.batch_size)]
        if args.learning_rate is not None:
            s3_cmd += ["--learning-rate", str(args.learning_rate)]
        if args.model_device is not None:
            s3_cmd += ["--device", args.model_device]
        stage_times["s3_model"] = _run_stage("s3_model", s3_cmd, env)

    infer_input = Path(args.infer_input) if args.infer_input else (project_root / "data" / "gold" / "test" / "X.npy")
    infer_output = Path(args.infer_output)
    s5_output = Path(args.s5_output)
    # Stage 4: 추론
    if not args.skip_s4:
        infer_cmd = [
            "python",
            "-m",
            INFER_MODULE,
            "--model",
            str(args.infer_model or (project_root / "Python" / "pipeline" / "artifacts" / "models" / "model_best.pth")),
            "--input",
            str(infer_input),
            "--output",
            str(infer_output),
            "--close-index",
            str(args.close_index),
        ]
        if args.settings:
            infer_cmd += ["--settings", str(args.settings)]
        if args.close_values:
            infer_cmd += ["--close-values", str(args.close_values)]
        if args.infer_device is not None:
            infer_cmd += ["--device", args.infer_device]
        stage_times["s4_infer"] = _run_stage("s4_infer", infer_cmd, env)

    # Stage 5: 평가
    if not args.skip_s5:
        if args.skip_s4:
            raise ValueError("s5_evaluate 단계를 실행하려면 s4_infer 결과가 필요합니다. --skip-s5 옵션을 사용하거나 s4 단계를 실행해주세요.")
        predictions_path = infer_output
        actual_returns_path = Path(args.s5_actual_returns) if args.s5_actual_returns else infer_input.with_name("y.npy")
        if not actual_returns_path.exists():
            raise FileNotFoundError(f"평가에 사용할 실제 수익률 파일을 찾을 수 없습니다: {actual_returns_path}")
        if not predictions_path.exists():
            raise FileNotFoundError(f"s4_infer 결과 파일이 존재하지 않습니다: {predictions_path}")
        if args.close_values:
            close_values = np.load(args.close_values)
        else:
            price_data = np.load(infer_input)
            if args.close_index < 0 or args.close_index >= price_data.shape[2]:
                raise ValueError("close_index가 feature 차원 범위를 벗어났습니다.")
            close_values = price_data[:, -1, args.close_index]
        close_values = np.asarray(close_values, dtype=float)
        if close_values.ndim != 1:
            close_values = close_values.reshape(-1)
        actual_returns = np.load(actual_returns_path)
        actual_returns = np.asarray(actual_returns, dtype=float)
        if actual_returns.ndim == 1:
            actual_returns = actual_returns[:, None]
        if close_values.shape[0] != actual_returns.shape[0]:
            raise ValueError("실제 종가 배열과 실제 수익률 배열의 샘플 수가 일치하지 않습니다.")
        actual_prices = close_values[:, None] * (1.0 + actual_returns)
        actual_prices_path = Path(args.s5_actual_prices) if args.s5_actual_prices else (project_root / "data" / "outputs" / "actual_prices.npy")
        actual_prices_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(actual_prices_path, actual_prices.astype(float))

        # 자동 티커 탐색 시 top_mover_report.py 사용
        if args.auto_tickers:
            s5_cmd = [
                "python",
                "-m",
                "Python.pipeline.pipelines.s5_evaluate.top_mover_report_clean",
                "--top-movers",
                str(discovery_output),
                "--predictions",
                str(predictions_path),
                "--actual-prices",
                str(actual_prices_path),
                "--output",
                str(s5_output.with_name("top_mover_forecast.json")),
            ]
        else:
            s5_cmd = [
                "python",
                "-m",
                "Python.pipeline.pipelines.s5_evaluate.top_mover_report_clean",
                "--predictions",
                str(predictions_path),
                "--actual-prices",
                str(actual_prices_path),
                "--output",
                str(s5_output),
            ]
            if args.s5_horizons:
                s5_cmd += ["--horizons", *map(str, args.s5_horizons)]
        stage_times["s5_evaluate"] = _run_stage("s5_evaluate", s5_cmd, env)

    # Final one-shot time summary
    if stage_times:
        total = sum(stage_times.values())
        print("[Pipeline] Time summary (seconds):")
        for k in ("s0_discover", "s1_collect", "s2_preprocess", "s3_model", "s4_infer", "s5_evaluate"):
            if k in stage_times:
                print(f"  - {k}: {stage_times[k]:.3f}s")
        print(f"  = Total: {total:.3f}s")

    print("Pipeline completed successfully.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run full pipeline from s1 to s5.")
    parser.add_argument("--tickers", nargs="*", default=[], help="수집/전처리에 사용할 티커 목록")
    parser.add_argument("--start-date", default="2015-09-19", help="수집 시작일 (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2025-09-18", help="수집 종료일 (YYYY-MM-DD)")

    # auto ticker discovery
    parser.add_argument("--auto-tickers", action="store_true", help="pykrx 변동성 상위 종목 자동 선택")
    parser.add_argument("--auto-date", default=datetime.now().strftime("%Y%m%d"), help="top movers 기준 일자 (YYYYMMDD)")
    parser.add_argument("--auto-market", default="KOSPI", help="시장 (KOSPI/KOSDAQ/ALL)")
    parser.add_argument("--auto-count", type=int, default=5, help="선정 종목 수")
    parser.add_argument("--auto-source", default="kiwoom", choices=["pykrx", "kiwoom"], help="top movers 탐색 소스")
    parser.add_argument("--auto-output", type=Path, help="탐색 결과 저장 경로")

    # Stage control
    parser.add_argument("--skip-s1", action="store_true")
    parser.add_argument("--skip-s2", action="store_true")
    parser.add_argument("--skip-s3", action="store_true")
    parser.add_argument("--skip-s4", action="store_true")
    parser.add_argument("--skip-s5", action="store_true")

    parser.add_argument("--skip-merge", action="store_true")
    parser.add_argument("--skip-features", action="store_true")
    parser.add_argument("--skip-datasets", action="store_true")

    parser.add_argument("--epochs", type=int, help="학습 epoch 수")
    parser.add_argument("--batch-size", type=int, help="학습 배치 크기")
    parser.add_argument("--learning-rate", type=float, help="학습률")
    parser.add_argument("--model-device", help="학습 디바이스")
    parser.add_argument("--settings", type=Path, help="공통 settings.yaml 경로")
    parser.add_argument("--gold-root", type=Path, help="gold 데이터 루트 경로")
    parser.add_argument("--artifacts-root", type=Path, help="artifacts 루트 경로")

    parser.add_argument("--infer-input", type=Path, help="추론 입력 numpy 파일 (기본: data/gold/test/X.npy)")
    parser.add_argument("--infer-output", type=Path, default=Path("data/outputs/preds.json"))
    parser.add_argument("--infer-model", type=Path, help="추론에 사용할 모델 가중치")
    parser.add_argument("--infer-device", help="추론 디바이스")
    parser.add_argument("--close-index", type=int, default=3, help="추론 시 종가가 위치한 feature 인덱스")
    parser.add_argument("--close-values", type=Path, help="추론용 기준 종가 numpy 파일")
    parser.add_argument("--s5-actual-prices", type=Path, help="s5 평가에 사용할 실제 가격 numpy 파일 경로")
    parser.add_argument("--s5-actual-returns", type=Path, help="s5 평가에 사용할 실제 수익률 numpy 파일 경로 (기본: infer-input 경로의 y.npy)")
    parser.add_argument("--s5-output", type=Path, default=Path("outputs/eval.json"), help="s5 평가 보고서 출력 경로")
    parser.add_argument("--s5-horizons", nargs="*", type=int, help="s5 평가 시 사용할 예측 지평 목록")
    return parser


def _run_stage(name: str, cmd: list[str], env: dict[str, str]) -> float:
    start = perf_counter()
    completed = subprocess.run(cmd, env=env)
    if completed.returncode != 0:
        raise RuntimeError(f"Stage {name} failed with exit code {completed.returncode}")
    return perf_counter() - start


def _build_env(project_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def _load_tickers(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("tickers", [])


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists():
            return parent
    for parent in current.parents:
        if (parent / "data").exists():
            return parent
    return current.parents[4]


def _load_corp_codes_from_csv(project_root: Path, tickers: list[str]) -> list[str]:
    """data/dart_corpcode.csv에서 stock_code(=ticker) -> corp_code 매핑을 읽어 반환한다.

    허용 헤더: ticker, stock_code, code, symbol / corp_code, corpcode, corpcode_id, corp
    반환: 입력 tickers 순서대로 매핑된 corp_code 목록(없으면 제외)
    """
    try:
        path = project_root / "data" / "dart_corpcode.csv"
        if not path.exists() or not tickers:
            return []
        want = [str(t).zfill(6) for t in tickers]
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
                        t = str(vals[0]).strip().zfill(6)
                        c = str(vals[1]).strip()
                        if t and c:
                            mapping[t] = c
            else:
                for row in reader:
                    t = str(row.get(t_col, "")).strip().zfill(6)
                    c = str(row.get(c_col, "")).strip()
                    if t and c:
                        mapping[t] = c
        return [mapping[t] for t in want if t in mapping]
    except Exception:
        return []


if __name__ == "__main__":
    raise SystemExit(main())






