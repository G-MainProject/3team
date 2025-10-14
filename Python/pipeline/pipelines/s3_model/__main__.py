# -*- coding: utf-8 -*-
"""3단계 모델 학습·평가 CLI 엔트리 포인트.

이 스크립트는 가격/텍스트 지표를 입력으로 받아 멀티-호라이즌 회귀 모델을 구성하고, 학습·요약·내보내기까지 수행한다.

주요 옵션:
- --use-base-price-input: 시퀀스 마지막 종가(베이스 가격)를 스칼라 입력으로 추가
- --close-index: 입력 텐서에서 종가가 위치한 인덱스
- --horizon-weights: 예측 호라이즌별 손실 가중치
"""

from __future__ import annotations

import argparse
import json
import math
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
# 명령줄 인터페이스
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    dataset_cfg = build_datasets._load_config(None, args.gold_root, args.artifacts_root, args.settings)
    # horizons: gold/horizons.json이 있으면 호라이즌 목록을 파일에서 읽는다
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
            print(f"[s3_model] seq-len {seq_len} -> 데이터 길이 {data_seq_len}로 조정합니다.")
            seq_len = data_seq_len
        if price_dim is None or price_dim != data_feat_dim:
            if price_dim is not None and price_dim != data_feat_dim:
                print(f"[s3_model] price-dim {price_dim} != 데이터 피처 차원 {data_feat_dim}; 데이터에 맞춰 변경합니다.")
            price_dim = data_feat_dim
    elif price_dim is None:
        raise RuntimeError("가격 피처 차원을 추론하지 못했습니다. --price-dim 옵션을 지정하세요.")

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
            early_stop=bool(args.early_stop),
            patience=int(args.patience),
            min_delta=float(args.min_delta),
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
        description="3단계 모델 구성·학습을 위한 CLI",
    )
    parser.add_argument("--seq-len", type=int, default=30, help="입력 시퀀스 길이")
    parser.add_argument("--price-dim", type=int, default=None, help="가격 피처 차원(지정하지 않으면 gold 데이터에서 추론)")
    parser.add_argument("--text-dim", type=int, help="텍스트 입력 피처 차원(옵션)")
    parser.add_argument("--text-hidden", type=int, default=128, help="텍스트 브랜치 은닉 차원")
    parser.add_argument("--hidden-dim", type=int, default=128, help="퓨전 헤드 은닉 차원")
    parser.add_argument("--dropout", type=float, default=0.4, help="드롭아웃 비율")
    parser.add_argument("--device", default="cuda", help="사용할 디바이스(cuda/cpu)")
    parser.add_argument("--gold-root", type=Path, help="gold 데이터 경로")
    parser.add_argument("--artifacts-root", type=Path, help="학습 산출물 저장 경로")
    parser.add_argument("--settings", type=Path, help="settings.yaml 경로")
    parser.add_argument("--seq-drop", type=int, default=0, help="시퀀스 앞단 샘플을 버릴 개수(0이면 미사용)")
    parser.add_argument("--batch-size", type=int, default=32, help="배치 크기")
    parser.add_argument("--epochs", type=int, default=50, help="학습 epoch 수")
    parser.add_argument("--learning-rate", type=float, default=1e-3, help="학습률")
    parser.add_argument("--close-index", type=int, default=3, help="입력 텐서에서 종가가 위치한 인덱스")
    parser.add_argument("--use-base-price-input", action="store_true", help="마지막 종가(베이스 가격)를 스칼라 입력으로 추가")
    parser.add_argument("--horizon-weights", nargs="*", type=float, help="호라이즌별 손실 가중치")
    parser.add_argument("--train", action="store_true", help="학습을 수행(미지정 시 모델 요약만 출력)")
    parser.add_argument("--save-best", type=Path, help="최고 성능 모델 저장 경로")
    parser.add_argument("--save-last", type=Path, help="마지막 모델 저장 경로")
    parser.add_argument("--early-stop", action="store_true", help="검증 손실 기준 조기 종료 사용")
    parser.add_argument("--patience", type=int, default=5, help="조기 종료 대기 epoch 수")
    parser.add_argument("--min-delta", type=float, default=0.001, help="조기 종료 판단을 위한 최소 개선폭")
    parser.add_argument("--recency-weighting", choices=["none", "linear", "exp"], default="exp", help="최근 샘플 가중 방식(none/linear/exp)")
    parser.add_argument("--recency-decay", type=float, default=1.5, help="최근 샘플 가중 강도")
    parser.add_argument("--export", type=Path, help="학습한 가중치(state_dict) 저장 경로")
    parser.add_argument("--report-json", type=Path, help="학습 요약 정보를 JSON으로 저장")
    return parser



