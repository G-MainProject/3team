# -*- coding: utf-8 -*-
"""Clean inference script for multi-horizon price forecasting (ASCII only).

Inputs
- --model: path to model state_dict (.pth)
- --input: numpy file (N, seq_len, feat_dim) with price features
- --text-input: optional numpy file (N, seq_len, text_dim)
- --close-values: optional numpy file (N,) with base close per sample
- --close-index: feature index of close price in --input (used if --close-values not given)

Outputs
- --output: .json (default) with returns/prices and metadata, or .csv table

Notes
- Horizon labels are derived from settings or horizons.json under data/gold when present.
- 1y label is used for 250/252 or any horizon between 240..260.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import torch

from Python.pipeline.pipelines.s2_preprocess import build_datasets
from Python.pipeline.pipelines.s3_model.fusion_head import create_fusion_head
from Python.pipeline.pipelines.s3_model.price_branch import create_price_branch
from Python.pipeline.pipelines.s3_model.text_branch import create_text_branch


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    opts = parser.parse_args(argv)

    # Load settings and horizons (may be overridden by checkpoint out-dim later)
    dataset_cfg = build_datasets._load_config(None, None, None, opts.settings)
    try:
        gold_root = _find_project_root() / "data" / "gold"
        hfile = gold_root / "horizons.json"
        if hfile.exists():
            dataset_cfg.horizons = [int(x) for x in json.loads(hfile.read_text(encoding="utf-8"))]
    except Exception:
        pass
    horizons = list(dataset_cfg.horizons)

    # Load checkpoint first to infer output dimension robustly
    state = torch.load(opts.model, map_location="cpu")
    ckpt_out_dim: int | None = None
    try:
        # FusionClassifier last layer key pattern
        w = state.get("classifier.3.weight")
        if w is not None and hasattr(w, "shape") and len(w.shape) == 2:
            ckpt_out_dim = int(w.shape[0])
    except Exception:
        ckpt_out_dim = None
    if ckpt_out_dim is None:
        # Fallback: try any leaf weight that looks like (H, hidden)
        try:
            for k, v in state.items():
                if k.endswith(".weight") and hasattr(v, "shape") and len(getattr(v, "shape", [])) == 2:
                    rows = int(v.shape[0])
                    if rows in (4, 5):
                        ckpt_out_dim = rows
                        break
        except Exception:
            pass
    if ckpt_out_dim is not None and ckpt_out_dim > 0:
        # Align horizons to checkpoint dimension (trim or pad simple days if needed)
        if len(horizons) != ckpt_out_dim:
            if len(horizons) > ckpt_out_dim:
                horizons = horizons[:ckpt_out_dim]
            else:
                # pad with last-known step (e.g., 250d) if shorter
                pad_val = horizons[-1] if horizons else 250
                while len(horizons) < ckpt_out_dim:
                    horizons.append(pad_val)
    horizon_labels = _format_horizon_labels(horizons)

    # Device
    device = torch.device(opts.device if (opts.device == "cpu" or torch.cuda.is_available()) else "cpu")

    # Load arrays
    price_data = _load_array(opts.input)
    if price_data.ndim != 3:
        raise ValueError("Price input must be a 3D numpy array: (N, seq_len, feat_dim)")
    _, seq_len, feat_dim = price_data.shape

    text_data = None
    if opts.text_input:
        text_data = _load_array(opts.text_input)
        if text_data.shape[:2] != price_data.shape[:2]:
            raise ValueError("Text input must match (N, seq_len) of price input")

    # Build model
    price_branch = create_price_branch(input_shape=(seq_len, feat_dim))
    text_branch = create_text_branch(input_dim=text_data.shape[2]) if text_data is not None else None
    model = create_fusion_head(
        price_branch=price_branch,
        text_branch=text_branch,
        hidden_dim=opts.hidden_dim,
        dropout=opts.dropout,
        output_dim=len(horizons),
    )
    model.load_state_dict(state)
    model.to(device)
    model.eval()

    # Inference
    with torch.no_grad():
        p_t = torch.tensor(price_data, dtype=torch.float32, device=device)
        t_t = torch.tensor(text_data, dtype=torch.float32, device=device) if text_data is not None else None
        try:
            base_scalar = p_t[:, -1, opts.close_index].unsqueeze(-1)
            preds = model(p_t, t_t, base_scalar).cpu().numpy()
        except TypeError:
            preds = model(p_t, t_t).cpu().numpy()

    clip_env = os.getenv("RETURN_CLIP_MAX")
    clip_val = None
    if clip_env:
        try:
            clip_val = float(clip_env)
        except Exception:
            clip_val = None
    if clip_val is None:
        clip_val = 0.3
    if clip_val and clip_val > 0:
        np.clip(preds, -clip_val, clip_val, out=preds)

    # preds: returns (N, H)
    close_values = _resolve_close_values(price_data, opts.close_values, opts.close_index)
    if close_values.shape[0] != preds.shape[0]:
        raise ValueError("Length of close vector must match number of samples in predictions")
    predicted_prices = close_values[:, None] * (1.0 + preds)

    # Output
    out = {
        "model": str(opts.model),
        "input": str(opts.input),
        "count": int(preds.shape[0]),
        "horizons": horizon_labels,
        "returns": preds.tolist(),
        "current_close": close_values.tolist(),
        "prices": predicted_prices.tolist(),
    }

    opts.output.parent.mkdir(parents=True, exist_ok=True)
    if opts.output.suffix.lower() == ".json":
        opts.output.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        _write_csv(opts.output, horizon_labels, close_values, preds, predicted_prices)

    print(f"Inference completed. Results saved to {opts.output}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run inference with trained multi-horizon model")
    p.add_argument("--model", type=Path, required=True, help="Path to model state_dict (.pth)")
    p.add_argument("--input", type=Path, required=True, help="Price sequence numpy file (N, seq, feat)")
    p.add_argument("--text-input", type=Path, help="Text sequence numpy file (optional)")
    p.add_argument("--output", type=Path, required=True, help="Output file (.json or .csv)")
    p.add_argument("--close-values", type=Path, help="Per-sample base close numpy file (N,)")
    p.add_argument("--close-index", type=int, default=3, help="Index of close feature in price data")
    p.add_argument("--hidden-dim", type=int, default=128, help="Hidden dimension size")
    p.add_argument("--dropout", type=float, default=0.2, help="Dropout probability")
    p.add_argument("--device", default="cuda", help="Device to use (cuda/cpu)")
    p.add_argument("--settings", type=Path, help="Path to settings.yaml (optional)")
    return p


def _load_array(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(path)
    return np.load(path)


def _resolve_close_values(price_data: np.ndarray, close_path: Optional[Path], close_index: int) -> np.ndarray:
    if close_path is not None:
        values = _load_array(close_path)
        if values.ndim != 1:
            raise ValueError("Close values array must be 1-D")
        return values.astype(float)
    if close_index < 0 or close_index >= price_data.shape[2]:
        raise ValueError("close_index is out of feature range")
    return price_data[:, -1, close_index].astype(float)


def _write_csv(path: Path, labels: list[str], closes: np.ndarray, returns: np.ndarray, prices: np.ndarray) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    header = ["index", "current_close"] + [f"return_{l}" for l in labels] + [f"price_{l}" for l in labels]
    with path.open("w", newline="", encoding="utf-8") as fp:
        w = csv.writer(fp)
        w.writerow(header)
        for idx, (c, r_row, p_row) in enumerate(zip(closes, returns, prices)):
            w.writerow([idx, float(c), *r_row.tolist(), *p_row.tolist()])


def _format_horizon_labels(horizons: Iterable[int]) -> list[str]:
    mapping = {1: "1d", 5: "1w", 20: "1m", 120: "6m", 250: "1y", 252: "1y"}
    labels: list[str] = []
    for h in horizons:
        try:
            hh = int(h)
        except Exception:
            labels.append(str(h))
            continue
        if hh in mapping:
            labels.append(mapping[hh])
        elif 240 <= hh <= 260:
            labels.append("1y")
        else:
            labels.append(f"{hh}d")
    return labels


def _find_project_root() -> Path:
    cur = Path(__file__).resolve()
    for p in cur.parents:
        if (p / ".env").exists() or (p / "data").exists():
            return p
    return cur.parents[4]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
