"""Long-Duration Energy Storage (LDES) model (Iron-Air, Flow, PSH, Hydrogen)."""

from __future__ import annotations

from dataclasses import dataclass

from irp.resources.base import StorageResource


@dataclass
class LDES(StorageResource):
    """Long-Duration Energy Storage (LDES) with duration from 24 to 100+ hours."""

    technology_type: str = "Iron-Air"       # Iron-Air, Flow, PSH, CAES, Hydrogen
    power_capex_per_mw: float = 800000.0   # Power equipment CapEx ($/MW)
    energy_capex_per_mwh: float = 25000.0  # Energy reservoir CapEx ($/MWh)
    min_duration_hrs: float = 24.0         # Minimum duration ratio (Hours)
    max_duration_hrs: float = 150.0        # Maximum duration ratio (Hours)

    def __post_init__(self) -> None:
        if self.power_rating_mw <= 0.0:
            self.power_rating_mw = 100.0
        min_energy = self.power_rating_mw * self.min_duration_hrs
        if self.energy_capacity_mwh < min_energy:
            self.energy_capacity_mwh = min_energy
        if self.initial_soc_mwh is None:
            self.initial_soc_mwh = 0.5 * self.energy_capacity_mwh

    @property
    def total_capital_cost(self) -> float:
        """Total overnight capital cost = (PowerCapEx * MW) + (EnergyCapEx * MWh)."""
        power_cost = self.power_capex_per_mw * self.power_rating_mw
        energy_cost = self.energy_capex_per_mwh * self.energy_capacity_mwh
        return power_cost + energy_cost

    def is_seasonal_capable(self) -> bool:
        """Check if storage has sufficient duration for multi-day buffering."""
        return self.duration_hrs >= 48.0
