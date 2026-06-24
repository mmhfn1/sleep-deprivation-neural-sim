"""
Pharmacological Model — Caffeine and Nicotine PK/PD.

SCIENTIFIC CORRECTIONS in this version:
1. S_mod represents the reduction in *felt* adenosine signalling (receptor
   blockade), NOT a reduction in actual adenosine concentration.
   True biological S is always computed by the two-process ODE;
   S_mod modulates how strongly that S is felt (i.e. how much of it
   reaches effective receptor activation).

2. Post-48h washout now applies to S_mod as well as regional modifiers.
   Chronic caffeine use causes receptor upregulation, reducing the
   masking efficacy of further doses.

3. The W coefficient for S_mod is now 0.85 (consistent with the
   W = 0.85·S − 0.40·C formula) rather than an ad-hoc 0.60.
   This is set here as metadata; the engine applies it.
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass


@dataclass(frozen=True)
class CaffeineParams:
    t_half: float = 5.5; t_peak: float = 1.0
    E_max: float = 0.60; EC50_uM: float = 3.5
    uM_per_mg: float = 0.05
    rebound_threshold: float = 0.10; rebound_S_boost: float = 0.12
    anxiety_dose_mg: float = 400.0; anxiety_amygdala_boost: float = 0.15

@dataclass(frozen=True)
class NicotineParams:
    t_half: float = 2.0; t_peak: float = 0.25
    E_pfc: float = 0.18; E_hippocampus: float = 0.12
    E_brainstem: float = 0.10; E_amygdala: float = 0.08; E_thalamus: float = 0.05
    Kd: float = 2.0; tolerance_rate: float = 0.15; synergy_amyg: float = 0.05

@dataclass
class SubstanceDose:
    substance: str
    dose_mg:   float
    hour:      float


class PharmacologyModel:
    def __init__(self):
        self._caff = CaffeineParams()
        self._nic  = NicotineParams()
        self.doses: list[SubstanceDose] = []
        self._n_nicotine_doses_given = 0

    def add_dose(self, dose: SubstanceDose):
        self.doses.append(dose)
        if dose.substance == "nicotine":
            self._n_nicotine_doses_given += 1

    def clear_doses(self):
        self.doses.clear(); self._n_nicotine_doses_given = 0

    def _bateman(self, dose_units: float, dt: float, k_a: float, k_e: float) -> float:
        if dt < 0: return 0.0
        if abs(k_a - k_e) < 1e-9:
            return dose_units * k_e * dt * np.exp(-k_e * dt)
        return float(np.clip(
            dose_units * k_a / (k_a - k_e) * (np.exp(-k_e * dt) - np.exp(-k_a * dt)),
            0.0, 1e6
        ))

    def caffeine_plasma_uM(self, t: float) -> float:
        p = self._caff; k_e = np.log(2)/p.t_half; k_a = np.log(2)/p.t_peak
        return float(np.clip(sum(
            self._bateman(d.dose_mg * p.uM_per_mg, t - d.hour, k_a, k_e)
            for d in self.doses if d.substance == "caffeine" and d.hour <= t
        ), 0.0, 200.0))

    def nicotine_plasma_norm(self, t: float) -> float:
        p = self._nic; k_e = np.log(2)/p.t_half; k_a = np.log(2)/p.t_peak
        return float(np.clip(sum(
            self._bateman(d.dose_mg / 2.0, t - d.hour, k_a, k_e)
            for d in self.doses if d.substance == "nicotine" and d.hour <= t
        ), 0.0, 10.0))

    def _caffeine_rebound_S(self, t: float, C_caff: float) -> float:
        caff_doses = [d for d in self.doses if d.substance == "caffeine"]
        if not caff_doses: return 0.0
        p = self._caff; k_e = np.log(2)/p.t_half; k_a = np.log(2)/p.t_peak
        last = max(caff_doses, key=lambda d: d.hour)
        peak = last.dose_mg * p.uM_per_mg * self._bateman(1.0, p.t_peak, k_a, k_e)
        return p.rebound_S_boost if (peak > 0 and C_caff < p.rebound_threshold * peak) else 0.0

    def compute_modifiers(self, t_current: float, S_current: float) -> dict:
        """
        Returns:
          region_modifiers  : {name: multiplicative float}
          S_mod             : REDUCTION in felt adenosine signalling (≤0 means less felt pressure)
                              True biological S is UNCHANGED — this is receptor-level blockade.
          caff_conc / nic_conc
        """
        region_mods = {r: 1.0 for r in ["pfc","hippocampus","thalamus","amygdala","brainstem"]}
        S_mod = 0.0

        C_caff = self.caffeine_plasma_uM(t_current)
        if C_caff > 0.01:
            p = self._caff
            S_mod -= (p.E_max * C_caff) / (p.EC50_uM + C_caff)
            total_caff = sum(d.dose_mg for d in self.doses if d.substance == "caffeine")
            if total_caff > p.anxiety_dose_mg:
                region_mods["amygdala"] *= (1.0 + p.anxiety_amygdala_boost)
        S_mod += self._caffeine_rebound_S(t_current, C_caff)

        C_nic = self.nicotine_plasma_norm(t_current)
        if C_nic > 0.01:
            p = self._nic
            tol = float(np.exp(-p.tolerance_rate * max(0, self._n_nicotine_doses_given - 1)))
            occ = C_nic / (p.Kd + C_nic)
            region_mods["pfc"]         *= 1.0 + p.E_pfc         * occ * tol
            region_mods["hippocampus"] *= 1.0 + p.E_hippocampus * occ * tol
            region_mods["brainstem"]   *= 1.0 + p.E_brainstem   * occ * tol
            region_mods["amygdala"]    *= 1.0 + p.E_amygdala    * occ * tol
            region_mods["thalamus"]    *= 1.0 + p.E_thalamus    * occ * tol
            if C_caff > p.Kd:
                region_mods["amygdala"] *= (1.0 + p.synergy_amyg)

        # ── Post-48h washout ────────────────────────────────────────────────
        # Applies to BOTH S_mod AND regional modifiers (consistent with
        # receptor upregulation under chronic stimulant use).
        if t_current >= 48.0:
            decay = max(0.30, 1.0 - 0.007 * (t_current - 48.0))
            # S_mod is negative (reducing felt pressure); decay brings it toward 0
            # meaning caffeine becomes LESS effective at masking sleep pressure
            S_mod *= decay
            for r in region_mods:
                boost = region_mods[r] - 1.0
                if boost > 0:
                    region_mods[r] = 1.0 + boost * decay

        return {
            "region_modifiers": region_mods,
            "S_modifier":       float(np.clip(S_mod, -0.80, 0.30)),
            "caff_conc":        C_caff,
            "nic_conc":         C_nic,
        }

    def get_precomputed_timeline(self, max_hours: float = 72.0) -> list[dict]:
        return [self.compute_modifiers(float(h), 0.5) for h in range(int(max_hours)+1)]
