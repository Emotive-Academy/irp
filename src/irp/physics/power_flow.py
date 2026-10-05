"""Linearized DC Power Flow physics calculations and PTDF matrices."""

from __future__ import annotations

from typing import Dict, List, Tuple
import numpy as np

from irp.core.network import PowerGrid
from irp.core.exceptions import PhysicsViolationError, TopologyError


class DCPowerFlow:
    """Solves DC power flow physics and evaluates line flows and PTDF factors."""

    def __init__(self, grid: PowerGrid) -> None:
        self.grid = grid
        self.base_mva = grid.base_mva
        self.idx_map = grid.get_bus_index_map()
        self.rev_idx_map = {v: k for k, v in self.idx_map.items()}
        self.slack_bus = grid.get_slack_bus()
        self.slack_idx = self.idx_map[self.slack_bus.bus_id]

    def solve(
        self,
        net_injections_mw: Dict[str, float],
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Solve DC power flow given net active power injections at each bus.

        Net injection = Generation - Demand (MW).
        """
        n = self.grid.num_buses
        if n == 0:
            raise TopologyError("Cannot run power flow on an empty grid.")

        # Convert injections to per-unit vector
        p_inj = np.zeros(n, dtype=float)
        for bus_id, val in net_injections_mw.items():
            if bus_id in self.idx_map:
                p_inj[self.idx_map[bus_id]] = val / self.base_mva

        # Residual mismatch absorbed by slack bus to maintain energy conservation
        total_mismatch = np.sum(p_inj)
        p_inj[self.slack_idx] -= total_mismatch

        # Build B_bus matrix
        b_bus = self.grid.build_b_bus_matrix()

        # Non-slack indices
        non_slack_idx = [i for i in range(n) if i != self.slack_idx]

        if not non_slack_idx:
            return {self.slack_bus.bus_id: 0.0}, {}

        # Reduced B matrix and injection vector
        b_red = b_bus[np.ix_(non_slack_idx, non_slack_idx)]
        p_red = p_inj[non_slack_idx]

        try:
            theta_red = np.linalg.solve(b_red, p_red)
        except np.linalg.LinAlgError as err:
            raise PhysicsViolationError(
                "Nodal susceptance matrix is singular. Disconnected grid."
            ) from err

        # Reconstruct full angle vector with theta_slack = 0
        theta = np.zeros(n, dtype=float)
        for i, red_idx in enumerate(non_slack_idx):
            theta[red_idx] = theta_red[i]

        voltage_angles_rad = {
            self.rev_idx_map[i]: float(theta[i]) for i in range(n)
        }

        # Compute branch flows: F_ij = (theta_i - theta_j) / X_ij * base_mva
        line_flows_mw: Dict[str, float] = {}
        for branch_id, branch in self.grid.branches.items():
            if not branch.status:
                line_flows_mw[branch_id] = 0.0
                continue
            i = self.idx_map[branch.from_bus]
            j = self.idx_map[branch.to_bus]
            if branch.is_hvdc:
                continue
            f_ij_pu = (theta[i] - theta[j]) / branch.x_pu
            line_flows_mw[branch_id] = float(f_ij_pu * self.base_mva)

        return voltage_angles_rad, line_flows_mw

    def calculate_ptdf(self) -> Tuple[np.ndarray, List[str], List[str]]:
        """Calculate the Power Transfer Distribution Factor (PTDF) matrix."""
        n_buses = self.grid.num_buses
        ac_branches = [
            b for b in self.grid.branches.values() if b.status and not b.is_hvdc
        ]
        n_branches = len(ac_branches)

        if n_buses <= 1 or n_branches == 0:
            return np.zeros((0, n_buses)), [], list(self.grid.buses.keys())

        b_bus = self.grid.build_b_bus_matrix()
        non_slack_idx = [i for i in range(n_buses) if i != self.slack_idx]

        b_red_inv = np.linalg.pinv(b_bus[np.ix_(non_slack_idx, non_slack_idx)])

        # Full inverted B matrix with zero row/col for slack
        x_bus = np.zeros((n_buses, n_buses), dtype=float)
        for i_loc, i_orig in enumerate(non_slack_idx):
            for j_loc, j_orig in enumerate(non_slack_idx):
                x_bus[i_orig, j_orig] = b_red_inv[i_loc, j_loc]

        ptdf = np.zeros((n_branches, n_buses), dtype=float)
        branch_ids = []

        for k, branch in enumerate(ac_branches):
            branch_ids.append(branch.branch_id)
            i = self.idx_map[branch.from_bus]
            j = self.idx_map[branch.to_bus]
            b_line = 1.0 / branch.x_pu
            for m in range(n_buses):
                ptdf[k, m] = b_line * (x_bus[i, m] - x_bus[j, m])

        bus_ids = [self.rev_idx_map[i] for i in range(n_buses)]
        return ptdf, branch_ids, bus_ids
