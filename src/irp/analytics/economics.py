"""Techno-economic analytics: NPVRR, LCOE, and LCOS."""

from __future__ import annotations

from typing import List
from irp.core.units import Units


class Economics:
    """Standardized financial and economic calculations for utility planning."""

    @staticmethod
    def capital_recovery_factor(discount_rate: float, lifetime_years: int) -> float:
        """Calculate Capital Recovery Factor (CRF):

        CRF = [d * (1 + d)^N] / [(1 + d)^N - 1]
        """
        if discount_rate <= 0.0:
            return 1.0 / max(1, lifetime_years)
        d = discount_rate
        n = lifetime_years
        return (d * (1.0 + d) ** n) / (((1.0 + d) ** n) - 1.0)

    @classmethod
    def calculate_npvrr(
        cls,
        annual_revenue_requirements: List[float],
        discount_rate: float = 0.07,
    ) -> float:
        """Calculate the Net Present Value of Revenue Requirement (NPVRR)."""
        npv = 0.0
        for t, rev_req in enumerate(annual_revenue_requirements, start=1):
            npv += rev_req / ((1.0 + discount_rate) ** t)
        return float(npv)

    @classmethod
    def calculate_lcoe(
        cls,
        overnight_capex_per_kw: float,
        fixed_om_per_kw_yr: float,
        variable_om_per_mwh: float,
        heat_rate_mmbtu_per_mwh: float = 0.0,
        fuel_cost_per_mmbtu: float = 0.0,
        capacity_factor: float = 0.50,
        discount_rate: float = 0.07,
        lifetime_years: int = 30,
    ) -> float:
        """Calculate Levelized Cost of Energy (LCOE) in $/MWh."""
        if capacity_factor <= 0.0:
            raise ValueError("Capacity factor must be positive.")

        crf = cls.capital_recovery_factor(discount_rate, lifetime_years)
        annual_fixed_per_kw = (overnight_capex_per_kw * crf) + fixed_om_per_kw_yr
        annual_gen_mwh = (Units.HOURS_PER_YEAR * capacity_factor) / 1000.0

        fixed_lcoe = annual_fixed_per_kw / annual_gen_mwh
        fuel_cost_per_mwh = heat_rate_mmbtu_per_mwh * fuel_cost_per_mmbtu
        total_lcoe = fixed_lcoe + variable_om_per_mwh + fuel_cost_per_mwh
        return float(total_lcoe)

    @classmethod
    def calculate_lcos(
        cls,
        capex_per_kwh: float,
        fixed_om_per_kw_yr: float,
        duration_hrs: float = 4.0,
        round_trip_efficiency: float = 0.85,
        charging_cost_per_mwh: float = 30.0,
        cycles_per_year: float = 365.0,
        discount_rate: float = 0.07,
        lifetime_years: int = 15,
    ) -> float:
        """Calculate Levelized Cost of Storage (LCOS) in $/MWh of delivered energy."""
        crf = cls.capital_recovery_factor(discount_rate, lifetime_years)
        capex_per_kw = capex_per_kwh * duration_hrs
        annual_fixed = (capex_per_kw * crf) + fixed_om_per_kw_yr

        annual_delivered_mwh_per_kw = (duration_hrs * cycles_per_year) / 1000.0
        capital_cost_per_mwh = annual_fixed / max(1e-4, annual_delivered_mwh_per_kw)

        eff_rte = max(1e-4, round_trip_efficiency)
        effective_charging_cost = charging_cost_per_mwh / eff_rte

        total_lcos = capital_cost_per_mwh + effective_charging_cost
        return float(total_lcos)
