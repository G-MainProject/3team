# -*- coding: utf-8 -*-
"""CLI entrypoint for stage-02 preprocessing (bronze -> silver -> gold)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Sequence

if __package__ in (None, ""):
    start = Path(__file__).resolve()
    project_root = next((parent for parent in start.parents if (parent / "Python").exists()), start.parents[4])
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    merge_align = __import__("Python.pipeline.pipelines.s2_preprocess.merge_align", fromlist=["run"])
    features = __import__("Python.pipeline.pipelines.s2_preprocess.features", fromlist=["run"])
    build_datasets = __import__("Python.pipeline.pipelines.s2_preprocess.build_datasets", fromlist=["run"])
else:
    from . import merge_align, features, build_datasets


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    summary: Dict[str, list[str]] = {}

    if not args.skip_merge:
        merge_outputs = merge_align.run(
            tickers=args.tickers,
            raw_root=args.raw_root,
            bronze_root=args.bronze_root,
            price_source=args.price_source,
            news_dir=args.news_dir,
            fundamentals_dir=args.fundamentals_dir,
        )
        summary["merge"] = [str(path) for path in merge_outputs]

    if not args.skip_features:
        feature_outputs = features.run(
            tickers=args.tickers,
            bronze_root=args.bronze_root,
            silver_root=args.silver_root,
        )
        summary["features"] = [str(path) for path in feature_outputs]

    if not args.skip_datasets:
        dataset_outputs = build_datasets.run(
            silver_root=args.silver_root,
            gold_root=args.gold_root,
            artifacts_root=args.artifacts_root,
            settings_path=args.settings,
            tickers=args.tickers,
        )
        summary["datasets"] = {split: str(path) for split, path in dataset_outputs.items()}

    _print_summary(summary)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage-02 preprocessing pipeline (bronze/silver/gold)",
    )
    parser.add_argument("--tickers", nargs="*", help="처리할 티커 목록 (미지정 시 bronze/silver 파일 전체 대상)")
    parser.add_argument("--raw-root", type=Path, default=None, help="raw 데이터 루트 경로")
    parser.add_argument("--bronze-root", type=Path, default=None, help="bronze 저장 경로")
    parser.add_argument("--silver-root", type=Path, default=None, help="silver 저장 경로")
    parser.add_argument("--gold-root", type=Path, default=None, help="gold 저장 경로")
    parser.add_argument("--artifacts-root", type=Path, default=None, help="artifacts 저장 경로")
    parser.add_argument("--settings", type=Path, default=None, help="settings.yaml 경로")
    parser.add_argument("--price-source", default="pykrx", choices=["pykrx", "kiwoom"], help="가격 데이터 우선 소스")
    parser.add_argument("--news-dir", type=Path, help="뉴스 데이터 경로(티커별 하위)"
    )
    parser.add_argument("--fundamentals-dir", type=Path, help="재무 데이터 경로(DART 결과 등)")
    parser.add_argument("--skip-merge", action="store_true", help="merge_align 단계를 건너뛰기")
    parser.add_argument("--skip-features", action="store_true", help="features 단계를 건너뛰기")
    parser.add_argument("--skip-datasets", action="store_true", help="build_datasets 단계를 건너뛰기")
    return parser


def _print_summary(summary: Dict[str, list[str]]) -> None:
    if not summary:
        print("No preprocessing stages executed.")
        return
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
