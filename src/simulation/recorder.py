"""SimulationRecorder — time-series store and CSV export."""
from __future__ import annotations
import csv
from pathlib import Path
from ..models.brain_regions import REGION_ORDER


class SimulationRecorder:
    def __init__(self):
        self._records: list[dict] = []

    def record(self, snapshot) -> None:
        row: dict = {
            "hour":             snapshot.hour,
            "S":                round(snapshot.S, 5),
            "C":                round(snapshot.C, 5),
            "W":                round(snapshot.W, 5),
            "impairment_label": snapshot.impairment_label,
            "impairment_index": round(snapshot.impairment_index, 5),
            "caff_conc":        round(snapshot.caff_conc, 4),
            "nic_conc":         round(snapshot.nic_conc, 4),
        }
        for name in REGION_ORDER:
            rs = snapshot.region_states.get(name)
            row[f"{name}_hz"] = round(rs.firing_rate_hz, 3) if rs else 0.0
        self._records.append(row)

    def get_region_series(self) -> dict[str, list[float]]:
        return {n: [r.get(f"{n}_hz", 0.0) for r in self._records] for n in REGION_ORDER}

    def get_hours(self) -> list[int]:
        return [r["hour"] for r in self._records]

    def export_csv(self, filepath: str) -> bool:
        if not self._records: return False
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(self._records[0].keys()))
                w.writeheader(); w.writerows(self._records)
            return True
        except Exception as e:
            print(f"[Recorder] Export error: {e}"); return False

    def clear(self): self._records.clear()
    def __len__(self): return len(self._records)
