# -*- coding: utf-8 -*-
"""Deprecated entrypoint.

This file is kept for backward compatibility only.
Use scripts/run_s1_to_s5.py for one-shot execution, or run each stage module directly:
  - python -m Python.pipeline.pipelines.s1_collect ...
  - python -m Python.pipeline.pipelines.s2_preprocess ...
  - python -m Python.pipeline.pipelines.s3_model --train
  - python -m Python.pipeline.pipelines.s4_infer.predict ...
  - python -m Python.pipeline.pipelines.s5_evaluate.top_mover_report_clean ...
"""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "[Deprecated] Use scripts/run_s1_to_s5.py (or stage modules).",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

