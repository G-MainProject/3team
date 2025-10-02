# -*- coding: utf-8 -*-
"""One-shot runner to execute s1..s5 using a top_movers JSON or explicit tickers.

Examples (run from project root):
  python scripts/run_s1_to_s5.py --top-movers data/raws/top_movers_auto.json --close-values data/gold/test/close.npy
  python scripts/run_s1_to_s5.py --top-movers data/raws/top_movers_auto.json --skip-s1
  python scripts/run_s1_to_s5.py --tickers 005930 000660 --skip-s3 --infer-model Python/pipeline/artifacts/models/model_best.pth
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from time import perf_counter
from pathlib import Path
from typing import List, Any


# Ensure project root on sys.path so imports and .env work when running this file directly
def _project_root() -> Path:
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "Python").exists() or (p / ".env").exists():
            return p
    return here.parents[1]


ROOT = _project_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# Configure stdout/stderr to UTF-8 to avoid mojibake on Windows consoles
try:
    _out: Any = sys.stdout
    _err: Any = sys.stderr
    _reconf = getattr(_out, "reconfigure", None)
    if callable(_reconf):
        _reconf(encoding="utf-8", errors="replace")
    _reconf_err = getattr(_err, "reconfigure", None)
    if callable(_reconf_err):
        _reconf_err(encoding="utf-8", errors="replace")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
except Exception:
    pass


# Load .env (UTF-8-SIG), idempotent
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


def _run(cmd: List[str]) -> int:
    return subprocess.call(cmd)


def _run_env(cmd: List[str], extra: dict | None = None) -> int:
    env = os.environ.copy()
    if extra:
        env.update({k: str(v) for k, v in extra.items()})
    proc = subprocess.run(cmd, env=env)
    return int(proc.returncode)


def _print_time_summary(times: dict[str, float]) -> None:
    if not times:
        return
    total = sum(times.values())
    print("[run_s1_to_s5] time summary (seconds):")
    for k in ("s1", "s2", "s3", "s4", "s5"):
        if k in times:
            print(f"  - {k}: {times[k]:.2f}")
    print(f"  - total: {total:.2f}")


def _load_tickers(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        arr = data.get("tickers")
        if isinstance(arr, list):
            return [str(x) for x in arr]
    except Exception:
        pass
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'"tickers"\s*:\s*\[(.*?)\]', raw, flags=re.S)
        if m:
            inner = m.group(1)
            items = [x.strip().strip('"\'') for x in inner.split(',') if x.strip()]
            return [i for i in items if i]
    except Exception:
        pass
    return []


def _date_defaults(start: str | None, end: str | None) -> tuple[str, str]:
    today = datetime.now().strftime("%Y-%m-%d")
    start_default = (datetime.now() - timedelta(days=365 * 10)).strftime("%Y-%m-%d")
    return (start or start_default, end or today)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run s1..s5 using an s0 top_movers JSON or explicit tickers")
    p.add_argument("--top-movers", type=Path, default=Path("data/raws/top_movers_auto.json"), help="Path to s0 output JSON")
    p.add_argument("--tickers", nargs="*", help="Explicit tickers (overrides top-movers)")
    p.add_argument("--start-date", help="YYYY-MM-DD (default: 10y ago)")
    p.add_argument("--end-date", help="YYYY-MM-DD (default: today)")
    p.add_argument("--skip-s1", action="store_true", help="Skip s1 collect")
    p.add_argument("--skip-s2", action="store_true", help="Skip s2 preprocess")
    p.add_argument("--skip-s3", action="store_true", help="Skip s3 train")
    p.add_argument("--skip-s4", action="store_true", help="Skip s4 infer")
    p.add_argument("--skip-s5", action="store_true", help="Skip s5 report")
    p.add_argument("--infer-model", type=Path, help="Model to use when skipping s3")
    p.add_argument("--close-values", type=Path, default=Path("data/gold/test/close.npy"), help="Path to close.npy for s4/s5")
    p.add_argument("--preds", type=Path, default=Path("data/outputs/preds.json"), help="Path for s4 predictions output (.json or .npy)")
    p.add_argument("--actual-prices", type=Path, default=Path("data/outputs/actual_prices.npy"), help="Path for s5 actual prices output")
    p.add_argument("--report", type=Path, default=Path("data/outputs/top_mover_forecast.json"), help="Path for s5 report output")
    # Defaults: enable Kiwoom and DART; provide opt-out switches
    p.add_argument("--no-kiwoom", action="store_true", help="Disable s1 Kiwoom REST collector (default: enabled)")
    p.add_argument("--no-dart", action="store_true", help="Disable s1 DART even if DART_API_KEY is set (default: enabled)")
    args = p.parse_args(argv)

    # Resolve tickers
    tickers = list(args.tickers or [])
    if not tickers and args.top_movers.exists():
        tickers = _load_tickers(args.top_movers)
    if not tickers and not args.skip_s1:
        print("[run_s1_to_s5] No tickers provided and top-movers missing.", file=sys.stderr)
        return 2

    start_date, end_date = _date_defaults(args.start_date, args.end_date)

    # Track per-stage timings
    stage_times: dict[str, float] = {}

    # s1: collect
    if not args.skip_s1:
        t0 = perf_counter()
        s1 = [
            sys.executable,
            "-m",
            "Python.pipeline.pipelines.s1_collect",
            "--tickers",
            *tickers,
            "--start-date",
            start_date,
            "--end-date",
            end_date,
        ]
        # Enable Kiwoom by default unless explicitly disabled
        enable_kiwoom = not args.no_kiwoom
        if enable_kiwoom:
            s1.append("--with-kiwoom")
        # Enable DART by default if key exists, unless explicitly disabled
        use_dart = (not args.no_dart) and bool(os.getenv("DART_API_KEY"))
        if (not args.no_dart) and not use_dart:
            print("[run_s1_to_s5] DART disabled: missing DART_API_KEY", file=sys.stderr)
        if use_dart:
            s1.append("--with-dart")
        # Avoid pykrx when either Kiwoom or DART collection is enabled
        if enable_kiwoom or use_dart:
            s1.append("--skip-pykrx")
        print("[run_s1_to_s5] s1 collect:", " ".join(s1))
        rc = _run_env(s1, {"DART_AUTO": "1" if use_dart else "0"})
        stage_times["s1"] = perf_counter() - t0
        if rc != 0:
            print(f"[run_s1_to_s5] s1 failed(code={rc})", file=sys.stderr)
            _print_time_summary(stage_times)
            return rc

    # s2: preprocess
    if not args.skip_s2:
        t0 = perf_counter()
        s2 = [
            sys.executable,
            "-m",
            "Python.pipeline.pipelines.s2_preprocess",
            "--tickers",
            *tickers,
        ]
        print("[run_s1_to_s5] s2 preprocess:", " ".join(s2))
        # Force full horizons (include 1y) without requiring .env edits
        rc = _run_env(s2, {"FORCE_1Y": "1"})
        stage_times["s2"] = perf_counter() - t0
        if rc != 0:
            print(f"[run_s1_to_s5] s2 failed(code={rc})", file=sys.stderr)
            _print_time_summary(stage_times)
            return rc

    # s3: train (optional)
    if not args.skip_s3:
        t0 = perf_counter()
        s3 = [sys.executable, "-m", "Python.pipeline.pipelines.s3_model", "--train"]
        print("[run_s1_to_s5] s3 train:", " ".join(s3))
        rc = _run(s3)
        stage_times["s3"] = perf_counter() - t0
        if rc != 0:
            print(f"[run_s1_to_s5] s3 failed(code={rc})", file=sys.stderr)
            _print_time_summary(stage_times)
            return rc

    # s4: infer
    if not args.skip_s4:
        t0 = perf_counter()
        model_path = str(args.infer_model or Path("Python/pipeline/artifacts/models/model_best.pth"))
        s4 = [
            sys.executable,
            "-m",
            "Python.pipeline.pipelines.s4_infer.predict",
            "--model",
            model_path,
            "--input",
            str(Path("data/gold/test/X.npy")),
            "--output",
            str(args.preds),
        ]
        if args.close_values:
            s4 += ["--close-values", str(args.close_values)]
        print("[run_s1_to_s5] s4 infer:", " ".join(s4))
        rc = _run(s4)
        stage_times["s4"] = perf_counter() - t0
        if rc != 0:
            print(f"[run_s1_to_s5] s4 failed(code={rc})", file=sys.stderr)
            _print_time_summary(stage_times)
            return rc

    # s5: build/align actual_prices to match predictions shape
    try:
        import numpy as np
        want_n = want_h = None
        # Infer predictions shape from file extension
        try:
            if str(args.preds).lower().endswith('.npy'):
                _preds = np.load(args.preds)
                if _preds.ndim == 1:
                    _preds = _preds[:, None]
                want_n, want_h = _preds.shape[0], _preds.shape[1]
            else:
                _data = json.loads(Path(args.preds).read_text(encoding='utf-8'))
                if isinstance(_data, dict):
                    if isinstance(_data.get('prices'), list) and _data['prices']:
                        want_n, want_h = len(_data['prices']), len(_data['prices'][0])
                    elif isinstance(_data.get('returns'), list) and _data['returns']:
                        want_n, want_h = len(_data['returns']), len(_data['returns'][0])
        except Exception:
            pass

        need_build = True
        if args.actual_prices.exists() and want_n and want_h:
            try:
                ap = np.load(args.actual_prices)
                if ap.ndim == 1:
                    ap = ap[:, None]
                if ap.shape == (want_n, want_h):
                    need_build = False
                else:
                    print(f"[run_s1_to_s5] actual_prices shape {ap.shape} != preds ({want_n}, {want_h}); rebuilding", file=sys.stderr)
            except Exception:
                need_build = True
        if need_build:
            close_path = args.close_values
            y_path = Path('data/gold/test/y.npy')
            if not y_path.exists():
                cand = close_path.parent / 'y.npy'
                y_path = cand if cand.exists() else y_path
            close_vals = np.load(close_path).astype(float)
            returns = np.load(y_path).astype(float)
            if returns.ndim == 1:
                returns = returns[:, None]
            if close_vals.ndim != 1:
                close_vals = close_vals.reshape(-1)
            if want_n and want_h:
                n = min(want_n, returns.shape[0], close_vals.shape[0])
                h = min(want_h, returns.shape[1])
            else:
                n = min(returns.shape[0], close_vals.shape[0])
                h = returns.shape[1]
            if (n, h) != (returns.shape[0], returns.shape[1]):
                print(f"[run_s1_to_s5] aligning shapes to (n={n}, h={h})", file=sys.stderr)
            returns = returns[:n, :h]
            close_vals = close_vals[:n]
            actual_prices = close_vals[:, None] * (1.0 + returns)
            args.actual_prices.parent.mkdir(parents=True, exist_ok=True)
            np.save(args.actual_prices, actual_prices)
            print(f"[run_s1_to_s5] actual_prices saved: {args.actual_prices}")
    except Exception as e:
        print(f"[run_s1_to_s5] failed to build actual_prices: {e}", file=sys.stderr)

    if not args.skip_s5:
        t0 = perf_counter()
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
        print("[run_s1_to_s5] s5 report:", " ".join(s5))
        # Show full logs from s5 in console
        rc = _run(s5)
        stage_times["s5"] = perf_counter() - t0
        _print_time_summary(stage_times)
        return rc

    _print_time_summary(stage_times)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

