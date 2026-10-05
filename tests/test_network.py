"""Unit tests for Bus, Branch, and PowerGrid network topology."""

import unittest
from irp.core.network import Bus, Branch, PowerGrid
from irp.core.exceptions import TopologyError


class TestNetwork(unittest.TestCase):
    def test_bus_creation(self):
        b = Bus(bus_id="bus1", name="Substation A", base_kv=230.0, is_slack=True)
        self.assertEqual(b.bus_id, "bus1")
        self.assertTrue(b.is_slack)

        with self.assertRaises(TopologyError):
            # v_min >= v_max
            Bus(bus_id="b_invalid", v_min_pu=1.1, v_max_pu=1.0)

    def test_branch_creation(self):
        br = Branch(
            branch_id="line1",
            from_bus="bus1",
            to_bus="bus2",
            x_pu=0.05,
            rating_mw=500.0,
        )
        self.assertEqual(br.from_bus, "bus1")
        self.assertAlmostEqual(br.susceptance_pu, 20.0)

        with self.assertRaises(TopologyError):
            # Connects bus to itself
            Branch(branch_id="loop", from_bus="bus1", to_bus="bus1")

        with self.assertRaises(TopologyError):
            # Negative reactance for AC line
            Branch(branch_id="bad_x", from_bus="bus1", to_bus="bus2", x_pu=-0.05)

    def test_power_grid_assembly(self):
        grid = PowerGrid("TestGrid")
        b1 = Bus("bus1", is_slack=True)
        b2 = Bus("bus2")
        grid.add_bus(b1)
        grid.add_bus(b2)

        self.assertEqual(grid.num_buses, 2)
        self.assertEqual(grid.get_slack_bus().bus_id, "bus1")

        br = Branch("line1", "bus1", "bus2", x_pu=0.1)
        grid.add_branch(br)
        self.assertEqual(grid.num_branches, 1)

        b_bus = grid.build_b_bus_matrix()
        self.assertEqual(b_bus.shape, (2, 2))
        self.assertAlmostEqual(b_bus[0, 0], 10.0)
        self.assertAlmostEqual(b_bus[0, 1], -10.0)
        self.assertAlmostEqual(b_bus[1, 0], -10.0)
        self.assertAlmostEqual(b_bus[1, 1], 10.0)


if __name__ == "__main__":
    unittest.main()
