"""Regeneration quality and density (SLH), Elfving (1992) Arbetsrapporter nr 67.

This module implements the *full tabulated form* -- the Tab. 1-2 coefficient
tables with their application notes.

Note:
A *simplified form* of the same functions also circulates, expressed directly in
ASINSLH/ASINW. It differs in several respects: seed trees are scaled by /100,
inverse_area uses 1/(plot_area + 1), inverse_map_number uses 1/(map_number + 5),
wet is used instead of moist, and the SYZ flag includes X (Gävleborg). The two
forms therefore do not agree numerically, and this module follows the tabulated
one. (The two were previously labelled after the appendix numbers of a secondary
document, which said nothing about what actually distinguishes them.)

Note:
Is Jonsbon actually site index scale [1-9], or MAImax according to Jonson
scale? MAImax= 8*0.75(Jonson index - 2).
"""

from __future__ import annotations

from math import exp, sin, sqrt
from typing import Optional

from pyforestry.base.contracts import SourceReference
from pyforestry.base.helpers.primitives import SiteIndexValue
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies
from pyforestry.sweden.site.enums import Sweden
from pyforestry.sweden.siteindex.translate.jonson_index import jonson_index_from_site_index
from pyforestry.sweden.siteindex.validation import validate_hagglund_1970_h100_site_index


