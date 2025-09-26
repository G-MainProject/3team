"""시계열 모델 추론 스크립트 (다중 기간 수익률 -> 예상 주가)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import torch

from Python.pipeline.pipelines.s2_preprocess import build_datasets
from Python.pipeline.pipelines.s3_model.fusion_head import create_fusion_head
from Python.pipeline.pipelines.s3_model.price_branch import create_price_branch
from Python.pipeline.pipelines.s3_model.text_branch import create_text_branch


def main(args: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    opts = parser.parse_args(args)

    project_root = _find_project_root()
    dataset_cfg = build_datasets._load_config(None, None, None, opts.settings)
    # 동적 horizon: gold/horizons.json이 있으면 우선 적용
    try:
        gold_root = _find_project_root() / "data" / "gold"
        hfile = gold_root / "horizons.json"
        if hfile.exists():
            import json as _json
            dataset_cfg.horizons = [int(x) for x in _json.loads(hfile.read_text(encoding="utf-8"))]
    except Exception:
        pass
    horizons = dataset_cfg.horizons
    horizon_labels = _format_horizon_labels(horizons)

    device = torch.device(opts.device if torch.cuda.is_available() or opts.device == "cpu" else "cpu")

    price_data = _load_array(opts.input)
    if price_data.ndim != 3:
        raise ValueError("가격 입력은 (N, seq_len, feat_dim) 형태여야 합니다.")
    batch_size, seq_len, price_dim = price_data.shape

    text_data = None
    if opts.text_input:
        text_data = _load_array(opts.text_input)
        if text_data.shape[:2] != (batch_size, seq_len):
            raise ValueError("텍스트 입력은 가격 입력과 동일한 (N, seq_len) 형태여야 합니다.")

    price_branch = create_price_branch(input_shape=(seq_len, price_dim))
    text_branch = create_text_branch(input_dim=text_data.shape[2]) if text_data is not None else None
    model = create_fusion_head(
        price_branch=price_branch,
        text_branch=text_branch,
        hidden_dim=opts.hidden_dim,
        dropout=opts.dropout,
        output_dim=len(horizons),
    )

    state = torch.load(opts.model, map_location="cpu")
    model.load_state_dict(state)
    model.to(device)
    model.eval()

    with torch.no_grad():
        price_tensor = torch.tensor(price_data, dtype=torch.float32, device=device)
        text_tensor = torch.tensor(text_data, dtype=torch.float32, device=device) if text_data is not None else None
        preds = model(price_tensor, text_tensor).cpu().numpy()

    # preds: returns (N, len(horizons))
    close_values = _resolve_close_values(price_data, opts.close_values, opts.close_index)
    if close_values.shape[0] != preds.shape[0]:
        raise ValueError("종가 벡터의 길이가 입력 샘플 수와 다릅니다.")

    predicted_prices = close_values[:, None] * (1.0 + preds)

    output = {
        "model": str(opts.model),
        "input": str(opts.input),
        "count": int(preds.shape[0]),
        "horizons": horizon_labels,
        "returns": preds.tolist(),
        "current_close": close_values.tolist(),
        "prices": predicted_prices.tolist(),
        "meta": {
            "description": "Multi-horizon inference outputs produced by s4_infer.",
            "description_ko": "s4_infer 단계에서 생성된 다중 수평선 예측 결과 요약",
            "fields": {
                "model": "Path to the trained model state_dict (.pth).",
                "input": "Path to the preprocessed input numpy array (N, seq, feat).",
                "count": "Number of samples included in this prediction batch.",
                "horizons": "List of horizon labels (e.g., 1d, 1w).",
                "returns": "Predicted returns for each sample and horizon (shape: N x H).",
                "current_close": "Close price per sample used as the prediction base (length N).",
                "prices": "Predicted future close prices per sample and horizon (shape: N x H)."
            },
            "fields_ko": {
                "model": "학습된 PyTorch state_dict(.pth) 파일 경로",
                "input": "전처리된 입력 numpy 배열 경로 (형태: N x seq x feat)",
                "count": "이번 추론에 포함된 샘플 개수",
                "horizons": "예측을 수행한 기간 레이블 목록 (예: 1d, 1w)",
                "returns": "샘플·수평선별 예측 수익률 (배열 크기: N x H)",
                "current_close": "각 샘플의 기준 종가 배열 (길이 N)",
                "prices": "각 샘플과 수평선에 대한 예측 종가 (배열 크기: N x H)"
            }
        }
    }

    opts.output.parent.mkdir(parents=True, exist_ok=True)
    if opts.output.suffix.lower() == ".json":
        opts.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        _write_csv(opts.output, horizon_labels, close_values, preds, predicted_prices)

    print(f"Inference completed. Results saved to {opts.output}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run inference with trained multi-horizon model")
    parser.add_argument("--model", type=Path, required=True, help="모델 state_dict 경로 (.pth)")
    parser.add_argument("--input", type=Path, required=True, help="가격 시퀀스 numpy 파일 (N, seq, feat)")
    parser.add_argument("--text-input", type=Path, help="텍스트 시퀀스 numpy 파일 (선택)")
    parser.add_argument("--output", type=Path, required=True, help="출력 파일 (json 또는 csv)")
    parser.add_argument("--close-values", type=Path, help="샘플별 기준 종가 numpy 파일 (N,)")
    parser.add_argument("--close-index", type=int, default=3, help="가격 텐서에서 종가가 위치한 feature 인덱스")
    parser.add_argument("--hidden-dim", type=int, default=128, help="분류 헤드 은닉 차원")
    parser.add_argument("--dropout", type=float, default=0.2, help="분류 헤드 드롭아웃")
    parser.add_argument("--device", default="cuda", help="추론 디바이스")
    parser.add_argument("--settings", type=Path, help="settings.yaml 경로 (horizon 정보 로드용)")
    return parser


def _load_array(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(path)
    return np.load(path)


def _resolve_close_values(price_data: np.ndarray, close_path: Optional[Path], close_index: int) -> np.ndarray:
    if close_path is not None:
        values = _load_array(close_path)
        if values.ndim != 1:
            raise ValueError("종가 배열은 1차원이어야 합니다.")
        return values.astype(float)
    if close_index < 0 or close_index >= price_data.shape[2]:
        raise ValueError("close_index가 feature 범위를 벗어났습니다.")
    return price_data[:, -1, close_index].astype(float)


def _write_csv(path: Path, labels: list[str], closes: np.ndarray, returns: np.ndarray, prices: np.ndarray) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    header = ["index", "current_close"] + [f"return_{label}" for label in labels] + [f"price_{label}" for label in labels]
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(header)
        for idx, (c, ret_row, price_row) in enumerate(zip(closes, returns, prices)):
            writer.writerow([idx, float(c), *ret_row.tolist(), *price_row.tolist()])


def _format_horizon_labels(horizons: Iterable[int]) -> list[str]:
    mapping = {1: "1d", 5: "1w", 20: "1m", 120: "6m", 250: "1y"}
    return [mapping.get(int(h), f"{h}d") for h in horizons]


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists():
            return parent
    for parent in current.parents:
        if (parent / "data").exists():
            return parent
    return current.parents[4]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
