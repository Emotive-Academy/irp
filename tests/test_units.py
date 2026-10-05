"""Unit tests for Units and dimensional conversions."""

import unittest
from irp.core.units import Units


class TestUnits(unittest.TestCase):
    def test_power_conversions(self):
        self.assertAlmostEqual(Units.mw_to_kw(10.0), 10000.0)
        self.assertAlmostEqual(Units.kw_to_mw(5000.0), 5.0)
        self.assertAlmostEqual(Units.gw_to_mw(2.5), 2500.0)
        self.assertAlmostEqual(Units.mw_to_gw(3000.0), 3.0)

    def test_energy_and_heat_rate(self):
        # 1 MWh = 3.412142 MMBtu
        self.assertAlmostEqual(Units.mwh_to_mmbtu(1.0), 3.412142, places=5)
        self.assertAlmostEqual(Units.mmbtu_to_mwh(3.412142), 1.0, places=5)

        # Heat rate to efficiency: 3.412142 / 6.824284 = 0.50 (50%)
        eta = Units.heat_rate_to_efficiency(3.412142 * 2)
        self.assertAlmostEqual(eta, 0.50, places=4)

        hr = Units.efficiency_to_heat_rate(0.50)
        self.assertAlmostEqual(hr, 6.824284, places=4)

        with self.assertRaises(ValueError):
            Units.heat_rate_to_efficiency(0.0)

        with self.assertRaises(ValueError):
            Units.efficiency_to_heat_rate(0.0)

    def test_per_unit_impedance(self):
        # Z_base = 230^2 / 100 = 529 Ohms
        z_base = Units.base_impedance(base_kv=230.0, base_mva=100.0)
        self.assertAlmostEqual(z_base, 529.0)

        # 52.9 Ohms -> 0.1 pu
        pu = Units.ohms_to_pu(52.9, base_kv=230.0, base_mva=100.0)
        self.assertAlmostEqual(pu, 0.10)

        ohms = Units.pu_to_ohms(0.10, base_kv=230.0, base_mva=100.0)
        self.assertAlmostEqual(ohms, 52.9)


if __name__ == "__main__":
    unittest.main()
