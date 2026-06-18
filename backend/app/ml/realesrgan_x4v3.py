from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class SRVGGNetCompact(nn.Module):
    def __init__(
        self,
        num_in_ch: int = 3,
        num_out_ch: int = 3,
        num_feat: int = 64,
        num_conv: int = 32,
        upscale: int = 4,
        act_type: str = "prelu",
    ) -> None:
        super().__init__()
        self.upscale = upscale

        def make_act():
            if act_type == "relu":
                return nn.ReLU(inplace=True)
            if act_type == "leakyrelu":
                return nn.LeakyReLU(negative_slope=0.1, inplace=True)
            return nn.PReLU(num_parameters=num_feat)

        body: list[nn.Module] = [nn.Conv2d(num_in_ch, num_feat, 3, 1, 1), make_act()]
        for _ in range(num_conv):
            body.extend([nn.Conv2d(num_feat, num_feat, 3, 1, 1), make_act()])
        body.append(nn.Conv2d(num_feat, num_out_ch * upscale * upscale, 3, 1, 1))
        self.body = nn.ModuleList(body)
        self.upsampler = nn.PixelShuffle(upscale)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = x
        for layer in self.body:
            out = layer(out)
        out = self.upsampler(out)
        base = F.interpolate(x, scale_factor=self.upscale, mode="nearest")
        return out + base

