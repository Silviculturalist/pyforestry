"""Above-ground biomass functions after Petersson (1999)."""

from __future__ import annotations

import warnings
from inspect import getmodule

import numpy as np

from pyforestry.base.helpers import (
    Age,
    AgeMeasurement,
    Diameter_cm,
    SiteIndexValue,
    TreeName,
    TreeSpecies,
    parse_tree_species,
)


class Petersson1999:
    """Above-ground biomass models for common Swedish tree species.

    The formulas implemented here originate from:

    Petersson, H. (1999). *Biomassafunktioner för trädfaktorer av tall,
    gran och björk i Sverige*. Report 59, Dept. of Forest Resources and
    Geomatics, Swedish University of Agricultural Sciences.
    """

    @staticmethod
    def _validate_site_index(si: SiteIndexValue) -> TreeName:
        """Validate a :class:`SiteIndexValue`.

        Args:
            si: Site index to validate.

        Returns:
            TreeName: Dominant species referenced by ``si``.

        Raises:
            TypeError: If ``si`` is not a :class:`SiteIndexValue`.
            ValueError: If ``si`` does not reference pine or spruce at age
                ``Age.TOTAL(100)`` or its function is not from
                ``Hagglund_1970``.
        """

        if not isinstance(si, SiteIndexValue):
            raise TypeError("SI must be a SiteIndexValue")
        if si.reference_age != Age.TOTAL(100):
            raise ValueError("SI must have reference age Age.TOTAL(100)")
        if si.species == {TreeSpecies.Sweden.picea_abies}:
            dominant = TreeSpecies.Sweden.picea_abies
        elif si.species == {TreeSpecies.Sweden.pinus_sylvestris}:
            dominant = TreeSpecies.Sweden.pinus_sylvestris
        else:
            raise ValueError("SI must reference Picea abies or Pinus sylvestris")
        mod = getmodule(si.fn)
        if mod is None or not mod.__name__.endswith("hagglund_1970"):
            raise ValueError("SI.fn must come from Hagglund_1970")
        return dominant

    @staticmethod
    def _get_dominant_species(
        si: SiteIndexValue | float,
        dominant_species: TreeName | str | None,
    ) -> tuple[TreeName, float]:
        """Resolve dominant species from ``SI`` and return its value.

        Args:
            si: Site index as an object or numeric value.
            dominant_species: Species used when ``si`` is numeric.

        Returns:
            tuple[TreeName, float]: Dominant species and numeric site index.

        Raises:
            TypeError: If ``si`` is numeric and ``dominant_species`` is ``None``.
            ValueError: If ``dominant_species`` is not pine or spruce.
        """

        if isinstance(si, SiteIndexValue):
            dom = Petersson1999._validate_site_index(si)
            if dominant_species is not None:
                warnings.warn(
                    "dominant_species ignored when SI is SiteIndexValue",
                    stacklevel=2,
                )
            return dom, float(si)

        si_value = float(si)
        if dominant_species is None:
            raise TypeError("dominant_species required when SI is numeric")
        if isinstance(dominant_species, str):
            dominant_species = parse_tree_species(dominant_species)
        if dominant_species not in {
            TreeSpecies.Sweden.picea_abies,
            TreeSpecies.Sweden.pinus_sylvestris,
        }:
            raise ValueError("dominant_species must be Picea abies or Pinus sylvestris")
        return dominant_species, si_value

    @staticmethod
    def spruce(
        diameter_cm: float | Diameter_cm,
        height_m: float,
        age_at_breast_height: float | AgeMeasurement,
        SI: SiteIndexValue | float,
        five_years_radial_increment_mm: float,
        peat: bool,
        latitude: float,
        longitude: float,
        altitude: float,
        dominant_species: TreeName | str | None = None,
    ) -> dict:
        """Biomass components for a Norway spruce.

        Args:
            diameter_cm: Diameter at breast height in centimetres.
                If ``Diameter_cm`` is given, it must represent 1.3 m
                measurement height and be taken over bark.
            height_m: Tree height in metres.
            age_at_breast_height: Age at breast height in years.
            SI: Site index for the stand. When numeric, ``dominant_species``
                must specify pine or spruce.
            five_years_radial_increment_mm: Radial increment over five years
                in millimetres.
            peat: ``True`` if soil is peat (>30 cm deep).
            latitude: Latitude in decimal degrees.
            longitude: Longitude in decimal degrees.
            altitude: Altitude in metres above sea level.
            dominant_species: Species used for ``SI`` when ``SI`` is numeric.

        Returns:
            dict: Dry weight components in grams keyed by component name.
        """
        dominant_species, SI = Petersson1999._get_dominant_species(SI, dominant_species)
        picea = dominant_species is TreeSpecies.Sweden.picea_abies
        pinus = dominant_species is TreeSpecies.Sweden.pinus_sylvestris

        if isinstance(diameter_cm, Diameter_cm):
            if diameter_cm.measurement_height_m != 1.3:
                warnings.warn("diameter_cm measurement height not 1.3 m", stacklevel=2)
            if not diameter_cm.over_bark:
                raise ValueError("diameter_cm must be measured over bark")
            diameter_cm = float(diameter_cm)
        diameter_mm = diameter_cm * 10

        if isinstance(age_at_breast_height, AgeMeasurement):
            if age_at_breast_height.code != Age.DBH.value:
                raise TypeError("age_at_breast_height must use Age.DBH measurement")
            age_val = float(age_at_breast_height)
        else:
            age_val = float(age_at_breast_height)

        increment_01mm = five_years_radial_increment_mm * 10
        age_log = np.log(age_val)
        inc_log = np.log(increment_01mm)
        res = {}
        res["stem_above_bark"] = np.exp(
            -6.839310
            + 3.578450 * np.log(diameter_mm + 25)
            - 0.003042 * diameter_mm
            + 0.093033 * inc_log
            - 0.002763 * increment_01mm
            + 0.111347 * age_log
            + 0.012148 * float(SI) * picea
            + 0.011586 * float(SI) * pinus
            - 0.000020194 * latitude
            + (0.17069**2) / 2
        )
        res["bark"] = np.exp(
            -4.084706
            + 2.397166 * np.log(diameter_mm + 10)
            - 0.066053 * inc_log
            + 0.151696 * age_log
            + (0.22759**2) / 2
        )
        res["needles"] = np.exp(
            -1.130238
            + 1.485407 * np.log(diameter_mm)
            + 0.514648 * inc_log
            + 0.206901 * age_log
            + (0.30852**2) / 2
        )
        res["living_branches"] = np.exp(
            -0.718621
            + 1.740810 * np.log(diameter_mm)
            + 0.348379 * inc_log
            + 0.180503 * age_log
            + (0.28825**2) / 2
        )
        res["dead_branches"] = np.exp(
            -1.763738
            + 2.616200 * np.log(diameter_mm)
            - 0.745459 * inc_log
            - 0.359509 * age_log
            + (0.79373**2) / 2
        )
        res["stump_root_gt5"] = np.exp(
            -1.980469 + 2.339527 * np.log(diameter_mm) + 0.342786 * peat + (0.28283**2) / 2
        )
        res["above_stump"] = np.exp(
            -0.437361
            + 2.446692 * np.log(diameter_mm + 9)
            + 0.065779 * inc_log
            + 0.102290 * age_log
            - 0.000021633 * latitude
            + (0.15492**2) / 2
        )
        res["total"] = np.exp(
            -0.614093
            + 2.425997 * np.log(diameter_mm + 8)
            + 0.081636 * inc_log
            + 0.128027 * age_log
            - 0.000015810 * latitude
            + (0.15985**2) / 2
        )
        res["excluding_small_roots"] = np.exp(
            -0.766217
            + 2.491024 * np.log(diameter_mm + 8)
            + 0.070526 * inc_log
            + 0.113514 * age_log
            - 0.000017876 * latitude
            + (0.16274**2) / 2
        )
        return res

    @staticmethod
    def pine(
        diameter_cm: float | Diameter_cm,
        height_m: float,
        age_at_breast_height: float | AgeMeasurement,
        SI: SiteIndexValue | float,
        five_years_radial_increment_mm: float,
        peat: bool,
        latitude: float,
        longitude: float,
        altitude: float,
        dominant_species: TreeName | str | None = None,
    ) -> dict:
        """Biomass components for a Scots pine.

        Args:
            diameter_cm: Diameter at breast height in centimetres.
                ``Diameter_cm`` must describe a 1.3 m, over-bark
                measurement when used.
            height_m: Tree height in metres.
            age_at_breast_height: Age at breast height in years.
            SI: Site index of the stand. When numeric, ``dominant_species``
                must define pine or spruce.
            five_years_radial_increment_mm: Radial increment over five years
                in millimetres.
            peat: ``True`` if soil is peat (>30 cm deep).
            latitude: Latitude in decimal degrees.
            longitude: Longitude in decimal degrees.
            altitude: Altitude in metres above sea level.
            dominant_species: Species used for ``SI`` when ``SI`` is numeric.

        Returns:
            dict: Dry weight components in grams keyed by component name.
        """
        dominant_species, SI = Petersson1999._get_dominant_species(SI, dominant_species)
        picea = dominant_species is TreeSpecies.Sweden.picea_abies
        pinus = dominant_species is TreeSpecies.Sweden.pinus_sylvestris

        if isinstance(diameter_cm, Diameter_cm):
            if diameter_cm.measurement_height_m != 1.3:
                warnings.warn("diameter_cm measurement height not 1.3 m", stacklevel=2)
            if not diameter_cm.over_bark:
                raise ValueError("diameter_cm must be measured over bark")
            diameter_cm = float(diameter_cm)
        diameter_mm = diameter_cm * 10

        if isinstance(age_at_breast_height, AgeMeasurement):
            if age_at_breast_height.code != Age.DBH.value:
                raise TypeError("age_at_breast_height must use Age.DBH measurement")
            age_val = float(age_at_breast_height)
        else:
            age_val = float(age_at_breast_height)

        increment_01mm = five_years_radial_increment_mm * 10
        age_log = np.log(age_val)
        inc_log = np.log(increment_01mm)
        res = {}
        res["stem_above_bark"] = np.exp(
            -7.674621
            + 3.155671 * np.log(diameter_mm + 25)
            - 0.002197 * diameter_mm
            + 0.084427 * inc_log
            - 0.002665 * increment_01mm
            + 0.253227 * age_log
            + 0.028478 * float(SI) * picea
            + 0.031435 * float(SI) * pinus
            + 0.000008342 * latitude
            + (0.17803**2) / 2
        )
        res["bark"] = np.exp(
            -1.340149
            + 2.209719 * np.log(diameter_mm + 13)
            - 0.001986 * inc_log
            - 0.000024146 * latitude
            + (0.26942**2) / 2
        )
        res["needles"] = np.exp(
            -2.597267
            + 1.506121 * np.log(diameter_mm)
            + 0.571366 * inc_log
            + 0.208130 * age_log
            + 0.000870 * altitude
            + (0.35753**2) / 2
        )
        res["living_branches"] = np.exp(
            -2.533220
            + 1.989129 * np.log(diameter_mm)
            + 0.387203 * inc_log
            + 0.105215 * age_log
            + (0.34938**2) / 2
        )
        res["dead_branches"] = np.exp(
            1.596001
            + 2.441173 * np.log(diameter_mm)
            - 0.437497 * inc_log
            - 0.711616 * age_log
            - 0.001358 * altitude
            - 0.000129 * longitude
            + (0.76730**2) / 2
        )
        res["above_stump"] = np.exp(
            -2.032666
            + 2.413856 * np.log(diameter_mm + 6)
            + 0.130304 * age_log
            + 0.011834 * float(SI) * picea
            + 0.013668 * float(SI) * pinus
            + (0.15651**2) / 2
        )
        res["total"] = np.exp(
            -1.507568
            + 2.449121 * np.log(diameter_mm + 5)
            + 0.104243 * age_log
            - 0.000321 * altitude
            + (0.16332**2) / 2
        )
        res["excluding_small_roots"] = np.exp(
            -1.756201
            + 2.483808 * np.log(diameter_mm + 5)
            + 0.107190 * age_log
            - 0.000325 * altitude
            + (0.16086**2) / 2
        )
        res["stump_root_gt5"] = np.exp(
            -1.980469
            + 2.339527 * np.log(diameter_mm)
            + 0.342786 * peat
            - 0.224812
            + (0.28283**2) / 2
        )
        return res

    @staticmethod
    def birch(
        diameter_cm: float | Diameter_cm,
        height_m: float,
        age_at_breast_height: float | AgeMeasurement,
        SI: SiteIndexValue | float,
        five_years_radial_increment_mm: float,
        peat: bool,
        latitude: float,
        longitude: float,
        altitude: float,
        dominant_species: TreeName | str | None = None,
    ) -> dict:
        """Biomass components for birch (``Betula`` spp.).

        Args:
            diameter_cm: Diameter at breast height in centimetres. If a
                ``Diameter_cm`` instance is supplied it must refer to a 1.3 m
                over-bark measurement.
            height_m: Tree height in metres.
            age_at_breast_height: Age at breast height in years.
            SI: Site index for the stand. Numeric values require
                ``dominant_species``.
            five_years_radial_increment_mm: Radial increment over five years in
                millimetres.
            peat: ``True`` if soil is peat (>30 cm deep).
            latitude: Latitude in decimal degrees.
            longitude: Longitude in decimal degrees.
            altitude: Altitude in metres above sea level.
            dominant_species: Species used for ``SI`` when ``SI`` is numeric.

        Returns:
            dict: Dry weight components in grams keyed by component name.
        """
        dominant_species, SI = Petersson1999._get_dominant_species(SI, dominant_species)
        picea = dominant_species is TreeSpecies.Sweden.picea_abies
        pinus = dominant_species is TreeSpecies.Sweden.pinus_sylvestris

        if isinstance(diameter_cm, Diameter_cm):
            if diameter_cm.measurement_height_m != 1.3:
                warnings.warn("diameter_cm measurement height not 1.3 m", stacklevel=2)
            if not diameter_cm.over_bark:
                raise ValueError("diameter_cm must be measured over bark")
            diameter_cm = float(diameter_cm)
        diameter_mm = diameter_cm * 10

        if isinstance(age_at_breast_height, AgeMeasurement):
            if age_at_breast_height.code != Age.DBH.value:
                raise TypeError("age_at_breast_height must use Age.DBH measurement")
            age_val = float(age_at_breast_height)
        else:
            age_val = float(age_at_breast_height)

        increment_01mm = five_years_radial_increment_mm * 10
        age_log = np.log(age_val)
        inc_log = np.log(increment_01mm)
        res = {}
        res["stem_above_bark"] = np.exp(
            -3.091932
            + 2.479648 * np.log(diameter_mm + 7)
            + 0.243747 * age_log
            + 0.022185 * float(SI) * picea
            + 0.022955 * float(SI) * pinus
            + (0.19827**2) / 2
        )
        res["bark"] = np.exp(
            -3.244490
            + 2.525420 * np.log(diameter_mm + 18)
            + 0.329744 * age_log
            - 0.000030180 * latitude
            + (0.25483**2) / 2
        )
        res["living_branches"] = np.exp(
            -2.782537 + 2.276815 * np.log(diameter_mm) + 0.228528 * inc_log + (0.45153**2) / 2
        )
        res["dead_branches"] = np.exp(
            -2.059091 + 1.657683 * np.log(diameter_mm) + (1.12848**2) / 2
        )
        res["above_stump"] = np.exp(
            -0.423749
            + 2.574575 * np.log(diameter_mm + 8)
            + 0.090419 * age_log
            - 0.000026862 * latitude
            + (0.17071**2) / 2
        )
        return res

    @staticmethod
    def biomass(
        species: TreeName | str,
        diameter_cm: float | Diameter_cm,
        height_m: float,
        age_at_breast_height: float | AgeMeasurement,
        SI: SiteIndexValue | float,
        five_years_radial_increment_mm: float,
        peat: bool,
        latitude: float,
        longitude: float,
        altitude: float,
        dominant_species: TreeName | str | None = None,
    ) -> dict:
        """Calculate biomass for a given species.

        Args:
            species: Tree species name or enum value.
            diameter_cm: Diameter at breast height in centimetres.
            height_m: Tree height in metres.
            age_at_breast_height: Age at breast height in years.
            SI: Site index for the stand. Numeric values require
                ``dominant_species``.
            five_years_radial_increment_mm: Radial increment over five years in
                millimetres.
            peat: ``True`` if soil is peat (>30 cm deep).
            latitude: Latitude in decimal degrees.
            longitude: Longitude in decimal degrees.
            altitude: Altitude in metres above sea level.
            dominant_species: Species used when ``SI`` is numeric.

        Returns:
            dict: Dry weight components in grams keyed by component name.

        Raises:
            TypeError: If ``species`` is not a valid tree species.
            ValueError: If the species is not supported.
        """
        if isinstance(species, str):
            species = parse_tree_species(species)
        if not isinstance(species, TreeName):
            raise TypeError("species must be a TreeName or string")

        if species is TreeSpecies.Sweden.picea_abies:
            return Petersson1999.spruce(
                diameter_cm,
                height_m,
                age_at_breast_height,
                SI,
                five_years_radial_increment_mm,
                peat,
                latitude,
                longitude,
                altitude,
                dominant_species,
            )
        if species is TreeSpecies.Sweden.pinus_sylvestris:
            return Petersson1999.pine(
                diameter_cm,
                height_m,
                age_at_breast_height,
                SI,
                five_years_radial_increment_mm,
                peat,
                latitude,
                longitude,
                altitude,
                dominant_species,
            )
        if species in {
            TreeSpecies.Sweden.betula_pendula,
            TreeSpecies.Sweden.betula_pubescens,
        }:
            return Petersson1999.birch(
                diameter_cm,
                height_m,
                age_at_breast_height,
                SI,
                five_years_radial_increment_mm,
                peat,
                latitude,
                longitude,
                altitude,
                dominant_species,
            )
        raise ValueError("Tree species not supported.")
