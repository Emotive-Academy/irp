"""Electric load demand and Demand Response (DR) flexibility models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ElectricLoad:
    """Inflexible electrical power demand at a specific grid bus."""

    load_id: str
    bus_id: str
    base_mw: float = 100.0
    hourly_profile: List[float] = field(default_factory=list)

    def get_demand_mw(self, hour: int) -> float:
        """Return the electric demand (MW) at a specific hour."""
        if not self.hourly_profile:
            return self.base_mw
        multiplier = self.hourly_profile[hour % len(self.hourly_profile)]
        return self.base_mw * max(0.0, multiplier)


@dataclass
class DemandResponse:
    """Flexible demand response: peak load shedding and shifting capability."""

    dr_id: str
    bus_id: str
    max_shed_mw: float = 20.0
    curtailment_cost_per_mwh: float = 250.0  # Call payment incentive ($/MWh)
    max_consecutive_hours: int = 4
    annual_call_limit_hours: int = 100
    shift_capable: bool = True               # Whether load can be shifted
    max_shift_advance_hours: int = 6
