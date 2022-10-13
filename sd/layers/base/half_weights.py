from __future__ import annotations
from typing_extensions import Self

import torch.nn as nn
from torch import Tensor


class HalfWeights(nn.Module):
    use_half_weights: bool = False

    def half_weights(self, use: bool = True) -> None:
        self.use_half_weights = use

        if use:
            self.half()
        else:
            self.float()

    def half_weights_forward(self, x: Tensor) -> Tensor:
        if not self.use_half_weights:
            return super().forward(x)

        self.float()
        out = super().forward(x)
        self.half()

        return out


class HalfWeightsModel(nn.Module):
    def half_weights(self, use: bool = True) -> Self:
        """Store the weights in half-precision but
    compute forward pass in full precision.
    Useful for GPUs that gives NaN when used in half-precision.
    """

        for name, module in self.named_modules():
            if isinstance(module, HalfWeights):
                module.half_weights(use)

        return self
