"""Unit tests for Short-Duration BESS and Long-Duration LDES storage models."""

import unittest
from irp.resources.storage.bess import BESS
from irp.resources.storage.ldes import LDES


class TestStorage(unittest.TestCase):
    def test_bess_properties(self):
        bess = BESS(
            resource_id="bess1",
            name="Lithium Pack",
            bus_id="bus1",
            power_rating_mw=100.0,
            energy_capacity_mwh=400.0,
            eta_charge=0.92,
            eta_discharge=0.92,
            cell_replacement_cost_per_mwh=120000.0,
            cycle_life_at_80_dod=5000,
        )
        self.assertAlmostEqual(bess.duration_hrs, 4.0)
        self.assertAlmostEqual(bess.round_trip_efficiency, 0.92 * 0.92, places=4)

        # Degradation wear cost: 120,000 / (2 * 5000 * 0.8) = $15.00/MWh
        self.assertAlmostEqual(bess.get_degradation_cost_per_mwh(), 15.0)

    def test_bess_soc_update(self):
        bess = BESS(
            resource_id="bess1",
            name="Lithium Pack",
            bus_id="bus1",
            power_rating_mw=100.0,
            energy_capacity_mwh=400.0,
            eta_charge=0.90,
            eta_discharge=0.90,
            self_discharge_hourly=0.001,
        )
        # Starting with 200 MWh SOC, charging at 50 MW for 1 hr -> +45 MWh
        # (200 * 0.999) + 45 = 244.8 MWh
        soc_next = bess.update_soc(
            current_soc_mwh=200.0,
            p_charge_mw=50.0,
            p_discharge_mw=0.0,
            dt_hours=1.0,
        )
        self.assertAlmostEqual(soc_next, 244.8, places=3)

    def test_ldes_properties(self):
        ldes = LDES(
            resource_id="ldes1",
            name="Iron-Air System",
            bus_id="bus1",
            power_rating_mw=50.0,
            energy_capacity_mwh=5000.0,  # 100-hour system
            power_capex_per_mw=800000.0,
            energy_capex_per_mwh=20000.0,
        )
        self.assertAlmostEqual(ldes.duration_hrs, 100.0)
        self.assertTrue(ldes.is_seasonal_capable())

        # Total capital cost: (50 * 800k) + (5000 * 20k) = 40M + 100M = $140M
        self.assertAlmostEqual(ldes.total_capital_cost, 140.0e6)


if __name__ == "__main__":
    unittest.main()
