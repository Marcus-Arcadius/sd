from __future__ import annotations
from typing_extensions import Self

from pathlib import Path
import re
import json

import torch
import torch.nn as nn
from torch import Tensor

from ..utils import normalize, denormalize
from ..layers.base import Conv2d, HalfWeightsModel, SplitAttentionModel
from ..layers.distribution import DiagonalGaussianDistribution
from ..layers.auto_encoder import Encoder, Decoder
from .config import VaeConfig


class AutoencoderKL(HalfWeightsModel, SplitAttentionModel, nn.Module):
    debug: bool = False

    @classmethod
    def from_config(cls, path: str | Path) -> Self:
        """'Creates a model from a config file."""

        path = Path(path)
        if path.is_dir():
            path /= "config.json"
        assert path.suffix == ".json"

        db = json.load(open(path, "r"))
        config = VaeConfig(**db)

        return cls(
            in_channels=config.in_channels,
            out_channels=config.out_channels,
            block_out_channels=tuple(config.block_out_channels),
            layers_per_block=config.layers_per_block,
            latent_channels=config.latent_channels,
        )

    def __init__(
        self,
        *,
        in_channels: int = 3,
        out_channels: int = 3,
        block_out_channels: tuple[int, ...] = (128, 256, 512, 512),
        layers_per_block: int = 2,
        latent_channels: int = 4,
        norm_num_groups: int = 32,
    ) -> None:
        super().__init__()

        self.in_channels = in_channels
        self.out_channels = out_channels
        self.block_out_channels = block_out_channels
        self.layers_per_block = layers_per_block
        self.latent_channels = latent_channels
        self.norm_num_groups = norm_num_groups

        self.encoder = Encoder(
            in_channels=in_channels,
            out_channels=latent_channels,
            block_out_channels=block_out_channels,
            layers_per_block=layers_per_block,
            norm_num_groups=norm_num_groups,
            double_z=True,
        )

        self.decoder = Decoder(
            in_channels=latent_channels,
            out_channels=out_channels,
            block_out_channels=block_out_channels,
            layers_per_block=layers_per_block,
            norm_num_groups=norm_num_groups,
        )

        self.quant_conv = Conv2d(2 * latent_channels)
        self.post_quant_conv = Conv2d(latent_channels)

    def encode(self, x: Tensor) -> DiagonalGaussianDistribution:
        """Encode an byte-Tensor into a posterior distribution."""

        x = normalize(x)
        x = self.encoder(x)

        moments = self.quant_conv(x)
        mean, logvar = moments.chunk(2, dim=1)

        return DiagonalGaussianDistribution(mean, logvar)

    def decode(self, z: Tensor) -> Tensor:
        """Decode the latent's space into an image."""

        z = self.post_quant_conv(z)
        out = self.decoder(z)

        out = denormalize(out)

        return out

    @classmethod
    def load_sd(cls, path: str | Path) -> Self:
        """Load Stable-Diffusion from diffusers checkpoint."""

        path = Path(path)
        model = cls.from_config(path)

        state_path = next(path.glob("*.bin"))
        state = torch.load(state_path, map_location="cpu")

        # modify state-dict
        for key in list(state.keys()):
            for (c1, c2) in REPLACEMENTS:
                new_key = re.sub(c1, c2, key)
                if new_key != key:
                    value = state.pop(key)
                    state[new_key] = value

        # debug
        if cls.debug:
            old_keys = list(state.keys())
            new_keys = list(model.state_dict().keys())

            in_old = set(old_keys) - set(new_keys)
            in_new = set(new_keys) - set(old_keys)

            if len(in_old) > 0:
                with open("in-old.txt", "w") as f:
                    f.write("\n".join(sorted(list(in_old))))

            if len(in_new) > 0:
                with open("in-new.txt", "w") as f:
                    f.write("\n".join(sorted(list(in_new))))

        model.load_state_dict(state)

        return model


REPLACEMENTS: list[tuple[str, str]] = [
    # up/down samplers
    (r"(up|down)samplers.0", r"\1sampler"),
    # post_process
    (
        r"(decoder|encoder).conv_norm_out.(bias|weight)",
        r"\1.post_process.0.\2",
    ),
    (r"(decoder|encoder).conv_out.(bias|weight)", r"\1.post_process.2.\2",),
    # resnet-blocks pre/post-process
    (r"resnets.(\d).norm1.(bias|weight)", r"resnets.\1.pre_process.0.\2",),
    (r"resnets.(\d).conv1.(bias|weight)", r"resnets.\1.pre_process.2.\2",),
    (r"resnets.(\d).norm2.(bias|weight)", r"resnets.\1.post_process.0.\2",),
    (r"resnets.(\d).conv2.(bias|weight)", r"resnets.\1.post_process.2.\2",),
]
