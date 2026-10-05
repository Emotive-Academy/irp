"""Unit tests for DC Power Flow physics calculations and PTDF matrices."""

import unittest
from irp.core.network import Bus, Branch, PowerGrid
from irp.physics.power_flow import DCPowerFlow
from irp.core.exceptions import PhysicsViolationError


class TestPhysics(unittest.TestCase):
    def setUp(self):
        # Build 3-bus triangle test grid
        # Bus 1 (Slack) --- line1 (X=0.1) --- Bus 2
        #    \                                 /
        #  line3 (X=0.2)                  line2 (X=0.1)
        #      \                             /
        #       +-------- Bus 3 ------------+
        self.grid = PowerGrid("3BusGrid", base_mva=100.0)
        self.b1 = Bus("B1", is_slack=True)
        self.b2 = Bus("B2")
        self.b3 = Bus("B3")
        self.grid.add_bus(self.b1)
        self.grid.add_bus(self.b2)
        self.grid.add_bus(self.b3)

        self.l1 = Branch("L1", "B1", "B2", x_pu=0.1)
        self.l2 = Branch("L2", "B2", "B3", x_pu=0.1)
        self.l3 = Branch("L3", "B1", "B3", x_pu=0.2)
        self.grid.add_branch(self.l1)
        self.grid.add_branch(self.l2)
        self.grid.add_branch(self.l3)

    def test_dc_power_flow_solution(self):
        pf = DCPowerFlow(self.grid)
        injections = {"B1": 100.0, "B2": 0.0, "B3": -100.0}
        angles, flows = pf.solve(injections)

        # Slack angle should be 0.0
        self.assertAlmostEqual(angles["B1"], 0.0)
        flow_into_b3 = flows["L2"] + flows["L3"]
        self.assertAlmostEqual(flow_into_b3, 100.0, places=3)

    def test_ptdf_calculation(self):
        pf = DCPowerFlow(self.grid)
        ptdf, branch_ids, bus_ids = pf.calculate_ptdf()
        self.assertEqual(ptdf.shape, (3, 3))
        # Injection at slack bus causes zero flow change relative to slack
        slack_col = bus_ids.index("B1")
        for k in range(3):
            self.assertAlmostEqual(ptdf[k, slack_col], 0.0)

    def test_disconnected_grid_error(self):
        # Create grid with isolated islanded bus
        grid = PowerGrid("IslandGrid")
        grid.add_bus(Bus("B1", is_slack=True))
        grid.add_bus(Bus("B2_isolated"))
        pf = DCPowerFlow(grid)
        with self.assertRaises(PhysicsViolationError):
            pf.solve({"B1": 50.0, "B2_isolated": -50.0})


if __name__ == "__main__":
    unittest.main()
