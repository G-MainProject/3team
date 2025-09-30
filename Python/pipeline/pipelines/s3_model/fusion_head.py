# -*- coding: utf-8 -*-
"""가격/텍스트 브랜치를 결합해 회귀 출력을 생성하는 헤드 모듈."""

from __future__ import annotations

from typing import Optional

import torch
from torch import nn


class FusionClassifier(nn.Module):
    """여러 브랜치에서 추출한 특징을 결합해 다중 출력 회귀를 수행한다."""

    def __init__(
        self,
        price_branch: nn.Module,
        text_branch: Optional[nn.Module] = None,
        hidden_dim: int = 128,
        dropout: float = 0.2,
        output_dim: int = 5,
        use_base_scalar: bool = False,
    ) -> None:
        super().__init__()
        self.price_branch = price_branch
        self.text_branch = text_branch
        self.output_dim = output_dim
        self.use_base_scalar = use_base_scalar

        fused_dim = self._infer_dim(price_branch)
        if text_branch is not None:
            fused_dim += self._infer_dim(text_branch)

        # 현재가/기준가(스칼라) 입력을 임베딩해 결합할 수 있도록 선택 지원
        if self.use_base_scalar:
            self.base_scalar_proj = nn.Sequential(
                nn.Linear(1, max(8, hidden_dim // 8)),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout),
            )
            fused_dim += max(8, hidden_dim // 8)

        self.classifier = nn.Sequential(
            nn.Linear(fused_dim, hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(
        self,
        price_seq: torch.Tensor,
        text_seq: Optional[torch.Tensor] = None,
        base_scalar: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        price_feat = self.price_branch(price_seq)
        features = [price_feat]
        if self.text_branch is not None and text_seq is not None:
            features.append(self.text_branch(text_seq))
        if self.use_base_scalar and base_scalar is not None:
            # base_scalar: (batch, 1) 또는 (batch,) 허용
            if base_scalar.dim() == 1:
                base_scalar = base_scalar.unsqueeze(-1)
            features.append(self.base_scalar_proj(base_scalar.float()))
        fused = torch.cat(features, dim=-1)
        return self.classifier(fused)

    @staticmethod
    def _infer_dim(module: nn.Module) -> int:
        if hasattr(module, "output_dim"):
            return int(getattr(module, "output_dim"))
        raise RuntimeError("브랜치 모듈에서 output_dim 속성을 찾을 수 없습니다. create_* 함수를 사용해 주세요.")


def create_fusion_head(
    *,
    price_branch: nn.Module,
    text_branch: Optional[nn.Module] = None,
    hidden_dim: int = 128,
    dropout: float = 0.2,
    output_dim: int = 5,
    use_base_scalar: bool = False,
) -> FusionClassifier:
    return FusionClassifier(
        price_branch=price_branch,
        text_branch=text_branch,
        hidden_dim=hidden_dim,
        dropout=dropout,
        output_dim=output_dim,
        use_base_scalar=use_base_scalar,
    )
