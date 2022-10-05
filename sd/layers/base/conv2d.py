from __future__ import annotations
from typing import Optional

import torch.nn as nn

from .half_weights import HalfWeights


class Conv2d(HalfWeights, nn.Conv2d):
    # bypass_half: bool = False

    def __init__(
        self,
        in_channels: int,
        out_channels: Optional[int] = None,
        *,
        kernel_size: int = 1,
        stride: int = 1,
        padding: int = 0,
        groups: int = 1,
        bias: bool = True,
    ) -> None:
        out_channels = out_channels or in_channels

        super().__init__(
            in_channels=in_channels,
            out_channels=out_channels,
            kernel_size=kernel_size,
            stride=stride,
            padding=padding,
            groups=groups,
            bias=bias,
        )

    # ! Hacky fix NaN when using half-precision
    # def forward(self, x: Tensor) -> Tensor:
    #     if self.bypass_half:
    #         return super().forward(x.float()).half()

    #     out = super().forward(x)

    #     if torch.isnan(out).any():
    #         self.bypass_half = True
    #         self.float()
    #         out = super().forward(x.float()).half()

    #     return out
