"""Thermal generation models: Peakers (SCGT) and Combined Cycle (CCGT)."""

from __future__ import annotations

from dataclasses import dataclass

from irp.resources.base import DispatchableGenerator


@dataclass
class PeakerPlant(DispatchableGenerator):
    """Fast-ramping Simple Cycle Gas Turbine (SCGT) or Peaker plant."""

    startup_time_minutes: float = 10.0      # Fast start capability (10-15 min)
    heat_rate_mmbtu_per_mwh: float = 9.8    # High heat rate (lower efficiency)
    fuel_cost_per_mmbtu: float = 4.0        # Natural gas $/MMBtu
    variable_om_per_mwh: float = 8.0
    co2_intensity_tons_per_mwh: float = 0.53  # ~0.53 MT CO2/MWh for SCGT
    hydrogen_blend_vol_pct: float = 0.0     # % volumetric hydrogen blend

    def __post_init__(self) -> None:
        self.p_min_mw = 0.0  # Peakers can turn on and dispatch down to 0
        # Aeroderivative peakers can ramp full range in an hour
        self.ramp_rate_mw_per_hr = self.p_max_mw

    def adjust_for_hydrogen_blend(self, h2_pct: float) -> None:
        """Adjust heat rate and emissions for volumetric H2 blending."""
        self.hydrogen_blend_vol_pct = max(0.0, min(100.0, h2_pct))
        energy_fraction_h2 = (self.hydrogen_blend_vol_pct / 3.0) / (
            1.0 + (self.hydrogen_blend_vol_pct / 3.0)
        )
        self.co2_intensity_tons_per_mwh = 0.53 * (1.0 - energy_fraction_h2)


@dataclass
class CombinedCyclePlant(DispatchableGenerator):
    """High-efficiency Combined Cycle Gas Turbine (CCGT) plant."""

    heat_rate_mmbtu_per_mwh: float = 6.4     # High efficiency (~53-60% efficiency)
    fuel_cost_per_mmbtu: float = 3.5
    variable_om_per_mwh: float = 4.0
    co2_intensity_tons_per_mwh: float = 0.35  # ~0.35 MT CO2/MWh
    p_min_fraction: float = 0.40              # Minimum compliance load ~40%
    ccs_equipped: bool = False               # Carbon Capture and Storage flag
    ccs_capture_rate: float = 0.90           # 90% CO2 capture rate
    ccs_energy_penalty_pct: float = 15.0     # Parasitic auxiliary load penalty (%)

    def __post_init__(self) -> None:
        if self.p_min_mw is None:
            self.p_min_mw = self.p_max_mw * self.p_min_fraction
        self.ramp_rate_mw_per_hr = self.p_max_mw * 0.40  # 40% of capacity/hr

        if self.ccs_equipped:
            self.co2_intensity_tons_per_mwh *= (1.0 - self.ccs_capture_rate)
            penalty_factor = 1.0 + (self.ccs_energy_penalty_pct / 100.0)
            self.heat_rate_mmbtu_per_mwh *= penalty_factor
