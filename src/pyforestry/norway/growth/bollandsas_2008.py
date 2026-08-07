"""Bollandsås size-class matrix model for mixed stands in Norway.

Implements the transition-matrix model of Bollandsås, Buongiorno & Gobakken
(2008), Scand. J. For. Res. 23(2):167-178. All coefficients are taken from that
paper and verified term-by-term against its published tables: recruitment
probability (Table V, eq. 4), conditional recruits (Table VI, eq. 5), diameter
increment (Table VII) and mortality (Table VIII).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

import numpy as np

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.helpers import Stand
from pyforestry.base.helpers.primitives import StandBasalArea
from pyforestry.base.helpers.tree_species import TreeName


@dataclass(frozen=True)
class _RecruitProbParams:
    """Parameters for the probability that recruitment is present."""

    a0: float
    a_ba: float
    a_si: float
    a_pba: float


@dataclass(frozen=True)
class _RecruitCondParams:
    """Parameters for expected recruits given recruitment presence."""

    b0: float
    b_ba: float
    b_si: float
    b_pba: float


@dataclass(frozen=True)
class _IncrementParams:
    """Parameters for diameter increment in millimetres per 5-year period."""

    u0: float
    u_dbh: float
    u_dbh2: float
    u_bal: float
    u_si: float
    u_ba: float
    u_lat: float
    u_dbh3: float = 0.0


@dataclass(frozen=True)
class _MortalityParams:
    """Parameters for 5-year mortality probability."""

    d0: float
    d_dbh: float
    d_dbh2: float
    d_ba: float


class Bollandsas2008:
    """Size-class stand model with recruitment, increment, and mortality."""

    SPECIES: tuple[str, ...] = ("spruce", "pine", "birch", "other_broadleaves")

    def __init__(
        self,
        site_index_by_species: Mapping[str, float],
        latitude_deg: float,
        *,
        n_classes: int = 15,
        class_width_mm: float = 50.0,
    ) -> None:
        """Store site parameters and initialize fixed class geometry."""
        if n_classes < 1:
            raise ValueError("n_classes must be >= 1.")
        if class_width_mm <= 0.0:
            raise ValueError("class_width_mm must be positive.")

        self.n_classes = int(n_classes)
        self.class_width_mm = float(class_width_mm)
        self.class_lower = np.array(
            [50.0 + i * self.class_width_mm for i in range(self.n_classes)],
            dtype=float,
        )
        self.class_mid = self.class_lower + 0.5 * self.class_width_mm
        self.site_index = {sp: float(site_index_by_species.get(sp, 0.0)) for sp in self.SPECIES}
        self.latitude_deg = float(latitude_deg)
        self._init_parameters()

    def _init_parameters(self) -> None:
        """Initialize published parameter tables for all species groups."""
        # Recruitment-presence (stage-1 logistic) coefficients: Bollandsas,
        # Buongiorno & Gobakken (2008), Table V (eq. 4). Verified term-by-term
        # against the paper for all four species, incl. 'other_broadleaves' SI =
        # 0.123 (SE 0.011). (The sitree R package's 0.0123 is a 10x error; the
        # published value is 0.123. Pine/birch SI = 0.0: not significant in Table V.)
        self._recruit_prob = {
            "spruce": _RecruitProbParams(-2.291, -0.018, 0.066, 0.019),
            "pine": _RecruitProbParams(-3.552, -0.062, 0.000, 0.031),
            "birch": _RecruitProbParams(-0.904, -0.037, 0.000, 0.016),
            "other_broadleaves": _RecruitProbParams(-3.438, -0.029, 0.123, 0.048),
        }
        self._recruit_cond = {
            "spruce": _RecruitCondParams(43.142, -0.157, 0.368, 0.051),
            "pine": _RecruitCondParams(67.152, -0.076, 0.000, 0.000),
            "birch": _RecruitCondParams(64.943, -0.161, 0.143, 0.104),
            "other_broadleaves": _RecruitCondParams(31.438, -0.1695, 0.442, 0.193),
        }
        self._increment = {
            "spruce": _IncrementParams(17.839, 0.0476, -11.585e-5, -0.3412, 0.906, -0.024, -0.268),
            "pine": _IncrementParams(25.543, 0.0251, -5.660e-5, -0.216, 0.698, -0.123, -0.336),
            "birch": _IncrementParams(
                11.808, 0.0, 9.616e-5, 0.0, 0.519, -0.152, -0.161, -9.585e-8
            ),
            "other_broadleaves": _IncrementParams(
                2.204, 0.063, -8.320e-5, 0.0, 0.359, -0.177, 0.0
            ),
        }
        self._mortality = {
            "spruce": _MortalityParams(-2.492, -0.020, 3.200e-5, 0.031),
            "pine": _MortalityParams(-1.808, -0.027, 3.300e-5, 0.055),
            "birch": _MortalityParams(-2.188, -0.016, 2.700e-5, 0.030),
            "other_broadleaves": _MortalityParams(-1.551, -0.011, 1.400e-5, 0.016),
        }

    @staticmethod
    def logistic(x: float) -> float:
        """Return numerically stable logistic transform."""
        if x >= 0.0:
            z = math.exp(-x)
            return 1.0 / (1.0 + z)
        z = math.exp(x)
        return z / (1.0 + z)

    @staticmethod
    def _species_group(species: TreeName | None) -> str | None:
        """Map a TreeName into the model's species groups."""
        if species is None:
            return None
        genus = species.genus.name.lower()
        if genus == "picea":
            return "spruce"
        if genus == "pinus":
            return "pine"
        if genus == "betula":
            return "birch"
        if genus in {"alnus", "populus", "quercus", "fagus", "ulmus", "fraxinus", "acer"}:
            return "other_broadleaves"
        return None

    @staticmethod
    def _basal_area_per_tree_m2(dbh_mm: float) -> float:
        """Return single-tree basal area from diameter in millimetres."""
        dbh_m = dbh_mm / 1000.0
        return math.pi * dbh_m * dbh_m * 0.25

    def _empty_state(self) -> dict[str, np.ndarray]:
        """Return an all-zero state dictionary for model species groups."""
        return {sp: np.zeros(self.n_classes, dtype=float) for sp in self.SPECIES}

    def _validate_state(self, state: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
        """Validate and normalize state vectors for all species groups."""
        out: dict[str, np.ndarray] = {}
        for sp in self.SPECIES:
            arr = np.array(state.get(sp, np.zeros(self.n_classes, dtype=float)), dtype=float)
            if arr.shape != (self.n_classes,):
                raise ValueError(f"State for '{sp}' must have shape ({self.n_classes},).")
            out[sp] = arr
        return out

    def stand_to_state(self, stand: Stand) -> dict[str, np.ndarray]:
        """Bin tree-list plot data into model diameter classes (stems/ha)."""
        if not stand.plots:
            return self._empty_state()

        per_plot: list[dict[str, np.ndarray]] = []
        for plot in stand.plots:
            eff_area_ha = max(1e-9, plot.area_ha * max(1e-9, 1.0 - float(plot.occlusion)))
            bins = self._empty_state()
            for tree in plot.trees:
                group = self._species_group(getattr(tree, "species", None))
                if group is None:
                    continue
                dbh_raw = getattr(tree, "diameter_cm", None)
                if dbh_raw is None:
                    continue
                dbh_mm = 10.0 * float(dbh_raw)
                if dbh_mm < 50.0:
                    continue
                idx = int((dbh_mm - 50.0) // self.class_width_mm)
                idx = min(max(idx, 0), self.n_classes - 1)
                weight = float(getattr(tree, "weight_n", 1.0) or 1.0)
                bins[group][idx] += weight / eff_area_ha
            per_plot.append(bins)

        out = self._empty_state()
        for sp in self.SPECIES:
            out[sp] = np.mean([plot_state[sp] for plot_state in per_plot], axis=0)
        return out

    def compute_stand_basal_area_by_species(
        self, state: Mapping[str, np.ndarray]
    ) -> dict[str, StandBasalArea]:
        """Compute stand basal area (`m2/ha`) for each model species group."""
        parsed = self._validate_state(state)
        ba_per_tree = np.array([self._basal_area_per_tree_m2(d) for d in self.class_mid])
        return {sp: StandBasalArea(float(np.dot(parsed[sp], ba_per_tree))) for sp in self.SPECIES}

    def _predict_recruits(self, state: Mapping[str, np.ndarray]) -> dict[str, float]:
        """Predict 5-year recruits entering the first diameter class."""
        ba_by_species = self.compute_stand_basal_area_by_species(state)
        ba_total = float(sum(float(v) for v in ba_by_species.values()))
        if ba_total <= 0.0:
            pba = {sp: 0.0 for sp in self.SPECIES}
        else:
            pba = {sp: 100.0 * float(ba_by_species[sp]) / ba_total for sp in self.SPECIES}

        recruits: dict[str, float] = {}
        for sp in self.SPECIES:
            si = self.site_index[sp]
            rp = self._recruit_prob[sp]
            rc = self._recruit_cond[sp]
            eta = rp.a0 + rp.a_ba * ba_total + rp.a_si * si + rp.a_pba * pba[sp]
            p_pos = self.logistic(eta)
            # Conditional expected recruits: Bollandsas et al. (2008) Table VI,
            # eq. (5) CR = b0 * BA^b1 * SI^b2 * (PBA+1)^b3 (product of powers; fitted
            # by linear regression on log-transformed variables). The +1 on PBA is
            # per Table VI footnote b (added to allow log-transform when PBA = 0).
            cond = rc.b0 * (max(ba_total, 1e-6) ** rc.b_ba) * (max(si, 1e-6) ** rc.b_si)
            cond *= (1.0 + pba[sp]) ** rc.b_pba
            recruits[sp] = max(0.0, p_pos * cond)
        return recruits

    def _compute_bal_vector(self, state: Mapping[str, np.ndarray]) -> np.ndarray:
        """Return class-wise basal area in larger trees (`m2/ha`)."""
        parsed = self._validate_state(state)
        ba_per_tree = np.array(
            [self._basal_area_per_tree_m2(d) for d in self.class_mid], dtype=float
        )
        class_ba = np.zeros(self.n_classes, dtype=float)
        for sp in self.SPECIES:
            class_ba += parsed[sp] * ba_per_tree
        reverse_cumsum = np.cumsum(class_ba[::-1])[::-1]
        bal = np.zeros(self.n_classes, dtype=float)
        bal[:-1] = reverse_cumsum[1:]
        return bal

    def step_5y(
        self,
        state: Mapping[str, np.ndarray],
        harvest_by_species: Mapping[str, np.ndarray] | None = None,
    ) -> dict[str, np.ndarray]:
        """Run one 5-year transition step with optional class-wise harvest."""
        current = self._validate_state(state)
        harvest = self._validate_state(harvest_by_species or {})
        ba_total = sum(
            float(v) for v in self.compute_stand_basal_area_by_species(current).values()
        )
        bal = self._compute_bal_vector(current)
        recruits = self._predict_recruits(current)

        next_state = self._empty_state()
        for sp in self.SPECIES:
            params_inc = self._increment[sp]
            params_mort = self._mortality[sp]
            counts = np.maximum(0.0, current[sp] - harvest[sp])
            moved = np.zeros(self.n_classes, dtype=float)
            for j in range(self.n_classes):
                dbh = self.class_mid[j]
                inc = (
                    params_inc.u0
                    + params_inc.u_dbh * dbh
                    + params_inc.u_dbh2 * (dbh**2)
                    + params_inc.u_dbh3 * (dbh**3)
                    + params_inc.u_bal * bal[j]
                    + params_inc.u_si * self.site_index[sp]
                    + params_inc.u_ba * ba_total
                    + params_inc.u_lat * self.latitude_deg
                )
                if j == (self.n_classes - 1):
                    move_prob = 0.0
                else:
                    move_prob = min(max(inc, 0.0) / self.class_width_mm, 0.999)
                mort_eta = (
                    params_mort.d0
                    + params_mort.d_dbh * dbh
                    + params_mort.d_dbh2 * (dbh**2)
                    + params_mort.d_ba * ba_total
                )
                mort_prob = min(max(self.logistic(mort_eta), 0.0), 0.999)
                stay_prob = max(0.0, 1.0 - move_prob - mort_prob)
                stayed = counts[j] * stay_prob
                moved[j] += stayed
                if j < (self.n_classes - 1):
                    moved[j + 1] += counts[j] * move_prob
            moved[0] += recruits[sp]
            next_state[sp] = moved
        return next_state

    def simulate_years(
        self,
        state0: Mapping[str, np.ndarray],
        years: int,
        harvest_schedule: Mapping[int, Mapping[str, np.ndarray]] | None = None,
    ) -> list[dict[str, np.ndarray]]:
        """Simulate a stand trajectory in 5-year steps."""
        steps = max(1, int(round(years / 5)))
        history = [self._validate_state(state0)]
        current = history[0]
        for k in range(1, steps + 1):
            harvest = None if harvest_schedule is None else harvest_schedule.get(5 * k)
            current = self.step_5y(current, harvest)
            history.append(current)
        return history


__all__ = ["Bollandsas2008"]


DESCRIPTOR = FormulaDescriptor(
    component_id="bollandsas_2008_growth",
    source=SourceReference(
        author="Bollandsås, O.M., Buongiorno, J. & Gobakken, T.",
        year=2008,
        title=(
            "Predicting the growth of stands of trees of mixed species and size: "
            "a matrix model for Norway"
        ),
        note=(
            "Scandinavian Journal of Forest Research 23(2):167-178. "
            "doi:10.1080/02827580801995315. Submodels from Bollandsås (2007)."
        ),
    ),
    species_groups={
        "spruce": frozenset({"Picea abies"}),
        "pine": frozenset({"Pinus sylvestris"}),
        "birch": frozenset({"Betula pubescens", "Betula pendula"}),
    },
    units={},
    kernel_names=("Bollandsas2008",),
)
