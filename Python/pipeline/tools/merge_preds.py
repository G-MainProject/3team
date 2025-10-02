"""
호라이즌별 예측 결과 JSON(outputs/preds_<tag>.json)들을 하나의 멀티-호라이즌
결과(outputs/preds.json)로 병합합니다.

사용법(프로젝트 루트에서 실행):
  python -m Python.tools.merge_preds \
    --inputs outputs \
    --order 1d 1w 1m 6m 1y \
    --output outputs/preds.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np


def main(argv: list[str] | None = None) -> int:
    # 호라이즌별 preds를 하나로 병합하는 CLI
    p = argparse.ArgumentParser(description="호라이즌별 예측을 멀티-호라이즌 JSON으로 병합")
    p.add_argument("--inputs", type=Path, default=Path("outputs"), help="preds_<tag>.json 파일들이 있는 폴더")
    p.add_argument("--order", nargs="*", default=["1d", "1w", "1m", "6m", "1y"], help="호라이즌(태그) 병합 순서")
    p.add_argument("--output", type=Path, default=Path("outputs/preds.json"))
    args = p.parse_args(argv)

    parts: list[tuple[str, Path]] = []
    for tag in args.order:
        pth = args.inputs / f"preds_{tag}.json"
        if pth.exists():
            parts.append((tag, pth))
    if not parts:
        raise SystemExit("no per-horizon preds found")

    prices: list[np.ndarray] = []
    returns: list[np.ndarray] = []
    tags: list[str] = []
    N: int | None = None
    current_close: np.ndarray | None = None
    for tag, pth in parts:
        d = json.loads(pth.read_text(encoding="utf-8"))
        pr = np.array(d.get("prices"), dtype=float)
        rt = np.array(d.get("returns"), dtype=float)
        cc = d.get("current_close")
        if pr.ndim == 1:
            pr = pr[:, None]
        if rt.ndim == 1:
            rt = rt[:, None]
        if N is None:
            N = int(pr.shape[0])
        n0 = min(int(N), int(pr.shape[0]))
        prices.append(pr[:n0])  # 샘플 수(N)가 다른 경우 최소치로 정렬
        returns.append(rt[:n0])
        tags.append(tag)
        if current_close is None and cc is not None:
            arr = np.array(cc, dtype=float)
            current_close = arr[:n0]

    prices_cat = np.concatenate(prices, axis=1)
    returns_cat = np.concatenate(returns, axis=1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # 최종 병합 JSON 저장
    args.output.write_text(
        json.dumps(
            {
                "prices": prices_cat.tolist(),
                "returns": returns_cat.tolist(),
                "horizons": tags,
                **({"current_close": current_close.tolist()} if current_close is not None else {}),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"merged preds -> {args.output} with horizons {tags}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
