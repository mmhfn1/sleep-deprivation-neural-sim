"""
Brain Region Firing Rate Model.

rate(t) = f_floor + (f_base - f_floor) * (1 - 0.92 * tanh(|α| * W))

For amygdala (α < 0): rate = f_base * (1 + 0.65 * tanh(|α| * W))  → increases.
Biological floor = floor_fraction * baseline → neurons never go silent.
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Optional
from .two_process_model import TwoProcessState


@dataclass(frozen=True)
class RegionParams:
    name:             str
    display_name:     str
    baseline_hz:      float
    floor_fraction:   float
    alpha:            float
    circadian_weight: float
    color_rgb:        tuple


REGION_PARAMS: dict[str, RegionParams] = {
    "pfc": RegionParams(
        name="pfc", display_name="Prefrontal Cortex",
        baseline_hz=35.0, floor_fraction=0.08, alpha=0.90,
        circadian_weight=0.80, color_rgb=(100, 149, 237),
    ),
    "hippocampus": RegionParams(
        name="hippocampus", display_name="Hippocampus",
        baseline_hz=28.0, floor_fraction=0.08, alpha=0.75,
        circadian_weight=0.55, color_rgb=(50, 205, 100),
    ),
    "thalamus": RegionParams(
        name="thalamus", display_name="Thalamus",
        baseline_hz=40.0, floor_fraction=0.10, alpha=0.65,
        circadian_weight=0.75, color_rgb=(180, 100, 220),
    ),
    "amygdala": RegionParams(
        name="amygdala", display_name="Amygdala",
        baseline_hz=22.0, floor_fraction=0.10, alpha=-0.50,
        circadian_weight=0.25, color_rgb=(220, 70, 70),
    ),
    "brainstem": RegionParams(
        name="brainstem", display_name="Brainstem RAS",
        baseline_hz=30.0, floor_fraction=0.12, alpha=0.45,
        circadian_weight=0.30, color_rgb=(240, 160, 30),
    ),
}

REGION_ORDER: list[str] = ["pfc", "hippocampus", "thalamus", "amygdala", "brainstem"]


@dataclass
class RegionState:
    name:           str
    firing_rate_hz: float
    baseline_hz:    float
    suppression:    float
    trend:          str


class BrainRegionModel:
    def __init__(self):
        self.params = REGION_PARAMS

    def compute_firing_rate(
        self,
        region_name: str,
        state: TwoProcessState,
        pharma_modifiers: Optional[dict[str, float]] = None,
    ) -> RegionState:
        p      = self.params[region_name]
        W      = state.W
        C      = state.C
        f_base = p.baseline_hz
        f_floor= f_base * p.floor_fraction

        suppression_raw = float(np.tanh(abs(p.alpha) * W))

        if p.alpha >= 0.0:
            rate = f_floor + (f_base - f_floor) * (1.0 - 0.92 * suppression_raw)
        else:
            rate = f_base * (1.0 + 0.65 * suppression_raw)

        # Circadian modulation ±8%
        rate *= 1.0 + 0.08 * p.circadian_weight * (C - 0.5)

        if pharma_modifiers and region_name in pharma_modifiers:
            rate *= pharma_modifiers[region_name]

        rate = max(rate, f_floor)

        if p.alpha >= 0.0:
            sup = float(np.clip(1.0 - (rate - f_floor) / max(f_base - f_floor, 1e-9), 0.0, 1.0))
        else:
            sup = 0.0

        trend = "↑" if rate > f_base * 1.04 else ("↓" if rate < f_base * 0.96 else "→")

        return RegionState(
            name=region_name,
            firing_rate_hz=float(np.clip(rate, 0.1, 300.0)),
            baseline_hz=f_base,
            suppression=sup,
            trend=trend,
        )

    def compute_all_regions(
        self,
        state: TwoProcessState,
        pharma_modifiers: Optional[dict[str, float]] = None,
    ) -> dict[str, RegionState]:
        return {n: self.compute_firing_rate(n, state, pharma_modifiers) for n in REGION_ORDER}

    def compute_microsleep_probability(self, hours_awake: float) -> float:
        if hours_awake < 28.0: return 0.0
        frac = (hours_awake - 28.0) / (72.0 - 28.0)
        return float(np.clip(0.005 + 0.035 * frac, 0.0, 0.04))

    def compute_impairment_index(self, region_states: dict[str, RegionState]) -> float:
        weights = {"pfc": 0.35, "hippocampus": 0.25, "thalamus": 0.20,
                   "amygdala": 0.10, "brainstem": 0.10}
        total = 0.0
        for name, rs in region_states.items():
            p = self.params[name]
            w = weights.get(name, 0.0)
            if p.alpha >= 0.0:
                floor = p.baseline_hz * p.floor_fraction
                drop  = float(np.clip(1.0 - (rs.firing_rate_hz - floor) / max(p.baseline_hz - floor, 1e-9), 0.0, 1.0))
                total += w * drop
            else:
                excess = float(np.clip((rs.firing_rate_hz - p.baseline_hz) / (p.baseline_hz * 0.65), 0.0, 1.0))
                total += w * excess
        return float(np.clip(total, 0.0, 1.0))
