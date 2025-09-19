"""뉴스 임베딩을 요약하는 간단한 텍스트 브랜치."""

from __future__ import annotations

import torch
from torch import nn


class TextBranch(nn.Module):
    """뉴스 임베딩 시퀀스를 평균 Pooling 후 투사한다."""

    def __init__(self, input_dim: int, hidden_dim: int = 128, dropout: float = 0.1) -> None:
        super().__init__()
        self.projection = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
        )
        self.output_dim = hidden_dim

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() != 3:
            raise ValueError("text_branch 입력은 (batch, seq_len, embed_dim) 이어야 합니다.")
        pooled = x.mean(dim=1)
        return self.projection(pooled)


def create_text_branch(*, input_dim: int, hidden_dim: int = 128) -> TextBranch:
    return TextBranch(input_dim=input_dim, hidden_dim=hidden_dim)
