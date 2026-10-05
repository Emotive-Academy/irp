"""Resource Adequacy analytics: PRM, LOLH, and marginal ELCC."""

from __future__ import annotations

from typing import Sequence
import numpy as np


class Adequacy:
    """Resource adequacy metrics and loss-of-load calculations."""

    @staticmethod
    def calculate_prm(accredited_capacity_mw: float, peak_demand_mw: float) -> float:
        """Calculate Planning Reserve Margin (PRM) as a percentage.

        Formula: PRM = [(AccreditedCapacity - PeakDemand) / PeakDemand] * 100%
        """
        if peak_demand_mw <= 0.0:
            raise ValueError("Peak demand must be strictly positive.")
        return ((accredited_capacity_mw - peak_demand_mw) / peak_demand_mw) * 100.0

    @staticmethod
    def evaluate_loss_of_load_hours(
        total_fleet_capacity_mw: float,
        hourly_demand_mw: Sequence[float],
        expected_unavailability_pct: float = 0.05,
    ) -> float:
        """Calculate expected Loss of Load Hours (LOLH) under derated capacity."""
        derated = total_fleet_capacity_mw * (1.0 - expected_unavailability_pct)
        unserved_hours = sum(1 for d in hourly_demand_mw if d > derated)
        return float(unserved_hours)

    @staticmethod
    def evaluate_marginal_elcc(
        resource_hourly_mw: Sequence[float],
        net_load_mw: Sequence[float],
        top_risk_hours: int = 50,
    ) -> float:
        """Estimate marginal Effective Load Carrying Capability (ELCC) percentage.

        Measures resource generation coincidence with the top net-load risk hours.
        """
        if len(net_load_mw) == 0 or len(resource_hourly_mw) == 0:
            return 0.0

        arr_load = np.array(net_load_mw)
        arr_gen = np.array(resource_hourly_mw)
        nameplate_mw = np.max(arr_gen) if np.max(arr_gen) > 0 else 1.0

        n_hours = min(top_risk_hours, len(arr_load))
        peak_hour_indices = np.argsort(arr_load)[-n_hours:]

        coincident_generation = arr_gen[peak_hour_indices]
        avg_coincident_mw = np.mean(coincident_generation)

        elcc_pct = (avg_coincident_mw / nameplate_mw) * 100.0
        return float(max(0.0, min(100.0, elcc_pct)))
