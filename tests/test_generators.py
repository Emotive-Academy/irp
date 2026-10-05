"""Unit tests for Nuclear, Thermal, and Renewable generation resources."""

import unittest
from irp.resources.generation.nuclear import NuclearPlant
from irp.resources.generation.thermal import PeakerPlant, CombinedCyclePlant
from irp.resources.generation.renewable import SolarPV, WindTurbine


class TestGenerators(unittest.TestCase):
    def test_nuclear_plant(self):
        nuc = NuclearPlant(
            resource_id="nuc1",
            name="Vogtle Unit",
            bus_id="bus1",
            p_max_mw=1100.0,
            p_min_fraction=0.85,
            ramp_rate_pct_per_hr=5.0,
        )
        self.assertAlmostEqual(nuc.p_min_mw, 1100.0 * 0.85)
        self.assertAlmostEqual(nuc.ramp_rate_mw_per_hr, 1100.0 * 0.05)
        self.assertEqual(nuc.co2_intensity_tons_per_mwh, 0.0)
        self.assertFalse(nuc.is_smr())

        smr = NuclearPlant(
            resource_id="smr1",
            name="NuScale SMR",
            bus_id="bus1",
            p_max_mw=77.0,
        )
        self.assertTrue(smr.is_smr())

    def test_thermal_peaker_and_ccgt(self):
        peaker = PeakerPlant(
            resource_id="peak1",
            name="Aero Peaker",
            bus_id="bus1",
            p_max_mw=100.0,
            heat_rate_mmbtu_per_mwh=10.0,
            fuel_cost_per_mmbtu=4.0,
            variable_om_per_mwh=5.0,
        )
        # Marginal cost = 5 + (10 * 4) = $45/MWh
        self.assertAlmostEqual(peaker.get_marginal_cost_per_mwh(), 45.0)

        # Hydrogen blend test
        peaker.adjust_for_hydrogen_blend(30.0)
        self.assertLess(peaker.co2_intensity_tons_per_mwh, 0.53)

        # CCGT with CCS
        ccgt = CombinedCyclePlant(
            resource_id="ccgt1",
            name="CCGT Facility",
            bus_id="bus1",
            p_max_mw=500.0,
            ccs_equipped=True,
            ccs_capture_rate=0.90,
        )
        # CO2 reduced by 90%: 0.35 * 0.10 = 0.035 MT/MWh
        self.assertAlmostEqual(ccgt.co2_intensity_tons_per_mwh, 0.035, places=4)

    def test_renewables(self):
        solar = SolarPV(
            resource_id="pv1",
            name="Desert Solar",
            bus_id="bus1",
            capacity_factor_profile=[0.0, 0.0, 0.2, 0.8, 0.9, 0.4, 0.0],
        )
        # Hour 3 has 0.80 CF -> 80 MW on 100 MW
        self.assertAlmostEqual(solar.get_max_generation_mw(3, 100.0), 80.0)
        self.assertEqual(solar.get_marginal_cost_per_mwh(), 0.0)

        wind = WindTurbine(
            resource_id="wind1",
            name="Plains Wind",
            bus_id="bus1",
            wind_type="Onshore",
        )
        self.assertEqual(wind.wind_type, "Onshore")


if __name__ == "__main__":
    unittest.main()
