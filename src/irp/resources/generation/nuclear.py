"""Nuclear power plant physics and economics: baseload and SMR options."""

from __future__ import annotations

from dataclasses import dataclass

from irp.resources.base import DispatchableGenerator


@dataclass
class NuclearPlant(DispatchableGenerator):
    """Nuclear power plant model (Light Water Reactor or SMR)."""

    reactor_type: str = "PWR"             # PWR, BWR, SMR, Microreactor
    p_min_fraction: float = 0.80          # Minimum stable output (80-100% of P_max)
    ramp_rate_pct_per_hr: float = 10.0    # Restricted ramping (% of P_max per hr)
    availability_factor: float = 0.93     # Annual availability (refueling cycles)
    fuel_cost_per_mmbtu: float = 0.75     # Nuclear fuel cost (~$0.75/MMBtu)
    heat_rate_mmbtu_per_mwh: float = 10.4  # Thermal efficiency ~33%
    variable_om_per_mwh: float = 2.50
    co2_intensity_tons_per_mwh: float = 0.0  # Zero direct Scope 1 operational CO2

    def __post_init__(self) -> None:
        if self.p_min_mw is None:
            self.p_min_mw = self.p_max_mw * self.p_min_fraction
        # Set absolute ramp rate based on percentage limit
        self.ramp_rate_mw_per_hr = self.p_max_mw * (self.ramp_rate_pct_per_hr / 100.0)

    def is_smr(self) -> bool:
        """Check if unit qualifies as Small Modular Reactor (typically <= 300 MWe)."""
        return self.p_max_mw <= 300.0
