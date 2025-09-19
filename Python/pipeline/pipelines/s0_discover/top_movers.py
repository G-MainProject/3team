"""Identify top volatile tickers using pykrx data."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import List

try:
    from pykrx import stock  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise ImportError("pykrx가 설치되어 있어야 합니다. `pip install pykrx` 후 실행하세요.") from exc


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    project_root = _find_project_root()
    output_path = Path(args.output) if args.output else _default_output(project_root, args.date)

    movers = _fetch_top_movers(args.date, args.market, args.count)
    output = {
        "date": args.date,
        "market": args.market,
        "count": len(movers),
        "tickers": movers,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"Top movers saved to {output_path}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Select top volatile tickers using pykrx")
    parser.add_argument("--date", default=datetime.now().strftime("%Y%m%d"), help="기준 일자 (YYYYMMDD)")
    parser.add_argument("--market", default="KOSPI", help="시장 구분 (KOSPI, KOSDAQ, ALL)")
    parser.add_argument("--count", type=int, default=5, help="선정할 티커 수")
    parser.add_argument("--output", type=Path, help="결과 저장 경로 (json)")
    return parser


def _fetch_top_movers(date: str, market: str, count: int) -> List[str]:
    data = stock.get_market_ohlcv_by_ticker(date, market=market)
    if data.empty:
        raise RuntimeError(f"pykrx에서 데이터를 가져오지 못했습니다: {date}, {market}")

    data = data.reset_index().rename(columns={"티커": "ticker", "고가": "high", "저가": "low", "시가": "open"})
    data["volatility"] = (data["high"] - data["low"]).abs() / data["open"].replace(0, float("nan"))
    data = data.dropna(subset=["volatility"]).sort_values("volatility", ascending=False)
    top = data.head(count)["ticker"].tolist()
    return top


def _default_output(project_root: Path, date: str) -> Path:
    return project_root / "data" / "raw" / f"top_movers_{date}.json"


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists():
            return parent
    for parent in current.parents:
        if (parent / "data").exists():
            return parent
    return current.parents[4]


if __name__ == "__main__":
    raise SystemExit(main())


