"""Module for Bitterlich (angle count) sampling techniques.

This module provides classes to tally tree counts per species
using the angle-count (relascope) method and to aggregate
multiple sampling points into stand-level basal area and
stem density metrics.

Source:
    Bitterlich, W. (1948). *Die Winkelzählprobe.* Allgemeine Forst- und
    Holzwirtschaftliche Zeitung 59(1/2), 4-5. The angle-count principle: with a
    basal area factor ``k``, every tallied tree contributes ``k`` m^2/ha of basal
    area regardless of its distance from the sample point.
"""

import math
import statistics
from typing import Dict, List, Optional, Set, Tuple, Union

from pyforestry.base.helpers.primitives import StandBasalArea, Stems
from pyforestry.base.helpers.tree_species import TreeName


class AngleCount:
    """Parameters and tallies for angle-count sampling at a single point.

    See Also:
        https://en.wikipedia.org/wiki/Relascope_sampling

    Attributes:
        ba_factor (float): Basal area factor (m²/ha) applied per count.
        slope (float): Terrain slope at the point as a ratio (rise/run, i.e.
            tan of the inclination). A slope correction factor
            ``sqrt(1 + slope**2)`` (= sec of the inclination angle) is applied to
            the per-hectare estimates during aggregation; ``0.0`` means level
            ground (no correction). Leave it at ``0.0`` for instruments that
            already compensate for inclination, or the correction is doubled.
        point_id (Optional[str]): Identifier for the sampling point.
        species (List[TreeName]): List of tree species encountered.
        value (List[float]): Corresponding tallied counts for each species.
        diameters_cm (Optional[List[List[float]]]): Optional breast-height
            diameters (cm) of the tallied ("in") trees, one inner list per
            species aligned with ``species``. When supplied for every species,
            it enables an unbiased stems/ha estimate (``sum(BAF / g_i)``); a
            relascope tally alone cannot yield stems/ha without these diameters.
        occlusion (float): Portion ``[0, 1)`` of the sweep that could not be
            observed because the point lies on/near the stand boundary (e.g.
            ``0.5`` for a 180° half-sweep at the border). The per-hectare
            estimates are scaled up by ``1 / (1 - occlusion)`` to compensate.
    """

    def __init__(
        self,
        ba_factor: float,
        value: Optional[List[float]] = None,
        species: Optional[List[TreeName]] = None,
        point_id: Optional[str] = None,
        slope: float = 0.0,
        diameters_cm: Optional[List[List[float]]] = None,
        occlusion: float = 0.0,
    ):
        """Initialize sampling parameters and optional existing tallies.

        Args:
            ba_factor (float): Basal area factor in m²/ha per count.
            slope (float, optional): Terrain slope (rise/run) at the point; a
                ``sqrt(1 + slope**2)`` correction is applied. Defaults to 0.0.
            point_id (Optional[str], optional): Plot identifier. Defaults to None.
            species (Optional[List[TreeName]], optional): Initial species list.
                Defaults to empty list.
            value (Optional[List[float]], optional): Initial counts list.
                Defaults to empty list.
            diameters_cm (Optional[List[List[float]]], optional): Diameters (cm)
                of the tallied trees per species, aligned with ``species``.
                Defaults to None (stems/ha then unavailable).
            occlusion (float, optional): Unobserved sweep fraction ``[0, 1)`` for
                a boundary point (e.g. 0.5 for a half-sweep). Defaults to 0.0.
        """
        self.ba_factor = ba_factor
        self.value: List[float] = value if value is not None else []
        self.species: List[TreeName] = species if species is not None else []
        self.point_id = point_id
        self.slope = slope
        self.diameters_cm: Optional[List[List[float]]] = diameters_cm
        if not 0 <= occlusion < 1:
            raise ValueError(f"occlusion must be in [0, 1) for point {point_id}")
        self.occlusion = occlusion

        if len(self.species) != len(self.value):
            raise ValueError(f"Length mismatch for point {point_id}")
        if self.diameters_cm is not None and len(self.diameters_cm) != len(self.species):
            raise ValueError(f"diameters_cm length must match species for point {point_id}")
        self._validate_diameter_counts()

    def _validate_diameter_counts(self) -> None:
        """Check that every tallied tree has a diameter, when diameters are used.

        Basal area is derived from the tally count and stems/ha from the recorded
        diameters. If the two disagree they describe different sets of trees, and
        the resulting basal area and stem density are mutually inconsistent --
        a quadratic mean diameter computed from them would not match any tree
        actually measured. A record therefore either carries a diameter for every
        tallied tree or carries none at all.

        This also rules out fractional tallies (e.g. counting a borderline tree
        as 0.5) on a record that records diameters; use a whole tally, or omit
        the diameters and accept that stems/ha is then not estimable.
        """
        if self.diameters_cm is None:
            return
        for index, species in enumerate(self.species):
            recorded = len(self.diameters_cm[index])
            tallied = self.value[index]
            if recorded != tallied:
                raise ValueError(
                    f"Point {self.point_id}: species {species} was tallied "
                    f"{tallied} time(s) but {recorded} diameter(s) were recorded. "
                    "Supply one diameter per tallied tree, or no diameters at all "
                    "(stems/ha is then reported as unavailable)."
                )

    @property
    def correction_factor(self) -> float:
        """Combined per-hectare correction: slope (``sec θ``) over visible sweep.

        ``sqrt(1 + slope**2) / (1 - occlusion)``.

        The first term is the secant of the inclination. On sloping ground the
        gauge's limiting distance is measured in the inclined sight plane, whose
        horizontal projection is shorter by ``cos θ``; fewer trees are counted
        than the horizontal projection warrants, so multiplying by ``sec θ``
        restores the estimate to a hectare of *horizontal (map)* area, the usual
        reference for per-hectare statistics. Leave ``slope`` at ``0.0`` when the
        instrument already compensates for inclination (as a Spiegelrelaskop
        does), otherwise the correction is applied twice.

        The second term divides by the observed fraction of the sweep, scaling a
        boundary (half-)sweep back up to a full circle.
        """
        return math.sqrt(1.0 + self.slope**2) / (1.0 - self.occlusion)

    def add_observation(self, sp: TreeName, count: float, diameters: Optional[List[float]] = None):
        """Add or update tally for a species at this point.

        Args:
            sp (TreeName): Tree species identifier.
            count (float): Count increment for species tallies.
            diameters (Optional[List[float]], optional): Diameters (cm) of the
                tallied trees to record for ``sp``. Defaults to None.
        """
        if sp in self.species:
            idx = self.species.index(sp)
            self.value[idx] += count
            if diameters is not None:
                self._ensure_diameter_slots()
                self.diameters_cm[idx].extend(diameters)
        else:
            self.species.append(sp)
            self.value.append(count)
            if self.diameters_cm is not None or diameters is not None:
                self._ensure_diameter_slots()
                self.diameters_cm[-1].extend(diameters or [])
        self._validate_diameter_counts()

    def _ensure_diameter_slots(self) -> None:
        """Ensure ``diameters_cm`` exists with one (possibly empty) list per species."""
        if self.diameters_cm is None:
            self.diameters_cm = [[] for _ in self.species]
        while len(self.diameters_cm) < len(self.species):
            self.diameters_cm.append([])

    def update_series(self, sp: TreeName, diameter_cm: Optional[float] = None) -> None:
        """Increment count for ``sp`` by one, adding a new entry if needed.

        Args:
            sp (TreeName): Tree species identifier.
            diameter_cm (Optional[float], optional): Diameter (cm) of the tallied
                tree to record. Defaults to None.
        """
        self.add_observation(sp, 1.0, diameters=None if diameter_cm is None else [diameter_cm])


