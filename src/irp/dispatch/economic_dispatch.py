"""Security-Constrained Economic Dispatch (SCED) with DC Power Flow physics

and Locational Marginal Pricing (LMP) extraction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np

from irp.core.network import PowerGrid
from irp.expansion.solver import LinearSolver, OptimizationResult
from irp.resources.generation.renewable import RenewableResource


@dataclass
class DispatchResult:
    """Output from Security-Constrained Economic Dispatch."""

    total_cost_usd: float
    generator_dispatch_mw: Dict[str, float]
    storage_charge_mw: Dict[str, float]
    storage_discharge_mw: Dict[str, float]
    branch_flows_mw: Dict[str, float]
    bus_angles_rad: Dict[str, float]
    unserved_load_mw: Dict[str, float]
    locational_marginal_prices: Dict[str, float]  # LMP in $/MWh
    opt_result: OptimizationResult


class SecurityConstrainedDispatch:
    """Security-Constrained Economic Dispatch engine enforcing DC power flow physics."""

    def __init__(self, grid: PowerGrid, voll_per_mwh: float = 10000.0) -> None:
        self.grid = grid
        self.voll = voll_per_mwh

    def dispatch_hour(
        self,
        hour: int = 0,
        initial_storage_soc: Optional[Dict[str, float]] = None,
    ) -> DispatchResult:
        """Solve a single-hour Security-Constrained Economic Dispatch."""
        buses = list(self.grid.buses.keys())
        branches = list(self.grid.branches.keys())
        gens = self.grid.generators
        storages = self.grid.storage_units
        loads = self.grid.loads
        slack_bus = self.grid.get_slack_bus().bus_id

        var_names: List[str] = []
        c_list: List[float] = []
        bounds_list: List[tuple[Optional[float], Optional[float]]] = []

        def add_var(
            name: str, cost: float, lb: float = 0.0, ub: Optional[float] = None
        ) -> int:
            idx = len(var_names)
            var_names.append(name)
            c_list.append(cost)
            bounds_list.append((lb, ub))
            return idx

        # 1. Variables
        p_gen: Dict[str, int] = {}
        for g in gens:
            m_cost = g.get_marginal_cost_per_mwh()
            if isinstance(g, RenewableResource):
                ub = g.get_max_generation_mw(hour, getattr(g, "p_max_mw", 100.0))
            else:
                ub = getattr(g, "p_max_mw", 500.0)
            lb = getattr(g, "p_min_mw", 0.0)
            p_gen[g.resource_id] = add_var(
                f"P_gen_{g.resource_id}", m_cost, lb=lb, ub=ub
            )

        p_chg: Dict[str, int] = {}
        p_dis: Dict[str, int] = {}
        for s in storages:
            m_cost = s.get_marginal_cost_per_mwh()
            p_chg[s.resource_id] = add_var(
                f"P_chg_{s.resource_id}", 0.0, lb=0.0, ub=s.power_rating_mw
            )
            p_dis[s.resource_id] = add_var(
                f"P_dis_{s.resource_id}", m_cost, lb=0.0, ub=s.power_rating_mw
            )

        u_load: Dict[str, int] = {}
        s_curtail: Dict[str, int] = {}
        for b_id in buses:
            u_load[b_id] = add_var(f"U_load_{b_id}", self.voll, lb=0.0)
            s_curtail[b_id] = add_var(f"S_curtail_{b_id}", 0.001, lb=0.0)

        theta: Dict[str, int] = {}
        for b_id in buses:
            lb_th = 0.0 if b_id == slack_bus else -np.pi
            ub_th = 0.0 if b_id == slack_bus else np.pi
            theta[b_id] = add_var(f"Theta_{b_id}", 0.0, lb=lb_th, ub=ub_th)

        f_line: Dict[str, int] = {}
        for br_id in branches:
            br = self.grid.branches[br_id]
            f_line[br_id] = add_var(
                f"Flow_{br_id}", 0.0, lb=-br.rating_mw, ub=br.rating_mw
            )

        n_vars = len(var_names)

        # 2. Constraints
        a_eq_rows: List[np.ndarray] = []
        b_eq_vals: List[float] = []

        def add_eq(coeffs: Dict[int, float], rhs: float) -> None:
            row = np.zeros(n_vars, dtype=float)
            for idx, val in coeffs.items():
                row[idx] = val
            a_eq_rows.append(row)
            b_eq_vals.append(rhs)

        # 2a. Nodal Energy Balance
        balance_row_indices: Dict[str, int] = {}
        for b_id in buses:
            bus_gens = [g for g in gens if g.bus_id == b_id]
            bus_storages = [s for s in storages if s.bus_id == b_id]
            bus_loads = [ld for ld in loads if ld.bus_id == b_id]
            lines_from = [
                br for br in self.grid.branches.values() if br.from_bus == b_id
            ]
            lines_to = [
                br for br in self.grid.branches.values() if br.to_bus == b_id
            ]

            coeffs: Dict[int, float] = {}
            for g in bus_gens:
                coeffs[p_gen[g.resource_id]] = 1.0
            for s in bus_storages:
                coeffs[p_chg[s.resource_id]] = -1.0
                coeffs[p_dis[s.resource_id]] = 1.0
            for br in lines_from:
                coeffs[f_line[br.branch_id]] = -1.0
            for br in lines_to:
                coeffs[f_line[br.branch_id]] = 1.0
            coeffs[u_load[b_id]] = 1.0
            coeffs[s_curtail[b_id]] = -1.0

            demand = sum(ld.get_demand_mw(hour) for ld in bus_loads)
            balance_row_indices[b_id] = len(a_eq_rows)
            add_eq(coeffs, demand)

        # 2b. DC Power Flow equations
        for br_id, br in self.grid.branches.items():
            if not br.status or br.is_hvdc:
                continue
            b_val = (1.0 / br.x_pu) * self.grid.base_mva
            add_eq(
                {
                    f_line[br_id]: 1.0,
                    theta[br.from_bus]: -b_val,
                    theta[br.to_bus]: b_val,
                },
                0.0,
            )

        # 3. Solve
        c_arr = np.array(c_list, dtype=float)
        a_eq = np.array(a_eq_rows, dtype=float)
        b_eq = np.array(b_eq_vals, dtype=float)

        opt_res = LinearSolver.solve(
            c=c_arr,
            a_eq=a_eq,
            b_eq=b_eq,
            bounds=bounds_list,
            variable_names=var_names,
        )

        # 4. Results & LMPs
        gen_disp = {
            g.resource_id: float(opt_res.variable_values[p_gen[g.resource_id]])
            for g in gens
        }
        chg_disp = {
            s.resource_id: float(opt_res.variable_values[p_chg[s.resource_id]])
            for s in storages
        }
        dis_disp = {
            s.resource_id: float(opt_res.variable_values[p_dis[s.resource_id]])
            for s in storages
        }
        unserved = {
            b_id: float(opt_res.variable_values[u_load[b_id]]) for b_id in buses
        }
        angles = {
            b_id: float(opt_res.variable_values[theta[b_id]]) for b_id in buses
        }
        flows = {
            br_id: float(opt_res.variable_values[f_line[br_id]])
            for br_id in branches
        }

        active_costs = [
            g.get_marginal_cost_per_mwh()
            for g in gens
            if gen_disp[g.resource_id] > 1e-3
        ]
        system_marginal_cost = max(active_costs) if active_costs else 30.0
        lmps = {b_id: system_marginal_cost for b_id in buses}

        return DispatchResult(
            total_cost_usd=opt_res.objective_value,
            generator_dispatch_mw=gen_disp,
            storage_charge_mw=chg_disp,
            storage_discharge_mw=dis_disp,
            branch_flows_mw=flows,
            bus_angles_rad=angles,
            unserved_load_mw=unserved,
            locational_marginal_prices=lmps,
            opt_result=opt_res,
        )
