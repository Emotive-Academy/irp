"""Physical units, dimensional constants, and per-unit transformations."""

from __future__ import annotations

from typing import Final


class Units:
    """Standard unit conversions and physical constants for electric power systems."""

    # Base Constants
    DEFAULT_BASE_MVA: Final[float] = 100.0  # 100 MVA standard system base
    HOURS_PER_YEAR: Final[int] = 8760
    HOURS_PER_LEAP_YEAR: Final[int] = 8784

    # Thermal / Energy Conversion Factors
    MMBTU_PER_MWH: Final[float] = 3.412142  # 1 MWh = 3.412142 MMBtu
    MWH_PER_MMBTU: Final[float] = 1.0 / 3.412142  # ~0.293071 MWh/MMBtu
    JOULES_PER_MWH: Final[float] = 3.6e9  # 1 MWh = 3.6 GJ

    # Mass / Emissions Constants
    KG_PER_METRIC_TON: Final[float] = 1000.0
    LBS_PER_METRIC_TON: Final[float] = 2204.62

    # Power Prefixes
    W_PER_KW: Final[float] = 1e3
    KW_PER_MW: Final[float] = 1e3
    MW_PER_GW: Final[float] = 1e3
    W_PER_MW: Final[float] = 1e6
    W_PER_GW: Final[float] = 1e9

    @classmethod
    def mw_to_kw(cls, mw: float) -> float:
        """Convert Megawatts (MW) to Kilowatts (kW)."""
        return mw * cls.KW_PER_MW

    @classmethod
    def kw_to_mw(cls, kw: float) -> float:
        """Convert Kilowatts (kW) to Megawatts (MW)."""
        return kw / cls.KW_PER_MW

    @classmethod
    def gw_to_mw(cls, gw: float) -> float:
        """Convert Gigawatts (GW) to Megawatts (MW)."""
        return gw * cls.MW_PER_GW

    @classmethod
    def mw_to_gw(cls, mw: float) -> float:
        """Convert Megawatts (MW) to Gigawatts (GW)."""
        return mw / cls.MW_PER_GW

    @classmethod
    def mwh_to_mmbtu(cls, mwh: float) -> float:
        """Convert thermal MWh to MMBtu."""
        return mwh * cls.MMBTU_PER_MWH

    @classmethod
    def mmbtu_to_mwh(cls, mmbtu: float) -> float:
        """Convert MMBtu to equivalent electric/thermal MWh."""
        return mmbtu * cls.MWH_PER_MMBTU

    @classmethod
    def heat_rate_to_efficiency(cls, heat_rate_mmbtu_per_mwh: float) -> float:
        """Convert heat rate (MMBtu/MWh) to efficiency (eta in [0, 1])."""
        if heat_rate_mmbtu_per_mwh <= 0.0:
            raise ValueError("Heat rate must be strictly positive.")
        return cls.MMBTU_PER_MWH / heat_rate_mmbtu_per_mwh

    @classmethod
    def efficiency_to_heat_rate(cls, efficiency: float) -> float:
        """Convert thermal efficiency (eta in (0, 1]) to heat rate (MMBtu/MWh)."""
        if not (0.0 < efficiency <= 1.0):
            raise ValueError("Efficiency must be in the open interval (0, 1].")
        return cls.MMBTU_PER_MWH / efficiency

    @classmethod
    def base_impedance(
        cls, base_kv: float, base_mva: float = DEFAULT_BASE_MVA
    ) -> float:
        """Calculate base impedance (Z_base in Ohms) for voltage and MVA base."""
        if base_kv <= 0.0 or base_mva <= 0.0:
            raise ValueError("Base voltage and base MVA must be positive.")
        return (base_kv**2) / base_mva

    @classmethod
    def ohms_to_pu(
        cls,
        ohms: float,
        base_kv: float,
        base_mva: float = DEFAULT_BASE_MVA,
    ) -> float:
        """Convert physical impedance in Ohms to per-unit (p.u.) system."""
        z_base = cls.base_impedance(base_kv, base_mva)
        return ohms / z_base

    @classmethod
    def pu_to_ohms(
        cls,
        pu: float,
        base_kv: float,
        base_mva: float = DEFAULT_BASE_MVA,
    ) -> float:
        """Convert per-unit impedance (p.u.) to physical Ohms."""
        z_base = cls.base_impedance(base_kv, base_mva)
        return pu * z_base
