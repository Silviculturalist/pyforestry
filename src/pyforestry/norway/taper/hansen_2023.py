"""Hansen et al. (2023) taper model for spruce, pine, and birch in Norway."""

from __future__ import annotations

import math
import warnings

import numpy as np
from scipy.optimize import minimize_scalar

from pyforestry.base.contracts import FormulaDescriptor, SourceReference
from pyforestry.base.taper import Taper
from pyforestry.base.timber import Timber


class Hansen2023(Taper):
    """Stateful taper model implementation for a single `Timber` instance."""

    _ALIASES = {
        "spruce": {"spruce", "s", "gran", "g", "1", "picea abies"},
        "pine": {"pine", "p", "furu", "f", "2", "pinus sylvestris"},
        "birch": {"birch", "b", "bjork", "bjørk", "bj", "lauv", "l", "3", "betula"},
    }
    _PARAMS = {
        "spruce": (
            1.0625010,
            0.9590684,
            0.9982461,
            2.2909135,
            -0.5201230,
            3.8808849,
            -2.1078922,
            0.1695809,
        ),
        "pine": (
            1.14798036,
            0.90295964,
            1.00118665,
            0.24116857,
            -0.09667025,
            -0.50359177,
            0.32132441,
            0.05546691,
        ),
        "birch": (
            0.9810885,
            0.9936293,
            0.9941538,
            0.8526987,
            -0.1819791,
            0.4687623,
            -0.2198294,
            0.1591102,
        ),
    }

    def __init__(self, timber: Timber):
        """Create a new Hansen taper model for `timber`."""
        super().__init__(timber, self)
        self.validate(timber)
        self._species_key = self._normalize_species(timber.species)
        self._params = self._PARAMS[self._species_key]

    @classmethod
    def _normalize_species(cls, species: str) -> str:
        """Map a species label to one of: spruce, pine, birch."""
        key = species.strip().lower()
        for normalized, aliases in cls._ALIASES.items():
            if key in aliases:
                return normalized
        raise ValueError(f"Species '{species}' is not recognized for Hansen2023.")

    @classmethod
    def validate(cls, timber: Timber) -> None:
        """Validate timber compatibility with Hansen2023 requirements."""
        if not isinstance(timber, Timber):
            raise TypeError("Provided object is not a Timber instance.")
        if not isinstance(timber.species, str) or not timber.species.strip():
            raise ValueError("Timber species must be a non-empty string.")
        if not isinstance(timber.diameter_cm, (int, float)) or timber.diameter_cm <= 0:
            raise ValueError("Timber diameter_cm must be a positive number.")
        if not isinstance(timber.height_m, (int, float)) or timber.height_m <= 0:
            raise ValueError("Timber height_m must be a positive number.")
        cls._normalize_species(timber.species)

    def _diameter_over_bark_cm(self, height_m: float) -> float:
        """Return modeled over-bark diameter (cm) at `height_m` above ground."""
        dbh = float(self.timber.diameter_cm)
        total_height = float(self.timber.height_m)

        if height_m < 0:
            warnings.warn("Requested height below ground. Returning zero diameter.", stacklevel=2)
            return 0.0
        if height_m >= total_height:
            return 0.0

        relative_h = height_m / total_height
        b1, b2, b3, b4, b5, b6, b7, b8 = self._params

        denom_term = 1.0 - math.sqrt(0.2)
        num_term = 1.0 - math.sqrt(max(0.0, min(relative_h, 1.0 - 1e-12)))
        base = num_term / denom_term
        if base <= 0.0:
            return 0.0

        exponent = (
            b4 * (relative_h**2)
            + b5 * math.log(max(relative_h, 0.0) + 0.001)
            + b6 * math.sqrt(max(relative_h, 0.0))
            + b7 * math.exp(relative_h)
            + b8 * (dbh / total_height)
        )
        pre_factor = b1 * (dbh**b2) * (b3**dbh)
        diameter = pre_factor * float(np.power(base, exponent))
        if not np.isfinite(diameter):
            return 0.0
        return max(0.0, diameter)

    def get_diameter_at_height(self, height_m: float, with_bark: bool = True) -> float:
        """Return stem diameter (cm) at `height_m` above ground."""
        if not with_bark:
            raise NotImplementedError(
                "Under-bark diameter requires a bark subtraction function not implemented here."
            )
        if not isinstance(height_m, (int, float)):
            raise ValueError("height_m must be numeric.")
        return self._diameter_over_bark_cm(float(height_m))

    def get_height_at_diameter(self, diameter_cm: float, with_bark: bool = True) -> float | None:
        """Return height (m above ground) where stem diameter equals `diameter_cm`."""
        if not with_bark:
            raise NotImplementedError("Under-bark diameter lookup is not implemented.")
        if not isinstance(diameter_cm, (int, float)) or diameter_cm < 0.0:
            raise ValueError("diameter_cm must be a non-negative number.")

        target = float(diameter_cm)
        total_height = float(self.timber.height_m)
        epsilon = 1e-6

        if target <= epsilon:
            return total_height

        base_diameter = self._diameter_over_bark_cm(epsilon)
        if target >= base_diameter:
            return 0.0

        def objective(h: float) -> float:
            """Minimize diameter mismatch at candidate height.

            Args:
                h: Candidate stem height in meters.

            Returns:
                Absolute difference between target diameter and taper diameter.

            Source:
                Hansen et al. (2023) taper implementation wrapped in pyforestry.
            """
            h_clamped = max(epsilon, min(float(h), total_height - epsilon))
            return abs(self._diameter_over_bark_cm(h_clamped) - target)

        result = minimize_scalar(
            objective,
            bounds=(epsilon, total_height - epsilon),
            method="bounded",
            options={"xatol": 1e-5, "maxiter": 100},
        )
        if not result.success:
            return None

        h_value = float(result.x)
        if objective(h_value) > 1e-2:
            return None
        return h_value


__all__ = ["Hansen2023"]


DESCRIPTOR = FormulaDescriptor(
    component_id="hansen_2023_taper",
    source=SourceReference(
        author="Hansen, E., Rahlf, J., Astrup, R. & Gobakken, T.",
        year=2023,
        title="Taper, volume, and bark thickness models for spruce, pine, and birch in Norway",
        note=(
            "Scandinavian Journal of Forest Research 38(6):413-428. "
            "doi:10.1080/02827581.2023.2243821. "
            "Taper sub-model; the taper equation form follows Kozak (1988)."
        ),
    ),
    species_groups={
        "spruce": frozenset({"Picea abies"}),
        "pine": frozenset({"Pinus sylvestris"}),
        "birch": frozenset({"Betula pubescens", "Betula pendula"}),
    },
    units={},
    kernel_names=("Hansen2023",),
)
