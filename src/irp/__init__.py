"""irp: An open-source, modular capacity expansion and techno-economic

optimization framework for electricity grid planning.
"""

from __future__ import annotations

from irp.core.network import PowerGrid, Bus, Branch
from irp.core.units import Units
from irp.physics.power_flow import DCPowerFlow
from irp.physics.transmission import TransmissionLine
from irp.resources.storage.bess import BESS
from irp.resources.storage.ldes import LDES
from irp.resources.generation.nuclear import NuclearPlant
from irp.resources.generation.thermal import PeakerPlant, CombinedCyclePlant
from irp.resources.generation.renewable import SolarPV, WindTurbine
from irp.resources.demand.load import ElectricLoad
from irp.expansion.model import CapacityExpansionModel
from irp.dispatch.economic_dispatch import SecurityConstrainedDispatch

try:
    from importlib.metadata import version, PackageNotFoundError
except Exception:  # pragma: no cover
    version = None
    PackageNotFoundError = Exception

__version__: str
try:
    __version__ = version("irp") if version else "0.1.0"
except PackageNotFoundError:
    __version__ = "0.1.0"

__all__ = [
    "__version__",
    "PowerGrid",
    "Bus",
    "Branch",
    "Units",
    "DCPowerFlow",
    "TransmissionLine",
    "BESS",
    "LDES",
    "NuclearPlant",
    "PeakerPlant",
    "CombinedCyclePlant",
    "SolarPV",
    "WindTurbine",
    "ElectricLoad",
    "CapacityExpansionModel",
    "SecurityConstrainedDispatch",
]
