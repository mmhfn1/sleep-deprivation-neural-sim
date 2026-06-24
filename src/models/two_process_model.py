"""
Borbély (1982) Two-Process Model of Sleep Regulation.

Process S: Homeostatic sleep pressure — adenosine accumulation.
  dS/dt = (1 - S) / τ_w
  At t=72h, S ≈ 0.982 — asymptotic, NEVER reaches 1.0.

Process C: Circadian alerting signal — SCN oscillator.
  C(t) = 0.5 * [1 + cos(2π(t - φ) / T)]

Combined propensity W = clip(μ_S·S - μ_C·C, 0, 1).
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Optional


def impairment_label(W: float) -> str:
    if W < 0.25:  return "NORMAL"
    if W < 0.45:  return "MILD"
    if W < 0.60:  return "MODERATE"
    if W < 0.75:  return "SEVERE"
    return "CRITICAL"


@dataclass
class TwoProcessParams:
    tau_w: float = 18.2
    tau_s: float = 4.2
    S0:    float = 0.20
    phi:   float = 14.0
    T:     float = 24.0
    mu_S:  float = 0.85
    mu_C:  float = 0.40
    dt:    float = 0.10


@dataclass
class TwoProcessState:
    t:                float
    S:                float
    C:                float
    W:                float
    impairment_level: str


class TwoProcessModel:
    def __init__(self, params: Optional[TwoProcessParams] = None):
        self.p = params or TwoProcessParams()
        self._states: list[TwoProcessState] = []
        self._solved = False

    def _circadian(self, t: float) -> float:
        return 0.5 * (1.0 + np.cos(2.0 * np.pi * (t - self.p.phi) / self.p.T))

    def _dS_dt(self, S: float) -> float:
        return (1.0 - S) / self.p.tau_w

    def _propensity(self, S: float, C: float) -> float:
        return float(np.clip(self.p.mu_S * S - self.p.mu_C * C, 0.0, 1.0))

    def solve(self, max_hours: float = 72.0) -> list[TwoProcessState]:
        states: list[TwoProcessState] = []
        S = self.p.S0
        t = 0.0
        n_steps = int(round(max_hours / self.p.dt)) + 1
        for _ in range(n_steps):
            C = float(self._circadian(t))
            W = self._propensity(S, C)
            states.append(TwoProcessState(
                t=round(t, 4), S=S, C=C, W=W,
                impairment_level=impairment_label(W),
            ))
            S = float(np.clip(S + self.p.dt * self._dS_dt(S), self.p.S0, 0.99999))
            t += self.p.dt
        self._states = states
        self._solved = True
        return states

    def get_state_at_hour(self, hour: float) -> TwoProcessState:
        if not self._solved: self.solve()
        idx = int(round(hour / self.p.dt))
        return self._states[max(0, min(idx, len(self._states) - 1))]

    def get_hourly_states(self) -> list[TwoProcessState]:
        if not self._solved: self.solve()
        hourly = []
        for h in range(73):
            idx = int(round(h / self.p.dt))
            hourly.append(self._states[max(0, min(idx, len(self._states) - 1))])
        return hourly

    def validate(self) -> dict:
        if not self._solved: self.solve()
        S_vals = [s.S for s in self._states]
        C_vals = [s.C for s in self._states]
        W_vals = [s.W for s in self._states]
        return {
            "S_never_reaches_1": max(S_vals) < 1.0,
            "S_max_value":       max(S_vals),
            "C_in_range":        0.0 <= min(C_vals) and max(C_vals) <= 1.0,
            "C_range":           (min(C_vals), max(C_vals)),
            "W_in_range":        0.0 <= min(W_vals) and max(W_vals) <= 1.0,
            "W_range":           (min(W_vals), max(W_vals)),
            "S_monotonic":       all(S_vals[i] <= S_vals[i+1] + 1e-9 for i in range(len(S_vals)-1)),
            "state_count":       len(self._states),
        }
