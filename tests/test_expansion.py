"""Unit tests for CapacityExpansionModel optimization engine."""

import unittest
from irp.core.network import Bus, Branch, PowerGrid
from irp.expansion.model import CapacityExpansionModel
from irp.resources.generation.thermal import PeakerPlant
from irp.resources.generation.renewable import SolarPV
from irp.resources.storage.bess import BESS
from irp.resources.demand.load import ElectricLoad


class TestExpansion(unittest.TestCase):
    def setUp(self):
        # 2-Bus Power Grid
        self.grid = PowerGrid("ExpansionGrid", base_mva=100.0)
        self.b1 = Bus("Bus1", is_slack=True)
        self.b2 = Bus("Bus2")
        self.grid.add_bus(self.b1)
        self.grid.add_bus(self.b2)

        # Transmission branch
        self.line = Branch("L1", "Bus1", "Bus2", x_pu=0.05, rating_mw=500.0)
        self.grid.add_branch(self.line)

        # Candidate Resources
        self.solar = SolarPV(
            resource_id="Solar1",
            name="Utility Solar",
            bus_id="Bus1",
            capital_cost_per_mw=1.0e6,
            fixed_om_per_mw_yr=15000.0,
            is_candidate=True,
            capacity_factor_profile=[0.0, 0.2, 0.8, 0.9, 0.4, 0.0],
        )
        self.peaker = PeakerPlant(
            resource_id="Peaker1",
            name="Gas Peaker",
            bus_id="Bus2",
            capital_cost_per_mw=0.9e6,
            fixed_om_per_mw_yr=12000.0,
            is_candidate=True,
            heat_rate_mmbtu_per_mwh=9.5,
            fuel_cost_per_mmbtu=4.0,
        )
        self.battery = BESS(
            resource_id="BESS1",
            name="Grid Battery",
            bus_id="Bus1",
            power_rating_mw=0.0,
            energy_capacity_mwh=0.0,
            capital_cost_per_mw=1.2e6,
            fixed_om_per_mw_yr=25000.0,
            is_candidate=True,
        )

        self.grid.add_generator(self.solar)
        self.grid.add_generator(self.peaker)
        self.grid.add_storage(self.battery)

        # Electric Load at Bus 2: 100 MW flat
        self.load = ElectricLoad(
            load_id="Load1",
            bus_id="Bus2",
            base_mw=100.0,
            hourly_profile=[1.0] * 6,
        )
        self.grid.add_load(self.load)

    def test_capacity_expansion_solution(self):
        cem = CapacityExpansionModel(
            grid=self.grid,
            num_hours=6,
            planning_reserve_margin=0.15,
            annualized_hours_weight=8760.0 / 6.0,
        )
        plan = cem.build_and_solve()

        # Check optimization success
        self.assertTrue(plan.opt_result.success)
        self.assertGreater(plan.total_cost_usd, 0.0)

        # At least some capacity must be built to serve the 100 MW load
        total_built = sum(plan.built_capacity_mw.values())
        self.assertGreater(total_built, 50.0)

        # Verify unserved energy is zero
        self.assertAlmostEqual(sum(plan.unserved_energy_mwh), 0.0, places=3)


if __name__ == "__main__":
    unittest.main()
