"""Variable renewable energy resources: Solar PV and Wind power models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from irp.resources.base import BaseResource


@dataclass
class RenewableResource(BaseResource):
    """Base class for weather-dependent, non-dispatchable renewable generators."""

    capacity_factor_profile: List[float] = field(default_factory=list)
    variable_om_per_mwh: float = 0.0
    co2_intensity_tons_per_mwh: float = 0.0

    def get_marginal_cost_per_mwh(self) -> float:
        """Near-zero short-run marginal operating cost ($/MWh)."""
        return self.variable_om_per_mwh

    def get_max_generation_mw(self, hour: int, installed_capacity_mw: float) -> float:
        """Calculate available meteorological generation potential at a given hour."""
        if not self.capacity_factor_profile:
            return installed_capacity_mw
        cf = self.capacity_factor_profile[hour % len(self.capacity_factor_profile)]
        return max(0.0, min(1.0, cf)) * installed_capacity_mw


@dataclass
class SolarPV(RenewableResource):
    """Utility-scale solar photovoltaic generation."""

    tracking_type: str = "Single-Axis"  # Fixed-Tilt, Single-Axis, Dual-Axis
    inverter_loading_ratio: float = 1.30  # DC-to-AC capacity ratio
    degradation_annual_pct: float = 0.5  # Annual PV panel degradation


@dataclass
class WindTurbine(RenewableResource):
    """Onshore or offshore wind turbine farm."""

    wind_type: str = "Onshore"          # Onshore, Offshore Fixed, Offshore Floating
    hub_height_m: float = 100.0
    cut_in_speed_m_s: float = 3.0
    rated_speed_m_s: float = 12.0
    cut_out_speed_m_s: float = 25.0
