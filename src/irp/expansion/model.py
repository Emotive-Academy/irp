"""Capacity Expansion Model (CEM) optimization engine.

Couples multi-period investment, chronological dispatch, DC power flow physics,
storage dynamics, and reliability constraints.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np

from irp.core.network import PowerGrid
from irp.expansion.solver import LinearSolver, OptimizationResult
from irp.resources.generation.nuclear import NuclearPlant
from irp.resources.generation.renewable import RenewableResource


@dataclass
class ExpansionPlan:
    """Results from solving the capacity expansion model."""

    total_cost_usd: float
    built_capacity_mw: Dict[str, float]
    dispatch_mw: Dict[str, List[float]]
    storage_soc_mwh: Dict[str, List[float]]
    unserved_energy_mwh: List[float]
    curtailed_energy_mwh: List[float]
    total_co2_tons: float
    opt_result: OptimizationResult


class CapacityExpansionModel:
    """Mathematical optimization model for power system capacity expansion."""

    def __init__(
        self,
        grid: PowerGrid,
        num_hours: int = 24,
        planning_reserve_margin: float = 0.15,
        discount_rate: float = 0.07,
        voll_per_mwh: float = 10000.0,
        co2_cap_tons: Optional[float] = None,
        annualized_hours_weight: float = 8760.0 / 24.0,
    ) -> None:
        self.grid = grid
        self.num_hours = num_hours
        self.prm = planning_reserve_margin
        self.discount_rate = discount_rate
        self.voll = voll_per_mwh
        self.co2_cap_tons = co2_cap_tons
        self.hours_weight = annualized_hours_weight

    def build_and_solve(self) -> ExpansionPlan:
        """Formulate and solve the capacity expansion linear program."""
        buses = list(self.grid.buses.keys())
        branches = list(self.grid.branches.keys())
        gens = self.grid.generators
        storages = self.grid.storage_units
        loads = self.grid.loads
        h_range = range(self.num_hours)

        # 1. Variable Registry & Indexing
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

        # Investment variables X_r for candidate generators
        x_gen: Dict[str, int] = {}
        for g in gens:
            n_yrs = getattr(g, "economic_lifetime_yrs", 30)
            crf = self.discount_rate / (1.0 - (1.0 + self.discount_rate) ** (-n_yrs))
            annualized_capex = g.capital_cost_per_mw * crf + g.fixed_om_per_mw_yr
            max_b = getattr(g, "max_build_mw", None)
            cost = annualized_capex if g.is_candidate else 0.0
            ub = max_b if g.is_candidate else 0.0
            x_gen[g.resource_id] = add_var(
                f"X_gen_{g.resource_id}", cost, lb=0.0, ub=ub
            )

        # Investment variables X_s for candidate storage
        x_storage: Dict[str, int] = {}
        for s in storages:
            n_yrs = getattr(s, "economic_lifetime_yrs", 20)
            crf = self.discount_rate / (1.0 - (1.0 + self.discount_rate) ** (-n_yrs))
            annualized_capex = s.capital_cost_per_mw * crf + s.fixed_om_per_mw_yr
            cost = annualized_capex if s.is_candidate else 0.0
            max_b = getattr(s, "max_build_mw", None)
            ub = max_b if s.is_candidate else 0.0
            x_storage[s.resource_id] = add_var(
                f"X_stor_{s.resource_id}", cost, lb=0.0, ub=ub
            )

        # Operational variables: Dispatch P_{g, h}
        p_gen: Dict[tuple[str, int], int] = {}
        for g in gens:
            m_cost = g.get_marginal_cost_per_mwh() * self.hours_weight
            for h in h_range:
                p_gen[(g.resource_id, h)] = add_var(
                    f"P_gen_{g.resource_id}_h{h}", m_cost, lb=0.0
                )

        # Operational variables: Storage Charge, Discharge, SOC
        p_chg: Dict[tuple[str, int], int] = {}
        p_dis: Dict[tuple[str, int], int] = {}
        soc: Dict[tuple[str, int], int] = {}
        for s in storages:
            m_cost = s.get_marginal_cost_per_mwh() * self.hours_weight
            for h in h_range:
                p_chg[(s.resource_id, h)] = add_var(
                    f"P_chg_{s.resource_id}_h{h}", 0.0, lb=0.0
                )
                p_dis[(s.resource_id, h)] = add_var(
                    f"P_dis_{s.resource_id}_h{h}", m_cost, lb=0.0
                )
                soc[(s.resource_id, h)] = add_var(
                    f"SOC_{s.resource_id}_h{h}", 0.0, lb=0.0
                )

        # Unserved energy variables U_{bus, h}
        u_load: Dict[tuple[str, int], int] = {}
        for b_id in buses:
            for h in h_range:
                u_cost = self.voll * self.hours_weight
                u_load[(b_id, h)] = add_var(f"U_load_{b_id}_h{h}", u_cost, lb=0.0)

        # Power flow variables: Theta_{bus, h} and LineFlow F_{branch, h}
        theta: Dict[tuple[str, int], int] = {}
        f_line: Dict[tuple[str, int], int] = {}
        slack_bus = self.grid.get_slack_bus().bus_id if buses else None

        for b_id in buses:
            for h in h_range:
                lb_th = 0.0 if b_id == slack_bus else -np.pi
                ub_th = 0.0 if b_id == slack_bus else np.pi
                theta[(b_id, h)] = add_var(
                    f"Theta_{b_id}_h{h}", 0.0, lb=lb_th, ub=ub_th
                )

        for br_id in branches:
            br = self.grid.branches[br_id]
            for h in h_range:
                f_line[(br_id, h)] = add_var(
                    f"Flow_{br_id}_h{h}", 0.0, lb=-br.rating_mw, ub=br.rating_mw
                )

        n_vars = len(var_names)

        # 2. Constraints Setup
        a_eq_rows: List[np.ndarray] = []
        b_eq_vals: List[float] = []
        a_ub_rows: List[np.ndarray] = []
        b_ub_vals: List[float] = []

        def add_eq(coeffs: Dict[int, float], rhs: float) -> None:
            row = np.zeros(n_vars, dtype=float)
            for idx, val in coeffs.items():
                row[idx] = val
            a_eq_rows.append(row)
            b_eq_vals.append(rhs)

        def add_le(coeffs: Dict[int, float], rhs: float) -> None:
            row = np.zeros(n_vars, dtype=float)
            for idx, val in coeffs.items():
                row[idx] = val
            a_ub_rows.append(row)
            b_ub_vals.append(rhs)

        # 2a. Nodal Energy Balance at each bus and hour
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

            for h in h_range:
                coeffs: Dict[int, float] = {}
                for g in bus_gens:
                    coeffs[p_gen[(g.resource_id, h)]] = 1.0
                for s in bus_storages:
                    coeffs[p_chg[(s.resource_id, h)]] = -1.0
                    coeffs[p_dis[(s.resource_id, h)]] = 1.0
                for br in lines_from:
                    coeffs[f_line[(br.branch_id, h)]] = -1.0
                for br in lines_to:
                    coeffs[f_line[(br.branch_id, h)]] = 1.0
                coeffs[u_load[(b_id, h)]] = 1.0

                demand_h = sum(ld.get_demand_mw(h) for ld in bus_loads)
                add_eq(coeffs, demand_h)

        # 2b. DC Power Flow equations
        for br_id, br in self.grid.branches.items():
            if not br.status or br.is_hvdc:
                continue
            b_val = (1.0 / br.x_pu) * self.grid.base_mva
            for h in h_range:
                add_eq(
                    {
                        f_line[(br_id, h)]: 1.0,
                        theta[(br.from_bus, h)]: -b_val,
                        theta[(br.to_bus, h)]: b_val,
                    },
                    0.0,
                )

        # 2c. Generator Capacity Bounds: P_{g, h} - X_gen_g <= K_exist
        for g in gens:
            k_exist = getattr(g, "p_max_mw", 0.0) if not g.is_candidate else 0.0
            for h in h_range:
                if isinstance(g, RenewableResource):
                    cf = g.get_max_generation_mw(h, 1.0)
                    add_le(
                        {
                            p_gen[(g.resource_id, h)]: 1.0,
                            x_gen[g.resource_id]: -cf,
                        },
                        cf * k_exist,
                    )
                else:
                    add_le(
                        {
                            p_gen[(g.resource_id, h)]: 1.0,
                            x_gen[g.resource_id]: -1.0,
                        },
                        k_exist,
                    )

                if isinstance(g, NuclearPlant) and g.p_min_fraction > 0:
                    add_le(
                        {
                            p_gen[(g.resource_id, h)]: -1.0,
                            x_gen[g.resource_id]: g.p_min_fraction,
                        },
                        -g.p_min_fraction * k_exist,
                    )

        # 2d. Storage Dynamics & Capacity Constraints
        for s in storages:
            dur = s.duration_hrs
            k_exist = s.power_rating_mw if not s.is_candidate else 0.0
            initial_soc = s.initial_soc_mwh or (0.5 * k_exist * dur)

            for h in h_range:
                add_le(
                    {
                        p_chg[(s.resource_id, h)]: 1.0,
                        x_storage[s.resource_id]: -1.0,
                    },
                    k_exist,
                )
                add_le(
                    {
                        p_dis[(s.resource_id, h)]: 1.0,
                        x_storage[s.resource_id]: -1.0,
                    },
                    k_exist,
                )
                add_le(
                    {
                        soc[(s.resource_id, h)]: 1.0,
                        x_storage[s.resource_id]: -dur,
                    },
                    dur * k_exist,
                )

                eta_c = s.eta_charge
                eta_d = max(1e-4, s.eta_discharge)
                loss_factor = 1.0 - s.self_discharge_hourly

                if h == 0:
                    add_eq(
                        {
                            soc[(s.resource_id, 0)]: 1.0,
                            p_chg[(s.resource_id, 0)]: -eta_c,
                            p_dis[(s.resource_id, 0)]: 1.0 / eta_d,
                        },
                        loss_factor * initial_soc,
                    )
                else:
                    add_eq(
                        {
                            soc[(s.resource_id, h)]: 1.0,
                            soc[(s.resource_id, h - 1)]: -loss_factor,
                            p_chg[(s.resource_id, h)]: -eta_c,
                            p_dis[(s.resource_id, h)]: 1.0 / eta_d,
                        },
                        0.0,
                    )

        # 2e. Planning Reserve Margin Constraint
        total_peak_load = 0.0
        for h in h_range:
            h_load = sum(ld.get_demand_mw(h) for ld in loads)
            if h_load > total_peak_load:
                total_peak_load = h_load

        required_prm_mw = (1.0 + self.prm) * total_peak_load
        prm_coeffs: Dict[int, float] = {}
        existing_firm_mw = 0.0

        for g in gens:
            elcc = 0.95 if isinstance(g, NuclearPlant) else (
                0.20 if isinstance(g, RenewableResource) else 0.90
            )
            prm_coeffs[x_gen[g.resource_id]] = -elcc
            if not g.is_candidate:
                existing_firm_mw += elcc * getattr(g, "p_max_mw", 0.0)

        for s in storages:
            elcc_s = 0.85 if s.duration_hrs >= 4.0 else 0.50
            prm_coeffs[x_storage[s.resource_id]] = -elcc_s
            if not s.is_candidate:
                existing_firm_mw += elcc_s * s.power_rating_mw

        add_le(prm_coeffs, existing_firm_mw - required_prm_mw)

        # 2f. Emissions Cap Constraint
        if self.co2_cap_tons is not None:
            co2_coeffs: Dict[int, float] = {}
            for g in gens:
                if g.co2_intensity_tons_per_mwh > 0:
                    for h in h_range:
                        co2_coeffs[p_gen[(g.resource_id, h)]] = (
                            g.co2_intensity_tons_per_mwh * self.hours_weight
                        )
            add_le(co2_coeffs, self.co2_cap_tons)

        # 3. Solve Optimization Problem
        c_arr = np.array(c_list, dtype=float)
        a_ub = np.array(a_ub_rows, dtype=float) if a_ub_rows else None
        b_ub = np.array(b_ub_vals, dtype=float) if b_ub_vals else None
        a_eq = np.array(a_eq_rows, dtype=float) if a_eq_rows else None
        b_eq = np.array(b_eq_vals, dtype=float) if b_eq_vals else None

        opt_res = LinearSolver.solve(
            c=c_arr,
            a_ub=a_ub,
            b_ub=b_ub,
            a_eq=a_eq,
            b_eq=b_eq,
            bounds=bounds_list,
            variable_names=var_names,
        )

        # 4. Extract Solution
        built_cap: Dict[str, float] = {}
        for g_id, var_idx in x_gen.items():
            built_cap[g_id] = float(opt_res.variable_values[var_idx])
        for s_id, var_idx in x_storage.items():
            built_cap[s_id] = float(opt_res.variable_values[var_idx])

        disp_dict: Dict[str, List[float]] = {}
        for g in gens:
            disp_dict[g.resource_id] = [
                float(opt_res.variable_values[p_gen[(g.resource_id, h)]])
                for h in h_range
            ]

        soc_dict: Dict[str, List[float]] = {}
        for s in storages:
            soc_dict[s.resource_id] = [
                float(opt_res.variable_values[soc[(s.resource_id, h)]])
                for h in h_range
            ]

        unserved_arr: List[float] = [
            sum(float(opt_res.variable_values[u_load[(b_id, h)]]) for b_id in buses)
            for h in h_range
        ]

        total_co2 = 0.0
        for g in gens:
            if g.co2_intensity_tons_per_mwh > 0:
                gen_mwh = sum(disp_dict[g.resource_id]) * self.hours_weight
                total_co2 += gen_mwh * g.co2_intensity_tons_per_mwh

        return ExpansionPlan(
            total_cost_usd=opt_res.objective_value,
            built_capacity_mw=built_cap,
            dispatch_mw=disp_dict,
            storage_soc_mwh=soc_dict,
            unserved_energy_mwh=unserved_arr,
            curtailed_energy_mwh=[0.0] * self.num_hours,
            total_co2_tons=total_co2,
            opt_result=opt_res,
        )
