"""Unit tests for Security-Constrained Economic Dispatch (SCED)."""

import unittest
from irp.core.network import Bus, Branch, PowerGrid
from irp.dispatch.economic_dispatch import SecurityConstrainedDispatch
from irp.resources.generation.thermal import CombinedCyclePlant, PeakerPlant
from irp.resources.demand.load import ElectricLoad


class TestDispatch(unittest.TestCase):
    def setUp(self):
        # 2-Bus Power Grid with transmission bottleneck
        self.grid = PowerGrid("DispatchGrid", base_mva=100.0)
        self.b1 = Bus("Bus1", is_slack=True)
        self.b2 = Bus("Bus2")
        self.grid.add_bus(self.b1)
        self.grid.add_bus(self.b2)

        # Transmission branch with 60 MW rating limit
        self.line = Branch("L1", "Bus1", "Bus2", x_pu=0.05, rating_mw=60.0)
        self.grid.add_branch(self.line)

        # Cheap CCGT at Bus 1: $25/MWh, 200 MW max
        self.cheap_gen = CombinedCyclePlant(
            resource_id="CCGT1",
            name="Cheap CCGT",
            bus_id="Bus1",
            p_min_mw=0.0,
            p_max_mw=200.0,
            variable_om_per_mwh=4.0,
            heat_rate_mmbtu_per_mwh=6.0,
            fuel_cost_per_mmbtu=3.5,  # 4 + (6 * 3.5) = $25/MWh
        )
        # Expensive Peaker at Bus 2: $65/MWh, 100 MW max
        self.expensive_gen = PeakerPlant(
            resource_id="Peaker1",
            name="Expensive Peaker",
            bus_id="Bus2",
            p_min_mw=0.0,
            p_max_mw=100.0,
            variable_om_per_mwh=5.0,
            heat_rate_mmbtu_per_mwh=10.0,
            fuel_cost_per_mmbtu=6.0,  # 5 + (10 * 6) = $65/MWh
        )
        self.grid.add_generator(self.cheap_gen)
        self.grid.add_generator(self.expensive_gen)

        # 100 MW Load at Bus 2
        self.load = ElectricLoad(
            load_id="Load2",
            bus_id="Bus2",
            base_mw=100.0,
        )
        self.grid.add_load(self.load)

    def test_transmission_constrained_dispatch(self):
        sced = SecurityConstrainedDispatch(self.grid)
        res = sced.dispatch_hour(hour=0)

        self.assertTrue(res.opt_result.success)

        # Due to 60 MW line limit:
        # Flow from Bus1 -> Bus2 must be <= 60 MW
        self.assertAlmostEqual(res.branch_flows_mw["L1"], 60.0, places=3)

        # Cheap generator dispatches 60 MW
        self.assertAlmostEqual(res.generator_dispatch_mw["CCGT1"], 60.0, places=3)

        # Expensive generator must cover the remaining 40 MW
        self.assertAlmostEqual(res.generator_dispatch_mw["Peaker1"], 40.0, places=3)

        # Unserved load should be zero
        self.assertAlmostEqual(res.unserved_load_mw["Bus2"], 0.0, places=3)


if __name__ == "__main__":
    unittest.main()
