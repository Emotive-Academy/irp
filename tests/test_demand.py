"""Unit tests for ElectricLoad and DemandResponse resources."""

import unittest
from irp.resources.demand.load import ElectricLoad, DemandResponse


class TestDemand(unittest.TestCase):
    def test_electric_load(self):
        load = ElectricLoad(
            load_id="load1",
            bus_id="bus1",
            base_mw=200.0,
            hourly_profile=[1.0, 1.2, 0.8],
        )
        self.assertAlmostEqual(load.get_demand_mw(0), 200.0)
        self.assertAlmostEqual(load.get_demand_mw(1), 240.0)
        self.assertAlmostEqual(load.get_demand_mw(2), 160.0)

    def test_demand_response(self):
        dr = DemandResponse(
            dr_id="dr1",
            bus_id="bus1",
            max_shed_mw=25.0,
            curtailment_cost_per_mwh=300.0,
        )
        self.assertEqual(dr.max_shed_mw, 25.0)
        self.assertTrue(dr.shift_capable)


if __name__ == "__main__":
    unittest.main()
