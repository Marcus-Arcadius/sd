from __future__ import annotations
from typing_extensions import Self

import torch.nn as nn


class InPlace(nn.Module):
    """Use in-place operations to save memory."""

    inplace: bool = True


class InPlaceModel(nn.Module):
    # TODO docstring duplicates
    """Use in-place operations to save memory."""
    
    def set_inplace(self, inplace: bool = False) -> Self:
        for name, module in self.named_modules():
            if isinstance(module, InPlace):
                module.inplace = inplace

        return self
