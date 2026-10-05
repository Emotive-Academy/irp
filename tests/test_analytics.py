"""Unit tests for Economics and Resource Adequacy analytics."""

import unittest
from irp.analytics.economics import Economics
from irp.analytics.adequacy import Adequacy


class TestAnalytics(unittest.TestCase):
    def test_economics_calculations(self):
        # CRF test: 7% discount rate, 30 years -> ~0.080586
        crf = Economics.capital_recovery_factor(0.07, 30)
        self.assertAlmostEqual(crf, 0.080586, places=5)

        # NPVRR test: $100M/year for 3 years at 7%
        npv = Economics.calculate_npvrr([100.0, 100.0, 100.0], discount_rate=0.07)
        expected = (100 / 1.07) + (100 / (1.07**2)) + (100 / (1.07**3))
        self.assertAlmostEqual(npv, expected, places=4)

        # LCOE calculation
        lcoe = Economics.calculate_lcoe(
            overnight_capex_per_kw=1000.0,
            fixed_om_per_kw_yr=15.0,
            variable_om_per_mwh=3.0,
            heat_rate_mmbtu_per_mwh=0.0,
            fuel_cost_per_mmbtu=0.0,
            capacity_factor=0.30,
            discount_rate=0.07,
            lifetime_years=30,
        )
        self.assertGreater(lcoe, 0.0)

        # LCOS calculation
        lcos = Economics.calculate_lcos(
            capex_per_kwh=300.0,
            fixed_om_per_kw_yr=25.0,
            duration_hrs=4.0,
            round_trip_efficiency=0.85,
        )
        self.assertGreater(lcos, 0.0)

    def test_adequacy_metrics(self):
        # PRM: 1200 MW accredited, 1000 MW peak -> 20% PRM
        prm = Adequacy.calculate_prm(
            accredited_capacity_mw=1200.0, peak_demand_mw=1000.0
        )
        self.assertAlmostEqual(prm, 20.0)

        # Loss of Load Hours
        hourly_demand = [800.0, 950.0, 1050.0, 1100.0, 850.0]
        # 1000 MW fleet with 5% outage -> 950 MW available
        # Hours with demand > 950 MW: 1050 and 1100 (2 hours)
        lolh = Adequacy.evaluate_loss_of_load_hours(
            total_fleet_capacity_mw=1000.0,
            hourly_demand_mw=hourly_demand,
            expected_unavailability_pct=0.05,
        )
        self.assertAlmostEqual(lolh, 2.0)

        # Marginal ELCC: coincidence with peak hours
        net_load = [100.0, 200.0, 300.0, 500.0, 600.0]
        solar_gen = [50.0, 80.0, 90.0, 10.0, 0.0]
        elcc = Adequacy.evaluate_marginal_elcc(solar_gen, net_load, top_risk_hours=2)
        self.assertAlmostEqual(elcc, 5.555, places=2)


if __name__ == "__main__":
    unittest.main()
