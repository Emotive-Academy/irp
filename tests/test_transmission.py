"""Unit tests for TransmissionLine modeling, ratings, and losses."""

import unittest
from irp.physics.transmission import TransmissionLine


class TestTransmission(unittest.TestCase):
    def test_transmission_line_properties(self):
        line = TransmissionLine(
            line_id="T1",
            from_bus="Sub1",
            to_bus="Sub2",
            voltage_kv=230.0,
            length_km=100.0,
            r_ohm_per_km=0.05,
            x_ohm_per_km=0.40,
            thermal_rating_mva=1000.0,
        )
        br = line.to_branch(base_mva=100.0)
        self.assertEqual(br.branch_id, "T1")
        self.assertAlmostEqual(br.x_pu, 40.0 / 529.0, places=4)

    def test_temperature_derating(self):
        line = TransmissionLine(
            line_id="T1",
            from_bus="Sub1",
            to_bus="Sub2",
            thermal_rating_mva=1000.0,
            reference_temp_c=25.0,
            temp_derating_coeff=0.01,
        )
        mw_ref = line.get_effective_rating_mw(ambient_temp_c=25.0, power_factor=0.98)
        self.assertAlmostEqual(mw_ref, 980.0)

        # At 45 C (+20 C delta): derating = 1 - (0.01 * 20) = 0.80 -> 784 MW
        mw_hot = line.get_effective_rating_mw(ambient_temp_c=45.0, power_factor=0.98)
        self.assertAlmostEqual(mw_hot, 784.0)

    def test_loss_estimation(self):
        line = TransmissionLine(
            line_id="T1",
            from_bus="Sub1",
            to_bus="Sub2",
            voltage_kv=230.0,
            length_km=50.0,
            r_ohm_per_km=0.04,  # Total R = 2.0 Ohms
        )
        loss = line.estimate_losses_mw(power_flow_mw=230.0)
        self.assertAlmostEqual(loss, 2.0)


if __name__ == "__main__":
    unittest.main()
