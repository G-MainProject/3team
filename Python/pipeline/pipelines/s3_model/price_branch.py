"""가격 시계열용 CNN+BiLSTM 기반 브랜치 모듈."""

from __future__ import annotations

import torch
from torch import nn


class PriceBranch(nn.Module):
    """OHLCV 시퀀스를 입력받아 가격 특징 벡터를 추출하는 모듈."""

    def __init__(
        self,
        input_channels: int,
        conv_channels: tuple[int, ...] = (32, 64),
        lstm_hidden: int = 64,
        lstm_layers: int = 1,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        in_ch = input_channels
        for out_ch in conv_channels:
            layers.append(nn.Conv1d(in_ch, out_ch, kernel_size=3, padding=1))
            layers.append(nn.BatchNorm1d(out_ch))
            layers.append(nn.ReLU(inplace=True))
            layers.append(nn.Dropout(dropout))
            in_ch = out_ch
        self.conv = nn.Sequential(*layers)

        self.lstm = nn.LSTM(
            input_size=in_ch,
            hidden_size=lstm_hidden,
            num_layers=lstm_layers,
            batch_first=True,
            dropout=dropout if lstm_layers > 1 else 0.0,
            bidirectional=True,
        )
        self.global_pool = nn.AdaptiveAvgPool1d(1)
        self.projection = nn.Sequential(
            nn.Linear(lstm_hidden * 2, lstm_hidden),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
        )
        self.output_dim = lstm_hidden

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # 입력 형태: (batch, seq_len, feature_dim)
        x = x.transpose(1, 2)  # Conv1d 입력을 위해 (batch, feature_dim, seq_len)
        x = self.conv(x)
        x = x.transpose(1, 2)  # LSTM 입력을 위해 (batch, seq_len, channels)
        lstm_out, _ = self.lstm(x)
        pooled = self.global_pool(lstm_out.transpose(1, 2)).squeeze(-1)
        return self.projection(pooled)


def create_price_branch(*, input_shape: tuple[int, ...]):
    """OHLCV 텐서를 처리하는 가격 브랜치를 생성한다."""

    if len(input_shape) != 2:
        raise ValueError("input_shape는 (sequence_length, feature_dim) 형태여야 합니다.")
    _, feature_dim = input_shape
    return PriceBranch(input_channels=feature_dim)