# ---------------------------------------------------------------------------
# 학습 구현부
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class TrainConfig:
    # 필수 인자(기본값 없음)는 앞쪽에 배치
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

    # 선택 인자(기본값이 있는 항목)는 그 다음에 배치
    close_index: int = 3
    horizon_weights: Optional[list[float]] = None
    # 최근 샘플 가중치 설정
    recency_weighting: str = "none"
    recency_decay: float = 1.5
    sample_weights: Optional[torch.Tensor] = None
    # 조기 종료 설정
    early_stop: bool = False
    patience: int = 5
    min_delta: float = 0.001


class GoldSequenceDataset(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    """gold/X.npy와 y.npy를 읽어 시퀀스 데이터를 반환한다."""

    def __init__(self, x_path: Path, y_path: Path) -> None:
        if not x_path.exists() or not y_path.exists():
            raise FileNotFoundError(f"Dataset files not found: {x_path}, {y_path}")
        self.features = np.load(x_path)
        self.labels = np.load(y_path)
        if self.features.shape[0] != self.labels.shape[0]:
            raise ValueError("features와 labels의 샘플 수가 일치하지 않습니다.")

    def __len__(self) -> int:  # type: ignore[override]
        return int(self.features.shape[0])

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor, int]:  # type: ignore[override]
        x = torch.tensor(self.features[idx], dtype=torch.float32)
        y = torch.tensor(self.labels[idx], dtype=torch.float32)
        return x, y, int(idx)


