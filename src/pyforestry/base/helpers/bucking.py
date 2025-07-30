"""Abstract helpers shared between bucking algorithms."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Iterator, List

import matplotlib.pyplot as plt
import numpy as np

from pyforestry.base.taper import Taper


class Bucker:
    """Simple base class for bucking implementations."""

    def __init__(self) -> None:
        """Initialize a new bucker instance."""


class QualityType(IntEnum):
    """Possible quality classes for bucked logs."""

    Undefined = 0
    ButtLog = 1
    MiddleLog = 2
    TopLog = 3
    Pulp = 4
    LogCull = 5
    Fuelwood = 6


@dataclass
class CrossCutSection:
    """Container for one section in a cutting solution."""

    start_point: int
    end_point: int
    volume: float
    top_diameter: float
    value: float
    species_group: str
    timber_proportion: float = 0.0
    pulp_proportion: float = 0.0
    cull_proportion: float = 0.0
    fuelwood_proportion: float = 0.0
    quality: QualityType = QualityType.Undefined


@dataclass(frozen=True)
class BuckingConfig:
    """Settings that modify bucking algorithm behaviour."""

    timber_price_factor: float = 1.0
    pulp_price_factor: float = 1.0
    use_downgrading: bool = False
    save_sections: bool = False


class _TreeCache:
    """Cache for tree taper calculations."""

    def __init__(self) -> None:
        """Initialise empty caches for diameter and height lookups."""
        self._diameters: dict[int, float] = {}
        self._heights: dict[float, int] = {}

    def diameter(self, taper: Taper, height: int) -> float:
        """Return the diameter at ``height`` (dm) caching the result."""
        if height not in self._diameters:
            self._diameters[height] = taper.get_diameter_at_height(height / 10.0)
        return self._diameters[height]

    def height(self, taper: Taper, target: float) -> int:
        """Return the height (dm) at ``target`` diameter using a cache."""
        if target not in self._heights:
            self._heights[target] = int(taper.get_height_at_diameter(target) * 10)
        return self._heights[target]


@dataclass
class BuckingResult(Mapping):
    """Encapsulates the output of a bucking algorithm."""

    species_group: str
    total_value: float
    top_proportion: float
    dead_wood_proportion: float
    high_stump_volume_proportion: float
    high_stump_value_proportion: float
    last_cut_relative_height: float
    volume_per_quality: List[float]
    timber_price_by_quality: List[float]
    vol_fub_5cm: float
    vol_sk_ub: float
    DBH_cm: float
    height_m: float
    stump_height_m: float
    diameter_stump_cm: float
    taperDiams_cm: List[float]
    taperHeights_m: List[float]
    sections: List[CrossCutSection] | None = field(default_factory=list)

    def __getitem__(self, key: str) -> Any:
        """Return attribute ``key`` or raise ``KeyError``."""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        """Iterate over attribute names."""
        return iter(self.__dict__)

    def __len__(self) -> int:
        """Return the number of stored attributes."""
        return len(self.__dict__)

    def plot(self) -> None:
        """Plot a simple representation of the bucking result."""
        if not self.sections:
            raise ValueError("No sections available for plotting.")

        fig, ax = plt.subplots(figsize=(10, 6))

        taper_heights = np.array(self.taperHeights_m, dtype=float)
        taper_diams = np.array(self.taperDiams_cm, dtype=float)
        taper_x = (taper_heights - self.stump_height_m) * 10
        taper_y = taper_diams

        ax.plot(taper_x, taper_y, linestyle="-", color="black", label="Taper")

        for section in self.sections:
            mask = (taper_x >= section.start_point) & (taper_x <= section.end_point)
            section_x = taper_x[mask]
            section_y = taper_y[mask]

            if len(section_x) == 0:
                section_x = np.array([section.start_point, section.end_point])
                section_y = np.interp(section_x, taper_x, taper_y)

            if section_x[0] > section.start_point:
                section_x = np.insert(section_x, 0, section.start_point)
                section_y = np.insert(
                    section_y,
                    0,
                    start_diameter := (
                        start_diameter
                        if (start_diameter := np.interp(section.start_point, taper_x, taper_y)) > 0
                        else 0
                    ),
                )
            if section_x[-1] < section.end_point:
                section_x = np.append(section_x, section.end_point)
                section_y = np.append(
                    section_y,
                    end_diameter := (
                        end_diameter
                        if (end_diameter := np.interp(section.end_point, taper_x, taper_y)) > 0
                        else 0
                    ),
                )

            ax.fill_between(section_x, 0, section_y, alpha=0.3)

            length = (section.end_point - section.start_point) / 10
            midpoint = (section.start_point + section.end_point) / 2

            ax.text(
                midpoint,
                section.top_diameter / 2,
                f"{section.top_diameter:.1f} cm\n{length:.2f} m\n Vol {section.volume * 1000:.0f} "
                f"$dm^3$\n {section.value:.0f} :-",
                ha="center",
                va="center",
                fontsize=8,
            )

        ax.plot(taper_x, taper_y, linestyle="-", color="black")

        for section in self.sections:
            p = section.end_point
            ax.axvline(x=p, color="grey", linestyle="--", alpha=0.7)
            y_value = np.interp(p, taper_x, taper_y)
            ax.text(
                p - 2, y_value + 0.5, f"{p}", ha="center", va="bottom", rotation=90, fontsize=9
            )

        ax.scatter(
            (1.3 - self.stump_height_m) * 10, self.DBH_cm, color="red", label="Diameter @ 1.3 m"
        )

        ax.set_xlabel("Distance from stump (dm)")
        ax.set_ylabel("Diameter (cm)")
        ax.set_title("Bucking Result Log Profile")
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)

        leg = ax.legend(loc="upper right")
        leg.get_frame().set_alpha(1)

        textstr = "\n".join(
            (
                f"Species Group: {self.species_group}",
                f"DBH: {self.DBH_cm:.1f} cm",
                f"Height: {self.height_m:.1f} m",
                f"Stump Height: {self.stump_height_m:.1f} m",
                f"Stump Diameter: {self.diameter_stump_cm:.1f} cm",
                f"Vol fub 5cm: {self.vol_fub_5cm:.3f} m³",
            )
        )

        plt.tight_layout()

        legend_x0, legend_y0, _, _ = (
            ax.get_legend().get_window_extent().transformed(ax.transAxes.inverted()).bounds
        )
        textbox_x = legend_x0
        textbox_y = legend_y0 - 0.02

        ax.text(
            textbox_x,
            textbox_y,
            textstr,
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment="top",
            horizontalalignment="left",
            bbox=dict(boxstyle="round", facecolor="white", alpha=1),
        )

        plt.show()
