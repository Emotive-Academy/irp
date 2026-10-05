"""Battery Energy Storage System (BESS) model with efficiency, C-rate,

state of charge dynamics, and cyclic degradation mechanics.
"""

from __future__ import annotations

from dataclasses import dataclass

from irp.resources.base import StorageResource


@dataclass
class BESS(StorageResource):
    """Short-duration Battery Energy Storage System (2-hr, 4-hr, 8-hr)."""

    cell_replacement_cost_per_mwh: float = 120000.0  # $/MWh
    cycle_life_at_80_dod: int = 5000                  # Cycles to 80% retention
    max_c_rate: float = 1.0                           # Maximum C-rate
    calendar_degradation_annual_pct: float = 1.5      # % loss per year

    def __post_init__(self) -> None:
        if self.initial_soc_mwh is None:
            self.initial_soc_mwh = 0.5 * self.energy_capacity_mwh

    def get_degradation_cost_per_mwh(self) -> float:
        """Calculate throughput-based wear cost ($/MWh of energy discharged)."""
        effective_full_cycles = self.cycle_life_at_80_dod * 0.8
        if effective_full_cycles <= 0.0:
            return 0.0
        return self.cell_replacement_cost_per_mwh / (2.0 * effective_full_cycles)

    def get_marginal_cost_per_mwh(self) -> float:
        """Total short-run marginal dispatch cost including degradation."""
        return self.variable_om_per_mwh + self.get_degradation_cost_per_mwh()

    def update_soc(
        self,
        current_soc_mwh: float,
        p_charge_mw: float,
        p_discharge_mw: float,
        dt_hours: float = 1.0,
    ) -> float:
        """Calculate next state of charge (SOC) given charge and discharge power."""
        loss_rate = self.self_discharge_hourly * dt_hours
        retained_soc = current_soc_mwh * (1.0 - loss_rate)
        added_energy = self.eta_charge * p_charge_mw * dt_hours
        eff_dis = max(1e-4, self.eta_discharge)
        withdrawn_energy = (p_discharge_mw * dt_hours) / eff_dis

        new_soc = retained_soc + added_energy - withdrawn_energy
        min_soc = self.min_soc_fraction * self.energy_capacity_mwh
        max_soc = self.max_soc_fraction * self.energy_capacity_mwh
        return max(min_soc, min(max_soc, new_soc))