def run_training(model: nn.Module, cfg: TrainConfig) -> None:
    device = cfg.device
    model.to(device)

    loaders = {
        split: _create_loader(cfg.gold_root, split, cfg.batch_size)
        for split in ("train", "val", "test")
    }
    if loaders["train"] is None:
        raise RuntimeError("train 분할을 찾을 수 없습니다. gold/train/X.npy, y.npy를 확인하세요.")

    # SmoothL1Loss(reduction='none')로 호라이즌별 손실을 계산
    criterion = nn.SmoothL1Loss(reduction='none')
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg.learning_rate, weight_decay=2e-4)

    # Build per-sample recency weights (train only)
    if getattr(cfg, "recency_weighting", "none") != "none" and loaders.get("train") is not None:
        try:
            ds = loaders["train"].dataset  # type: ignore[attr-defined]
            import numpy as _np
            N = int(getattr(ds, "features").shape[0])
            pos = _np.linspace(0.0, 1.0, N)
            if cfg.recency_weighting == "linear":
                w = 1.0 + float(cfg.recency_decay) * pos
            else:
                w = _np.exp(float(cfg.recency_decay) * pos)
            mean = w.mean() if w.mean() != 0 else 1.0
            w = w / mean
            cfg.sample_weights = torch.tensor(w, dtype=torch.float32, device=cfg.device)
        except Exception:
            cfg.sample_weights = None

    best_val_loss = float("inf")
    best_state = None
    best_epoch = None
    best_train_snapshot = None
    best_val_snapshot = None

    train_history = []
    val_history = []
    no_improve = 0  # early stopping counter

    def _categorize_overfit(diff: float) -> str:
        if not math.isfinite(diff):
            return "unknown"
        if diff <= 0.002:
            return "low"
        if diff <= 0.01:
            return "moderate"
        return "high"

    def _clean_float(value: float | None) -> float | None:
        if value is None:
            return None
        return value if math.isfinite(value) else None


    for epoch in range(1, cfg.epochs + 1):
        train_metrics = _run_epoch(model, loaders["train"], criterion, optimizer, device, cfg.horizons, cfg.close_index, cfg.horizon_weights, getattr(cfg, "sample_weights", None), train=True)
        val_metrics = _run_epoch(model, loaders["val"], criterion, None, device, cfg.horizons, cfg.close_index, cfg.horizon_weights, None, train=False)

        train_history.append({"epoch": epoch, **train_metrics})
        val_history.append({"epoch": epoch, **val_metrics})

        print(
            f"Epoch {epoch}/{cfg.epochs} | "
            f"train_loss={train_metrics['loss']:.4f}, train_mae={train_metrics['mae']:.4f} | "
            f"val_loss={val_metrics['loss']:.4f}, val_mae={val_metrics['mae']:.4f}"
        )

        # Check improvement (min_delta)
        if val_metrics["loss"] < (best_val_loss - cfg.min_delta):
            best_val_loss = val_metrics["loss"]
            best_state = model.state_dict()
            best_epoch = epoch
            best_train_snapshot = train_history[-1].copy()
            best_val_snapshot = val_history[-1].copy()
            cfg.save_best.parent.mkdir(parents=True, exist_ok=True)
            torch.save(best_state, cfg.save_best)
            print(f"Best model updated -> {cfg.save_best}")
            no_improve = 0
        else:
            no_improve += 1

        # Early stopping
        if cfg.early_stop and no_improve >= cfg.patience:
            print(f"Early stopping triggered at epoch {epoch} (no improvement for {cfg.patience} epochs)")
            break

    final_train = train_history[-1] if train_history else None
    final_val = val_history[-1] if val_history else None

    final_train_loss = float(final_train.get("loss", float("nan"))) if final_train else float("nan")
    final_val_loss = float(final_val.get("loss", float("nan"))) if final_val else float("nan")

    overfit_score = final_val_loss - final_train_loss if math.isfinite(final_val_loss) and math.isfinite(final_train_loss) else float("nan")
    overfit_ratio = (final_val_loss / final_train_loss) if math.isfinite(final_val_loss) and math.isfinite(final_train_loss) and final_train_loss != 0.0 else float("nan")

    overfit_entry = {
        "score": _clean_float(overfit_score),
        "ratio": _clean_float(overfit_ratio),
        "category": _categorize_overfit(overfit_score),
    }

    metrics_payload = {
        "epochs": cfg.epochs,
        "train_history": train_history,
        "val_history": val_history,
        "final": {
            "train": final_train,
            "val": final_val,
            "overfit": overfit_entry,
        },
        "best": {
            "epoch": best_epoch,
            "train": best_train_snapshot,
            "val": best_val_snapshot,
            "val_loss": _clean_float(best_val_loss),
        },
    }

    metrics_path = cfg.artifacts_root / "models" / "training_metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    cfg.save_last.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), cfg.save_last)
    print(f"Last model saved -> {cfg.save_last}")

    if best_state is not None:
        model.load_state_dict(best_state)

    if loaders["test"] is not None:
        test_metrics = _run_epoch(
            model,
            loaders["test"],
            criterion,
            None,
            device,
            cfg.horizons,
            cfg.close_index,
            cfg.horizon_weights,
            None,
            train=False,
        )
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
    sample_weights: Optional[torch.Tensor],
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

    for batch in loader:
        if isinstance(batch, (list, tuple)) and len(batch) == 3:
            price_seq, labels, idxs = batch
        else:
            price_seq, labels = batch  # type: ignore[misc]
            idxs = None
        price_seq = price_seq.to(device)
        labels = labels.to(device)

        # base scalar: 마지막 시점 종가를 스칼라 형태로 추가(옵션)
        base_scalar = price_seq[:, -1, close_index].unsqueeze(-1)
        try:
            preds = model(price_seq, None, base_scalar)
        except TypeError:
            preds = model(price_seq)

        # 호라이즌별 손실을 계산해 샘플 단위로 축약하고 가중치(옵션)를 적용
        loss_mat = criterion(preds, labels)  # (B,H) or scalar
        if loss_mat.dim() == 0:
            per_sample = loss_mat.view(1)
        else:
            if weights_tensor is not None:
                wh = weights_tensor / (weights_tensor.sum() if weights_tensor.sum() != 0 else 1.0)
                per_sample = (loss_mat * wh).sum(dim=1)
            else:
                per_sample = loss_mat.mean(dim=1)
        if sample_weights is not None and idxs is not None:
            if not torch.is_tensor(idxs):
                idxs = torch.tensor(idxs, dtype=torch.long, device=sample_weights.device)
            w = sample_weights[idxs]
            loss = (per_sample * w).sum() / (w.sum() if w.sum() != 0 else 1.0)
        else:
            loss = per_sample.mean()

        if train and optimizer is not None:
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
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
# 유틸리티 함수
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
            print(f"[s3_model] gold/{split}/X.npy 로딩 오류: {exc}")
            continue
    return None


def _summarize_model(model: torch.nn.Module, seq_len: int, price_dim: int, text_dim: Optional[int], output_dim: int) -> dict:
    model.eval()
    with torch.no_grad():
        price_dummy = torch.zeros(1, seq_len, price_dim)
        text_dummy = torch.zeros(1, seq_len, text_dim) if text_dim is not None else None
        # base_scalar 더미 입력
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
