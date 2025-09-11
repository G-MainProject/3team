# -*- coding: utf-8 -*-
"""
Build symbols_krx.csv using DART corpCode API.

Requires .env with DART_API_KEY. Outputs:
  - data/dart_corpcode.csv (via dart_client)
  - data/symbols_krx.csv (columns: 종목코드,종목명)
"""

from __future__ import annotations

import csv
from pathlib import Path

from Python.Sentiment.Libs.env import load_env
from Python.Sentiment.Libs.dart_client import fetch_and_cache_corpcode, corpcode_cache_path


def main() -> None:
    load_env()

    cur = Path(__file__).resolve()
    project_root = str(cur.parents[2])  # .../3team
    # fetch (and write dart_corpcode.csv)
    fetch_and_cache_corpcode(project_root)

    src_path = Path(corpcode_cache_path(project_root))
    out_path = Path(project_root) / "data" / "symbols_krx.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    with src_path.open("r", encoding="utf-8") as rf, out_path.open("w", encoding="utf-8", newline="") as wf:
        rd = csv.DictReader(rf)
        wr = csv.writer(wf)
        wr.writerow(["종목코드", "종목명"])  # minimal columns accepted by symbols.py
        for row in rd:
            code = (row.get("stock_code") or "").strip()
            name = (row.get("corp_name") or "").strip()
            if code and len(code) == 6 and code.isdigit():
                wr.writerow([code, name])
                total += 1

    print(f"[build_symbols_from_dart] wrote {total} rows -> {out_path}")


if __name__ == "__main__":
    main()

