"""Extracted HUGIN (Elfving 1982) formulas and NYSKOG reconstruction kernels.

These are the kernel equations behind
:mod:`pyforestry.sweden.blocks.elfving_1982`, which carries the catalog
descriptor for the pair; the per-function docstrings below cite the section of
the report each formula comes from.

Source:
    Elfving, B. (1982). *HUGINs ungskogstaxering 1976-1979.* Sveriges
    lantbruksuniversitet, Projekt HUGIN, Rapport nr 27, Umeå, 115 s.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp, log, sin, sqrt
from typing import Any, Literal, Mapping, Optional, Sequence

from pyforestry.base.helpers.tree import Tree
from pyforestry.base.helpers.tree_species import TreeName, TreeSpecies, get_tree_type_by_genus
from pyforestry.sweden.site.enums import Sweden

_PINE_SPECIES = {
    TreeSpecies.Sweden.pinus_sylvestris,
    TreeSpecies.Sweden.pinus_contorta,
}
_LARCH_SPECIES = {
    TreeSpecies.Sweden.larix_sibirica,
    TreeSpecies.Sweden.larix_decidua,
    TreeSpecies.Sweden.larix_europaea_x_leptolepis,
    TreeSpecies.Sweden.larix_sukaczewii,
}
_PINE_SPECIES = _PINE_SPECIES | _LARCH_SPECIES
_SPRUCE_SPECIES = {
    TreeSpecies.Sweden.picea_abies,
    TreeSpecies.Sweden.picea_sitchensis,
    TreeSpecies.Sweden.picea_mariana,
}
_BIRCH_SPECIES = {TreeSpecies.Sweden.betula_pendula, TreeSpecies.Sweden.betula_pubescens}
_ASPEN_SPECIES = {
    TreeSpecies.Sweden.populus_tremula,
    TreeSpecies.Sweden.populus_tremula_x_tremuloides,
}
_BEECH_SPECIES = {TreeSpecies.Sweden.fagus_sylvatica}
_OAK_SPECIES = {
    TreeSpecies.Sweden.quercus_robur,
    TreeSpecies.Sweden.quercus_petraea,
    TreeSpecies.Sweden.quercus_rubra,
}
_NATURAL_REGENERATION_TYPES = {"natural_regeneration", "extensive"}
_CONTORTA_DECIDUOUS_PLANTATION_TYPES = {"contorta_plantation", "deciduous_plantation"}
RegenerationTypeName = Literal[
    "natural_regeneration",
    "extensive",
    "sown",
    "pine_plantation",
    "spruce_plantation",
    "contorta_plantation",
    "deciduous_plantation",
]
NfiRegionName = Literal["Reg1", "Reg21", "Reg22", "Reg3", "Reg4", "Reg5"]
_REPRESENTATIVE_SPECIES: dict[str, TreeName] = {
    "pine": TreeSpecies.Sweden.pinus_sylvestris,
    "spruce": TreeSpecies.Sweden.picea_abies,
    "contorta": TreeSpecies.Sweden.pinus_contorta,
    "larch": TreeSpecies.Sweden.larix_sibirica,
    "birch": TreeSpecies.Sweden.betula_pendula,
    "other_broadleaf": TreeSpecies.Sweden.populus_tremula,
}


def _is_conifer(species: TreeName) -> bool:
    """Return whether a species belongs to a coniferous genus."""
    return get_tree_type_by_genus(species.genus.name) == "Coniferous"


def _species_key(species: TreeName) -> str:
    """Map a species to the internal Hugin species-group key."""
    if species is TreeSpecies.Sweden.pinus_contorta:
        return "contorta"
    if species in _LARCH_SPECIES:
        return "larch"
    if species in _PINE_SPECIES:
        return "pine"
    if species in _SPRUCE_SPECIES:
        return "spruce"
    if species in _BIRCH_SPECIES:
        return "birch"
    return "other_broadleaf"


def site_index_for_species(  # pragma: no cover - legacy parity branch table
    species: TreeName, *, site_index_pine_m: float, site_index_spruce_m: float
) -> float:
    """Translate pine/spruce site indices to a species-specific site index."""
    if species is TreeSpecies.Sweden.pinus_contorta:
        return 0.888 + 1.336 * site_index_pine_m - 0.0094 * site_index_pine_m**2
    if species in _PINE_SPECIES:
        return site_index_pine_m
    if species in _SPRUCE_SPECIES:
        return site_index_spruce_m
    if species in _BIRCH_SPECIES:
        if species is TreeSpecies.Sweden.betula_pendula:
            return site_index_pine_m + 1.5
        return site_index_pine_m if site_index_pine_m < 24 else site_index_pine_m + 1.5
    if species in _ASPEN_SPECIES:
        return site_index_pine_m
    if species in _BEECH_SPECIES:
        return 7.4 + 0.755 * site_index_spruce_m - 0.00268 * site_index_spruce_m**2
    if species in _OAK_SPECIES:
        return 6.5 + 0.5 * site_index_pine_m
    return site_index_pine_m if site_index_pine_m < 24 else site_index_pine_m + 1.5


def _b_coeffs(  # pragma: no cover - legacy parity branch table
    species: TreeName, site_index_m: float
) -> tuple[float, float, float]:
    """Return species-specific ``(b0, b1, b2)`` mean-height coefficients."""
    if species in _PINE_SPECIES:
        b0 = 7.0
        b1 = -0.57 + -0.05 * site_index_m
        si = site_index_m
        if 29.78723 < si <= 29.8:
            si = 29.78723
        b2 = -0.28 + 0.0094 * si
        return b0, b1, b2

    if species in _SPRUCE_SPECIES or species in _BEECH_SPECIES:
        b0 = 6.27 + 12.1 / site_index_m
        si = min(site_index_m, 0.0575 / (2.0 * 0.00088))
        b1 = -0.262 + -0.0575 * si + 0.00088 * si**2
        b2 = -0.323 + -0.134 * b1
        return b0, b1, b2

    if species in _ASPEN_SPECIES:
        b0 = 10.024 + -0.1664 * site_index_m
        b1 = -4.093 + 0.1605 * site_index_m + -0.0025 * site_index_m**2
        return b0, b1, 0.0

    b0 = 6.836 + 0.03165 * site_index_m + -0.002757 * site_index_m**2
    b1 = -2.694 + 0.4937 * b0 + -0.05331 * b0**2
    return b0, b1, 0.0


def mean_height(  # pragma: no cover - legacy parity formula
    *,
    age_years: float,
    species: TreeName,
    site_index_pine_m: float,
    site_index_spruce_m: float,
) -> float:
    """Compute mean height (m) from total age and site indices.

    Reference: Elfving (1982), Rapport 27 §2.2. H = SI/(exp(Y)+1) with Y a
    quadratic in ln(total age); coefficients per species group.
    """
    if age_years <= 0:
        return 0.0

    si = site_index_for_species(
        species, site_index_pine_m=site_index_pine_m, site_index_spruce_m=site_index_spruce_m
    )
    b0, b1, b2 = _b_coeffs(species, si)
    ln_age = log(age_years)
    power = b0 + b1 * ln_age + b2 * ln_age**2
    height = si / (exp(power) + 1.0)
    return max(0.3, height)


def mean_age(  # pragma: no cover - legacy parity formula inversion
    *,
    mean_height_m: float,
    species: TreeName,
    site_index_pine_m: float,
    site_index_spruce_m: float,
) -> float:
    """Invert mean height to mean age (years)."""
    if mean_height_m <= 0.0:
        return 0.0

    si = site_index_for_species(
        species, site_index_pine_m=site_index_pine_m, site_index_spruce_m=site_index_spruce_m
    )
    if mean_height_m >= si:
        raise ValueError("mean_height_m must be less than site index for inversion.")

    b0, b1, b2 = _b_coeffs(species, si)
    y = log(si / mean_height_m - 1.0)

    is_conifer = (
        species in _PINE_SPECIES or species in _SPRUCE_SPECIES or species in _BEECH_SPECIES
    )
    if is_conifer and abs(b2) > 1e-12:
        disc = b1**2 - 4.0 * b2 * (b0 - y)
        disc = max(disc, 0.0)
        ln_age = (-b1 - sqrt(disc)) / (2.0 * b2)
        return exp(ln_age)
    return exp((y - b0) / b1)


def crop_tree_probability(  # pragma: no cover - legacy parity formula
    *,
    height_m: float,
    mean_height_m: float,
    conifer_stems_per_100m2: float,
    rec_stems_per_ha: float,
    coniferous: bool,
) -> float:
    """Compute crop-tree probability for a single tree.

    Reference: Elfving (1982), Rapport 27 §2.1. p = sin^2(...) in relative tree
    height H=h/HA and sqrt of conifer stem count; separate conifer/broadleaf forms.
    """
    if mean_height_m <= 0.0:
        raise ValueError("mean_height_m must be > 0.")
    if rec_stems_per_ha <= 0.0:
        raise ValueError("rec_stems_per_ha must be > 0.")
    if conifer_stems_per_100m2 < 0.0:
        raise ValueError("conifer_stems_per_100m2 must be >= 0.")

    hrel = height_m / mean_height_m
    hrel2 = hrel * hrel
    corr_stem = 1600.0 / rec_stems_per_ha
    conifer_sqrt = sqrt(conifer_stems_per_100m2 * corr_stem)

    if coniferous:
        s = (
            0.7433
            + 1.4339 * hrel
            + -0.4902 * hrel2
            + -0.1070 * conifer_sqrt
            + -0.1097 * conifer_sqrt * hrel
            + 0.0587 * conifer_sqrt * hrel2
        )
    else:
        s = (
            0.0185
            + 1.0991 * hrel
            + -0.2665 * hrel2
            + -0.1615 * conifer_sqrt * hrel
            + 0.0453 * conifer_sqrt * hrel2
        )
    prob = sin(s) ** 2
    return max(0.0, min(1.0, prob))


def probabilities_from_tree_list(  # pragma: no cover - legacy parity helper
    trees: Sequence[Tree],
    *,
    rec_stems_per_ha: float,
    expansion_factor: float = 1.0,
) -> list[float]:
    """Compute crop-tree probabilities for a tree list."""
    if not trees:
        return []

    sum_height = 0.0
    sum_weight = 0.0
    sum_conifer = 0.0
    for tree in trees:
        if tree.height_m is None:
            continue
        stems = (tree.weight_n or 0.0) * expansion_factor
        sum_height += tree.height_m * stems
        sum_weight += stems
        if tree.species and _is_conifer(tree.species):
            sum_conifer += stems

    if sum_weight <= 0.0:
        raise ValueError("Tree weights sum to zero; cannot compute mean height.")

    mean_height_val = sum_height / sum_weight
    conifer_per_100m2 = sum_conifer * 0.01

    probs: list[float] = []
    for tree in trees:
        if tree.height_m is None or tree.species is None:
            probs.append(0.0)
            continue
        probs.append(
            crop_tree_probability(
                height_m=tree.height_m,
                mean_height_m=mean_height_val,
                conifer_stems_per_100m2=conifer_per_100m2,
                rec_stems_per_ha=rec_stems_per_ha,
                coniferous=_is_conifer(tree.species),
            )
        )
    return probs


def nyskog_indicators_from_site(  # pragma: no cover - legacy indicator mapping
    *,
    field_layer: Optional[Sweden.FieldLayer],
    soil_moisture: Optional[Sweden.SoilMoistureEnum],
) -> dict[str, int]:
    """Map Swedish site enums to NYSKOG indicator variables."""
    wet = (
        int(soil_moisture in {Sweden.SoilMoistureEnum.MOIST, Sweden.SoilMoistureEnum.WET})
        if soil_moisture
        else 0
    )
    dry = int(soil_moisture == Sweden.SoilMoistureEnum.DRY) if soil_moisture else 0

    rich = poor = shrubs = lichen = herb = hwd = hwod = 0
    if field_layer is not None:
        if field_layer in {
            Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS,
            Sweden.FieldLayer.HIGH_HERB_WITH_SHRUBS_BLUEBERRY,
            Sweden.FieldLayer.HIGH_HERB_WITH_SHRUBS_LINGON,
            Sweden.FieldLayer.LOW_HERB_WITHOUT_SHRUBS,
            Sweden.FieldLayer.LOW_HERB_WITH_SHRUBS_BLUEBERRY,
            Sweden.FieldLayer.LOW_HERB_WITH_SHRUBS_LINGON,
        }:
            rich = 1
            hwod = 1
        elif field_layer in {
            Sweden.FieldLayer.NO_FIELD_LAYER,
            Sweden.FieldLayer.BROADLEAVED_GRASS,
            Sweden.FieldLayer.THINLEAVED_GRASS,
            Sweden.FieldLayer.HORSETAIL,
        }:
            rich = 1
        elif field_layer in {Sweden.FieldLayer.SEDGE_LOW}:
            poor = 1
        elif field_layer in {
            Sweden.FieldLayer.LINGONBERRY,
            Sweden.FieldLayer.CROWBERRY,
            Sweden.FieldLayer.POOR_SHRUB,
        }:
            poor = 1
            shrubs = 1
        elif field_layer in {Sweden.FieldLayer.LICHEN_FREQUENT, Sweden.FieldLayer.LICHEN_DOMINANT}:
            poor = 1
            shrubs = 1
            lichen = 1
        elif field_layer in {Sweden.FieldLayer.BILBERRY}:
            shrubs = 1

        if field_layer in {
            Sweden.FieldLayer.BROADLEAVED_GRASS,
            Sweden.FieldLayer.THINLEAVED_GRASS,
            Sweden.FieldLayer.HIGH_HERB_WITHOUT_SHRUBS,
            Sweden.FieldLayer.HIGH_HERB_WITH_SHRUBS_BLUEBERRY,
            Sweden.FieldLayer.HIGH_HERB_WITH_SHRUBS_LINGON,
            Sweden.FieldLayer.LOW_HERB_WITHOUT_SHRUBS,
            Sweden.FieldLayer.LOW_HERB_WITH_SHRUBS_BLUEBERRY,
            Sweden.FieldLayer.LOW_HERB_WITH_SHRUBS_LINGON,
            Sweden.FieldLayer.HORSETAIL,
        }:
            herb = 1

    return {
        "wet": wet,
        "dry": dry,
        "rich": rich,
        "poor": poor,
        "shrubs": shrubs,
        "lichen": lichen,
        "herb": herb,
        "hwd": hwd,
        "hwod": hwod,
    }


@dataclass(frozen=True)
class _AsinwCoeff:
    """Coefficients for young-stand quality W (ASINW) as a function of stocking."""

    intercept: float
    linear: float
    quadratic: float
    ns: float  # deterministic latitude dummy: NS = 1 if latitude > 60 N


# Young-stand quality W vs regeneration stocking (Elfving 1982, Hugin Rapport 27;
# as published in Elfving (1982) Rapport 27):
#   natural      W = sin^2(-0.11  + 1.671*asinslh - 0.583*asinslh^2)
#   cultivation  W = sin^2(-0.058 + 1.380*asinslh - 0.315*asinslh^2 - 0.031*NS)
# with asinslh = arcsin(sqrt(SLH)) in radians and NS = 1 if latitude > 60 N. The
# report defines W deterministically ("expected W"); it carries no residual/noise
# term (Heureka's regeneration stochasticity comes from representative-plot
# selection, not from perturbing W).
_REJUV_ASINW_COEFF = _AsinwCoeff(intercept=-0.11, linear=1.671, quadratic=-0.583, ns=0.0)
_PLANT_ASINW_COEFF = _AsinwCoeff(intercept=-0.058, linear=1.380, quadratic=-0.315, ns=-0.031)


def young_stand_quality_asinw(
    *,
    stocking_arcsine_radians: float,
    regeneration_type: RegenerationTypeName | str,
    latitude_deg: float | None = None,
) -> float:
    """Young-stand quality on the arcsine scale, ASINW = arcsin(sqrt(W)).

    Elfving (1982), Hugin Rapport 27::

        natural      W = sin^2(-0.11  + 1.671*asinslh - 0.583*asinslh^2)
        cultivation  W = sin^2(-0.058 + 1.380*asinslh - 0.315*asinslh^2 - 0.031*NS)

    where NS = 1 if ``latitude_deg`` > 60 N (cultivation only; ignored for natural,
    whose NS coefficient is 0). ``stocking_arcsine_radians`` is the SLH linear
    predictor (= 2*asinslh); the return value feeds :func:`production_potential_q`
    (q = 100*sin^2(asinw)).
    """
    name = getattr(regeneration_type, "value", regeneration_type)
    coeff = _REJUV_ASINW_COEFF if name in _NATURAL_REGENERATION_TYPES else _PLANT_ASINW_COEFF
    asinslh = 0.5 * stocking_arcsine_radians
    ns = 1.0 if (latitude_deg is not None and latitude_deg > 60.0) else 0.0
    return coeff.intercept + coeff.linear * asinslh + coeff.quadratic * asinslh**2 + coeff.ns * ns


def production_potential_q(asinw: float) -> float:  # pragma: no cover - legacy formula
    """Production potential Q (0-100) from ASINW = arcsin(sqrt(W)).

    q = 100 * W, with W = sin^2(asinw). Elfving (1982), the published
    regeneration report (Elfving 1982).
    """
    return (sin(asinw) ** 2) * 100.0


def udim_probability(  # pragma: no cover - legacy formula
    q: float, *, deterministic: bool = True, rng: Optional[float] = None
) -> float:
    """Compute under-dimensioned probability or Bernoulli draw indicator."""
    y = -18.4313 + 4.6441 * log(q) - 0.0282 * q
    p_udim = 1.0 / (1.0 + exp(-y))
    if deterministic:
        return p_udim
    r = rng if rng is not None else 0.5
    return 1.0 if p_udim <= r else 0.0


def total_stems(  # pragma: no cover - legacy formula
    *,
    regeneration_type: RegenerationTypeName | str,
    mean_height_main_m: float,
    q: float,
    ln_q: float,
    ln_si: float,
    under_dimension_prob: float,
    wet: int,
    dry: int,
    height_indicator_dm: float,
    deterministic: bool = True,
    noise: float = 0.0,
) -> float:
    """Step 1 NYSKOG equation: compute total stems per hectare."""
    if mean_height_main_m <= 0.0:
        return 0.0
    if height_indicator_dm <= 0.0:
        raise ValueError("height_indicator_dm must be > 0.")

    height_dm = mean_height_main_m * 10.0
    ln_height = log(height_dm)
    regeneration_type_name = getattr(regeneration_type, "value", regeneration_type)

    if regeneration_type_name in _NATURAL_REGENERATION_TYPES:
        intercept = 4.3328
        coef_q = -0.0076
        coef_ln_q = 1.2245
        coef_height_dm = 0.0
        coef_ln_height = -0.2822
        coef_q_over_hind = 0.0
        coef_ln_si = 0.0
        coef_wet = 0.1693
        coef_dry = -0.1295
        coef_udim_lnq = 0.1969
        variance = 0.1334
        bias = 1.093
    elif regeneration_type_name == "sown":
        intercept = 5.48811
        coef_q = 0.0
        coef_ln_q = 0.4274
        coef_height_dm = 0.0086
        coef_ln_height = 0.0
        coef_q_over_hind = 0.1341
        coef_ln_si = 0.0
        coef_wet = 0.2865
        coef_dry = 0.0
        coef_udim_lnq = 0.1741
        variance = 0.1291
        bias = 1.063
    elif regeneration_type_name == "pine_plantation":
        intercept = 0.8869
        coef_q = -0.0252
        coef_ln_q = 1.7140
        coef_height_dm = 0.0070
        coef_ln_height = 0.0
        coef_q_over_hind = 0.1935
        coef_ln_si = 0.2665
        coef_wet = 0.1589
        coef_dry = -0.0944
        coef_udim_lnq = 0.1907
        variance = 0.1420
        bias = 1.103
    elif regeneration_type_name == "spruce_plantation":
        intercept = 3.9939
        coef_q = -0.0157
        coef_ln_q = 0.9207
        coef_height_dm = 0.0172
        coef_ln_height = 0.0
        coef_q_over_hind = 0.2477
        coef_ln_si = 0.0
        coef_wet = 0.1696
        coef_dry = 0.0
        coef_udim_lnq = 0.1944
        variance = 0.1455
        bias = 1.117
    elif regeneration_type_name in _CONTORTA_DECIDUOUS_PLANTATION_TYPES:
        intercept = 4.5904
        coef_q = 0.0
        coef_ln_q = 0.6144
        coef_height_dm = 0.0
        coef_ln_height = 0.0
        coef_q_over_hind = 0.1687
        coef_ln_si = 0.0
        coef_wet = 0.0
        coef_dry = -0.1350
        coef_udim_lnq = 0.2444
        variance = 0.0920
        bias = 1.077
    else:
        raise ValueError(f"Unsupported regeneration_type: {regeneration_type_name!r}")

    temp = (
        intercept
        + coef_q * q
        + coef_ln_q * ln_q
        + coef_height_dm * height_dm
        + coef_ln_height * ln_height
        + coef_q_over_hind * (q / height_indicator_dm)
        + coef_ln_si * ln_si
        + coef_wet * wet
        + coef_dry * dry
        + coef_udim_lnq * (under_dimension_prob * ln_q)
    )
    if deterministic:
        return exp(temp) * bias - 1.0
    return exp(temp + noise * sqrt(variance)) - 1.0


def proportion_conifer(  # pragma: no cover - legacy formula
    *,
    regeneration_type: RegenerationTypeName | str,
    q: float,
    ln_qind: float,
    stem_total: float,
    ln_si: float,
    wet: int,
    dry: int,
    rich: int,
    poor: int,
    deterministic: bool = True,
    noise: float = 0.0,
) -> float:
    """Step 2 NYSKOG equation: conifer proportion of total stems."""
    regeneration_type_name = getattr(regeneration_type, "value", regeneration_type)

    if regeneration_type_name in _NATURAL_REGENERATION_TYPES:
        intercept = -3.5301
        coef_q = 0.0
        coef_ln_qind = 2.3451
        coef_stem_total = -0.00011
        coef_ln_si = -1.5062
        coef_wet = -0.6372
        coef_dry = 0.8493
        coef_rich = 0.0
        coef_poor = 0.0
        variance = 3.6327
        bias = 0.904
    elif regeneration_type_name == "sown":
        intercept = 17.2044
        coef_q = 0.1035
        coef_ln_qind = -5.2596
        coef_stem_total = -0.00018
        coef_ln_si = 0.0
        coef_wet = 0.0
        coef_dry = 0.0
        coef_rich = -0.3590
        coef_poor = 0.6612
        variance = 3.7452
        bias = 0.889
    elif regeneration_type_name == "pine_plantation":
        intercept = -11.9666
        coef_q = 0.0
        coef_ln_qind = 3.2567
        coef_stem_total = -0.00014
        coef_ln_si = 0.0
        coef_wet = -0.8526
        coef_dry = 0.6199
        coef_rich = 0.0
        coef_poor = 0.0
        variance = 4.8840
        bias = 0.918
    elif regeneration_type_name == "spruce_plantation":
        intercept = -6.0583
        coef_q = 0.0
        coef_ln_qind = 1.9416
        coef_stem_total = -0.00014
        coef_ln_si = 0.0
        coef_wet = 0.0
        coef_dry = 0.0
        coef_rich = 0.0
        coef_poor = 0.0
        variance = 4.0676
        bias = 0.882
    elif regeneration_type_name == "contorta_plantation":
        intercept = -13.6254
        coef_q = 0.0
        coef_ln_qind = 3.7771
        coef_stem_total = -0.00027
        coef_ln_si = 0.0
        coef_wet = 0.0
        coef_dry = 0.4915
        coef_rich = 0.0
        coef_poor = 0.0
        variance = 4.0106
        bias = 0.892
    else:
        return 0.0

    temp = (
        intercept
        + coef_q * q
        + coef_ln_qind * ln_qind
        + coef_stem_total * stem_total
        + coef_ln_si * ln_si
        + coef_wet * wet
        + coef_dry * dry
        + coef_rich * rich
        + coef_poor * poor
    )
    if deterministic:
        tmp = exp(temp)
        return (tmp / (tmp + 1.0)) * bias
    # pyforestry uses the true residual-variance index for the Step-2 stochastic
    # sigma (e.g. 3.6327 for natural regeneration). Only the stochastic path is
    # affected; the deterministic path above is unaffected.
    tmp = exp(temp + noise * sqrt(variance))
    return tmp / (tmp + 1.0)


def dominant_conifer_share(  # pragma: no cover - legacy formula
    *,
    regeneration_type: RegenerationTypeName | str,
    qind: float,
    ln_si: float,
    wet: int,
    dry: int,
    rich: int,
    poor: int,
    hwod: int,
    hwd: int,
    shrubs: int,
    lichen: int,
    deterministic: bool = True,
    noise: float = 0.0,
) -> float:
    """Step 3 NYSKOG equation: dominant conifer share within conifers."""
    ln_qind = log(qind)
    regeneration_type_name = getattr(regeneration_type, "value", regeneration_type)

    if regeneration_type_name in _NATURAL_REGENERATION_TYPES:
        intercept = -7.9523
        coef_ln_qind = 1.8529
        coef_pl_spruce = 0.0
        coef_ln_si = 0.0
        coef_wet = 0.0
        coef_dry = 1.2180
        coef_rich = 0.0
        coef_poor = 0.0
        coef_hwod = -1.3832
        coef_hwd = -0.4425
        coef_shrubs = 1.1268
        coef_lichen = 2.1238
        variance = 5.6084
        bias = 0.937
    elif regeneration_type_name == "sown":
        intercept = -12.7319
        coef_ln_qind = 3.4089
        coef_pl_spruce = 0.0
        coef_ln_si = 0.0
        coef_wet = 0.0
        coef_dry = 0.0
        coef_rich = 0.0
        coef_poor = 0.0
        coef_hwod = -1.8143
        coef_hwd = -0.8255
        coef_shrubs = 0.5712
        coef_lichen = 0.9929
        variance = 9.0704
        bias = 0.828
    elif regeneration_type_name == "pine_plantation":
        intercept = -8.6426
        coef_ln_qind = 2.4374
        coef_pl_spruce = -3.2733
        coef_ln_si = 0.0
        coef_wet = -0.6729
        coef_dry = 0.8271
        coef_rich = 0.0
        coef_poor = 0.0
        coef_hwod = 0.0
        coef_hwd = 0.0
        coef_shrubs = 0.0
        coef_lichen = 1.1508
        variance = 8.5676
        bias = 0.832
    elif regeneration_type_name == "spruce_plantation":
        intercept = 4.8204
        coef_ln_qind = 1.0575
        coef_pl_spruce = 0.0
        coef_ln_si = 0.0
        coef_wet = 0.0
        coef_dry = 0.0
        coef_rich = 0.0
        coef_poor = 0.0
        coef_hwod = 1.0575
        coef_hwd = 0.3764
        coef_shrubs = -2.0587
        coef_lichen = -2.0208
        variance = 6.2259
        bias = 0.893
    else:
        intercept = 1.8124
        coef_ln_qind = 0.0
        coef_pl_spruce = 0.0
        coef_ln_si = 0.0
        coef_wet = 0.0
        coef_dry = 0.0
        coef_rich = 0.0
        coef_poor = 0.0
        coef_hwod = 0.0
        coef_hwd = 0.0
        coef_shrubs = 0.0
        coef_lichen = 0.0
        variance = 4.0225
        bias = 0.826

    temp = (
        intercept
        + coef_ln_qind * ln_qind
        + coef_pl_spruce * 0.0
        + coef_ln_si * ln_si
        + coef_wet * wet
        + coef_dry * dry
        + coef_rich * rich
        + coef_poor * poor
        + coef_hwod * hwod
        + coef_hwd * hwd
        + coef_shrubs * shrubs
        + coef_lichen * lichen
    )
    if deterministic:
        tmp = exp(temp)
        return (tmp / (tmp + 1.0)) * bias
    tmp = exp(temp + noise * sqrt(variance))
    return tmp / (tmp + 1.0)


def secondary_mean_height(  # pragma: no cover - legacy formula
    *,
    regeneration_type: RegenerationTypeName | str,
    secondary_species: TreeName,
    site_index_m: float,
    mean_height_main_m: float,
    herb: int,
    dry: int,
    wet: int,
    deterministic: bool = True,
    noise: float = 0.0,
) -> float:
    """Step 4A NYSKOG equation: mean height for secondary species."""
    is_spruce = secondary_species in _SPRUCE_SPECIES
    is_pine = secondary_species in _PINE_SPECIES
    regeneration_type_name = getattr(regeneration_type, "value", regeneration_type)

    if regeneration_type_name == "contorta_plantation":
        if is_pine:
            intercept = 2.9042
            coef_ln_h = -0.7510
            coef_si = 0.0
            coef_ln_si = -0.8629
            coef_herb = 0.0
            coef_dry = 0.0
            coef_wet = 0.0
            variance = 0.0931
            bias = 1.06
        elif is_spruce:
            intercept = 0.6600
            coef_ln_h = -1.2462
            coef_si = 0.0
            coef_ln_si = 0.0
            coef_herb = 0.0
            coef_dry = 0.0
            coef_wet = 0.0
            variance = 0.1818
            bias = 1.06
        else:
            intercept = 1.8398
            coef_ln_h = -1.6750
            coef_si = 0.0
            coef_ln_si = 0.0
            coef_herb = 0.0
            coef_dry = 0.0
            coef_wet = 0.0
            variance = 0.1461
            bias = 1.08
    elif regeneration_type_name == "pine_plantation":
        if is_spruce:
            intercept = 0.4598
            coef_ln_h = -1.2752
            coef_si = 0.0222
            coef_ln_si = 0.0
            coef_herb = 0.0
            coef_dry = 0.0
            coef_wet = 0.0
            variance = 0.0969
            bias = 1.06
        else:
            intercept = 0.9896
            coef_ln_h = -1.0873
            coef_si = 0.0
            coef_ln_si = 0.0
            coef_herb = 0.1435
            coef_dry = -0.1917
            coef_wet = 0.0
            variance = 0.1639
            bias = 1.08
    elif regeneration_type_name == "spruce_plantation":
        if is_pine:
            intercept = 3.8108
            coef_ln_h = -1.0346
            coef_si = 0.0
            coef_ln_si = -0.9054
            coef_herb = 0.0
            coef_dry = 0.0
            coef_wet = 0.0
            variance = 0.0973
            bias = 1.06
        else:
            intercept = 2.1372
            coef_ln_h = -1.0943
            coef_si = 0.0
            coef_ln_si = -0.2628
            coef_herb = 0.0
            coef_dry = 0.0
            coef_wet = 0.0
            variance = 0.1261
            bias = 1.08
    elif regeneration_type_name in _NATURAL_REGENERATION_TYPES:
        if is_spruce:
            intercept = 0.2296
            coef_ln_h = -0.9488
            coef_si = 0.0
            coef_ln_si = 0.0200
            coef_herb = 0.0
            coef_dry = 0.0
            coef_wet = 0.0
            variance = 0.1257
            bias = 1.06
        else:
            intercept = 0.5086
            coef_ln_h = -1.0196
            coef_si = 0.0
            coef_ln_si = 0.0301
            coef_herb = 0.0
            coef_dry = -0.1075
            coef_wet = 0.1458
            variance = 0.1576
            bias = 1.08
    elif regeneration_type_name == "sown":
        if is_spruce:
            intercept = 0.4598
            coef_ln_h = -1.2752
            coef_si = 0.0222
            coef_ln_si = 0.0
            coef_herb = 0.0
            coef_dry = 0.0
            coef_wet = 0.0
            variance = 0.0969
            bias = 1.06
        else:
            intercept = 0.9896
            coef_ln_h = -1.0873
            coef_si = 0.0
            coef_ln_si = 0.0
            coef_herb = 0.1435
            coef_dry = -0.1917
            coef_wet = 0.0
            variance = 0.1639
            bias = 1.08
    else:
        intercept = 0.9896
        coef_ln_h = -1.0873
        coef_si = 0.0
        coef_ln_si = 0.0
        coef_herb = 0.1435
        coef_dry = -0.1917
        coef_wet = 0.0
        variance = 0.1639
        bias = 1.08

    ln_h = log(mean_height_main_m)
    ln_si = log(site_index_m)
    temp = (
        intercept
        + coef_ln_h * ln_h
        + coef_si * site_index_m
        + coef_ln_si * ln_si
        # pyforestry activates the herb term on herb-rich sites per the published
        # model (the herb indicator enters the secondary-species mean height).
        + coef_herb * herb
        + coef_dry * dry
        + coef_wet * wet
    )
    if deterministic:
        rel_h = exp(temp) * bias
    else:
        rel_h = exp(temp + noise * sqrt(variance))
    return rel_h * mean_height_main_m


def height_variation(  # pragma: no cover - legacy formula
    *,
    species: TreeName,
    species_height_m: float,
    q: float,
    ln_q: float,
    self_rejuvenated: int,
    deterministic: bool = True,
    noise: float = 0.0,
    min_cv: float = 0.1,
    max_cv: float = 1.0,
) -> float:
    """Step 4B NYSKOG equation: height variation (CV)."""
    if species is TreeSpecies.Sweden.pinus_contorta:
        intercept = 0.4902
        coef_height = -0.05924
        coef_q = -0.00113
        coef_ln_q = 0.0
        coef_self_rejuv = 0.0
        variance = 0.00250
    elif species in _PINE_SPECIES:
        intercept = 0.3242
        coef_height = -0.12590
        coef_q = -0.00928
        coef_ln_q = 0.2684
        coef_self_rejuv = 0.03563
        variance = 0.02382
    elif species in _SPRUCE_SPECIES:
        intercept = 1.1065
        coef_height = -0.09513
        coef_q = -0.00483
        coef_ln_q = 0.0
        coef_self_rejuv = 0.02813
        variance = 0.03487
    else:
        intercept = 0.8290
        coef_height = -0.07222
        coef_q = -0.00249
        coef_ln_q = 0.0
        coef_self_rejuv = 0.0
        variance = 0.03348

    temp = (
        intercept
        + coef_height * species_height_m
        + coef_q * q
        + coef_ln_q * ln_q
        + coef_self_rejuv * self_rejuvenated
    )
    cvh = temp if deterministic else temp + noise * sqrt(variance)
    return max(min_cv, min(min(species_height_m, max_cv), cvh))


def weibull_parameters(  # pragma: no cover - legacy formula
    *,
    species: TreeName,
    cvh: float,
    mean_height_m: float,
) -> tuple[float, float]:
    """Step 5 NYSKOG equation: Weibull scale (beta) and shape (lambda)."""
    if mean_height_m <= 0.0 or cvh <= 0.0:
        return 0.0, 0.0
    ln_cvh = log(cvh)
    ln_h = log(mean_height_m)

    if species is TreeSpecies.Sweden.pinus_contorta:
        beta_intercept = 0.41484
        beta_coef_h = 1.06154
        beta_coef_ln_h = 0.0
        beta_coef_cvh = -0.15508
        beta_coef_ln_cvh = 0.20504

        lambda_intercept = 0.34883
        lambda_coef_ln_h = 0.19180
        lambda_coef_cvh = -0.62607
        lambda_coef_ln_cvh = -0.84180
        lambda_bias = 0.041
    elif species in _PINE_SPECIES:
        beta_intercept = 1.30058
        beta_coef_h = 1.08544
        beta_coef_ln_h = 0.0
        beta_coef_cvh = -1.55305
        beta_coef_ln_cvh = 0.63942

        lambda_intercept = 0.32591
        lambda_coef_ln_h = -0.02888
        lambda_coef_cvh = -0.42790
        lambda_coef_ln_cvh = -0.95373
        lambda_bias = 0.060
    elif species in _SPRUCE_SPECIES:
        beta_intercept = 1.31357
        beta_coef_h = 1.07955
        beta_coef_ln_h = 0.0
        beta_coef_cvh = -1.52749
        beta_coef_ln_cvh = 0.63053

        lambda_intercept = 0.32605
        lambda_coef_ln_h = -0.02401
        lambda_coef_cvh = -0.34569
        lambda_coef_ln_cvh = -0.98817
        lambda_bias = 0.047
    else:
        beta_intercept = 1.12188
        beta_coef_h = 1.08160
        beta_coef_ln_h = 0.0
        beta_coef_cvh = -1.30002
        beta_coef_ln_cvh = 0.51977

        lambda_intercept = 0.26635
        lambda_coef_ln_h = 0.01323
        lambda_coef_cvh = -0.29358
        lambda_coef_ln_cvh = -0.96208
        lambda_bias = 0.055

    beta = (
        beta_intercept
        + beta_coef_h * mean_height_m
        + beta_coef_ln_h * ln_h
        + beta_coef_cvh * cvh
        + beta_coef_ln_cvh * ln_cvh
    )

    temp = (
        lambda_intercept
        + lambda_coef_ln_h * ln_h
        + lambda_coef_cvh * cvh
        + lambda_coef_ln_cvh * ln_cvh
    )
    lamb = exp(temp + lambda_bias)
    return beta, lamb


def _deciduous_proportions(  # pragma: no cover - legacy lookup table
    nfi_region: NfiRegionName | str,
) -> tuple[float, float]:
    """Return ``(birch_share, other_broadleaf_share)`` for an NFI region."""
    nfi_region_name = getattr(nfi_region, "value", nfi_region)
    if nfi_region_name == "Reg1":
        return 0.96, 0.04
    if nfi_region_name == "Reg21":
        return 0.92, 0.08
    if nfi_region_name == "Reg22":
        return 0.90, 0.10
    if nfi_region_name == "Reg3":
        return 0.96, 0.04
    if nfi_region_name == "Reg4":
        return 0.90, 0.10
    return 0.84, 0.16


def stems_per_species(  # pragma: no cover - legacy formula
    *,
    regeneration_type: RegenerationTypeName | str,
    species_to_plant: TreeName,
    stem_total: float,
    prop_conifer: float,
    prop_dom_conifer: float,
    site_index_m: float,
    nfi_region: NfiRegionName | str,
) -> dict[str, float]:
    """Step 3 NYSKOG equation: resolve stems per species group."""
    conifer_stems = stem_total * prop_conifer
    decid_stems = stem_total * (1.0 - prop_conifer)

    regeneration_type_name = getattr(regeneration_type, "value", regeneration_type)
    prop_pine = prop_larch = prop_contorta = prop_spruce = 0.0
    if regeneration_type_name in {"natural_regeneration", "extensive", "sown"}:
        if species_to_plant is TreeSpecies.Sweden.pinus_contorta:
            prop_contorta = prop_dom_conifer
            prop_pine = max(0.0, 0.1312 - 0.00941 * site_index_m)
            prop_spruce = 1.0 - prop_contorta - prop_pine
        elif species_to_plant in _LARCH_SPECIES:
            prop_larch = prop_dom_conifer
            prop_spruce = 1.0 - prop_larch
        elif species_to_plant in _PINE_SPECIES:
            prop_pine = prop_dom_conifer
            prop_spruce = 1.0 - prop_pine
        elif species_to_plant in _SPRUCE_SPECIES:
            prop_pine = prop_dom_conifer
            prop_spruce = 1.0 - prop_pine
        else:
            prop_pine = prop_dom_conifer
            prop_spruce = 1.0 - prop_pine
    elif regeneration_type_name == "pine_plantation":
        if species_to_plant in _LARCH_SPECIES:
            prop_larch = prop_dom_conifer
        elif species_to_plant in _PINE_SPECIES:
            prop_pine = prop_dom_conifer
        prop_spruce = 1.0 - prop_pine - prop_larch
    elif regeneration_type_name == "spruce_plantation":
        prop_spruce = prop_dom_conifer
        prop_pine = 1.0 - prop_spruce
    elif regeneration_type_name == "contorta_plantation":
        prop_contorta = prop_dom_conifer
        prop_pine = max(0.0, 0.1312 - 0.00941 * site_index_m)
        prop_spruce = 1.0 - prop_contorta - prop_pine

    stems = {
        "pine": conifer_stems * prop_pine,
        "spruce": conifer_stems * prop_spruce,
        "contorta": conifer_stems * prop_contorta,
        "larch": conifer_stems * prop_larch,
    }

    birch_prop, other_prop = _deciduous_proportions(nfi_region)
    stems["birch"] = decid_stems * birch_prop
    stems["other_broadleaf"] = decid_stems * other_prop
    return stems


def reconstruct_summary(  # pragma: no cover - legacy workflow
    *,
    asinw: float,
    mean_height_main_m: float,
    site_index_m: float,
    regeneration_type: RegenerationTypeName | str,
    species_to_plant: TreeName,
    nfi_region: NfiRegionName | str,
    field_layer: Optional[Sweden.FieldLayer] = None,
    soil_moisture: Optional[Sweden.SoilMoistureEnum] = None,
    indicators: Optional[dict[str, int]] = None,
    deterministic: bool = True,
    noise: float = 0.0,
    rng: Optional[float] = None,
) -> dict[str, Any]:
    """Run the full NYSKOG reconstruction workflow and return summary outputs."""
    if indicators is None:
        indicators = nyskog_indicators_from_site(
            field_layer=field_layer,
            soil_moisture=soil_moisture,
        )

    wet = int(indicators.get("wet", 0))
    dry = int(indicators.get("dry", 0))
    rich = int(indicators.get("rich", 0))
    poor = int(indicators.get("poor", 0))
    shrubs = int(indicators.get("shrubs", 0))
    lichen = int(indicators.get("lichen", 0))
    herb = int(indicators.get("herb", 0))
    hwd = int(indicators.get("hwd", 0))
    hwod = int(indicators.get("hwod", 0))

    main_species_key = _species_key(species_to_plant)
    if mean_height_main_m <= 0.0 or site_index_m <= 0.0:
        return {
            "q": 0.0,
            "qind": 0.0,
            "udim": 0.0,
            "stem_total": 0.0,
            "prop_conifer": 0.0,
            "prop_dom_conifer": 0.0,
            "stems_per_species": {},
            "mean_heights_m": {},
            "cvh": {},
            "weibull_params": {},
            "main_species_key": main_species_key,
        }

    q = production_potential_q(asinw)
    if q <= 0.0:
        return {
            "q": q,
            "qind": 0.0,
            "udim": 0.0,
            "stem_total": 0.0,
            "prop_conifer": 0.0,
            "prop_dom_conifer": 0.0,
            "stems_per_species": {},
            "mean_heights_m": {},
            "cvh": {},
            "weibull_params": {},
            "main_species_key": main_species_key,
        }

    ln_q = log(q)
    qind = max(45.0, q)
    ln_qind = log(qind)
    ln_si = log(site_index_m)
    regeneration_type_name = getattr(regeneration_type, "value", regeneration_type)

    udim = udim_probability(q, deterministic=deterministic, rng=rng)
    stem_total = total_stems(
        regeneration_type=regeneration_type_name,
        mean_height_main_m=mean_height_main_m,
        q=q,
        ln_q=ln_q,
        ln_si=ln_si,
        under_dimension_prob=udim,
        wet=wet,
        dry=dry,
        height_indicator_dm=max(15.0, 10.0 * mean_height_main_m),
        deterministic=deterministic,
        noise=noise,
    )
    prop_conifer = proportion_conifer(
        regeneration_type=regeneration_type_name,
        q=q,
        ln_qind=ln_qind,
        stem_total=stem_total,
        ln_si=ln_si,
        wet=wet,
        dry=dry,
        rich=rich,
        poor=poor,
        deterministic=deterministic,
        noise=noise,
    )
    prop_dom_conifer = dominant_conifer_share(
        regeneration_type=regeneration_type_name,
        qind=qind,
        ln_si=ln_si,
        wet=wet,
        dry=dry,
        rich=rich,
        poor=poor,
        hwod=hwod,
        hwd=hwd,
        shrubs=shrubs,
        lichen=lichen,
        deterministic=deterministic,
        noise=noise,
    )
    stems = stems_per_species(
        regeneration_type=regeneration_type_name,
        species_to_plant=species_to_plant,
        stem_total=stem_total,
        prop_conifer=prop_conifer,
        prop_dom_conifer=prop_dom_conifer,
        site_index_m=site_index_m,
        nfi_region=nfi_region,
    )

    mean_heights: dict[str, float] = {key: 0.0 for key in stems}
    cvh: dict[str, float] = {key: 0.0 for key in stems}
    weibull: dict[str, tuple[float, float]] = {key: (0.0, 0.0) for key in stems}
    self_rejuv = int(regeneration_type_name in _NATURAL_REGENERATION_TYPES)

    for key in stems:
        species = _REPRESENTATIVE_SPECIES.get(key)
        if species is None:
            continue
        if key == main_species_key:
            mean_h = mean_height_main_m
        else:
            mean_h = secondary_mean_height(
                regeneration_type=regeneration_type_name,
                secondary_species=species,
                site_index_m=site_index_m,
                mean_height_main_m=mean_height_main_m,
                herb=herb,
                dry=dry,
                wet=wet,
                deterministic=deterministic,
                noise=noise,
            )
        mean_heights[key] = mean_h

        cv_val = height_variation(
            species=species,
            species_height_m=mean_h,
            q=q,
            ln_q=ln_q,
            self_rejuvenated=self_rejuv,
            deterministic=deterministic,
            noise=noise,
        )
        cvh[key] = cv_val
        weibull[key] = weibull_parameters(
            species=species,
            cvh=cv_val,
            mean_height_m=mean_h,
        )

    return {
        "q": q,
        "qind": qind,
        "udim": udim,
        "stem_total": stem_total,
        "prop_conifer": prop_conifer,
        "prop_dom_conifer": prop_dom_conifer,
        "stems_per_species": stems,
        "mean_heights_m": mean_heights,
        "cvh": cvh,
        "weibull_params": weibull,
        "main_species_key": main_species_key,
    }


@dataclass(frozen=True)
class HuginMeanHeightKernel:
    """Mapping-style kernel for Hugin mean-height calculations.

    Reference:
        Elfving, B. (1982). Hugins ungskogstaxering 1976-1979. SLU, Projekt
        Hugin, Rapport 27 (§2.2, mean-height development in young stands).
    """

    name: str = "hugin_mean_height"
    version: str = "1.0.0"
    units_contract: Mapping[str, str] = field(
        default_factory=lambda: {
            "age_years": "years",
            "site_index_pine_m": "m",
            "site_index_spruce_m": "m",
        }
    )

    def compute(self, inputs: Mapping[str, Any]) -> Mapping[str, float]:
        """Evaluate the kernel and return ``{\"mean_height_m\": ...}``."""
        value = mean_height(
            age_years=float(inputs["age_years"]),
            species=inputs["species"],
            site_index_pine_m=float(inputs["site_index_pine_m"]),
            site_index_spruce_m=float(inputs["site_index_spruce_m"]),
        )
        return {"mean_height_m": float(value)}


@dataclass(frozen=True)
class HuginCropTreeProbabilityKernel:
    """Mapping-style kernel for Hugin crop-tree probability.

    Reference:
        Elfving, B. (1982). Hugins ungskogstaxering 1976-1979. SLU, Projekt
        Hugin, Rapport 27 (§2.1, prioritizing trees at pre-commercial thinning).
    """

    name: str = "hugin_crop_tree_probability"
    version: str = "1.0.0"
    units_contract: Mapping[str, str] = field(
        default_factory=lambda: {
            "height_m": "m",
            "mean_height_m": "m",
            "conifer_stems_per_100m2": "count_100m2",
            "rec_stems_per_ha": "count_ha",
        }
    )

    def compute(self, inputs: Mapping[str, Any]) -> Mapping[str, float]:
        """Evaluate the kernel and return ``{\"crop_tree_probability\": ...}``."""
        value = crop_tree_probability(
            height_m=float(inputs["height_m"]),
            mean_height_m=float(inputs["mean_height_m"]),
            conifer_stems_per_100m2=float(inputs["conifer_stems_per_100m2"]),
            rec_stems_per_ha=float(inputs["rec_stems_per_ha"]),
            coniferous=bool(inputs["coniferous"]),
        )
        return {"crop_tree_probability": float(value)}


__all__ = [
    "HuginCropTreeProbabilityKernel",
    "HuginMeanHeightKernel",
    "crop_tree_probability",
    "mean_age",
    "mean_height",
    "nyskog_indicators_from_site",
    "probabilities_from_tree_list",
    "proportion_conifer",
    "reconstruct_summary",
    "secondary_mean_height",
    "young_stand_quality_asinw",
    "production_potential_q",
    "site_index_for_species",
    "stems_per_species",
    "dominant_conifer_share",
    "total_stems",
    "udim_probability",
    "height_variation",
    "weibull_parameters",
]
