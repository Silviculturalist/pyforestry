from functools import lru_cache  # to cache results

import numpy as np
from scipy.optimize import minimize_scalar

from pyforestry.base.taper import Taper
from pyforestry.sweden.timber.swe_timber import SweTimber
from pyforestry.sweden.volume.naslund_1947 import NaslundFormFactor


class EdgrenNylinder1949Consts:
    # --- Define constants at the class level so they are only created ONCE ---
    _CONST_SPRUCE_NORTH = np.array(
        [
            [0.5, np.nan, 1.671, 16.104, np.nan, 103.06],
            [0.55, 0.62, 1.422, 14.883, 286.36, 140.91],
            [0.6, 1.594, 1.976, 13.784, 151.04, 127.89],
            [0.65, 3.240, 2.906, 12.906, 102.7, 110.68],
            [0.7, 6.320, 3.759, 12.099, 76.543, 105.15],
            [0.75, 13.056, 4.026, 11.321, 59.096, 112.59],
            [0.8, 32.012, 3.595, 10.540, 45.754, 134.76],
        ],
        dtype=float,
    )

    _CONST_SPRUCE_SOUTH = np.array(
        [
            [0.5, np.nan, 0.892, 15.765, np.nan, 176.40],
            [0.55, 0.620, 0.923, 14.818, 287.44, 202.65],
            [0.6, 1.594, 1.093, 14.032, 148.97, 202.51],
            [0.65, 3.240, 2.164, 13.479, 99.532, 132.69],
            [0.7, 6.320, 3.324, 13.040, 72.736, 108.43],
            [0.75, 13.059, 4.463, 12.775, 54.618, 97.49],
            [0.8, 33.208, 5.586, 12.578, 40.509, 91.77],
        ],
        dtype=float,
    )

    _CONST_PINE_NORTH = np.array(
        [
            [0.5, np.nan, 1.513, 14.233, np.nan, 123.91],
            [0.55, 0.620, 1.228, 13.321, 311.68, 172.85],
            [0.6, 1.594, 1.506, 12.657, 160.29, 167.68],
            [0.65, 3.240, 2.493, 12.177, 106.67, 128.16],
            [0.7, 6.320, 4.488, 11.880, 77.416, 94.947],
            [0.75, 13.056, 6.602, 11.759, 57.767, 81.725],
            [0.8, 32.307, 7.594, 11.753, 42.808, 80.776],
        ],
        dtype=float,
    )

    _CONST_PINE_SOUTH = np.array(
        [
            [0.5, np.nan, 0.8409, 15.970, np.nan, 183.44],
            [0.55, 0.620, 0.3694, 14.948, 285.28, 458.59],
            [0.6, 1.594, 0.4251, 14.214, 147.44, 463.07],
            [0.65, 3.240, 1.529, 13.646, 98.601, 171.70],
            [0.7, 6.320, 3.974, 13.240, 71.915, 95.286],
            [0.75, 13.070, 5.510, 12.951, 54.050, 84.904],
            [0.8, 33.502, 6.445, 12.755, 39.982, 83.659],
        ],
        dtype=float,
    )
    # ----------------------------------------------------------------------

    @staticmethod
    @lru_cache(maxsize=None)  # <-- ADD THIS DECORATOR TO CACHE RESULTS
    def get_constants(species: str, north: bool, form_factor: float):
        # Species and region logic now refers to the pre-defined constants
        if north and species == "picea abies":
            constants = EdgrenNylinder1949Consts._CONST_SPRUCE_NORTH
        elif not north and species == "picea abies":
            constants = EdgrenNylinder1949Consts._CONST_SPRUCE_SOUTH
        elif north:  # and species == 'pinus sylvestris': #Other species
            constants = EdgrenNylinder1949Consts._CONST_PINE_NORTH
        elif not north:  # and species == 'pinus sylvestris': #Other species
            constants = EdgrenNylinder1949Consts._CONST_PINE_SOUTH
        else:
            # Should never occur.
            raise ValueError(f"Unsupported species or region: {species}, North={north}")

        # Step 1: Round form factor to the nearest 0.5
        rounded_form_factor = round(form_factor * 2) / 2

        # Step 2: Enforce limits between 0.5 and 0.8
        if rounded_form_factor < 0.5:
            rounded_form_factor = 0.5
        elif rounded_form_factor > 0.8:
            rounded_form_factor = 0.8

        # Step 3: Select the corresponding row
        row = constants[np.isclose(constants[:, 0], rounded_form_factor)]

        if row.size == 0:
            raise ValueError(f"No matching row for form factor: {rounded_form_factor}")

        return row

    @staticmethod
    def get_inflexion_point(species: str, north: bool, form_quotient: float) -> float:
        if north:
            if species == "picea abies":
                return 0.08631 / (1 - form_quotient) ** 0.5
            else:  # species == "pinus sylvestris":
                return 0.05270 / (1 - form_quotient) ** 0.9
        else:
            if species == "picea abies":
                return 0.06731 / (1 - form_quotient) ** 0.8
            else:  # species == "pinus sylvestris":
                return 0.06873 / (1 - form_quotient) ** 0.8


