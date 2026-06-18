from __future__ import annotations

import gc
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn

from app.core.config import settings
from app.core.logging import logger
from app.ml.generator import Generator
from app.ml.realesrgan_x4v3 import SRVGGNetCompact
from app.ml.rrdbnet import RRDBNet


def resolve_device() -> torch.device:
    if settings.MODEL_DEVICE == "cpu":
        return torch.device("cpu")
    if settings.MODEL_DEVICE == "cuda":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_state(path: Path) -> dict:
    state = torch.load(path, map_location="cpu", weights_only=True)
    if isinstance(state, dict) and "params_ema" in state:
        return state["params_ema"]
    if isinstance(state, dict) and "params" in state:
        return state["params"]
    return state


def _remap_bsrgan_keys(state: dict) -> dict:
    """Remap BSRGAN/ESRGAN-style keys to our RRDBNet naming convention."""
    mapping = {
        "RRDB_trunk.": "body.",
        ".RDB1.": ".rdb1.",
        ".RDB2.": ".rdb2.",
        ".RDB3.": ".rdb3.",
        "trunk_conv.": "conv_body.",
        "upconv1.": "conv_up1.",
        "upconv2.": "conv_up2.",
        "HRconv.": "conv_hr.",
    }
    remapped = {}
    for key, value in state.items():
        new_key = key
        for old, new in mapping.items():
            new_key = new_key.replace(old, new)
        remapped[new_key] = value
    return remapped


def _blend_states(state_a: dict, state_b: dict, weight_a: float, weight_b: float) -> dict:
    out = {}
    for key in state_a.keys():
        out[key] = weight_a * state_a[key] + weight_b * state_b[key]
    return out


class ModelCache:
    """Memory-safe model loader. Keeps at most one model in memory at a time."""

    def __init__(self) -> None:
        self._current_name: str | None = None
        self._current_model: nn.Module | None = None
        self._device: torch.device = resolve_device()

    def load(self, name: str) -> tuple[nn.Module, torch.device]:
        """Load a model by name, evicting any previously loaded model."""
        if self._current_name == name and self._current_model is not None:
            return self._current_model, self._device

        # Evict current model
        self.unload()

        logger.info("Loading model: %s", name)
        model = self._build_model(name)
        model.eval().to(self._device)
        self._current_name = name
        self._current_model = model
        logger.info("Model %s loaded (%.1fMB)", name, self._model_size_mb(model))
        return model, self._device

    def unload(self) -> None:
        """Free the currently loaded model from memory."""
        if self._current_model is not None:
            logger.info("Unloading model: %s", self._current_name)
            self._current_model.cpu()
            del self._current_model
            self._current_model = None
            self._current_name = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()

    def _build_model(self, name: str) -> nn.Module:
        if name == "srgan":
            model = Generator()
            state = torch.load(settings.SRGAN_WEIGHTS, map_location="cpu", weights_only=True)
            model.load_state_dict(state, strict=True)
            return model

        if name == "realesrgan":
            model = SRVGGNetCompact(num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=32, upscale=4, act_type="prelu")
            general = _load_state(settings.REALESRGAN_X4_WEIGHTS)
            wdn = _load_state(settings.REALESRGAN_WDN_X4_WEIGHTS)
            alpha = settings.DENOISE_STRENGTH
            state = _blend_states(general, wdn, alpha, 1.0 - alpha)
            model.load_state_dict(state, strict=True)
            return model

        if name == "realesrgan_x4plus":
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
            state = _load_state(settings.REALESRGAN_X4PLUS_WEIGHTS)
            model.load_state_dict(state, strict=True)
            return model

        if name == "bsrgan":
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
            state = _remap_bsrgan_keys(_load_state(settings.BSRGAN_WEIGHTS))
            model.load_state_dict(state, strict=True)
            return model

        raise ValueError(f"Unknown model: {name}")

    @staticmethod
    def _model_size_mb(model: nn.Module) -> float:
        return sum(p.numel() * p.element_size() for p in model.parameters()) / (1024 * 1024)


# Singleton instance
model_cache = ModelCache()
