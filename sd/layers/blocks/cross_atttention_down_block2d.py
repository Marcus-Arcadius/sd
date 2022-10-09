from __future__ import annotations
from typing import NamedTuple, Optional

import torch.nn as nn
from torch import Tensor

from ..resampling import Downsample2D
from ..attention import SpatialTransformer
from .resnet_block2d import ResnetBlock2D
from .utils import OutputStates


class CrossAttentionDownBlock2D(nn.Module):
    def __init__(
        self,
        *,
        in_channels: int,
        out_channels: int,
        temb_channels: int,
        num_layers: int,
        resnet_groups: int,
        attn_num_head_channels: int,
        cross_attention_dim: int,
        downsample_padding: int,
        add_downsample: bool,
    ) -> None:
        super().__init__()

        self.in_channels = in_channels
        self.out_channels = out_channels
        self.temb_channels = temb_channels
        self.num_layers = num_layers
        self.resnet_groups = resnet_groups
        self.attn_num_head_channels = attn_num_head_channels
        self.cross_attention_dim = cross_attention_dim
        self.downsample_padding = downsample_padding
        self.add_downsample = add_downsample

        self.resnets = nn.ModuleList()
        self.attentions = nn.ModuleList()
        for i in range(num_layers):
            in_channels = in_channels if i == 0 else out_channels

            self.resnets.append(
                ResnetBlock2D(
                    in_channels=in_channels,
                    out_channels=out_channels,
                    temb_channels=temb_channels,
                    groups=resnet_groups,
                    groups_out=None,
                )
            )

            self.attentions.append(
                SpatialTransformer(
                    in_channels=out_channels,
                    num_heads=attn_num_head_channels,
                    dim_head=out_channels // attn_num_head_channels,
                    depth=1,
                    num_groups=resnet_groups,
                    context_dim=cross_attention_dim,
                )
            )

        if add_downsample:
            self.downsampler = Downsample2D(
                channels=in_channels,
                use_conv=True,
                out_channels=out_channels,
                padding=downsample_padding,
            )
        else:
            self.downsampler = None

    def forward(
        self,
        x: Tensor,
        *,
        temb: Optional[Tensor] = None,
        context: Optional[Tensor] = None,
    ) -> OutputStates:
        states: list[Tensor] = []
        for resnet, attn in zip(self.resnets, self.attentions):
            x = resnet(x, temb=temb)
            x = attn(x, context=context)

            states.append(x)
        del temb, context

        if self.downsampler is not None:
            x = self.downsampler(x)

            states.append(x)

        return OutputStates(x, states)
