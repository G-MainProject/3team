"""
멀티 호라이즌 gold 데이터셋을 호라이즌별로 분할(gold_<tag>)하고,
해당 태그에 맞는 최소 설정 YAML을 생성하여 s3/s4에서 출력 차원(H)을 올바르게 사용하도록 합니다.

사용법(프로젝트 루트에서 실행):
  python -m Python.tools.split_horizons \
    --gold-root data/gold \
    --out-root data \
    --config-dir Python/pipeline/config

생성물:
  - data/gold_1d, data/gold_1w, ...
  - Python/pipeline/config/settings_1d.yaml, ... (예: horizons = [1], [5], ...)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np


# 태그 → 거래일 수(설정 파일에 기록할 horizon 값)
TAG_MAP: dict[str, int] = {"1d": 1, "1w": 5, "1m": 20, "6m": 120, "1y": 250}
# 처리 순서(가용 H 개수만큼 잘라서 사용)
ORDERED_TAGS: list[str] = ["1d", "1w", "1m", "6m", "1y"]


def main(argv: list[str] | None = None) -> int:
    # gold을 호라이즌별 폴더 및 설정으로 분할하는 CLI
    p = argparse.ArgumentParser(description="gold을 호라이즌별 폴더/설정으로 분할")
    p.add_argument("--gold-root", type=Path, default=Path("data/gold"))
    p.add_argument("--out-root", type=Path, default=Path("data"))
    p.add_argument("--config-dir", type=Path, default=Path("Python/pipeline/config"))
    args = p.parse_args(argv)

    base = args.gold_root.resolve()
    out_root = args.out_root.resolve()
    config_dir = args.config_dir.resolve()
    (config_dir).mkdir(parents=True, exist_ok=True)

    # test split의 y로 호라이즌 개수(H) 추론
    test_y = _load_y(base / "test" / "y.npy")
    H = int(test_y.shape[1])
    tags = ORDERED_TAGS[:H]

    for hi, tag in enumerate(tags):
        for split in ("train", "val", "test"):
            src = base / split
            dst = out_root / f"gold_{tag}" / split
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.mkdir(parents=True, exist_ok=True)

            # X/close/labels 복사
            _copy_if_exists(src / "X.npy", dst / "X.npy")
            _copy_if_exists(src / "close.npy", dst / "close.npy")
            _copy_text_if_exists(src / "labels.json", dst / "labels.json")

            # y 분리 저장(hi 번째 호라이즌만 선택)
            yp = src / "y.npy"
            if yp.exists():
                y = _load_y(yp)
                yh = y[:, [hi]]
                np.save(dst / "y.npy", yh)

        # 태그 전용 최소 settings.yaml 작성(horizons=[단일값])
        _write_settings(config_dir / f"settings_{tag}.yaml", horizons=[TAG_MAP[tag]])

    print("gold split done:", tags)
    return 0


def _load_y(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(path)
    y = np.load(path)
    if y.ndim == 1:
        y = y[:, None]
    return y


def _copy_if_exists(src: Path, dst: Path) -> None:
    # 바이너리(npy) 파일을 그대로 저장(메모리 로드 후 저장)하여 포맷 유지
    if src.exists():
        array = np.load(src)
        np.save(dst, array)


def _copy_text_if_exists(src: Path, dst: Path) -> None:
    # 텍스트(JSON) 파일은 인코딩 유지하여 복사
    if src.exists():
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def _write_settings(path: Path, *, horizons: Iterable[int]) -> None:
    # s3/s4가 읽을 최소 설정: paths + dataset.horizons 만 제공
    lines = [
        "# Python/tools/split_horizons.py가 자동 생성한 설정 파일",
        "paths:",
        "  # gold/artifacts는 CLI 인자로 덮어쓰일 수 있으므로 기본값만 기재",
        "  gold: data/gold",
        "  artifacts: Python/pipeline/artifacts",
        "dataset:",
        f"  horizons: [{', '.join(str(int(h)) for h in horizons)}]",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