class Pettersson1949_consts:
    @staticmethod
    def form_quotient(
        species: str, north: bool, height: float, dbh_ub: float, form_factor_ub: float
    ) -> float:
        if north:
            if species == "picea abies":
                return 0.239 + 0.01046 * height - 0.004407 * dbh_ub + 0.6532 * form_factor_ub
            else:  # species == "pinus sylvestris":
                return 0.293 + 0.00669 * height - 0.001384 * dbh_ub + 0.6348 * form_factor_ub
        else:
            if species == "picea abies":
                return 0.209 + 0.00859 * height - 0.003157 * dbh_ub + 0.7385 * form_factor_ub
            else:
                return 0.372 + 0.008742 * height - 0.003263 * dbh_ub + 0.4929 * form_factor_ub


class EdgrenNylinder1949(Taper):
    def __init__(self, timber: SweTimber):
        """
        Constructor is now stateful. It pre-calculates all taper parameters
        for the given timber object once.
        """
        super().__init__(timber, self)
        self.timber = timber
        self.validate(self.timber)

        # --- All expensive calculations are now done ONCE on initialization ---
        is_north = self.timber.region == "northern"

        form_factor = NaslundFormFactor.calculate(
            species=self.timber.species,
            height_m=self.timber.height_m,
            diameter_cm=self.timber.diameter_cm,
            double_bark_mm=self.timber.double_bark_mm,
            crown_base_height_m=self.timber.crown_base_height_m,
            over_bark=self.timber.over_bark,
            region=self.timber.region,
        )

        form_quotient = Pettersson1949_consts.form_quotient(
            species=self.timber.species,
            north=is_north,
            height=self.timber.height_m,
            dbh_ub=self.timber.diameter_cm,
            form_factor_ub=form_factor,
        )

        self.inflexion_point = EdgrenNylinder1949Consts.get_inflexion_point(
            species=self.timber.species, north=is_north, form_quotient=form_quotient
        )

        self.constants = EdgrenNylinder1949Consts.get_constants(
            species=self.timber.species, north=is_north, form_factor=form_quotient
        )

        # Pre-calculate base diameter
        dbh_relative = self.get_relative_diameter(rel_height=1.3 / self.timber.height_m)
        if dbh_relative is None or dbh_relative <= 0:
            raise ValueError(f"Invalid relative diameter at breast height: {dbh_relative}")

        self.base_diameter = 100 * (self.timber.diameter_cm / dbh_relative)
        if self.base_diameter <= 0:
            raise ValueError(f"Invalid base diameter: {self.base_diameter}")

    @staticmethod
    def validate(timber: SweTimber):
        """
        Validate that the Timber object is compatible with the taper implementation.
        """
        # Check instance type
        if not isinstance(timber, SweTimber):
            raise ValueError("Provided object is not an instance of Timber.")

        # Check height (total tree height must be > 0)
        if timber.height_m is None or timber.height_m <= 0:
            raise ValueError("Timber height_m must be a positive number.")

        # Check diameter at breast height (or base diameter) must be > 0
        if timber.diameter_cm is None or timber.diameter_cm <= 0:
            raise ValueError("Timber diameter_cm must be a positive number.")

        # Stump height should be non-negative (it could be zero)
        if timber.stump_height_m is None or timber.stump_height_m < 0:
            raise ValueError("Timber stump_height_m cannot be negative.")

        # Crown base height should be non-negative and less than total height
        if timber.crown_base_height_m is not None and timber.crown_base_height_m < 0:
            raise ValueError("Timber crown_base_height_m cannot be negative.")

        if timber.crown_base_height_m is not None and timber.height_m is not None:
            if timber.crown_base_height_m >= timber.height_m:
                raise ValueError("Timber crown_base_height_m must be less than timber.height_m.")

        # Double bark thickness should be non-negative
        if timber.double_bark_mm is not None and timber.double_bark_mm < 0:
            raise ValueError("Timber double_bark_mm cannot be negative.")

        # Check that over_bark is a boolean
        if not isinstance(timber.over_bark, bool):
            raise ValueError("Timber over_bark must be a boolean value.")

        # Ensure region is one of the accepted values
        if timber.region not in ("northern", "southern"):
            raise ValueError("Timber region must be either 'northern' or 'southern'.")

        # Ensure species is a non-empty string
        if not timber.species or not isinstance(timber.species, str):
            raise ValueError("Timber species must be provided as a non-empty string.")

    def get_relative_diameter(self, rel_height: float) -> float:
        """
        Instance method using pre-calculated parameters from self.
        """
        # Constants are now read directly from the instance
        const_F, const_beta, const_Gamma, const_q, const_Q, const_R = self.constants[0]
        inflexion_point = self.inflexion_point

        # Compute relative diameter based on height regions
        if rel_height <= inflexion_point:
            return 100 - const_q * np.log10(1 + 10000 * rel_height)
        elif inflexion_point < rel_height <= 0.6:
            if np.isnan(const_Q):
                Diameter_inflexion_point = 100 - const_q * np.log10(1 + 10000 * inflexion_point)
                Diameter_60p_height = const_R * np.log10(1 + (1 - 0.6) * const_Gamma)
                slope = (Diameter_60p_height - Diameter_inflexion_point) / (0.6 - inflexion_point)
                return Diameter_inflexion_point + slope * (rel_height - inflexion_point)
            else:
                return const_Q * np.log10(1 + (1 - rel_height) * const_beta)
        elif 0.6 < rel_height < 1:
            return const_R * np.log10(1 + (1 - rel_height) * const_Gamma)
        else:
            print(f"Warning: Unexpected value for relative height: {rel_height}")
            return 0

    def get_diameter_at_height(self, height_m: float) -> float:
        """
        Instance method using pre-calculated base diameter.
        """
        if height_m < 0 or height_m >= self.timber.height_m:
            return 0.0

        rel_height = height_m / self.timber.height_m
        relative_diameter = self.get_relative_diameter(rel_height)

        if relative_diameter is None or relative_diameter <= 0:
            return 0.0

        return (self.base_diameter * relative_diameter) / 100

    def get_height_at_diameter(self, diameter: float) -> float:
        """Instance method."""
        if diameter <= 0 or diameter > self.base_diameter:
            print(f"Invalid minDiameter: {diameter}. Must be between 0 and {self.base_diameter}.")
            return 0.0

        def objective(height):
            # The objective function now calls the fast instance method
            diameter_at_height = self.get_diameter_at_height(height)
            if diameter_at_height is None:
                return abs(0 - diameter)
            return abs(diameter_at_height - diameter)

        result = minimize_scalar(objective, bounds=(0, self.timber.height_m), method="bounded")
        if result.success:
            return result.x
        else:
            print(f"Optimization failed for minDiameter: {diameter}")
            return 0.0
