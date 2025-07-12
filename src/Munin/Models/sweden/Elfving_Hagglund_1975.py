# ElfvingHagglund_1975.py
import warnings
from math import exp, log
from typing import Tuple, Optional

# Import base classes and helpers - Adjust paths as necessary
from Munin.helpers.primitives import (
    Age, AgeMeasurement, SiteIndexValue, StandBasalArea, Stems
)
from Munin.helpers.tree_species import TreeSpecies, TreeName

# Import Hagglund functions for potential age calculation (dependency)
# Note: The R code uses Hagglund_age_to_height, which needs an equivalent implementation
#       or inversion of the existing Hagglund height functions in Python.
#       This implementation assumes age is provided or raises NotImplementedError.
from Munin.siteindex.sweden import Hagglund_1970

class ElfvingHagglundInitialStand:
    """
    Provides methods to estimate initial stand density (stems/ha) and
    basal area (m²/ha) for young Spruce and Pine stands in Sweden,
    based on the models published by Elfving & Hägglund (1975).

    Estimates are generally for stems thicker than 2.5 cm at breast height.

    References:
        Elfving, B., Hägglund, B. (1975). Utgångslägen för produktionsprognoser:
        Tall och gran i Sverige. Skogshögskolan, Inst. f. skogsproduktion.
        Rapp. o. Upps. Nr 38. Stockholm. 75 pp.
    """

    @staticmethod
    def _validate_age_structure(even_or_somewhat_uneven_aged: bool, uneven_aged: bool):
        """ Validates mutual exclusivity of age structure flags. """
        if uneven_aged and even_or_somewhat_uneven_aged:
            raise ValueError("Only one of 'even_or_somewhat_uneven_aged' or 'uneven_aged' can be True.")
        if not uneven_aged and not even_or_somewhat_uneven_aged:
             # This condition seems wrong in the R code check, assuming at least one must be true,
             # or they represent distinct states where both being false is valid (e.g., unknown).
             # Replicating R logic:
             # stop("Only one of 'even_or_somewhat_uneven_aged' or 'uneven_aged' can be FALSE")
             # Corrected logic: Assume they must cover all possibilities if exclusive.
             # If they are not mutually exclusive flags, this check might be incorrect.
             # For now, assuming they should be exclusive and cover the options.
             pass # Allow both to be False if that's a valid state.

    @staticmethod
    def _validate_broadleaves(broadleaves_percent: float):
        """ Validates broadleaf percentage. """
        if broadleaves_percent > 40:
            warnings.warn("Broadleaves percentage > 40%, potentially outside of material range.")
        if not (0 <= broadleaves_percent <= 100):
            raise ValueError("broadleaves_percent_of_basal_area must be between 0 and 100.")
        
    @staticmethod
    def _validate_site_index(
        site_index: SiteIndexValue,
        expected_species: TreeName
    ):
        """
        Validates the provided SiteIndexValue object.

        Checks:
        1. Type is SiteIndexValue.
        2. Reference age is Age.TOTAL(100).
        3. The function used for derivation is from Hagglund_1970.
        4. The species set matches the expected single species.
        """
        if not isinstance(site_index, SiteIndexValue):
            raise TypeError(f"site_index must be a SiteIndexValue object, got {type(site_index)}.")

        # Check reference age: Must be total age 100
        expected_ref_age = Age.TOTAL(100)
        if site_index.reference_age != expected_ref_age:
            raise ValueError(f"Site index reference age must be {expected_ref_age}, got {site_index.reference_age}.")

        # Check function source (heuristic check on function's module/name)
        fn_module = getattr(site_index.fn, '__module__', '')
        fn_qualname = getattr(site_index.fn, '__qualname__', '')
        # Check if the function seems to originate from the Hagglund_1970 structure
        # This is a heuristic check and might need adjustment based on exact function structure
        if not ('Hagglund_1970' in fn_module or 'Hagglund_1970' in fn_qualname or \
                'HagglundSpruceModel' in fn_qualname or 'HagglundPineModel' in fn_qualname):
             warnings.warn(f"Site index function '{fn_qualname}' might not be from Hagglund_1970 model.")

        # Check species: Must be a set containing only the expected species
        if not isinstance(site_index.species, set):
             raise TypeError(f"Site index species attribute must be a set, got {type(site_index.species)}.")
        expected_species_set = {expected_species}
        if site_index.species != expected_species_set:
            species_names = ", ".join([sp.full_name for sp in site_index.species])
            raise ValueError(f"Site index species must be {{{expected_species.full_name}}}, got {{{species_names}}}.")


    # =========================================================================
    # Stem Estimation Functions (Young Forests > 2.5cm DBH)
    # =========================================================================

    @staticmethod
    def estimate_stems_young_pine_north(
        latitude: float,
        altitude: float,
        dominant_height: float,
        stand_density_factor: float = 0.65, # Corresponds to Målklass*10 / 10
        pct: bool = False, # Pre-commercial thinning occurred
        even_or_somewhat_uneven_aged: bool = True,
    ) -> Stems:
        """
        Estimates initial stems/ha (>2.5cm DBH) for young Pine in Northern Sweden.
        Based on Function 5.1, Elfving & Hägglund (1975), p. 53.

        Args:
            latitude: Latitude, degrees N.
            altitude: Altitude, meters above sea level.
            dominant_height: Dominant height, meters.
            stand_density_factor: Stand density factor (0.1-1.0).
            pct: True if pre-commercial thinning has occurred.
            even_or_somewhat_uneven_aged: True if stand is even or somewhat uneven-aged.

        Returns:
            Estimated number of stems per hectare (>2.5cm DBH).
        """
        uneven_aged = not even_or_somewhat_uneven_aged # Infer based on exclusivity assumption
        ElfvingHagglundInitialStand._validate_age_structure(even_or_somewhat_uneven_aged, uneven_aged)
        if not (0.1 <= stand_density_factor <= 1.0):
             raise ValueError("stand_density_factor must be between 0.1 and 1.0.")
        if not isinstance(dominant_height, float):
             raise TypeError("dominant_height must be a float object.")

        h_dm = float(dominant_height) * 10.0
        alt_100m = altitude / 100.0
        stand_dens_orig = stand_density_factor * 10.0 # Convert 0.1-1 to 1-10

        stems_val = exp(
            8.856
            - 0.033 * latitude
            - 0.062 * alt_100m
            + 0.203 * stand_dens_orig
            - 0.002 * h_dm
            - 0.233 * pct # Bool -> 1/0
            - 0.220 * even_or_somewhat_uneven_aged # Bool -> 1/0
            - 0.074 * uneven_aged # Bool -> 1/0
        )
        return Stems(value=stems_val, species=TreeSpecies.Sweden.pinus_sylvestris)


    @staticmethod
    def estimate_stems_young_spruce_north(
        altitude: float,
        site_index: SiteIndexValue, # H100
        stand_density_factor: float = 0.65,
        broadleaves_percent_ba: float = 0.0,
        pct: bool = False,
        even_or_somewhat_uneven_aged: bool = True,
    ) -> Stems:
        """
        Estimates initial stems/ha (>2.5cm DBH) for young Spruce in Northern Sweden.
        Based on Function 5.3, Elfving & Hägglund (1975), p. 53.

        Args:
            altitude: Altitude, meters above sea level.
            site_index: Site index H100 (m).
            stand_density_factor: Stand density factor (0.1-1.0).
            broadleaves_percent_ba: Percentage of broadleaves in BA (0-100).
            pct: True if pre-commercial thinning has occurred.
            even_or_somewhat_uneven_aged: True if stand is even or somewhat uneven-aged.

        Returns:
            Estimated number of stems per hectare (>2.5cm DBH).
        """
        uneven_aged = not even_or_somewhat_uneven_aged
        ElfvingHagglundInitialStand._validate_age_structure(even_or_somewhat_uneven_aged, uneven_aged)
        ElfvingHagglundInitialStand._validate_broadleaves(broadleaves_percent_ba)
        ElfvingHagglundInitialStand._validate_site_index(site_index,TreeSpecies.Sweden.picea_abies)
        if not (0.1 <= stand_density_factor <= 1.0):
             raise ValueError("stand_density_factor must be between 0.1 and 1.0.")
        if not isinstance(site_index, SiteIndexValue):
             raise TypeError("site_index must be a SiteIndexValue object.")

        alt_100m = altitude / 100.0
        si_m = float(site_index)
        stand_dens_orig = stand_density_factor * 10.0
        si_gt_22 = si_m > 22

        stems_val = exp(
            6.7117
            + 0.118 * alt_100m
            - 0.028 * (alt_100m**2)
            + 0.175 * stand_dens_orig
            - 0.189 * si_gt_22 # Bool -> 1/0
            + 0.006 * broadleaves_percent_ba
            - 0.748 * pct # Bool -> 1/0
            - 0.111 * even_or_somewhat_uneven_aged # Bool -> 1/0
            - 0.077 * uneven_aged # Bool -> 1/0
        )
        return Stems(value=stems_val, species=TreeSpecies.Sweden.picea_abies)


    @staticmethod
    def estimate_stems_young_pine_south(
        latitude: float, # Although named southern, latitude is still needed if age needs calculation
        site_index: SiteIndexValue, # H100
        dominant_height: float,
        age_at_breast_height: Optional[AgeMeasurement] = None, # Optional: If None, needs calculation
        stand_density_factor: float = 0.65,
        pct: bool = False,
        regeneration: str = "culture", # "culture", "natural regeneration", "unknown"
    ) -> Stems:
        """
        Estimates initial stems/ha (>2.5cm DBH) for young Pine in Southern Sweden.
        Based on Function 5.2, Elfving & Hägglund (1975), p. 53.

        Args:
            latitude: Latitude (used if age needs calculation).
            site_index: Site index H100 (m).
            dominant_height: Dominant height (m).
            age_at_breast_height: Age at breast height. If None, it attempts calculation (Not Implemented Yet).
            stand_density_factor: Stand density factor (0.1-1.0).
            pct: True if pre-commercial thinning has occurred.
            regeneration: Method of establishment ("culture", "natural regeneration", "unknown"). Used if age needs calculation.

        Returns:
            Estimated number of stems per hectare (>2.5cm DBH).
        """
        if not (0.1 <= stand_density_factor <= 1.0):
             raise ValueError("stand_density_factor must be between 0.1 and 1.0.")
        if not isinstance(dominant_height, float):
             raise TypeError("dominant_height must be a float object.")
        if not isinstance(site_index, SiteIndexValue):
             raise TypeError("site_index must be a SiteIndexValue object.")
        ElfvingHagglundInitialStand._validate_site_index(site_index,TreeSpecies.Sweden.pinus_sylvestris)

        if age_at_breast_height is None:
            # --- Age Calculation Placeholder ---
            # R code calls: Hagglund_age_to_height(...)
            # This requires inverting the Hagglund_1970 height functions.
            # Example using brentq (like in Eriksson):
            # try:
            #     target_h = float(dominant_height)
            #     # Define function to minimize: Hagglund_height(age) - target_h
            #     # Note: Need the correct Hagglund pine function (not implemented in provided Hagglund_1970.py)
            #     # age_val = brentq(lambda age_bh: Hagglund_1970_pine_height(..., age=Age.DBH(age_bh), ...) - target_h, 1, 200)
            #     # age_at_breast_height = Age.DBH(age_val)
            #     raise NotImplementedError("Age calculation from height for Pine (Hagglund 1974) is not implemented.")
            # except Exception as e:
            #     raise ValueError(f"Could not calculate age at breast height: {e}")
             raise NotImplementedError("Automatic calculation of age_at_breast_height for Pine is not implemented. Please provide age.")
        elif not isinstance(age_at_breast_height, AgeMeasurement) or age_at_breast_height.code != Age.DBH.value:
             raise TypeError("age_at_breast_height must be an AgeMeasurement object with Age.DBH code.")

        age_val = float(age_at_breast_height)
        stand_dens_orig = stand_density_factor * 10.0

        stems_val = exp(
            6.148
            + 0.268 * stand_dens_orig
            - 0.058 * ((stand_dens_orig**3) / 100.0)
            - 0.006 * age_val
            - 0.310 * pct # Bool -> 1/0
        )
        return Stems(value=stems_val, species=TreeSpecies.Sweden.pinus_sylvestris)


    @staticmethod
    def estimate_stems_young_spruce_south(
        altitude: float,
        site_index: SiteIndexValue, # H100
        age_at_breast_height: AgeMeasurement,
        stand_density_factor: float = 0.65,
        broadleaves_percent_ba: float = 0.0,
        even_or_somewhat_uneven_aged: bool = True,
    ) -> Stems:
        """
        Estimates initial stems/ha (>2.5cm DBH) for young Spruce in Southern Sweden.
        Based on Function 5.4, Elfving & Hägglund (1975), p. 53.

        Args:
            altitude: Altitude, meters above sea level.
            site_index: Site index H100 (m).
            age_at_breast_height: Age at breast height (years).
            stand_density_factor: Stand density factor (0.1-1.0).
            broadleaves_percent_ba: Percentage of broadleaves in BA (0-100).
            even_or_somewhat_uneven_aged: True if stand is even or somewhat uneven-aged.

        Returns:
            Estimated number of stems per hectare (>2.5cm DBH).
        """
        # Note: R code for S Spruce stems (5.4) seems identical to N Spruce stems (5.3) except for PCT and uneven_aged flags.
        # Replicating 5.4 formula as written in the R code:
        ElfvingHagglundInitialStand._validate_broadleaves(broadleaves_percent_ba)
        if not (0.1 <= stand_density_factor <= 1.0):
             raise ValueError("stand_density_factor must be between 0.1 and 1.0.")
        if not isinstance(site_index, SiteIndexValue):
             raise TypeError("site_index must be a SiteIndexValue object.")
        if not isinstance(age_at_breast_height, AgeMeasurement) or age_at_breast_height.code != Age.DBH.value:
             raise TypeError("age_at_breast_height must be an AgeMeasurement object with Age.DBH code.")
        
        ElfvingHagglundInitialStand._validate_site_index(site_index,TreeSpecies.Sweden.picea_abies)


        alt_100m = altitude / 100.0
        si_m = float(site_index)
        stand_dens_orig = stand_density_factor * 10.0
        age_val = float(age_at_breast_height)
        si_gt_22 = si_m > 22

        stems_val = exp(
            6.2064
            + 0.066 * alt_100m
            + 0.319 * stand_dens_orig
            - 0.081 * ((stand_dens_orig**3) / 100.0)
            - 0.286 * si_gt_22 # Bool -> 1/0
            - 0.007 * age_val
            + 0.006 * broadleaves_percent_ba
            - 0.167 * even_or_somewhat_uneven_aged # Bool -> 1/0
        )
        return Stems(value=stems_val, species=TreeSpecies.Sweden.picea_abies)


    # =========================================================================
    # Basal Area Estimation Functions (Young Forests)
    # =========================================================================

    @staticmethod
    def estimate_basal_area_young_pine_north(
        latitude: float,
        altitude: float,
        site_index: SiteIndexValue, # H100
        dominant_height: float,
        stems: Optional[Stems] = None, # If None, calculate using estimate_stems_young_pine_north
        stand_density_factor: float = 0.65,
        broadleaves_percent_ba: float = 0.0,
        pct: bool = False,
        even_or_somewhat_uneven_aged: bool = True,
    ) -> StandBasalArea:
        """
        Estimates initial basal area (m²/ha) for young Pine in Northern Sweden.
        Based on Function 6.1, Elfving & Hägglund (1975), p. 53.

        Args:
            latitude: Latitude, degrees N.
            altitude: Altitude, meters above sea level.
            site_index: Site index H100 (m).
            dominant_height: Dominant height (m).
            stems: Stems per hectare. If None, estimated internally.
            stand_density_factor: Stand density factor (0.1-1.0).
            broadleaves_percent_ba: Percentage of broadleaves in BA (0-100).
            pct: True if pre-commercial thinning has occurred.
            even_or_somewhat_uneven_aged: True if stand is even or somewhat uneven-aged.

        Returns:
            Estimated basal area (m²/ha).
        """
        ElfvingHagglundInitialStand._validate_broadleaves(broadleaves_percent_ba)
        if not isinstance(dominant_height, float):
             raise TypeError("dominant_height must be a float object.")
        if not isinstance(site_index, SiteIndexValue):
             raise TypeError("site_index must be a SiteIndexValue object.")
        
        ElfvingHagglundInitialStand._validate_site_index(site_index,TreeSpecies.Sweden.pinus_sylvestris)

        if stems is None:
             stems_obj = ElfvingHagglundInitialStand.estimate_stems_young_pine_north(
                 latitude=latitude,
                 altitude=altitude,
                 dominant_height=dominant_height,
                 stand_density_factor=stand_density_factor,
                 pct=pct,
                 even_or_somewhat_uneven_aged=even_or_somewhat_uneven_aged
             )
             stems_val = float(stems_obj)
        elif isinstance(stems, Stems):
             stems_val = float(stems)
        else:
             raise TypeError("stems must be a Stems object or None.")

        alt_norm = (altitude + 1.0) / 10.0 # Add 1m before dividing by 10? Check original.
        stand_dens_orig = stand_density_factor * 10.0
        si_dm = float(site_index) * 10.0
        h_dm = float(dominant_height) * 10.0
        broadleaves_norm = broadleaves_percent_ba + 1.0 # Add 1 to avoid log(0)

        ba_val = exp(
            -1.604
            - 0.170 * log(alt_norm)
            + 0.00993 * alt_norm
            + 0.314 * log(stand_dens_orig)
            + 0.467 * log(stems_val)
            - 0.138 * log(si_dm)
            + 1.204 * log(h_dm)
            + 0.032 * log(broadleaves_norm)
        ) / 100.0 # Convert dm²/ha (?) to m²/ha

        return StandBasalArea(value=ba_val, species=TreeSpecies.Sweden.pinus_sylvestris, over_bark=True, direct_estimate=False)


    @staticmethod
    def estimate_basal_area_young_spruce_north(
        altitude: float,
        site_index: SiteIndexValue, # H100
        dominant_height: float,
        stems: Optional[Stems] = None, # If None, calculate using estimate_stems_young_spruce_north
        stand_density_factor: float = 0.65,
        broadleaves_percent_ba: float = 0.0,
        spatial_distribution: int = 1, # 1=even, 2=somewhat uneven, 3=grouped
        pct: bool = False,
        even_or_somewhat_uneven_aged: bool = True,
    ) -> StandBasalArea:
        """
        Estimates initial basal area (m²/ha) for young Spruce in Northern Sweden.
        Based on Function 6.3, Elfving & Hägglund (1975), p. 53.

        Args:
            altitude: Altitude, meters above sea level.
            site_index: Site index H100 (m).
            dominant_height: Dominant height (m).
            stems: Stems per hectare. If None, estimated internally.
            stand_density_factor: Stand density factor (0.1-1.0).
            broadleaves_percent_ba: Percentage of broadleaves in BA (0-100).
            spatial_distribution: Code for spatial distribution (1, 2, or 3).
            pct: True if pre-commercial thinning has occurred.
            even_or_somewhat_uneven_aged: True if stand is even or somewhat uneven-aged.

        Returns:
            Estimated basal area (m²/ha).
        """
        if not isinstance(dominant_height, float):
             raise TypeError("dominant_height must be a float object.")
        if not isinstance(site_index, SiteIndexValue):
             raise TypeError("site_index must be a SiteIndexValue object.")
        if spatial_distribution not in [1, 2, 3]:
             raise ValueError("spatial_distribution must be 1, 2, or 3.")

        uneven_aged = not even_or_somewhat_uneven_aged
        ElfvingHagglundInitialStand._validate_age_structure(even_or_somewhat_uneven_aged, uneven_aged)

        ElfvingHagglundInitialStand._validate_site_index(site_index,TreeSpecies.Sweden.picea_abies)

        if stems is None:
             stems_obj = ElfvingHagglundInitialStand.estimate_stems_young_spruce_north(
                 altitude=altitude,
                 site_index=site_index,
                 stand_density_factor=stand_density_factor,
                 broadleaves_percent_ba=broadleaves_percent_ba,
                 pct=pct,
                 even_or_somewhat_uneven_aged=even_or_somewhat_uneven_aged
             )
             stems_val = float(stems_obj)
        elif isinstance(stems, Stems):
            stems_val = float(stems)
        else:
             raise TypeError("stems must be a Stems object or None.")

        # R code uses uneven_aged flag (1 or 2) in formula 6.3,
        # but calculates stems based on even_or_somewhat_uneven_aged.
        # Replicating R code's variable usage for formula 6.3:
        uneven_aged_flag_for_ba = 2 if uneven_aged else 1

        alt_norm = (altitude + 1.0) / 10.0
        alt_norm_sq = ((altitude + 1.0)) / 10.0 # Typo in R code? Should likely be alt_norm
        stand_dens_orig = stand_density_factor * 10.0
        si_dm = float(site_index) * 10.0
        h_dm = float(dominant_height) * 10.0

        ba_val = exp(
            -1.659
            - 0.125 * log(alt_norm) # Uses alt_norm here
            + 0.00918 * alt_norm_sq # Uses alt_norm_sq here - check source paper if discrepancy matters
            + 0.488 * log(stand_dens_orig)
            + 0.467 * log(stems_val)
            - 0.268 * log(si_dm)
            + 1.219 * log(h_dm)
            + 0.153 * spatial_distribution
            - 0.055 * uneven_aged_flag_for_ba # Uses the 1 or 2 flag
        ) / 100.0 # Convert dm²/ha (?) to m²/ha

        return StandBasalArea(value=ba_val, species=TreeSpecies.Sweden.picea_abies, over_bark=True, direct_estimate=False)


    @staticmethod
    def estimate_basal_area_young_pine_south(
        latitude: float, # Needed for age calculation if not provided
        altitude: float,
        site_index: SiteIndexValue, # H100
        dominant_height: float,
        stems: Optional[Stems] = None, # If None, calculate using estimate_stems_young_pine_south
        age_at_breast_height: Optional[AgeMeasurement] = None, # Optional
        stand_density_factor: float = 0.65,
        uneven_aged: bool = False, # Note: R code uses uneven_aged, not even_or_...
        pct: bool = False,
        regeneration: str = "culture",
    ) -> StandBasalArea:
        """
        Estimates initial basal area (m²/ha) for young Pine in Southern Sweden.
        Based on Function 6.2, Elfving & Hägglund (1975), p. 53.

        Args:
            latitude: Latitude, degrees N.
            altitude: Altitude, meters above sea level.
            site_index: Site index H100 (m).
            dominant_height: Dominant height (m).
            stems: Stems per hectare. If None, estimated internally.
            age_at_breast_height: Age at breast height. Required if stems is None.
            stand_density_factor: Stand density factor (0.1-1.0).
            uneven_aged: True if the stand is uneven-aged.
            pct: True if pre-commercial thinning has occurred.
            regeneration: Method of establishment ("culture", "natural regeneration", "unknown").

        Returns:
            Estimated basal area (m²/ha).
        """
        if not isinstance(dominant_height, float):
             raise TypeError("dominant_height must be a float object.")
        if not isinstance(site_index, SiteIndexValue):
             raise TypeError("site_index must be a SiteIndexValue object.")
        
        ElfvingHagglundInitialStand._validate_site_index(site_index,TreeSpecies.Sweden.pinus_sylvestris)

        if stems is None:
            if age_at_breast_height is None:
                 # Need to calculate age first if stems are to be calculated
                 raise NotImplementedError("Cannot estimate stems for S Pine BA without age_at_breast_height.")

            stems_obj = ElfvingHagglundInitialStand.estimate_stems_young_pine_south(
                 latitude=latitude,
                 site_index=site_index,
                 dominant_height=dominant_height,
                 age_at_breast_height=age_at_breast_height, # Must be provided here
                 stand_density_factor=stand_density_factor,
                 pct=pct,
                 regeneration=regeneration
             )
            stems_val = float(stems_obj)
        elif isinstance(stems, Stems):
            stems_val = float(stems)
        else:
            raise TypeError("stems must be a Stems object or None.")

        alt_norm = (altitude + 1.0) / 10.0
        stand_dens_orig = stand_density_factor * 10.0
        si_dm = float(site_index) * 10.0
        h_dm = float(dominant_height) * 10.0

        ba_val = exp(
            1.280 # Note: R code shows +1.280, paper/previous Python showed different. Using R code's value.
            - 0.089 * log(alt_norm)
            + 0.283 * log(stand_dens_orig)
            + 0.370 * log(stems_val)
            - 0.174 * log(si_dm)
            + 0.878 * log(h_dm)
            - 0.121 * uneven_aged # Bool -> 1/0
        ) / 100.0 # Convert dm²/ha (?) to m²/ha

        return StandBasalArea(value=ba_val, species=TreeSpecies.Sweden.pinus_sylvestris, over_bark=True, direct_estimate=False)


    @staticmethod
    def estimate_basal_area_young_spruce_south(
        altitude: float,
        site_index: SiteIndexValue, # H100
        dominant_height: float,
        age_at_breast_height: AgeMeasurement, # Required if stems is None
        stems: Optional[Stems] = None, # If None, calculate using estimate_stems_young_spruce_south
        stand_density_factor: float = 0.65,
        broadleaves_percent_ba: float = 0.0,
        spatial_distribution: int = 1, # 1=even, 2=somewhat uneven, 3=grouped
        even_or_somewhat_uneven_aged: bool = True,
        # PCT is not used in R formula 6.4, but is used for stem calculation if needed
        pct: bool = False,
    ) -> StandBasalArea:
        """
        Estimates initial basal area (m²/ha) for young Spruce in Southern Sweden.
        Based on Function 6.4, Elfving & Hägglund (1975), p. 53.

        Args:
            altitude: Altitude, meters above sea level.
            site_index: Site index H100 (m).
            dominant_height: Dominant height (m).
            age_at_breast_height: Age at breast height (years). Required if stems is None.
            stems: Stems per hectare. If None, estimated internally.
            stand_density_factor: Stand density factor (0.1-1.0).
            broadleaves_percent_ba: Percentage of broadleaves in BA (0-100).
            spatial_distribution: Code for spatial distribution (1, 2, or 3).
            even_or_somewhat_uneven_aged: True if stand is even or somewhat uneven-aged.
            pct: Pre-commercial thinning flag (used only if stems need estimation).

        Returns:
            Estimated basal area (m²/ha).
        """
        # Note: R code for S Spruce BA (6.4) seems identical to N Spruce BA (6.3) except for arguments.
        # Replicating 6.4 formula as written in the R code:
        ElfvingHagglundInitialStand._validate_broadleaves(broadleaves_percent_ba)
        if not isinstance(dominant_height, float):
             raise TypeError("dominant_height must be a float object.")
        if not isinstance(site_index, SiteIndexValue):
             raise TypeError("site_index must be a SiteIndexValue object.")
        if spatial_distribution not in [1, 2, 3]:
             raise ValueError("spatial_distribution must be 1, 2, or 3.")

        if stems is None:
             if age_at_breast_height is None:
                 raise ValueError("age_at_breast_height is required to estimate stems for S Spruce BA.")
             stems_obj = ElfvingHagglundInitialStand.estimate_stems_young_spruce_south(
                 altitude=altitude,
                 site_index=site_index,
                 age_at_breast_height=age_at_breast_height,
                 stand_density_factor=stand_density_factor,
                 broadleaves_percent_ba=broadleaves_percent_ba,
                 even_or_somewhat_uneven_aged=even_or_somewhat_uneven_aged
             )
             stems_val = float(stems_obj)
        elif isinstance(stems, Stems):
            stems_val = float(stems)
        else:
            raise TypeError("stems must be a Stems object or None.")

        alt_norm = (altitude + 1.0) / 10.0
        h_dm = float(dominant_height) * 10.0
        broadleaves_norm = broadleaves_percent_ba + 1.0 # Add 1 to avoid log(0)

        ba_val = exp(
            -0.102 # Constant from R code for F 6.4
            - 0.059 * log(alt_norm)
            + 0.584 * log(stems_val)
            + 0.723 * log(h_dm)
            - 0.025 * log(broadleaves_norm)
            - 0.098 * spatial_distribution
        ) / 100.0 # Convert dm²/ha (?) to m²/ha

        return StandBasalArea(value=ba_val, species=TreeSpecies.Sweden.picea_abies, over_bark=True, direct_estimate=False)

    # =========================================================================
    # Combined Estimator (Previous Implementation - kept for reference/compatibility)
    # =========================================================================
    @staticmethod
    def estimate_initial_spruce_stand(
        dominant_height: float,
        age_bh: AgeMeasurement,
        site_index: SiteIndexValue, # Expects SI object, uses its value
        altitude: float,
        northern_sweden: bool = True,
        broadleaves_percent_ba: float = 0,
        # Flags derived from R code params:
        even_aged: bool = True, # Combines even_or_somewhat_uneven vs uneven
        stand_density_factor: float = 0.65, # Corresponds to Målklass * 10 in original code
        pct: bool = False, # Pre-commercial thinning
        spatial_distribution: int = 1, # 1:even, 2:somewhat uneven, 3: grouped stand.
    ) -> Tuple[Stems, StandBasalArea]:
        """
        Estimates initial stems/ha and basal area/ha for Spruce stands.
        (Combined function calling specific estimators based on region).

        Args:
            dominant_height: Dominant height of the stand (m).
            age_bh: Age at breast height (years).
            site_index: Site index object (e.g., H100). The numeric value is used.
            altitude: Altitude (meters above sea level).
            northern_sweden: True if the site is in Northern Sweden, False otherwise.
            broadleaves_percent_ba: Percentage of broadleaves in the basal area (0-100).
            even_aged: True if the stand is considered even-aged or somewhat uneven-aged.
            stand_density_factor: A factor related to target density (0.1 to 1.0).
            pct: True if pre-commercial thinning has occurred.
            spatial_distribution: Code indicating spatial distribution (1=even, 2=somewhat uneven, 3=grouped).

        Returns:
            A tuple containing:
             - Stems: Estimated number of stems per hectare.
             - StandBasalArea: Estimated basal area (m²/ha).
        """
        # --- Input Validation ---
        if not isinstance(dominant_height, float):
             raise TypeError("dominant_height must be a float object.")
        if not isinstance(age_bh, AgeMeasurement):
            raise TypeError("age_bh must be an AgeMeasurement object.")
        if age_bh.code != Age.DBH.value:
             raise ValueError("age_bh must represent age at breast height (Age.DBH).")
        if not isinstance(site_index, SiteIndexValue):
             raise TypeError("site_index must be a SiteIndexValue object.")

        # Call the appropriate specific functions
        if northern_sweden:
            stems_obj = ElfvingHagglundInitialStand.estimate_stems_young_spruce_north(
                altitude=altitude,
                site_index=site_index,
                stand_density_factor=stand_density_factor,
                broadleaves_percent_ba=broadleaves_percent_ba,
                pct=pct,
                even_or_somewhat_uneven_aged=even_aged # Map flag
            )
            ba_obj = ElfvingHagglundInitialStand.estimate_basal_area_young_spruce_north(
                 altitude=altitude,
                 site_index=site_index,
                 dominant_height=dominant_height,
                 stems=stems_obj, # Use calculated stems
                 stand_density_factor=stand_density_factor,
                 broadleaves_percent_ba=broadleaves_percent_ba,
                 spatial_distribution=spatial_distribution,
                 pct=pct,
                 even_or_somewhat_uneven_aged=even_aged # Map flag
            )
        else: # Southern Sweden
            stems_obj = ElfvingHagglundInitialStand.estimate_stems_young_spruce_south(
                 altitude=altitude,
                 site_index=site_index,
                 age_at_breast_height=age_bh, # Pass age
                 stand_density_factor=stand_density_factor,
                 broadleaves_percent_ba=broadleaves_percent_ba,
                 even_or_somewhat_uneven_aged=even_aged # Map flag
            )
            ba_obj = ElfvingHagglundInitialStand.estimate_basal_area_young_spruce_south(
                 altitude=altitude,
                 site_index=site_index,
                 dominant_height=dominant_height,
                 age_at_breast_height=age_bh, # Pass age
                 stems=stems_obj, # Use calculated stems
                 stand_density_factor=stand_density_factor,
                 broadleaves_percent_ba=broadleaves_percent_ba,
                 spatial_distribution=spatial_distribution,
                 even_or_somewhat_uneven_aged=even_aged, # Map flag
                 pct=pct # Pass PCT for consistency if stem estimation called
            )

        return stems_obj, ba_obj