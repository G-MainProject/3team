# -*- coding: utf-8 -*-
"""CLI entrypoint for stage-03 model building and training.

정상화한 파서/학습 루프를 포함합니다.
옵션:
- --use-base-price-input: 마지막 종가(또는 현재가)를 스칼라 입력으로 결합
- --close-index: X의 마지막 시점에서 종가 feature 인덱스
- --horizon-weights: 호라이즌별 손실 가중치
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence, Iterable

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from Python.pipeline.pipelines.s2_preprocess import build_datasets

from .fusion_head import create_fusion_head
from .price_branch import create_price_branch
from .text_branch import create_text_branch


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    dataset_cfg = build_datasets._load_config(None, args.gold_root, args.artifacts_root, args.settings)
    # horizons: gold/horizons.json이 있으면 덮어씀
    try:
        gold_root = dataset_cfg.gold_root
        hfile = gold_root / "horizons.json"
        if hfile.exists():
            dataset_cfg.horizons = [int(x) for x in json.loads(hfile.read_text(encoding="utf-8"))]
    except Exception:
        pass
    horizon_labels = _format_horizon_labels(dataset_cfg.horizons)

    seq_len = args.seq_len
    price_dim = args.price_dim

    inferred = _infer_price_shape(dataset_cfg.gold_root)
    if inferred is not None:
        data_seq_len, data_feat_dim = inferred
        if seq_len != data_seq_len:
            print(f"[s3_model] seq-len {seq_len} -> 데이터 기준 {data_seq_len} 로 변경합니다.")
            seq_len = data_seq_len
        if price_dim is None or price_dim != data_feat_dim:
            if price_dim is not None and price_dim != data_feat_dim:
                print(f"[s3_model] price-dim {price_dim} != 데이터 feature {data_feat_dim}; 데이터 기준으로 변경합니다.")
            price_dim = data_feat_dim
    elif price_dim is None:
        raise RuntimeError("가격 feature 차원을 추론하지 못했습니다. --price-dim 옵션을 지정해주세요.")

    price_branch = create_price_branch(input_shape=(seq_len, price_dim))
    text_branch = create_text_branch(input_dim=args.text_dim) if args.text_dim is not None else None

    model = create_fusion_head(
        price_branch=price_branch,
        text_branch=text_branch,
        hidden_dim=args.hidden_dim,
        dropout=args.dropout,
        output_dim=len(dataset_cfg.horizons),
        use_base_scalar=args.use_base_price_input,
    )

    summary = _summarize_model(model, seq_len, price_dim, args.text_dim, len(dataset_cfg.horizons))

    if not args.train:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        device = torch.device(args.device if torch.cuda.is_available() or args.device == "cpu" else "cpu")
        artifacts_root = dataset_cfg.artifacts_root
        gold_root = dataset_cfg.gold_root
        save_best = args.save_best or (artifacts_root / "models" / "model_best.pth")
        save_last = args.save_last or (artifacts_root / "models" / "model_last.pth")

        train_cfg = TrainConfig(
            gold_root=gold_root,
            artifacts_root=artifacts_root,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            device=device,
            save_best=save_best,
            save_last=save_last,
            horizons=dataset_cfg.horizons,
            horizon_labels=horizon_labels,
            close_index=args.close_index,
            horizon_weights=args.horizon_weights,
        )
        run_training(model, train_cfg)

    if args.export is not None:
        out_path = Path(args.export)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), out_path)
        print(f"Model weights saved to {out_path}")

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage-03 model assembly / training (multi-target regression)",
    )
    parser.add_argument("--seq-len", type=int, default=30, help="입력 시퀀스 길이")
    parser.add_argument("--price-dim", type=int, default=None, help="가격 feature 차원 (없으면 gold에서 추론)")
    parser.add_argument("--text-dim", type=int, help="텍스트 가지 입력 차원(옵션)")
    parser.add_argument("--text-hidden", type=int, default=128, help="텍스트 가지 은닉 차원")
    parser.add_argument("--hidden-dim", type=int, default=128, help="Fusion head 은닉 차원")
    parser.add_argument("--dropout", type=float, default=0.2, help="Dropout")
    parser.add_argument("--export", type=Path, help="훈련된 가중치 저장 경로 (state_dict)")

    parser.add_argument("--train", action="store_true", help="학습 실행 플래그")
    parser.add_argument("--settings", type=Path, help="settings.yaml 경로")
    parser.add_argument("--gold-root", type=Path, help="gold 데이터 루트 경로")
    parser.add_argument("--artifacts-root", type=Path, help="아티팩트 루트 경로")
    parser.add_argument("--epochs", type=int, default=20, help="학습 epoch 수")
    parser.add_argument("--batch-size", type=int, default=64, help="배치 크기")
    parser.add_argument("--learning-rate", type=float, default=1e-3, help="학습률")
    parser.add_argument("--device", default="cuda", help="장치 (cuda/cpu)")
    parser.add_argument("--save-best", type=Path, help="최고 성능 가중치 저장 경로")
    parser.add_argument("--save-last", type=Path, help="최근 epoch 가중치 저장 경로")
    # 현재가(기준가) 스칼라 입력 및 호라이즌 가중치 옵션
    parser.add_argument("--use-base-price-input", action="store_true", help="마지막 종가(또는 현재가)를 스칼라 입력으로 결합")
    parser.add_argument("--close-index", type=int, default=3, help="X의 마지막 시점에서 종가 feature 인덱스")
    parser.add_argument("--horizon-weights", nargs="*", type=float, help="호라이즌별 손실 가중치(길이 = 호라이즌 개수)")
    return parser


# ---------------------------------------------------------------------------
# Training implementation
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class TrainConfig:
    gold_root: Path
    artifacts_root: Path
    epochs: int
    batch_size: int
    learning_rate: float
    device: torch.device
    save_best: Path
    save_last: Path
    horizons: list[int]
    horizon_labels: list[str]
    close_index: int = 3
    horizon_weights: Optional[list[float]] = None


class GoldSequenceDataset(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    """gold/X.npy, y.npy를 읽어 시퀀스/타깃을 반환."""

    def __init__(self, x_path: Path, y_path: Path) -> None:
        if not x_path.exists() or not y_path.exists():
            raise FileNotFoundError(f"Dataset files not found: {x_path}, {y_path}")
        self.features = np.load(x_path)
        self.labels = np.load(y_path)
        if self.features.shape[0] != self.labels.shape[0]:
            raise ValueError("X와 y의 샘플 수가 일치하지 않습니다.")

    def __len__(self) -> int:  # type: ignore[override]
        return int(self.features.shape[0])

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:  # type: ignore[override]
        x = torch.tensor(self.features[idx], dtype=torch.float32)
        y = torch.tensor(self.labels[idx], dtype=torch.float32)
        return x, y


def run_training(model: nn.Module, cfg: TrainConfig) -> None:
    device = cfg.device
    model.to(device)

    loaders = {
        split: _create_loader(cfg.gold_root, split, cfg.batch_size)
        for split in ("train", "val", "test")
    }
    if loaders["train"] is None:
        raise RuntimeError("train split 데이터를 찾지 못했습니다. gold/train/X.npy, y.npy 를 확인해주세요.")

    # 가중 손실(reduction='none' 후 수동 가중 평균)
    criterion = nn.MSELoss(reduction='none')
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg.learning_rate)

    best_val_loss = float("inf")
    best_state = None

    for epoch in range(1, cfg.epochs + 1):
        train_metrics = _run_epoch(model, loaders["train"], criterion, optimizer, device, cfg.horizons, cfg.close_index, cfg.horizon_weights, train=True)
        val_metrics = _run_epoch(model, loaders["val"], criterion, None, device, cfg.horizons, cfg.close_index, cfg.horizon_weights, train=False)

        print(
            f"Epoch {epoch}/{cfg.epochs} | "
            f"train_loss={train_metrics['loss']:.4f}, train_mae={train_metrics['mae']:.4f} | "
            f"val_loss={val_metrics['loss']:.4f}, val_mae={val_metrics['mae']:.4f}"
        )

        if val_metrics["loss"] < best_val_loss:
            best_val_loss = val_metrics["loss"]
            best_state = model.state_dict()
            cfg.save_best.parent.mkdir(parents=True, exist_ok=True)
            torch.save(best_state, cfg.save_best)
            print(f"Best model updated -> {cfg.save_best}")

    cfg.save_last.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), cfg.save_last)
    print(f"Last model saved -> {cfg.save_last}")

    if best_state is not None:
        model.load_state_dict(best_state)

    if loaders["test"] is not None:
        test_metrics = _run_epoch(model, loaders["test"], criterion, None, device, cfg.horizons, cfg.close_index, cfg.horizon_weights, train=False)
        per_horizon = {
            label: value
            for label, value in zip(_format_horizon_labels(cfg.horizons), test_metrics["mae_per"])
        }
        print(json.dumps({"test": {"loss": test_metrics["loss"], "mae": test_metrics["mae"], "mae_per": per_horizon}}, ensure_ascii=False, indent=2))


def _run_epoch(
    model: nn.Module,
    loader: Optional[DataLoader],
    criterion: nn.Module,
    optimizer: Optional[torch.optim.Optimizer],
    device: torch.device,
    horizons: Iterable[int],
    close_index: int,
    horizon_weights: Optional[Sequence[float]],
    *,
    train: bool,
) -> Dict[str, float]:
    if loader is None:
        return {"loss": float("nan"), "mae": float("nan"), "mae_per": [float("nan") for _ in horizons]}

    model.train(train)
    total_loss = 0.0
    total = 0
    mae_sum: Optional[torch.Tensor] = None

    weights_tensor: Optional[torch.Tensor] = None
    if horizon_weights is not None and len(list(horizons)) == len(horizon_weights):
        weights_tensor = torch.tensor(horizon_weights, dtype=torch.float32, device=device)

    for price_seq, labels in loader:
        price_seq = price_seq.to(device)
        labels = labels.to(device)

        # base scalar: 마지막 시점 종가를 스칼라 입력으로 공급(옵션)
        base_scalar = price_seq[:, -1, close_index].unsqueeze(-1)
        try:
            preds = model(price_seq, None, base_scalar)
        except TypeError:
            preds = model(price_seq)

        # 가중 손실 계산: (batch,H) -> (H,) -> 스칼라
        loss_mat = criterion(preds, labels)
        if loss_mat.dim() == 0:
            loss = loss_mat
        else:
            per_h = loss_mat.mean(dim=0)
            if weights_tensor is not None:
                loss = (per_h * weights_tensor).sum() / weights_tensor.sum()
            else:
                loss = per_h.mean()

        if train and optimizer is not None:
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        batch_size = labels.size(0)
        total_loss += loss.item() * batch_size
        total += batch_size

        mae_batch = torch.abs(preds - labels).mean(dim=0).detach().cpu() * batch_size
        if mae_sum is None:
            mae_sum = mae_batch
        else:
            mae_sum += mae_batch

    avg_loss = total_loss / max(total, 1)
    if mae_sum is None:
        mae_per = np.zeros(len(list(horizons)))
    else:
        mae_per = (mae_sum / max(total, 1)).numpy()
    mae = float(mae_per.mean())
    return {"loss": avg_loss, "mae": mae, "mae_per": mae_per.tolist()}


def _create_loader(root: Path, split: str, batch_size: int) -> Optional[DataLoader]:
    split_dir = root / split
    x_path = split_dir / "X.npy"
    y_path = split_dir / "y.npy"
    if not x_path.exists() or not y_path.exists():
        return None
    dataset = GoldSequenceDataset(x_path, y_path)
    return DataLoader(dataset, batch_size=batch_size, shuffle=(split == "train"))


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _infer_price_shape(gold_root: Path) -> Optional[tuple[int, int]]:
    for split in ("train", "val", "test"):
        x_path = gold_root / split / "X.npy"
        if not x_path.exists():
            continue
        try:
            array = np.load(x_path, mmap_mode="r")
            return int(array.shape[1]), int(array.shape[2])
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[s3_model] gold/{split}/X.npy 읽기 오류: {exc}")
            continue
    return None


def _summarize_model(model: torch.nn.Module, seq_len: int, price_dim: int, text_dim: Optional[int], output_dim: int) -> dict:
    model.eval()
    with torch.no_grad():
        price_dummy = torch.zeros(1, seq_len, price_dim)
        text_dummy = torch.zeros(1, seq_len, text_dim) if text_dim is not None else None
        # base_scalar dummy
        try:
            outputs = model(price_dummy, text_dummy, torch.zeros(1, 1))
        except TypeError:
            outputs = model(price_dummy, text_dummy)
    param_count = sum(p.numel() for p in model.parameters())
    return {
        "architecture": model.__class__.__name__,
        "parameters": int(param_count),
        "output_shape": list(outputs.shape),
        "targets": output_dim,
    }


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists():
            return parent
    for parent in current.parents:
        if (parent / "data").exists():
            return parent
    return current.parents[4]


def _format_horizon_labels(horizons: Iterable[int]) -> list[str]:
    label_map = {1: "1d", 5: "1w", 20: "1m", 120: "6m", 250: "1y"}
    return [label_map.get(int(h), f"{h}d") for h in horizons]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

