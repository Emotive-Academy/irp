"""Electrical network topology definitions: Buses, Branches, and the PowerGrid."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np

from irp.core.exceptions import TopologyError


@dataclass
class Bus:
    """Electrical bus or regional market zone node."""

    bus_id: str
    name: str = ""
    base_kv: float = 230.0  # Nominal voltage in kV
    v_min_pu: float = 0.95  # Minimum allowable voltage in per-unit
    v_max_pu: float = 1.05  # Maximum allowable voltage in per-unit
    is_slack: bool = False  # Reference / slack bus flag
    zone: str = "default"
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def __post_init__(self) -> None:
        if not self.name:
            self.name = self.bus_id
        if self.v_min_pu >= self.v_max_pu:
            raise TopologyError(
                f"Bus {self.bus_id} has invalid voltage limits: "
                f"v_min={self.v_min_pu} >= v_max={self.v_max_pu}"
            )


@dataclass
class Branch:
    """Transmission line or transformer connecting two buses."""

    branch_id: str
    from_bus: str
    to_bus: str
    r_pu: float = 0.001  # Resistance in per-unit
    x_pu: float = 0.05   # Reactance in per-unit (X > 0 for inductive line)
    b_pu: float = 0.0    # Total line charging susceptance in per-unit
    rating_mw: float = 1000.0  # Continuous thermal rating in MW
    length_km: float = 50.0    # Physical length in kilometers
    is_hvdc: bool = False      # Whether line is High Voltage DC
    status: bool = True        # In-service (True) or out-of-service (False)

    def __post_init__(self) -> None:
        if self.from_bus == self.to_bus:
            raise TopologyError(
                f"Branch {self.branch_id} connects bus {self.from_bus} to itself."
            )
        if self.x_pu <= 0.0 and not self.is_hvdc:
            raise TopologyError(
                f"AC Branch {self.branch_id} must have positive reactance x_pu > 0."
            )
        if self.rating_mw <= 0.0:
            raise TopologyError(
                f"Branch {self.branch_id} rating must be positive."
            )

    @property
    def reactance(self) -> float:
        """Alias for x_pu."""
        return self.x_pu

    @property
    def susceptance_pu(self) -> float:
        """Series susceptance: B = -1 / X (neglecting small resistance)."""
        return 1.0 / self.x_pu if self.x_pu != 0.0 else 0.0


@dataclass
class PowerGrid:
    """Integrated container holding buses, transmission, resources, and loads."""

    name: str = "GridModel"
    base_mva: float = 100.0
    buses: Dict[str, Bus] = field(default_factory=dict)
    branches: Dict[str, Branch] = field(default_factory=dict)
    generators: List[Any] = field(default_factory=list)
    storage_units: List[Any] = field(default_factory=list)
    loads: List[Any] = field(default_factory=list)

    def add_bus(self, bus: Bus) -> None:
        """Add a bus to the power grid."""
        if bus.bus_id in self.buses:
            raise TopologyError(f"Duplicate bus ID: {bus.bus_id}")
        self.buses[bus.bus_id] = bus

    def add_branch(self, branch: Branch) -> None:
        """Add a transmission branch between existing buses."""
        if branch.from_bus not in self.buses:
            raise TopologyError(
                f"Branch {branch.branch_id} unknown from_bus: {branch.from_bus}"
            )
        if branch.to_bus not in self.buses:
            raise TopologyError(
                f"Branch {branch.branch_id} unknown to_bus: {branch.to_bus}"
            )
        if branch.branch_id in self.branches:
            raise TopologyError(f"Duplicate branch ID: {branch.branch_id}")
        self.branches[branch.branch_id] = branch

    def add_generator(self, gen: Any) -> None:
        """Add a generation resource."""
        if hasattr(gen, "bus_id") and gen.bus_id not in self.buses:
            raise TopologyError(
                f"Generator {getattr(gen, 'name', gen)} unknown bus {gen.bus_id}"
            )
        self.generators.append(gen)

    def add_storage(self, storage: Any) -> None:
        """Add an energy storage resource."""
        if hasattr(storage, "bus_id") and storage.bus_id not in self.buses:
            storage_name = getattr(storage, "name", storage)
            raise TopologyError(
                f"Storage {storage_name} unknown bus {storage.bus_id}"
            )
        self.storage_units.append(storage)

    def add_load(self, load: Any) -> None:
        """Add an electric load."""
        if hasattr(load, "bus_id") and load.bus_id not in self.buses:
            raise TopologyError(
                f"Load {getattr(load, 'name', load)} unknown bus {load.bus_id}"
            )
        self.loads.append(load)

    @property
    def num_buses(self) -> int:
        return len(self.buses)

    @property
    def num_branches(self) -> int:
        return len(self.branches)

    def get_bus_index_map(self) -> Dict[str, int]:
        """Return a mapping from bus_id to sequential zero-based integer index."""
        return {bus_id: i for i, bus_id in enumerate(self.buses.keys())}

    def get_slack_bus(self) -> Bus:
        """Return the designated slack/reference bus.

        If none is marked, the first bus is set as slack.
        """
        for bus in self.buses.values():
            if bus.is_slack:
                return bus
        if not self.buses:
            raise TopologyError("Cannot get slack bus in an empty grid.")
        first_bus = next(iter(self.buses.values()))
        first_bus.is_slack = True
        return first_bus

    def build_b_bus_matrix(self) -> np.ndarray:
        """Build the nodal imaginary susceptance matrix B_bus for DC power flow."""
        n = self.num_buses
        b_matrix = np.zeros((n, n), dtype=float)
        idx_map = self.get_bus_index_map()

        for branch in self.branches.values():
            if not branch.status or branch.is_hvdc:
                continue
            i = idx_map[branch.from_bus]
            j = idx_map[branch.to_bus]
            b_ij = 1.0 / branch.x_pu

            b_matrix[i, j] -= b_ij
            b_matrix[j, i] -= b_ij
            b_matrix[i, i] += b_ij
            b_matrix[j, j] += b_ij

        return b_matrix
