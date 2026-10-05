"""Transmission line physics modeling: thermal ratings, temperature de-rating,

voltage classes, line losses, and expansion parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from irp.core.units import Units
from irp.core.network import Branch


@dataclass
class TransmissionLine:
    """Detailed transmission corridor model with thermal physics and CapEx."""

    line_id: str
    from_bus: str
    to_bus: str
    voltage_kv: float = 230.0  # 138, 230, 345, 500, 765 kV AC or HVDC
    length_km: float = 100.0
    r_ohm_per_km: float = 0.05
    x_ohm_per_km: float = 0.40
    thermal_rating_mva: float = 1200.0
    is_hvdc: bool = False
    reference_temp_c: float = 25.0  # Reference ambient temperature
    temp_derating_coeff: float = 0.005  # Capacity reduction per deg C above ref
    capital_cost_per_km: float = 2.5e6  # CapEx in $/km for new expansion line
    lead_time_years: int = 5

    def get_effective_rating_mw(
        self,
        ambient_temp_c: Optional[float] = None,
        power_factor: float = 0.98,
    ) -> float:
        """Calculate effective real power capacity (MW) with thermal limits.

        Conductor heating (IEEE 738) restricts allowable current as ambient
        temperature rises.
        """
        nominal_mw = self.thermal_rating_mva * power_factor
        if ambient_temp_c is None or ambient_temp_c <= self.reference_temp_c:
            return nominal_mw

        delta_t = ambient_temp_c - self.reference_temp_c
        derating_factor = max(0.5, 1.0 - (self.temp_derating_coeff * delta_t))
        return nominal_mw * derating_factor

    def to_branch(self, base_mva: float = Units.DEFAULT_BASE_MVA) -> Branch:
        """Convert transmission line parameters into a per-unit network Branch."""
        total_r_ohms = self.r_ohm_per_km * self.length_km
        total_x_ohms = self.x_ohm_per_km * self.length_km

        r_pu = Units.ohms_to_pu(total_r_ohms, self.voltage_kv, base_mva)
        x_pu = Units.ohms_to_pu(total_x_ohms, self.voltage_kv, base_mva)

        return Branch(
            branch_id=self.line_id,
            from_bus=self.from_bus,
            to_bus=self.to_bus,
            r_pu=r_pu,
            x_pu=max(1e-5, x_pu),
            rating_mw=self.thermal_rating_mva,
            length_km=self.length_km,
            is_hvdc=self.is_hvdc,
            status=True,
        )

    def estimate_losses_mw(self, power_flow_mw: float) -> float:
        """Estimate resistive active power losses (MW) along the line."""
        r_total_ohms = self.r_ohm_per_km * self.length_km
        loss_mw = ((power_flow_mw**2) / (self.voltage_kv**2)) * r_total_ohms
        return max(0.0, float(loss_mw))