class AngleCountAggregator:
    """Aggregate multiple AngleCount samples into stand metrics.

    Combines per-point basal area factors (BAF) and tallies,
    merging duplicate point records and computing mean and
    standard error for basal area and stems per species.
    """

    def __init__(self, records: List[AngleCount]):
        """Initialize with a list of AngleCount records.

        Args:
            records (List[AngleCount]): Individual plot samples.
        """
        self.records = records

    def merge_by_point_id(self) -> List[AngleCount]:
        """Merge records sharing the same point_id, ensuring consistent BAF.

        Returns:
            List[AngleCount]: Merged samples per unique point.
        Raises:
            ValueError: If BAF differs among records with same point_id.
        """
        merged_records: Dict[Union[str, int], AngleCount] = {}
        for rec in self.records:
            key = rec.point_id if rec.point_id is not None else id(rec)
            if key in merged_records:
                existing_rec = merged_records[key]
                # --- SAFETY CHECK ---
                # Ensure BAFs match before merging counts for the same point.
                if existing_rec.ba_factor != rec.ba_factor:
                    raise ValueError(
                        f"Inconsistent BAF for point_id '{rec.point_id}': "
                        f"found {existing_rec.ba_factor} and {rec.ba_factor}."
                    )
                # Slope and occlusion set the point's per-hectare correction, so
                # merging records that disagree would silently apply one of them
                # to both sets of tallies.
                if existing_rec.slope != rec.slope:
                    raise ValueError(
                        f"Inconsistent slope for point_id '{rec.point_id}': "
                        f"found {existing_rec.slope} and {rec.slope}."
                    )
                if existing_rec.occlusion != rec.occlusion:
                    raise ValueError(
                        f"Inconsistent occlusion for point_id '{rec.point_id}': "
                        f"found {existing_rec.occlusion} and {rec.occlusion}."
                    )
                # Add observations from the new record to the existing one
                for i, (sp, count) in enumerate(zip(rec.species, rec.value, strict=False)):
                    diameters = rec.diameters_cm[i] if rec.diameters_cm is not None else None
                    existing_rec.add_observation(sp, count, diameters=diameters)
            else:
                # Create a fresh copy to avoid modifying original objects
                merged_records[key] = AngleCount(
                    rec.ba_factor,
                    list(rec.value),
                    list(rec.species),
                    rec.point_id,
                    rec.slope,
                    diameters_cm=(
                        [list(d) for d in rec.diameters_cm]
                        if rec.diameters_cm is not None
                        else None
                    ),
                    occlusion=rec.occlusion,
                )

        return list(merged_records.values())

    def aggregate_stand_metrics(
        self,
    ) -> Tuple[Dict[TreeName, StandBasalArea], Dict[TreeName, Stems]]:
        """Compute mean basal area and stems density per species across plots.

        Returns
        -------
        Tuple[Dict[TreeName, StandBasalArea], Dict[TreeName, Stems]]
            Mapping species to basal area and stems metrics.
        """
        merged_records = self.merge_by_point_id()
        if not merged_records:
            return {}, {}

        n_total_points = len(merged_records)

        all_species: Set[TreeName] = set()
        for rec in merged_records:
            all_species.update(rec.species)

        # Basal area is the directly-estimable quantity: each tallied tree
        # contributes ``BAF`` m²/ha regardless of size.
        species_ba_estimates: Dict[TreeName, List[float]] = {sp: [] for sp in all_species}

        # Stems/ha requires each tallied tree's basal area g_i, hence its DBH.
        # It is only estimable if every merged record carries diameters.
        stems_available = all(rec.diameters_cm is not None for rec in merged_records)
        species_stems_estimates: Dict[TreeName, List[float]] = {sp: [] for sp in all_species}

        for rec in merged_records:
            current_baf = rec.ba_factor
            # Per-point correction: slope (sec of the inclination) scaled up for
            # any unobserved (boundary) portion of the sweep.
            correction = rec.correction_factor
            counts_in_rec = dict(zip(rec.species, rec.value, strict=False))
            dbh_in_rec = (
                dict(zip(rec.species, rec.diameters_cm, strict=False))
                if rec.diameters_cm is not None
                else {}
            )

            for sp in all_species:
                # Basal area for this plot: count * BAF, slope/occlusion corrected.
                species_ba_estimates[sp].append(
                    counts_in_rec.get(sp, 0.0) * current_baf * correction
                )

                if stems_available:
                    # Stems/ha for this plot: sum over tallied trees of BAF / g_i.
                    stems_ha = 0.0
                    for d in dbh_in_rec.get(sp, []):
                        g_m2 = math.pi * ((d / 100.0) / 2.0) ** 2
                        if g_m2 > 0:
                            stems_ha += current_baf / g_m2
                    species_stems_estimates[sp].append(stems_ha * correction)

        basal_area_by_species: Dict[TreeName, StandBasalArea] = {}
        stems_by_species: Dict[TreeName, Stems] = {}

        for sp in all_species:
            ba_estimates = species_ba_estimates[sp]
            ba_mean = statistics.mean(ba_estimates)
            ba_var = statistics.variance(ba_estimates) if n_total_points > 1 else 0.0
            ba_sem = math.sqrt(ba_var / n_total_points) if n_total_points > 0 else 0.0

            basal_area_by_species[sp] = StandBasalArea(
                value=ba_mean, species=sp, precision=ba_sem, over_bark=True, direct_estimate=True
            )

            if stems_available:
                stems_estimates = species_stems_estimates[sp]
                stems_mean = statistics.mean(stems_estimates)
                stems_var = statistics.variance(stems_estimates) if n_total_points > 1 else 0.0
                stems_sem = math.sqrt(stems_var / n_total_points) if n_total_points > 0 else 0.0
                stems_by_species[sp] = Stems(value=stems_mean, species=sp, precision=stems_sem)

        # Empty stems mapping signals "stems/ha not estimable from these tallies".
        return basal_area_by_species, stems_by_species
