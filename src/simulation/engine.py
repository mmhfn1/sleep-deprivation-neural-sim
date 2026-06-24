"""
SimulationEngine — orchestrates all models, pre-computes 73 snapshots.

SCIENTIFIC CORRECTIONS in this version:

1. snap.S now stores TRUE BIOLOGICAL S (adenosine concentration from the ODE).
   Caffeine does not reduce adenosine; it blocks receptors.
   The pharmacological effect is applied ONLY to the effective W calculation,
   not to the adenosine readout shown in the header.

2. The W coefficient for S_mod is now mu_S = 0.85, matching the formula
   W = 0.85·S − 0.40·C. Previously 0.60 was used (ad-hoc, inconsistent).

3. snap.S_true stores true S; snap.W stores pharma-adjusted W.
   The gap between (0.85·S_true − 0.40·C) and snap.W shows the pharmacological
   masking effect.
"""
from __future__ import annotations
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

from ..models.two_process_model import TwoProcessModel, TwoProcessState, impairment_label
from ..models.brain_regions import BrainRegionModel, RegionState, REGION_ORDER
from ..models.pharmacology import PharmacologyModel, SubstanceDose
from .recorder import SimulationRecorder

MU_S = 0.85   # matches TwoProcessParams.mu_S — weight of S in W formula


class HourSnapshot:
    __slots__ = (
        "hour", "S", "W",
        "C", "impairment_label", "impairment_index",
        "region_states", "microsleep_prob",
        "caff_conc", "nic_conc",
        "W_unmasked",    # W without pharmacology (for display comparison)
    )

    def __init__(self):
        self.hour:             int   = 0
        self.S:                float = 0.0   # TRUE biological S (never pharma-modified)
        self.W:                float = 0.0   # effective W after pharmacology
        self.W_unmasked:       float = 0.0   # W if no drugs were taken
        self.C:                float = 0.0
        self.impairment_label: str   = "NORMAL"
        self.impairment_index: float = 0.0
        self.region_states:    dict  = {}
        self.microsleep_prob:  float = 0.0
        self.caff_conc:        float = 0.0
        self.nic_conc:         float = 0.0


class SimulationEngine(QObject):
    snapshot_ready = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._two_process = TwoProcessModel()
        self._brain       = BrainRegionModel()
        self._pharma      = PharmacologyModel()
        self._recorder    = SimulationRecorder()
        self._snapshots:  list[HourSnapshot] = []
        self._precomputed = False

    # ── Pharmacology config ───────────────────────────────────────────────
    def set_caffeine_dose(self, dose_mg: float, at_hour: float):
        self._pharma.add_dose(SubstanceDose("caffeine", dose_mg, at_hour))
        self._precomputed = False

    def set_nicotine_dose(self, dose_mg: float, at_hour: float):
        self._pharma.add_dose(SubstanceDose("nicotine", dose_mg, at_hour))
        self._precomputed = False

    def clear_pharma(self):
        self._pharma.clear_doses(); self._precomputed = False

    # ── Core computation ──────────────────────────────────────────────────
    def precompute(self) -> list[HourSnapshot]:
        self._recorder.clear(); self._snapshots.clear()

        self._two_process = TwoProcessModel()
        self._two_process.solve(max_hours=72.0)
        hourly = self._two_process.get_hourly_states()

        for h, state in enumerate(hourly):
            snap = HourSnapshot()
            snap.hour = h

            # ── True biological S (NEVER modified by pharmacology) ────────
            snap.S        = state.S   # adenosine concentration from ODE
            snap.C        = state.C
            snap.W_unmasked = state.W  # W without any drugs

            # ── Pharmacology ──────────────────────────────────────────────
            pharma       = self._pharma.compute_modifiers(float(h), state.S)
            region_mods  = pharma["region_modifiers"]
            S_mod        = pharma["S_modifier"]
            snap.caff_conc = pharma["caff_conc"]
            snap.nic_conc  = pharma["nic_conc"]

            # ── Effective W after pharmacological receptor blockade ───────
            # Caffeine blocks adenosine receptors → effective S signal is
            # reduced.  We propagate this through the W formula properly:
            #   W_eff = clip(mu_S·(S + S_mod) − mu_C·C, 0, 1)
            # which equals clip(W_true + mu_S·S_mod, 0, 1).
            # Using mu_S=0.85 matches the two-process formula exactly.
            mod_W = float(np.clip(state.W + MU_S * S_mod, 0.0, 1.0))
            snap.W = mod_W
            snap.impairment_label = impairment_label(mod_W)

            # ── Effective state for region firing rates ───────────────────
            mod_state = TwoProcessState(
                t=state.t, S=state.S, C=state.C,   # S unchanged
                W=mod_W,                             # W is pharma-adjusted
                impairment_level=snap.impairment_label,
            )

            snap.region_states  = self._brain.compute_all_regions(mod_state, region_mods)
            snap.impairment_index = self._brain.compute_impairment_index(snap.region_states)
            snap.microsleep_prob  = self._brain.compute_microsleep_probability(float(h))

            self._snapshots.append(snap)
            self._recorder.record(snap)

        self._precomputed = True
        return self._snapshots

    # ── Accessors ─────────────────────────────────────────────────────────
    def get_snapshot(self, hour: int) -> HourSnapshot:
        if not self._precomputed: self.precompute()
        return self._snapshots[int(np.clip(hour, 0, 72))]

    def get_all_snapshots(self) -> list[HourSnapshot]:
        if not self._precomputed: self.precompute()
        return self._snapshots

    def emit_snapshot(self, hour: int):
        self.snapshot_ready.emit(self.get_snapshot(hour))

    def export_csv(self, filepath: str) -> bool:
        return self._recorder.export_csv(filepath)

    def reset(self):
        self._pharma.clear_doses(); self._recorder.clear()
        self._snapshots.clear(); self._precomputed = False
        self.precompute()