class Elfving1992Regeneration:
    """SLH regeneration functions for natural and cultivated stands (full tabulated form).

    Defaults follow the tabulated form's application notes:
    - ``age_years`` = 12
    - ``n_full`` = 2_500
    - coefficient adjustments enabled (``use_adjusted_coeffs=True``)

    N.B. At application of the functions in Tab. 1-2 age was set to 12 and N-full to 2.5.
    Increased efficiency in provenance selection and scarification has also been considered by
    assumed influence on the cofficients. For cultivations the negative effect by increasing
    height above see level has been reduced from -0.0514 to -0.0257 and the positive effect by
    scarification has been increased from 0.0757 to 0.2. For natural regenerations the effect
    by scarification has been modified to 0.30 on mesic sites and 0.15 on other sites.

    Example:
        >>> site = SwedishSite(...)
        >>> jonson_index = jonson_index_from_site_index(
        ...     h100_input=site_index_value,
        ...     main_species=TreeSpecies.Sweden.picea_abies,
        ...     vegetation=site.field_layer,
        ...     altitude=site.altitude or 0.0,
        ...     county=site.county,
        ... )
        >>> Elfving1992Regeneration.slh_natural(
        ...     latitude_deg=site.latitude,
        ...     altitude_m=site.altitude or 0.0,
        ...     county=site.county,
        ...     soil_moisture=site.soil_moisture,
        ...     jonson_index=jonson_index,
        ... )
    """

    @staticmethod
    def _validate_h100_input(h100_input: SiteIndexValue, main_species: TreeName) -> None:
        """Validate H100 input uses Hagglund 1970 site index function."""
        validate_hagglund_1970_h100_site_index(
            h100_input,
            param_name="h100_input",
            expected_species=main_species,
            allowed_species={
                TreeSpecies.Sweden.picea_abies,
                TreeSpecies.Sweden.pinus_sylvestris,
            },
        )

    @staticmethod
    def slh_natural(
        *,
        latitude_deg: float,
        altitude_m: float,
        county: Optional[Sweden.County],
        soil_moisture: Optional[Sweden.SoilMoistureEnum],
        jonson_index: Optional[float] = None,
        h100_input: Optional[SiteIndexValue] = None,
        main_species: Optional[TreeName] = None,
        vegetation: Optional[Sweden.FieldLayer] = None,
        age_years: float = 12.0,
        n_full: float = 2500.0,
        prop_cultivated: float = 0.0,
        seed_trees_per_ha: float = 0.0,
        regen_area_ha: float = 1.0,
        scarified: bool = False,
        burnt: bool = False,
        no_treat: bool = False,
        uncleaned: bool = False,
        use_adjusted_coeffs: bool = True,
        natural_scarif_coeff_mesic: float = 0.30,
        natural_scarif_coeff_other: float = 0.15,
    ) -> tuple[float, float, float]:
        """Compute SLH for natural regeneration.

        Args:
            latitude_deg (float): Latitude in decimal degrees.
            altitude_m (float): Altitude in meters above sea level.
            county (Sweden.County | None): Swedish county enum. Used for Gotland/SYZ/T-area
                indicators and for Jonson index derivation when ``jonson_index`` is not supplied.
            soil_moisture (Sweden.SoilMoistureEnum | None): Soil moisture class. Used to set
                dry/mesic/moist indicator variables.
            jonson_index (float | None): Jonson site index (1..9). If omitted, supply
                ``h100_input``, ``main_species``, ``vegetation``, and ``county`` to derive it.
            h100_input (SiteIndexValue | None): H100 site index value used to derive Jonson
                index if ``jonson_index`` is not provided.
            main_species (TreeName | None): Species for H100 (pine or spruce) when deriving
                Jonson index.
            vegetation (Sweden.FieldLayer | None): Field layer vegetation enum for Hagglund
                1981 translation when deriving Jonson index.
            age_years (float): Vegetation periods since regeneration. Default is 12.
            n_full (float): Demanded seedlings per ha for full stocking (plants/ha).
                Default is 2_500 (the tabulated form uses 2.5 thousand/ha).
            prop_cultivated (float): Proportion cultivated seedlings in natural regeneration
                (0..1).
            seed_trees_per_ha (float): Number of seed trees per hectare. Set to 0 for
                stands without seed trees.
            regen_area_ha (float): Regeneration area (ha). Used as inverse_area = 1/area.
            scarified (bool): Indicator for scarification treatment.
            burnt (bool): Indicator for prescribed burning after final felling.
            no_treat (bool): Indicator for no regeneration treatments.
            uncleaned (bool): Indicator for uncleaned sites after clear-felling.
            use_adjusted_coeffs (bool): Use the tabulated form's adjusted
                scarification coefficients.
            natural_scarif_coeff_mesic (float): Scarification coefficient on mesic sites
                when adjusted (default 0.30).
            natural_scarif_coeff_other (float): Scarification coefficient on non-mesic
                sites when adjusted (default 0.15).

        Returns:
            tuple[float, float, float]: ``(asinslh, slh_est, slh_corr)`` where:
            - ``asinslh`` is the linear predictor (radians),
            - ``slh_est`` is back-transformed stocking (0..1),
            - ``slh_corr`` is bias-corrected stocking (0..1).

        Raises:
            ValueError: If ``jonson_index`` is not supplied and required inputs for deriving it
                are missing, or if ``h100_input`` is not from Hagglund 1970.
        """

        def map_number_from_latitude(lat_deg: float) -> float:
            """Convert latitude (deg) to the tabulated-form map number."""
            # Tabulated-form definition: map = (X - 6050) / 50, X in km north of equator.
            return (lat_deg * 111.1 - 6050.0) / 50.0

        def age_f_from_age(age: float) -> float:
            """Compute the tabulated-form age transformation for natural regeneration."""
            # Tabulated-form definition: age_f = 2 * (1 / (1 + exp(-0.3 * age)) - 0.5)
            # (equivalently tanh(0.15 * age)); an increasing S-curve bounded in [0, 1].
            return 2.0 * (1.0 / (1.0 + exp(-0.3 * age)) - 0.5)

        def resolve_jonson_index() -> float:
            """Resolve Jonson index from explicit input or Hagglund-based conversion."""
            if jonson_index is not None:
                return float(jonson_index)
            if h100_input is None:
                raise ValueError("jonson_index or h100_input must be provided.")
            if main_species is None or vegetation is None or county is None:
                raise ValueError(
                    "main_species, vegetation, and county are required to derive jonson_index."
                )
            Elfving1992Regeneration._validate_h100_input(h100_input, main_species)
            return float(
                jonson_index_from_site_index(
                    h100_input=h100_input,
                    main_species=main_species,
                    vegetation=vegetation,
                    altitude=altitude_m,
                    county=county,
                )
            )

        north_flag = int(latitude_deg >= 60.0)
        map_number_val = map_number_from_latitude(latitude_deg)
        gotland = int(county == Sweden.County.GOTLAND)
        syz_area = int(
            county
            in {
                Sweden.County.VARMLAND,
                Sweden.County.VASTERNORRLAND_ANGERMANLANDS,
                Sweden.County.VASTERNORRLAND_MEDELPADS,
                Sweden.County.JAMTLAND_JAMTLANDS,
                Sweden.County.JAMTLAND_HARJEDALENS,
            }
        )
        t_area = int(county == Sweden.County.OREBRO)

        dry = int(soil_moisture == Sweden.SoilMoistureEnum.DRY) if soil_moisture else 0
        mesic = (
            int(
                soil_moisture
                in {Sweden.SoilMoistureEnum.MESIC, Sweden.SoilMoistureEnum.MESIC_MOIST}
            )
            if soil_moisture
            else 0
        )
        moist = (
            int(soil_moisture in {Sweden.SoilMoistureEnum.MOIST, Sweden.SoilMoistureEnum.WET})
            if soil_moisture
            else 0
        )

        if not 0.0 <= prop_cultivated <= 1.0:
            raise ValueError("prop_cultivated must be within [0, 1].")
        if seed_trees_per_ha < 0:
            raise ValueError("seed_trees_per_ha must be >= 0.")
        if n_full < 0:
            raise ValueError("n_full must be >= 0.")

        age_f_val = age_f_from_age(age_years)
        n_full_thousands = n_full / 1000.0
        no_seed_trees = int(seed_trees_per_ha == 0.0)

        # NOTE: the tabulated form uses 1/area (ha). the simplified form uses
        # 1/(plot_area + 1). Keep this explicit so callers can choose behavior.
        inverse_area = 1.0 / regen_area_ha if regen_area_ha > 0 else 0.0

        # Tabulated-form scarification modification: 0.30 on mesic sites, 0.15 otherwise.
        scarif_coeff = 0.2692
        if use_adjusted_coeffs:
            scarif_coeff = natural_scarif_coeff_mesic if mesic == 1 else natural_scarif_coeff_other

        lp = (
            1.7413
            + (-0.0163) * (altitude_m / 100.0) ** 2 * north_flag
            + 0.6863 * age_f_val
            + 0.6663 * prop_cultivated
            + (-0.1500) * n_full_thousands
            + 0.0218 * map_number_val * dry
            + 0.2702 * moist
            + (-0.7552) * gotland
            + 0.3310 * t_area
            + (-0.1275) * syz_area
            + scarif_coeff * int(scarified)
            + 0.2030 * int(burnt)
            + (-0.1484) * int(no_treat)
            + (-0.0947) * int(uncleaned)
            # N-seedtrees enters in hundreds of seed-trees per ha: the report's
            # Table 1 variable mean is 0.263 (~26 seed-trees/ha / 100), which is
            # only consistent with a /100 scaling for the coefficient 0.1596.
            + 0.1596 * (seed_trees_per_ha / 100.0)
            + 0.0175 * map_number_val * no_seed_trees
            + (-0.0379) * resolve_jonson_index()
            + 0.1888 * inverse_area
            + 0.1075 * north_flag
            + (-0.00619) * map_number_val
        )

        slh_est = sin(lp / 2.0) ** 2
        slh_corr = 0.056 + 0.887 * slh_est
        slh_corr = max(0.0, min(1.0, slh_corr))
        return lp, slh_est, slh_corr

    @staticmethod
    def slh_cultivated(
        *,
        latitude_deg: float,
        altitude_m: float,
        county: Optional[Sweden.County],
        jonson_index: Optional[float] = None,
        h100_input: Optional[SiteIndexValue] = None,
        main_species: Optional[TreeName] = None,
        vegetation: Optional[Sweden.FieldLayer] = None,
        age_years: float = 12.0,
        n_full: float = 2500.0,
        spacing_m: Optional[float] = None,
        plant_count_per_ha: Optional[float] = None,
        scarified: bool = False,
        burnt: bool = False,
        sown: bool = False,
        spruce: bool = False,
        use_adjusted_coeffs: bool = True,
        cultivation_altxns_coeff: float = -0.0257,
        cultivation_scarif_coeff: float = 0.2,
    ) -> tuple[float, float, float]:
        """Compute SLH for cultivation (sowing/planting).

        Args:
            latitude_deg (float): Latitude in decimal degrees.
            altitude_m (float): Altitude in meters above sea level.
            county (Sweden.County | None): Swedish county enum. Used for T-area indicator
                and for Jonson index derivation when ``jonson_index`` is not supplied.
            jonson_index (float | None): Jonson site index (1..9). If omitted, supply
                ``h100_input``, ``main_species``, ``vegetation``, and ``county`` to derive it.
            h100_input (SiteIndexValue | None): H100 site index value used to derive Jonson
                index if ``jonson_index`` is not provided.
            main_species (TreeName | None): Species for H100 (pine or spruce) when deriving
                Jonson index.
            vegetation (Sweden.FieldLayer | None): Field layer vegetation enum for Hagglund
                1981 translation when deriving Jonson index.
            age_years (float): Vegetation periods since sowing/planting. Default is 12.
            n_full (float): Demanded seedlings per ha for full stocking (plants/ha).
                Default is 2_500 (the tabulated form uses 2.5 thousand/ha).
            spacing_m (float | None): Plant spacing in meters. If omitted, ``plant_count_per_ha``
                must be provided and spacing is derived as 100/sqrt(plant_count_per_ha).
            plant_count_per_ha (float | None): Plants per ha for spacing derivation when
                ``spacing_m`` is not provided.
            scarified (bool): Indicator for scarification treatment.
            burnt (bool): Indicator for prescribed burning after final felling.
            sown (bool): Indicator for sown regenerations.
            spruce (bool): Indicator for spruce cultivation.
            use_adjusted_coeffs (bool): Use the tabulated form's adjusted coefficients for
                altitude and scarification.
            cultivation_altxns_coeff (float): Adjusted altitude coefficient when enabled.
            cultivation_scarif_coeff (float): Adjusted scarification coefficient when enabled.

        Returns:
            tuple[float, float, float]: ``(asinslh, slh_est, slh_corr)`` where:
            - ``asinslh`` is the linear predictor (radians),
            - ``slh_est`` is back-transformed stocking (0..1),
            - ``slh_corr`` is bias-corrected stocking (0..1).

        Raises:
            ValueError: If ``jonson_index`` is not supplied and required inputs for deriving it
                are missing, if ``h100_input`` is not from Hagglund 1970, or if spacing
                cannot be derived.
        """

        def map_number_from_latitude(lat_deg: float) -> float:
            """Convert latitude (deg) to the tabulated-form map number."""
            return (lat_deg * 111.1 - 6050.0) / 50.0

        def resolve_jonson_index() -> float:
            """Resolve Jonson index from explicit input or Hagglund-based conversion."""
            if jonson_index is not None:
                return float(jonson_index)
            if h100_input is None:
                raise ValueError("jonson_index or h100_input must be provided.")
            if main_species is None or vegetation is None or county is None:
                raise ValueError(
                    "main_species, vegetation, and county are required to derive jonson_index."
                )
            Elfving1992Regeneration._validate_h100_input(h100_input, main_species)
            return float(
                jonson_index_from_site_index(
                    h100_input=h100_input,
                    main_species=main_species,
                    vegetation=vegetation,
                    altitude=altitude_m,
                    county=county,
                )
            )

        if spacing_m is None:
            if plant_count_per_ha is None or plant_count_per_ha <= 0:
                raise ValueError("Provide spacing_m or a positive plant_count_per_ha.")
            spacing_val = 100.0 / sqrt(plant_count_per_ha)
        else:
            spacing_val = spacing_m

        north_flag = int(latitude_deg > 60.0)
        map_number_val = map_number_from_latitude(latitude_deg)
        inverse_map_number = 1.0 / map_number_val if abs(map_number_val) > 1e-9 else 0.0
        t_area = int(county == Sweden.County.OREBRO)

        altxns_coeff = -0.0514
        scarif_coeff = 0.0757
        if use_adjusted_coeffs:
            # NOTE: The tabulated form reduces altitude effect and increases scarification effect.
            altxns_coeff = cultivation_altxns_coeff
            scarif_coeff = cultivation_scarif_coeff

        if n_full < 0:
            raise ValueError("n_full must be >= 0.")

        inverse_age = 1.0 / age_years if age_years > 0 else 0.0
        n_full_thousands = n_full / 1000.0

        lp = (
            3.0707
            + 0.4358 * inverse_age
            + (-0.0614) * resolve_jonson_index()
            + altxns_coeff * (altitude_m / 100.0) * north_flag
            + (-0.3591) * spacing_val
            + 0.0760 * int(spruce)
            + 0.1141 * int(burnt)
            + scarif_coeff * int(scarified)
            + (-0.0675) * int(sown)
            + 0.2597 * north_flag
            # NOTE: the tabulated form uses inverse_map_number = 1/map;
            # the simplified form uses 1/(ky + 5).
            + 4.7901 * inverse_map_number
            + 0.2178 * t_area
            + (-0.1500) * n_full_thousands
        )

        slh_est = sin(lp / 2.0) ** 2
        slh_corr = 0.037 + 0.926 * slh_est
        slh_corr = max(0.0, min(1.0, slh_corr))
        return lp, slh_est, slh_corr


__all__ = ["Elfving1992Regeneration"]


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


class _Descriptor:
    """FormulaModuleDescriptor for Elfving (1992) regeneration quality."""

    @property
    def component_id(self):
        return "Elfving1992Regeneration"

    @property
    def source(self):
        return SourceReference(
            author="Elfving, B.",
            year=1992,
            title=("Återväxtens etablering och utveckling till röjningstidpunkten"),
            note=(
                "Sveriges lantbruksuniversitet, institutionen för skogsskötsel, "
                "Arbetsrapporter nr 67, Umeå."
            ),
        )

    @property
    def species_groups(self):
        return {}

    @property
    def units(self):
        return {"latitude_deg": "degrees", "altitude_m": "m", "return": "SLH (stocking fraction)"}

    @property
    def kernel_names(self):
        return list(__all__)


DESCRIPTOR = _Descriptor()
