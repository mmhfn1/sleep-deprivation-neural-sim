"""
Stochastic Spike Generator — inhomogeneous Poisson process.

P(spike | rate λ, dt) = 1 - exp(-λ·dt)

At 60 FPS, dt = 1/60 s.
PFC floor 2.8 Hz  → P ≈ 4.5%  (sparse, never zero → no flatline)
PFC peak 35 Hz    → P ≈ 44%   (dense realistic bursting)
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Optional
from .brain_regions import RegionState, REGION_ORDER


@dataclass
class SpikeEvent:
    region_name:         str
    node_index:          int
    amplitude:           float
    is_microsleep_burst: bool = False


class SpikeGenerator:
    _MICRO_MIN_FRAMES  = 4
    _MICRO_MAX_FRAMES  = 12
    _MICRO_SUPPRESSION = 0.05

    def __init__(self, node_counts: dict[str, int], rng_seed: Optional[int] = None):
        self.node_counts = node_counts
        self.rng = np.random.default_rng(rng_seed)
        self._micro_active:    dict[str, bool] = {r: False for r in node_counts}
        self._micro_countdown: dict[str, int]  = {r: 0     for r in node_counts}

    def generate_frame_spikes(
        self,
        region_states: dict[str, RegionState],
        dt: float = 1.0 / 60.0,
        W: float = 0.0,
        microsleep_prob: float = 0.0,
    ) -> list[SpikeEvent]:
        self._tick_microsleep("thalamus", microsleep_prob)
        events: list[SpikeEvent] = []

        for region_name, rs in region_states.items():
            n_nodes     = self.node_counts.get(region_name, 40)
            in_micro    = self._micro_active.get(region_name, False)
            base_rate   = rs.firing_rate_hz * (self._MICRO_SUPPRESSION if in_micro else 1.0)
            noise_sigma = base_rate * 0.08 * (1.0 + 0.5 * W)
            noisy_rate  = float(np.clip(base_rate + self.rng.normal(0.0, noise_sigma), 0.1, 400.0))
            p_spike     = 1.0 - np.exp(-noisy_rate * dt)
            fired       = np.where(self.rng.random(n_nodes) < p_spike)[0]

            for idx in fired:
                amp = float(np.clip(noisy_rate / max(rs.baseline_hz, 1.0) + self.rng.normal(0.0, 0.04), 0.1, 3.0))
                events.append(SpikeEvent(
                    region_name=region_name,
                    node_index=int(idx),
                    amplitude=amp,
                    is_microsleep_burst=in_micro,
                ))
        return events

    def reset(self):
        self._micro_active    = {r: False for r in self.node_counts}
        self._micro_countdown = {r: 0     for r in self.node_counts}

    def is_in_microsleep(self, region_name: str) -> bool:
        return self._micro_active.get(region_name, False)

    def validate_no_flatline(self, region_states: dict[str, RegionState]) -> bool:
        return all(rs.firing_rate_hz > 0.1 for rs in region_states.values())

    def _tick_microsleep(self, region_name: str, prob: float):
        if self._micro_active.get(region_name, False):
            self._micro_countdown[region_name] -= 1
            if self._micro_countdown[region_name] <= 0:
                self._micro_active[region_name] = False
        elif prob > 0.0 and self.rng.random() < prob:
            duration = int(self.rng.integers(self._MICRO_MIN_FRAMES, self._MICRO_MAX_FRAMES + 1))
            self._micro_active[region_name]    = True
            self._micro_countdown[region_name] = duration
