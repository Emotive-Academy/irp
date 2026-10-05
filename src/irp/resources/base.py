"""Abstract base classes and common interfaces for all power grid resources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class BaseResource(ABC):
    """Base class for any grid asset (generator, storage, transmission, demand-side)."""

    resource_id: str
    name: str
    bus_id: str
    capital_cost_per_mw: float = 1.0e6   # Overnight CapEx in $/MW
    fixed_om_per_mw_yr: float = 20000.0  # Fixed O&M in $/MW-year
    variable_om_per_mwh: float = 5.0     # Variable O&M in $/MWh
    economic_lifetime_yrs: int = 30
    is_candidate: bool = False           # If True, model can build new capacity
    max_build_mw: Optional[float] = None  # Maximum allowable new capacity
    co2_intensity_tons_per_mwh: float = 0.0

    @abstractmethod
    def get_marginal_cost_per_mwh(self) -> float:
        """Return the short-run marginal operating cost ($/MWh)."""
        pass


@dataclass
class DispatchableGenerator(BaseResource):
    """Base class for dispatchable thermal, nuclear, or hydro generation units."""

    p_min_mw: Optional[float] = None
    p_max_mw: float = 500.0
    ramp_rate_mw_per_hr: float = 250.0
    min_up_time_hrs: int = 1
    min_down_time_hrs: int = 1
    heat_rate_mmbtu_per_mwh: float = 7.0
    fuel_cost_per_mmbtu: float = 3.5  # $/MMBtu

    def __post_init__(self) -> None:
        if self.p_min_mw is None:
            self.p_min_mw = 0.0

    def get_marginal_cost_per_mwh(self) -> float:
        """Short-run marginal cost = Variable O&M + (HeatRate * FuelCost)."""
        fuel_component = self.heat_rate_mmbtu_per_mwh * self.fuel_cost_per_mmbtu
        return self.variable_om_per_mwh + fuel_component


@dataclass
class StorageResource(BaseResource):
    """Base class for electrochemical, mechanical, or chemical energy storage."""

    power_rating_mw: float = 100.0
    energy_capacity_mwh: float = 400.0  # 4-hour duration default
    eta_charge: float = 0.93            # One-way charging efficiency
    eta_discharge: float = 0.93         # One-way discharging efficiency
    self_discharge_hourly: float = 0.0001  # Fraction of energy lost per hour
    min_soc_fraction: float = 0.05      # Minimum allowable state of charge
    max_soc_fraction: float = 1.00      # Maximum allowable state of charge
    initial_soc_mwh: Optional[float] = None

    @property
    def duration_hrs(self) -> float:
        """Storage duration ratio: Energy / Power (hours)."""
        if self.power_rating_mw > 0:
            return self.energy_capacity_mwh / self.power_rating_mw
        return 0.0

    @property
    def round_trip_efficiency(self) -> float:
        """Round-trip efficiency: eta_charge * eta_discharge."""
        return self.eta_charge * self.eta_discharge

    def get_marginal_cost_per_mwh(self) -> float:
        """Variable O&M per MWh throughput."""
        return self.variable_om_per_mwh
