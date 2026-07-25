"""Species cohort classes and factory for the Eko 1985 stand model.

Each cohort subclass implements the species-specific volume, mortality,
and basal-area increment equations from Ekö (1985).

Source:
    Ekö, P.-M. (1985). *En produktionsmodell för skog i Sverige, baserad på bestånd
    från riksskogstaxeringens provytor = A growth simulator for Swedish forests,
    based on data from the national forest survey.* Sveriges lantbruksuniversitet,
    institutionen för skogsskötsel, Rapport nr 16, Umeå.
"""

from __future__ import annotations

from math import exp
from typing import TYPE_CHECKING

from pyforestry.base.helpers import TreeName, TreeSpecies
from pyforestry.sweden.blocks.eko1985.engine import EngineStandPart
from pyforestry.sweden.blocks.eko1985.site_context import (
    EkoStandSite,
    _safe_log,
)

if TYPE_CHECKING:
    from pyforestry.sweden.blocks.eko1985.model import Eko1985Cohort


def _engine_cohort_factory(cohort: Eko1985Cohort, site: EkoStandSite):
    """Return an engine cohort instance for the given species or None."""
    species = cohort.species
    if species in {TreeSpecies.Sweden.picea_abies}:
        return SpruceEngineCohort(
            float(cohort.basal_area),
            float(cohort.stems),
            float(cohort.age),
            stand=None,
            site=site,
            species=species,
        )
    if species in {TreeSpecies.Sweden.pinus_sylvestris, TreeSpecies.Sweden.pinus_contorta}:
        return PineEngineCohort(
            float(cohort.basal_area),
            float(cohort.stems),
            float(cohort.age),
            stand=None,
            site=site,
            species=species,
        )
    genus = species.genus.name.lower()
    if genus == "betula":
        return BirchEngineCohort(
            float(cohort.basal_area),
            float(cohort.stems),
            float(cohort.age),
            stand=None,
            site=site,
            species=species,
        )
    if genus == "fagus":
        return BeechEngineCohort(
            float(cohort.basal_area),
            float(cohort.stems),
            float(cohort.age),
            stand=None,
            site=site,
            species=species,
        )
    if genus == "quercus":
        return OakEngineCohort(
            float(cohort.basal_area),
            float(cohort.stems),
            float(cohort.age),
            stand=None,
            site=site,
            species=species,
        )
    return BroadleafEngineCohort(
        float(cohort.basal_area),
        float(cohort.stems),
        float(cohort.age),
        stand=None,
        site=site,
        species=species,
    )


class SpruceEngineCohort(EngineStandPart):
    """Spruce cohort ported from the legacy EkoSpruce formulas."""

    MORT_INDEX = 1

    def __init__(
        self,
        ba,
        stems,
        age,
        stand,
        site,
        species: TreeName | str | None = None,
    ):
        """Create a spruce cohort tied to the given site."""
        super().__init__(
            ba,
            stems,
            age,
            species or TreeSpecies.Sweden.picea_abies,
            site,
        )
        if stand is not None:
            self.register_stand(stand)

    def get_volume(self, ba=None, qmd=None, age=None, stems=None, hk=None):
        """Compute spruce volume for the given stand state."""
        if self.stand is None:
            raise ValueError("Volume calculator requires stand connected.")
        ba = self.ba if ba is None else ba
        qmd = self.qmd if qmd is None else qmd
        age = self.age if age is None else age
        stems = self.stems if stems is None else stems
        hk = self.hk if hk is None else hk
        SIdm = self._site_index_dm()
        if self.Site.region == "North":
            b1 = -0.065
            b2 = -2.05
            F4age = 1 - exp(b1 * age)
            F4basal_area = 1 - exp(b2 * ba)
            lnVolume = (
                +0.362521e-02 * ba
                + 1.35682 * _safe_log(ba)
                - 1.47258 * (qmd / 100.0)  # Dg in metres (Eko 1985 p.61)
                - 0.438770 * F4basal_area
                + 1.46910 * F4age
                - 0.314730 * _safe_log(stems)
                + 0.228700 * _safe_log(SIdm)
                + 0.118700e-01 * self.Site.thinned
                + 0.254896e-02 * hk
                + 1.970094
            )
            return exp(lnVolume + 0.0388)
        if self.Site.region == "Central":
            b1 = -0.065
            b2 = -2.05
            F4age = 1 - exp(b1 * age)
            F4basal_area = 1 - exp(b2 * ba)
            lnVolume = (
                +1.28359 * _safe_log(ba)
                - 0.380690 * F4basal_area
                + 1.21756 * F4age
                - 0.216690 * _safe_log(stems)
                + 0.350370 * _safe_log(SIdm)
                + 0.413000e-01 * self.Site.herbs_grasses_no_field_layer
                + 0.362100e-01 * self.Site.thinned
                + 0.268645e-02 * hk
                + 0.700490
            )
            return exp(lnVolume + 0.0563)
        b1 = -0.04
        b2 = -2.05
        F4age = 1 - exp(b1 * age)
        F4basal_area = 1 - exp(b2 * ba)
        lnVolume = (
            +1.22886 * _safe_log(ba)
            - 0.349820 * F4basal_area
            + 0.485170 * F4age
            - 0.152050 * _safe_log(stems)
            + 0.337640 * _safe_log(SIdm)
            + 0.129800e-01 * self.Site.thinned
            + 0.548055e-03 * hk
            + 0.584600
        )
        return exp(lnVolume + 0.0325)

    def get_bai5(self, ba_quotient_chronic_mortality=0.0, ba_quotient_acute_mortality=0.0):
        """Compute spruce basal-area increment over five years."""
        if self.stand is None:
            raise ValueError("BAI calculator requires stand connected.")
        SIdm = self._site_index_dm()
        if self.Site.region == "North":
            independent_vars = (
                -0.767477 * ba_quotient_chronic_mortality
                + -0.514297 * ba_quotient_acute_mortality
                + -1.43974 * (self.qmd / 100.0)  # Dg in metres (Eko 1985 p.61)
                + -0.386338e-02 * self.hk
                + 0.204732 * self.Site.fertilised
                + 0.186343 * self.Site.herbs_grasses_no_field_layer
                + 0.392021e-01 * self.Site.Bilberry_or_Cowberry
                + -0.807207e-01 * self.Site.dry_soil
                + 0.833252
            )
            if SIdm < 160:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.736655e-02 * self.ba
                        + 0.875788 * _safe_log(self.ba)
                        - 0.642060e-04 * self.stems
                        + 0.125396 * _safe_log(self.stems)
                        + 0.159356e-02 * self.age
                        - 0.764340 * _safe_log(self.age)
                        - 0.594334e-02 * self.ba_other_species
                    )
                else:
                    dependent_vars = (
                        -0.187226e-01 * self.ba
                        + 0.855970 * _safe_log(self.ba)
                        + 0.106942e-03 * self.stems
                        + 0.107612 * _safe_log(self.stems)
                        + 0.321033e-02 * self.age
                        - 0.737062 * _safe_log(self.age)
                        - 0.206053e-01 * self.ba_other_species
                    )
            elif SIdm < 200:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.191493e-01 * self.ba
                        + 0.942389 * _safe_log(self.ba)
                        - 0.145476e-03 * self.stems
                        + 0.158511 * _safe_log(self.stems)
                        + 0.289628e-02 * self.age
                        - 0.804217 * _safe_log(self.age)
                        - 0.125949e-01 * self.ba_other_species
                    )
                else:
                    dependent_vars = (
                        -0.255254e-01 * self.ba
                        + 0.955380 * _safe_log(self.ba)
                        - 0.642149e-04 * self.stems
                        + 0.164265 * _safe_log(self.stems)
                        + 0.554025e-02 * self.age
                        - 0.866520 * _safe_log(self.age)
                        - 0.889755e-02 * self.ba_other_species
                    )
            else:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.210737e-01 * self.ba
                        + 0.932275 * _safe_log(self.ba)
                        - 0.572335e-04 * self.stems
                        + 0.152017 * _safe_log(self.stems)
                        + 0.342622e-02 * self.age
                        - 0.811183 * _safe_log(self.age)
                        - 0.905176e-02 * self.ba_other_species
                    )
                else:
                    dependent_vars = (
                        -0.133941e-01 * self.ba
                        + 0.837783 * _safe_log(self.ba)
                        - 0.245946e-03 * self.stems
                        + 0.205142 * _safe_log(self.stems)
                        + 0.602419e-02 * self.age
                        - 0.862195 * _safe_log(self.age)
                        - 0.135941e-01 * self.ba_other_species
                    )
            self.bai5 = exp(dependent_vars + independent_vars + 0.0564)
            return
        if self.Site.region == "Central":
            independent_vars = (
                -1.16597 * ba_quotient_chronic_mortality
                + -0.299327 * ba_quotient_acute_mortality
                + 0.783806e-01 * self.Site.thinned_5y
                + 0.572131e-01 * self.Site.herbs_grasses_no_field_layer
                + -0.112938e-01 * self.Site.wet_soil
                + 0.546176e-01 * self.Site.latitude
                + 0.332621e-01 * self.Site.tax77
            )
            if SIdm < 180:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.802837e-02 * self.ba
                        + 0.751220 * _safe_log(self.ba)
                        - 0.800241e-04 * self.stems
                        + 0.239814 * _safe_log(self.stems)
                        - 0.148757e-02 * self.age
                        - 0.476534 * _safe_log(self.age)
                        - 0.308451e-01 * self.ba_other_species
                        - 4.02484
                    )
                else:
                    dependent_vars = (
                        -0.330623e-01 * self.ba
                        + 1.06539 * _safe_log(self.ba)
                        + 0.145290e-03 * self.stems
                        + 0.422450e-01 * _safe_log(self.stems)
                        + 0.110998e-01 * self.age
                        - 1.71468 * _safe_log(self.age)
                        - 0.236447e-01 * self.ba_other_species
                        + 1.06383
                    )
            elif SIdm < 220:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.211171e-01 * self.ba
                        + 0.837241 * _safe_log(self.ba)
                        - 0.800241e-04 * self.stems
                        + 0.239814 * _safe_log(self.stems)
                        + 0.492578e-02 * self.age
                        - 0.839650 * _safe_log(self.age)
                        - 0.269523e-02 * self.ba_other_species
                        - 2.91926
                    )
                else:
                    dependent_vars = (
                        -0.180419e-01 * self.ba
                        + 0.943986 * _safe_log(self.ba)
                        + 0.145290e-03 * self.stems
                        + 0.422450e-01 * _safe_log(self.stems)
                        + 0.525585e-02 * self.age
                        - 0.982261 * _safe_log(self.age)
                        - 0.786807e-02 * self.ba_other_species
                        - 1.56544
                    )
            elif SIdm < 260:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.263745e-01 * self.ba
                        + 0.915196 * _safe_log(self.ba)
                        - 0.800241e-04 * self.stems
                        + 0.239814 * _safe_log(self.stems)
                        + 0.384471e-02 * self.age  # +age: ProdMod2 SPRUCE_BAI[C][unthin][2]
                        - 0.847753 * _safe_log(self.age)
                        - 0.252559e-01 * self.ba_other_species
                        - 2.85518  # K is negative (Eko 1985 Tabell 4e, 220<=SI<260)
                    )
                else:
                    dependent_vars = (
                        -0.217674e-01 * self.ba
                        + 0.847682 * _safe_log(self.ba)
                        - 0.145290e-03 * self.stems
                        + 0.422450e-01 * _safe_log(self.stems)
                        + 0.101626e-01 * self.age
                        - 1.37782 * _safe_log(self.age)
                        - 0.268779e-01 * self.ba_other_species
                        + 0.178428
                    )
            else:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.244742e-01 * self.ba
                        + 0.787195 * _safe_log(self.ba)
                        - 0.800241e-04 * self.stems
                        + 0.239814 * _safe_log(self.stems)
                        - 0.371613e-02 * self.age  # -age: ProdMod2 SPRUCE_BAI[C][unthin][3]
                        - 0.561641 * _safe_log(self.age)
                        - 0.298097e-01 * self.ba_other_species
                        - 3.17570
                    )
                else:
                    dependent_vars = (
                        -0.239679e-01 * self.ba
                        + 0.924765 * _safe_log(self.ba)
                        + 0.145290e-03 * self.stems
                        + 0.422450e-01 * _safe_log(self.stems)
                        + 0.631561e-03 * self.age
                        - 0.893401 * _safe_log(self.age)
                        - 0.908286e-02 * self.ba_other_species
                        - 1.46143
                    )
            self.bai5 = exp(dependent_vars + independent_vars + 0.0712)
            return
        independent_vars = (
            -0.780391 * ba_quotient_chronic_mortality
            + -0.252170 * ba_quotient_acute_mortality
            + -0.318464e-01 * self.Site.thinned_5y
            + 0.778093e-01 * self.Site.fertilised
            + 0.127135e-02 * SIdm
            + 0.262484e-01 * self.Site.herbs_grasses_no_field_layer
            + -0.736690e-01 * self.Site.dry_soil
            + -0.269193e-01 * self.Site.latitude
            + -0.959785e-01 * self.Site.tax77
        )
        if SIdm < 220:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.149200e-01 * self.ba
                    + 0.794859 * _safe_log(self.ba)
                    - 0.120956e-03 * self.stems
                    + 0.255053 * _safe_log(self.stems)
                    - 0.720252 * _safe_log(self.age)
                    - 0.229139e-01 * self.ba_other_species
                    + 1.52732
                )
            else:
                dependent_vars = (
                    -0.227763e-01 * self.ba
                    + 0.838105 * _safe_log(self.ba)
                    + 0.519813e-03 * self.stems
                    + 0.141232 * _safe_log(self.stems)
                    - 0.722723 * _safe_log(self.age)
                    - 0.237689e-01 * self.ba_other_species
                    + 1.93218
                )
        elif SIdm < 260:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.167127e-01 * self.ba
                    + 0.794738 * _safe_log(self.ba)
                    - 0.923244e-04 * self.stems
                    + 0.279717 * _safe_log(self.stems)
                    - 0.790588 * _safe_log(self.age)
                    - 0.187801e-01 * self.ba_other_species
                    + 1.67230
                )
            else:
                dependent_vars = (
                    -0.167448e-01 * self.ba
                    + 0.835811 * _safe_log(self.ba)
                    - 0.995431e-04 * self.stems
                    + 0.258612 * _safe_log(self.stems)
                    - 0.931549 * _safe_log(self.age)
                    - 0.167010e-01 * self.ba_other_species
                    + 2.34225
                )
        elif SIdm < 300:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.221875e-01 * self.ba
                    + 0.832287 * _safe_log(self.ba)
                    - 0.110872e-03 * self.stems
                    + 0.271386 * _safe_log(self.stems)
                    - 0.735989 * _safe_log(self.age)
                    - 0.196143e-01 * self.ba_other_species
                    + 1.50310
                )
            else:
                dependent_vars = (
                    -0.203970e-01 * self.ba
                    + 0.836890 * _safe_log(self.ba)
                    - 0.755155e-04 * self.stems
                    + 0.248563 * _safe_log(self.stems)
                    - 0.716504 * _safe_log(self.age)
                    - 0.151436e-01 * self.ba_other_species
                    + 1.50719
                )
        else:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.243263e-01 * self.ba
                    + 0.902730 * _safe_log(self.ba)
                    - 0.706319e-04 * self.stems
                    + 0.198283 * _safe_log(self.stems)
                    - 0.713230 * _safe_log(self.age)
                    - 0.135840e-01 * self.ba_other_species
                    + 1.71136
                )
            else:
                dependent_vars = (
                    -0.218319e-01 * self.ba
                    + 0.855200 * _safe_log(self.ba)
                    - 0.176554e-03 * self.stems
                    + 0.269091 * _safe_log(self.stems)
                    - 0.765104 * _safe_log(self.age)
                    - 0.180257e-01 * self.ba_other_species
                    + 1.62508
                )
        self.bai5 = exp(dependent_vars + independent_vars + 0.0737)


class PineEngineCohort(EngineStandPart):
    """Pine cohort ported from the legacy EkoPine formulas."""

    MORT_INDEX = 0

    def __init__(
        self,
        ba,
        stems,
        age,
        stand,
        site,
        species: TreeName | str | None = None,
    ):
        """Create a pine cohort tied to the given site."""
        super().__init__(
            ba,
            stems,
            age,
            species or TreeSpecies.Sweden.pinus_sylvestris,
            site,
        )
        if stand is not None:
            self.register_stand(stand)

    def _default_site_index_m(self) -> float:
        """Pine uses H100 pine (dm) as its site index (Eko 1985 p.61)."""
        return float(self.Site.H100_Pine or 0.0)

    def get_volume(self, ba=None, qmd=None, age=None, stems=None, hk=None):
        """Compute pine volume for the given stand state."""
        if self.stand is None:
            raise ValueError("Volume calculator requires stand connected.")
        ba = self.ba if ba is None else ba
        qmd = self.qmd if qmd is None else qmd
        age = self.age if age is None else age
        stems = self.stems if stems is None else stems
        hk = self.hk if hk is None else hk
        SIdm = self._site_index_dm()
        if self.Site.region == "North":
            b1 = -0.06
            b2 = -2.3
            F4age = 1 - exp(b1 * age)
            F4basal_area = 1 - exp(b2 * ba)
            lnVolume = (
                +1.24296 * _safe_log(ba)
                - 0.472530 * F4basal_area
                + 1.05864 * F4age
                - 0.170140 * _safe_log(stems)
                + 0.247550 * _safe_log(SIdm)
                + 0.213800e-01 * self.Site.thinned
                + 0.295300e-01 * self.Site.thinned_5y
                + 0.510332e-02 * hk
                + 1.08339
            )
            return exp(lnVolume + 0.0275)
        if self.Site.region == "Central":
            b1 = -0.06
            b2 = -2.2
            F4age = 1 - exp(b1 * age)
            F4basal_area = 1 - exp(b2 * ba)
            lnVolume = (
                +0.778157e-02 * ba
                + 1.14159 * _safe_log(ba)
                + 0.927460 * F4age
                - 0.166730 * _safe_log(stems)
                + 0.304900 * _safe_log(SIdm)
                + 0.270200e-01 * self.Site.thinned
                + 0.292836e-02 * hk
                + 0.910330
            )
            return exp(lnVolume + 0.0273)
        b1 = -0.075
        b2 = -2.2
        F4age = 1 - exp(b1 * age)
        F4basal_area = 1 - exp(b2 * ba)
        lnVolume = (
            +1.21272 * _safe_log(ba)
            - 0.299900 * F4basal_area
            + 1.01970 * F4age
            - 0.172300 * _safe_log(stems)
            + 0.369930 * _safe_log(SIdm)
            + 1.65136 * _safe_log(self.Site.latitude)
            + 0.349200e-01 * _safe_log(self.Site.altitude)
            - 0.197100e-01 * self.Site.herbs_grasses_no_field_layer
            + 0.229100e-01 * self.Site.thinned
            + 0.526017e-02 * hk
            - 6.46337
        )
        return exp(lnVolume + 0.0260)

    def get_bai5(self, ba_quotient_chronic_mortality=0.0, ba_quotient_acute_mortality=0.0):
        """Compute pine basal-area increment over five years."""
        if self.stand is None:
            raise ValueError("BAI calculator requires stand connected.")
        SIdm = self._site_index_dm()
        if self.Site.region == "North":
            independent_vars = (
                -0.598419 * ba_quotient_chronic_mortality
                + -0.486198 * ba_quotient_acute_mortality
                + -0.952624e-02 * self.hk
                + 0.674527e-01 * self.Site.thinned_5y
                + 0.100135 * self.Site.herbs_grasses_no_field_layer
                + -0.104076 * self.Site.wet_soil
                + -0.329437e-01 * _safe_log(self.Site.altitude)
                + 0.526479e-01 * self.Site.tax77
                + 0.164446
            )
            if SIdm < 160:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.342051e-01 * self.ba
                        + 0.757840 * _safe_log(self.ba)
                        - 0.161442e-03 * self.stems
                        + 0.367048 * _safe_log(self.stems)
                        + 0.313386e-02 * self.age
                        - 0.842335 * _safe_log(self.age)
                        - 0.157312e-01 * self.ba_other_species
                    )
                else:
                    dependent_vars = (
                        -0.222808e-01 * self.ba
                        + 0.707173 * _safe_log(self.ba)
                        - 0.407064e-03 * self.stems
                        + 0.386522 * _safe_log(self.stems)
                        + 0.309020e-02 * self.age
                        - 0.840856 * _safe_log(self.age)
                        - 0.168721e-01 * self.ba_other_species
                    )
            elif SIdm < 200:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.264194e-01 * self.ba
                        + 0.759517 * _safe_log(self.ba)
                        - 0.172838e-03 * self.stems
                        + 0.354319 * _safe_log(self.stems)
                        + 0.282339e-02 * self.age
                        - 0.830969 * _safe_log(self.age)
                        - 0.920265e-02 * self.ba_other_species
                    )
                else:
                    dependent_vars = (
                        -0.215557e-01 * self.ba
                        + 0.678298 * _safe_log(self.ba)
                        - 0.223194e-03 * self.stems
                        + 0.345910 * _safe_log(self.stems)
                        + 0.230893e-02 * self.age
                        - 0.759426 * _safe_log(self.age)
                        - 0.129081e-01 * self.ba_other_species
                    )
            else:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.242773e-01 * self.ba
                        + 0.743286 * _safe_log(self.ba)
                        - 0.127080e-03 * self.stems
                        + 0.328240 * _safe_log(self.stems)
                        + 0.203892e-02 * self.age
                        - 0.756105 * _safe_log(self.age)
                        - 0.136312e-01 * self.ba_other_species
                    )
                else:
                    dependent_vars = (
                        -0.100435e-01 * self.ba
                        + 0.659451 * _safe_log(self.ba)
                        - 0.181913e-03 * self.stems
                        + 0.369130 * _safe_log(self.stems)
                        + 0.227817e-02 * self.age
                        - 0.793134 * _safe_log(self.age)
                        - 0.817145e-02 * self.ba_other_species
                    )
            self.bai5 = exp(dependent_vars + independent_vars + 0.0645)
            return
        if self.Site.region == "Central":
            independent_vars = (
                -0.757422 * ba_quotient_chronic_mortality
                + -0.819721 * ba_quotient_acute_mortality
                + -0.156937e-01 * self.hk
                + 0.657419e-01 * self.Site.fertilised
                + 0.208293e-02 * SIdm
                + 0.393424e-01 * self.Site.herbs_grasses_no_field_layer
                + -0.787040e-01 * self.Site.dry_soil
                + 0.952773e-01 * self.Site.tax77
                - 0.466279
            )
            if SIdm < 180:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.247769e-01 * self.ba
                        + 0.739123 * _safe_log(self.ba)
                        - 0.724080e-04 * self.stems
                        + 0.307962 * _safe_log(self.stems)
                        + 0.213813e-02 * self.age
                        - 0.730167 * _safe_log(self.age)
                        - 0.304936e-02 * self.ba_other_species
                    )
                else:
                    dependent_vars = (
                        -0.454216e-01 * self.ba
                        + 0.967594 * _safe_log(self.ba)
                        + 0.134748e-03 * self.stems
                        + 0.106405 * _safe_log(self.stems)
                        + 0.322181e-02 * self.age
                        - 0.559074 * _safe_log(self.age)
                        - 0.146382e-01 * self.ba_other_species
                    )
            elif SIdm < 220:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.204976e-01 * self.ba
                        + 0.710569 * _safe_log(self.ba)
                        - 0.331436e-04 * self.stems
                        + 0.318007 * _safe_log(self.stems)
                        + 0.186999e-02 * self.age
                        - 0.732359 * _safe_log(self.age)
                        - 0.488064e-02 * self.ba_other_species
                    )
                else:
                    dependent_vars = (
                        +0.144234e-01 * self.ba
                        + 0.304194 * _safe_log(self.ba)
                        - 0.111460e-02 * self.stems
                        + 0.628499 * _safe_log(self.stems)
                        + 0.545633e-02 * self.age
                        - 0.977317 * _safe_log(self.age)
                        - 0.126636e-01 * self.ba_other_species
                    )
            else:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.242132e-01 * self.ba
                        + 0.746931 * _safe_log(self.ba)
                        - 0.120517e-03 * self.stems
                        + 0.327216 * _safe_log(self.stems)
                        + 0.254795e-02 * self.age
                        - 0.758639 * _safe_log(self.age)
                        - 0.978754e-02 * self.ba_other_species
                    )
                else:
                    dependent_vars = (
                        -0.126617e-01 * self.ba
                        + 0.599420 * _safe_log(self.ba)
                        - 0.405408e-03 * self.stems
                        + 0.472836 * _safe_log(self.stems)
                        + 0.455547e-02 * self.age
                        - 0.895734 * _safe_log(self.age)
                        - 0.106365e-01 * self.ba_other_species
                    )
            self.bai5 = exp(dependent_vars + independent_vars + 0.0507)
            return
        independent_vars = (
            -1.04202 * ba_quotient_chronic_mortality
            + -0.637943 * ba_quotient_acute_mortality
            + -1.75160 * (self.qmd / 100.0)  # Dg in metres (Eko 1985 p.61)
            + -0.592599e-02 * self.hk
            + 0.637421e-01 * self.Site.thinned_5y
            + 0.462966e-01 * self.Site.fertilised
            + 0.522489e-01 * self.Site.herbs_grasses_no_field_layer
            + -0.702839e-01 * self.Site.dry_soil
            + -0.111568e-01 * self.Site.latitude
            + -0.466973e-01 * self.Site.tax77
        )
        if SIdm < 160:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.497800e-01 * self.ba
                    + 1.19990 * _safe_log(self.ba)
                    + 0.114548e-04 * self.stems
                    + 0.164713 * _safe_log(self.stems)
                    - 0.884162e-03 * self.age
                    - 0.564604 * _safe_log(self.age)
                    - 0.153879e-01 * self.ba_other_species
                    + 0.579562
                )
            else:
                dependent_vars = (
                    -0.302305e-01 * self.ba
                    + 0.938947 * _safe_log(self.ba)
                    + 0.563241e-03 * self.stems
                    + 0.148914 * _safe_log(self.stems)
                    + 0.419586e-02 * self.age
                    - 1.15586 * _safe_log(self.age)
                    - 0.138465e-01 * self.ba_other_species
                    + 2.72773
                )
        elif SIdm < 200:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.123212e-01 * self.ba
                    + 0.864851 * _safe_log(self.ba)
                    - 0.497769e-04 * self.stems
                    + 0.200066 * _safe_log(self.stems)
                    + 0.211976e-02 * self.age
                    - 0.821163 * _safe_log(self.age)
                    - 0.941390e-02 * self.ba_other_species
                    + 1.59527
                )
            else:
                dependent_vars = (
                    -0.216126e-02 * self.ba
                    + 0.938131 * _safe_log(self.ba)
                    - 0.169034e-03 * self.stems
                    + 0.621225e-01 * _safe_log(self.stems)
                    + 0.305833e-02 * self.age
                    - 1.18279 * _safe_log(self.age)
                    - 0.439063e-03 * self.ba_other_species
                    + 3.39954
                )
        elif SIdm < 240:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.107718e-01 * self.ba
                    + 0.796896 * _safe_log(self.ba)
                    - 0.975686e-04 * self.stems
                    + 0.230066 * _safe_log(self.stems)
                    - 0.577520e-03 * self.age
                    - 0.570857 * _safe_log(self.age)
                    - 0.155230e-01 * self.ba_other_species
                    + 0.784527
                )
            else:
                dependent_vars = (
                    -0.632941e-02 * self.ba
                    + 0.767710 * _safe_log(self.ba)
                    - 0.173551e-03 * self.stems
                    + 0.173044 * _safe_log(self.stems)
                    + 0.163026e-02 * self.age
                    - 0.945376 * _safe_log(self.age)
                    - 0.133437e-01 * self.ba_other_species
                    + 2.49514
                )
        else:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.738511e-02 * self.ba
                    + 0.809028 * _safe_log(self.ba)
                    - 0.207393e-03 * self.stems
                    + 0.199179 * _safe_log(self.stems)
                    + 0.259619e-03 * self.age
                    - 0.663161 * _safe_log(self.age)
                    - 0.142082e-01 * self.ba_other_species
                    + 1.27892
                )
            else:
                dependent_vars = (
                    -0.207497e-01 * self.ba
                    + 1.00931 * _safe_log(self.ba)
                    - 0.653755e-05 * self.stems
                    + 0.851371e-01 * _safe_log(self.stems)
                    - 0.307386e-02 * self.age
                    - 0.635182 * _safe_log(self.age)
                    - 0.110970e-01 * self.ba_other_species
                    + 1.57124
                )
        self.bai5 = exp(dependent_vars + independent_vars + 0.0636)


class BirchEngineCohort(EngineStandPart):
    """Birch cohort ported from the legacy EkoBirch formulas."""

    MORT_INDEX = 2

    def _bai_diameter_caps(self):
        """ProdMod2 BIRCH_DIAMETER_COEFFS basal-area / stem limits for the BAI inputs."""
        si = self._bai_class_si_dm()
        if self.Site.region in ("North", "Central"):
            cls = 0 if si < 140 else 1 if si < 180 else 2 if si < 220 else 3
            caps = (
                [(20.0, 2400.0), (20.0, 2800.0), (20.0, 2800.0), (20.0, 2000.0)]
                if not self.Site.thinned
                else [(12.0, 1600.0), (12.0, 1600.0), (20.0, 1600.0), (20.0, 1200.0)]
            )
        else:
            cls = 0 if si < 220 else 1 if si < 260 else 2 if si < 300 else 3
            caps = (
                [(16.0, 2400.0), (20.0, 2800.0), (24.0, 2400.0), (28.0, 2800.0)]
                if not self.Site.thinned
                else [(12.0, 1600.0), (12.0, 1200.0), (16.0, 1200.0), (24.0, 1200.0)]
            )
        return caps[cls]

    def __init__(
        self,
        ba,
        stems,
        age,
        stand,
        site,
        species: TreeName | str | None = None,
    ):
        """Create a birch cohort tied to the given site."""
        super().__init__(
            ba,
            stems,
            age,
            species or TreeSpecies.Sweden.betula_pendula,
            site,
        )
        if stand is not None:
            self.register_stand(stand)

    def get_volume(self, ba=None, qmd=None, age=None, stems=None, hk=None):
        """Compute birch volume for the given stand state.

        Ekö 1985 Tabell 10c publishes two volume functions for birch -- område
        Nord+Mellan and område Syd (per §8.2.1 only North and Central are pooled;
        South is fitted separately). Both are transcribed faithfully and, by default,
        the canonical dissertation function for the cohort's region is used (unlike
        the övrigt löv Syd function, birch's Syd function stays physical).

        The recovered ProdMod2 program instead applies the Nord+Mellan function to
        *every* region for birch: its volume-coefficient table is region-identical at
        INDEX_BIRCH, exactly as for övrigt löv (INDEX_OTHER). Setting
        ``broadleaf_volume_prodmod`` on the site reproduces that -- the Nord+Mellan
        function is then used in the South too. See
        :meth:`BroadleafEngineCohort.get_volume` for the full rationale and sources.
        """
        if self.stand is None:
            raise ValueError("Volume calculator requires stand connected.")
        ba = self.ba if ba is None else ba
        qmd = self.qmd if qmd is None else qmd
        age = self.age if age is None else age
        stems = self.stems if stems is None else stems
        hk = self.hk if hk is None else hk
        SIdm = self._site_index_dm()

        # Ekö 1985 Tabell 10c, område Nord+Mellan. Used for North/Central always, and
        # for every region when ``broadleaf_volume_prodmod`` selects ProdMod2 behaviour.
        if self.Site.broadleaf_volume_prodmod or self.Site.region in ("North", "Central"):
            b1 = -0.035
            b2 = -2.05
            F4age = 1 - exp(b1 * age)
            F4basal_area = 1 - exp(b2 * ba)
            lnVolume = (
                +1.26244 * _safe_log(ba)
                - 0.459580 * F4basal_area
                + 0.540420 * F4age
                - 0.176040 * _safe_log(stems)
                + 0.201360 * _safe_log(SIdm)
                - 1.68251 * _safe_log(self.Site.latitude)
                - 0.404000e-01 * _safe_log(self.Site.altitude)
                + 0.757200e-01 * self.Site.fertilised
                + 0.301200e-01 * self.Site.thinned
                + 0.401844e-02 * hk
                + 8.44862
            )
            return exp(lnVolume + 0.0755)

        # Ekö 1985 Tabell 10c, område Syd (canonical dissertation default for South).
        b1 = -0.07
        b2 = -2.1
        F4age = 1 - exp(b1 * age)
        F4basal_area = 1 - exp(b2 * ba)
        lnVolume = (
            -0.786906e-02 * ba
            + 1.35254 * _safe_log(ba)
            - 1.30862 * (qmd / 100.0)  # Dg in metres (Eko 1985 p.61)
            - 0.524630 * F4basal_area
            + 1.01779 * F4age
            - 0.254630 * _safe_log(stems)
            + 0.204880 * _safe_log(SIdm)
            + 2.75025 * _safe_log(self.Site.latitude)
            + 0.774000e-01 * self.Site.fertilised
            + 0.434800e-01 * self.Site.thinned
            + 0.250449e-02 * hk
            - 9.38127
        )
        return exp(lnVolume + 0.0595)

    def get_bai5(self, ba_quotient_chronic_mortality=0.0, ba_quotient_acute_mortality=0.0):
        """Compute birch basal-area increment over five years."""
        if self.stand is None:
            raise ValueError("BAI calculator requires stand connected.")
        SIdm = self._bai_class_si_dm()  # H100 spruce (non-pine); boundary-nudged under flag

        if self.Site.region in ("North", "Central"):
            independent_vars = (
                -0.474848 * ba_quotient_chronic_mortality
                + -0.207333 * ba_quotient_acute_mortality
                + -0.202362e-02 * self.hk
                + 0.914442e-01 * self.Site.thinned_5y
                + 0.176843 * self.Site.fertilised
                + 0.256714 * self.Site.herbs_grasses_no_field_layer
                + -0.488706e-01 * self.Site.wet_soil
                + -0.139928e-01 * self.Site.latitude
                + -0.462992e-03 * self.Site.altitude  # ALT (Eko 1985 Tabell 4g)
                + 0.189383 * self.Site.tax77
            )
            if SIdm < 140:
                if not self.Site.thinned:
                    dependent_vars = (
                        +0.281210e-02 * self.ba
                        + 0.718062 * _safe_log(self.ba)
                        - 0.264120e-03 * self.stems
                        + 0.360947 * _safe_log(self.stems)
                        - 0.513560 * _safe_log(self.age)
                        - 0.146581e-01 * self.ba_other_species
                        - 0.768510
                    )
                else:
                    dependent_vars = (
                        +0.856585e-01 * self.ba
                        + 0.488507 * _safe_log(self.ba)
                        - 0.549010e-03 * self.stems
                        + 0.467588 * _safe_log(self.stems)
                        - 0.618645 * _safe_log(self.age)
                        - 0.477226e-02 * self.ba_other_species
                        - 0.768510
                    )
            elif SIdm < 180:
                if not self.Site.thinned:
                    dependent_vars = (
                        +0.831133e-02 * self.ba
                        + 0.660201 * _safe_log(self.ba)
                        - 0.161770e-03 * self.stems
                        + 0.361272 * _safe_log(self.stems)
                        - 0.609806 * _safe_log(self.age)
                        - 0.133204e-01 * self.ba_other_species
                        - 0.355882
                    )
                else:
                    dependent_vars = (
                        +0.665931e-02 * self.ba
                        + 0.700295 * _safe_log(self.ba)
                        - 0.221485e-03 * self.stems
                        + 0.316196 * _safe_log(self.stems)
                        - 0.489888 * _safe_log(self.age)
                        - 0.246752e-01 * self.ba_other_species
                        - 0.355882
                    )
            elif SIdm < 220:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.371203e-02 * self.ba
                        + 0.835899 * _safe_log(self.ba)
                        - 0.141238e-03 * self.stems
                        + 0.221611 * _safe_log(self.stems)
                        - 0.732659 * _safe_log(self.age)
                        - 0.131446e-01 * self.ba_other_species
                        + 0.891049
                    )
                else:
                    dependent_vars = (
                        -0.134251e-02 * self.ba
                        + 0.838751 * _safe_log(self.ba)
                        - 0.237653e-03 * self.stems
                        + 0.192259 * _safe_log(self.stems)
                        - 0.707746 * _safe_log(self.age)
                        - 0.499067e-02 * self.ba_other_species
                        + 0.891049
                    )
            else:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.281602e-01 * self.ba
                        + 0.800357 * _safe_log(self.ba)
                        + 0.673284e-04 * self.stems
                        + 0.205233 * _safe_log(self.stems)
                        - 0.631139 * _safe_log(self.age)
                        - 0.176494e-01 * self.ba_other_species
                        + 0.731245
                    )
                else:
                    dependent_vars = (
                        -0.177526e-01 * self.ba
                        + 0.814686 * _safe_log(self.ba)
                        + 0.781625e-04 * self.stems
                        + 0.183532 * _safe_log(self.stems)
                        - 0.593656 * _safe_log(self.age)
                        - 0.211444e-01 * self.ba_other_species
                        + 0.731245
                    )
            self.bai5 = exp(dependent_vars + independent_vars + 0.1642)
            return

        independent_vars = (
            -0.617367 * ba_quotient_chronic_mortality
            + -0.350920 * ba_quotient_acute_mortality
            + -0.134245e-02 * self.hk
            + 0.277904 * self.Site.fertilised
            + 0.154562 * self.Site.herbs_grasses_no_field_layer
            + 0.554711e-01 * self.Site.tax77
        )
        if SIdm < 220:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.850224e-02 * self.ba
                    + 0.931518 * _safe_log(self.ba)
                    - 0.874696e-04 * self.stems
                    + 0.124964 * _safe_log(self.stems)
                    - 0.890226e-02 * self.age
                    - 0.498825 * _safe_log(self.age)
                    - 0.493910e-02 * self.ba_other_species
                    - 0.135041
                )
            else:
                dependent_vars = (
                    +0.144427 * self.ba
                    + 0.332109 * _safe_log(self.ba)
                    - 0.457988e-03 * self.stems
                    + 0.474159 * _safe_log(self.stems)
                    + 0.922378e-02 * self.age
                    - 1.50315 * _safe_log(self.age)
                    - 0.116043e-01 * self.ba_other_species
                    + 1.19213
                )
        elif SIdm < 260:
            if not self.Site.thinned:
                dependent_vars = (
                    +0.129783e-01 * self.ba
                    + 0.688150 * _safe_log(self.ba)
                    - 0.158067e-03 * self.stems
                    + 0.304149 * _safe_log(self.stems)
                    + 0.411176e-02 * self.age
                    - 0.864501 * _safe_log(self.age)
                    - 0.533730e-02 * self.ba_other_species
                    - 0.135041
                )
            else:
                dependent_vars = (
                    -0.235447e-01 * self.ba
                    + 0.962877 * _safe_log(self.ba)
                    + 0.103737e-03 * self.stems
                    + 0.186790 * _safe_log(self.stems)
                    - 0.127109e-02 * self.age
                    - 1.02854 * _safe_log(self.age)
                    - 0.849201e-02 * self.ba_other_species
                    + 1.19213
                )
        elif SIdm < 300:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.110984e-01 * self.ba
                    + 0.748193 * _safe_log(self.ba)
                    - 0.434390e-04 * self.stems
                    + 0.270476 * _safe_log(self.stems)
                    + 0.823613e-03 * self.age
                    - 0.718419 * _safe_log(self.age)
                    - 0.174522e-01 * self.ba_other_species
                    - 0.135041
                )
            else:
                dependent_vars = (
                    -0.438786e-03 * self.ba
                    + 0.818427 * _safe_log(self.ba)
                    - 0.304146e-03 * self.stems
                    + 0.241055 * _safe_log(self.stems)
                    + 0.106700e-01 * self.age
                    - 1.16385 * _safe_log(self.age)
                    - 0.1978220e-01 * self.ba_other_species
                    + 1.19213
                )
        else:
            if not self.Site.thinned:
                dependent_vars = (
                    -0.204315e-01 * self.ba
                    + 0.792798 * _safe_log(self.ba)
                    - 0.179026e-03 * self.stems
                    + 0.316913 * _safe_log(self.stems)
                    + 0.262117e-02 * self.age
                    - 0.791796 * _safe_log(self.age)
                    - 0.146037e-01 * self.ba_other_species
                    - 0.135041
                )
            else:
                dependent_vars = (
                    +0.255898e-02 * self.ba
                    + 0.730671 * _safe_log(self.ba)
                    + 0.256307e-04 * self.stems
                    + 0.256131 * _safe_log(self.stems)
                    + 0.126785e-01 * self.age
                    - 1.24005 * _safe_log(self.age)
                    - 0.341768e-02 * self.ba_other_species
                    + 1.19213
                )
        self.bai5 = exp(dependent_vars + independent_vars + 0.1590)


class BroadleafEngineCohort(EngineStandPart):
    """Implementation for the grouped 'other broadleaf' cohort."""

    MORT_INDEX = 5

    def _bai_diameter_caps(self):
        """ProdMod2 OTHER_DIAMETER_COEFFS basal-area / stem limits for the BAI inputs."""
        si = self._bai_class_si_dm()
        if self.Site.region in ("North", "Central"):
            cls = 0 if si < 160 else 1 if si < 200 else 2 if si < 240 else 3
            caps = [(16.0, 2000.0), (16.0, 2000.0), (16.0, 2400.0), (24.0, 3200.0)]
        else:
            cls = 0 if si < 240 else 1 if si < 280 else 2 if si < 320 else 3
            caps = [(24.0, 2400.0), (24.0, 2800.0), (36.0, 3200.0), (40.0, 2800.0)]
        return caps[cls]

    def __init__(
        self,
        ba,
        stems,
        age,
        stand,
        site,
        species: TreeName | str | None = None,
    ):
        """Create an 'other broadleaf' cohort tied to the given site."""
        super().__init__(
            ba,
            stems,
            age,
            species or TreeSpecies.Sweden.alnus_glutinosa,
            site,
        )
        if stand is not None:
            self.register_stand(stand)

    def get_volume(self, ba=None, qmd=None, age=None, stems=None, hk=None):
        """Compute 'other broadleaf' (övrigt löv) volume for the given stand state.

        Ekö 1985 Tabell 10f publishes two volume functions for övrigt löv -- one for
        område Nord+Mellan and one for område Syd (per §8.2.1 only North and Central
        are pooled; South is fitted separately). Both are transcribed faithfully
        here, and by default the canonical dissertation function for the cohort's
        region is used.

        Caveat on the Syd function: it carries a TG (total stand basal area, all
        species) term, ``+0.859600e-01 * TG`` (Tabell 10f Syd, std. error 24 %),
        entering as ``exp(0.859600e-01 * TG)``. Övrigt löv volume is thereby
        modelled to climb steeply with total stand density, so a small broadleaf
        cohort inside a dense mixed stand extrapolates far outside the
        (sparse-broadleaf) data Ekö fitted: e.g. TG = 35.5 m2/ha alone scales the
        estimate by e**3.05 ~= 21x, a ~140 m form height at BA 7. The coefficient is
        a verified transcription of the scan (``0.859600E-01``, sharing the E-01
        exponent of its GALL1/ln(ALT) neighbours) -- not a typo on our side; whether
        Ekö's printed E-01 should read E-02 cannot be confirmed, as the recovered
        ProdMod2 program never implements the Syd function to cross-check.

        ProdMod2 instead applies the Nord+Mellan function to *every* region for
        övrigt löv: its volume-coefficient table is byte-identical across
        localisation 0/1/2 at INDEX_OTHER (SpeciesData/Growth/
        get_species_growth_coefficients.cpp, consumed by SpeciesData_485edc.cpp),
        while the same decompiler keeps the per-region spruce/pine rows distinct, so
        the collapse is deliberate. Setting ``broadleaf_volume_prodmod`` on the site
        (``Eko1985SiteContext.broadleaf_volume_prodmod`` /
        ``EkoStandSite.broadleaf_volume_prodmod``) reproduces that behaviour -- the
        Nord+Mellan function is then used in the South too, giving physical form
        heights. The default (False) keeps the canonical dissertation Syd function.
        The same flag likewise routes birch (Tabell 10c) through its Nord+Mellan
        function, which ProdMod2 pools identically; see ``BirchEngineCohort.get_volume``.
        (Beech and oak have a single volume function each, so they are unaffected.)
        """
        if self.stand is None:
            raise ValueError("Volume calculator requires stand connected.")
        ba = self.ba if ba is None else ba
        qmd = self.qmd if qmd is None else qmd
        age = self.age if age is None else age
        stems = self.stems if stems is None else stems
        hk = self.hk if hk is None else hk
        SIdm = self._site_index_dm()

        # Ekö 1985 Tabell 10f, område Nord+Mellan. Used for North/Central always, and
        # for every region when ``broadleaf_volume_prodmod`` selects ProdMod2 behaviour.
        if self.Site.broadleaf_volume_prodmod or self.Site.region in ("North", "Central"):
            b1 = -0.04
            b2 = -2.3
            F4age = 1 - exp(b1 * age)
            F4basal_area = 1 - exp(b2 * ba)
            ln_volume = (
                1.26649 * _safe_log(ba)
                - 0.580030 * F4basal_area
                + 0.486310 * F4age
                - 0.172050 * _safe_log(stems)
                + 0.174930 * _safe_log(SIdm)
                - 1.51968 * _safe_log(self.Site.latitude)
                - 0.368300e-01 * _safe_log(self.Site.altitude)
                + 0.547400e-01 * self.Site.thinned
                + 0.417126e-02 * hk
                + 7.79034
            )
            return exp(ln_volume + 0.0853)

        # Ekö 1985 Tabell 10f, område Syd (canonical dissertation default for South).
        # The +0.859600e-01*TG term (TG = total stand basal area) drives non-physical
        # form heights for a broadleaf cohort in a dense mixed stand -- see docstring.
        b1 = -0.075
        b2 = -2.1
        F4age = 1 - exp(b1 * age)
        F4basal_area = 1 - exp(b2 * ba)
        ln_volume = (
            -0.148700e-01 * ba
            + 1.29359 * _safe_log(ba)
            - 0.784820 * F4basal_area
            + 1.18741 * F4age
            - 0.135830 * _safe_log(stems)
            + 0.219890 * _safe_log(SIdm)
            + 2.02656 * _safe_log(self.Site.latitude)
            + 0.242500e-01 * self.Site.thinned
            + 0.859600e-01 * self.stand.stand_ba  # TG = total stand basal area (Tabell 10f)
            + 0.509488e-03 * hk
            - 7.50102  # K constant is negative (Eko 1985 Tabell 10f, område syd)
        )
        return exp(ln_volume + 0.0671)

    def get_bai5(self, ba_quotient_chronic_mortality=0.0, ba_quotient_acute_mortality=0.0):
        """Compute broadleaf basal-area increment over five years."""
        if self.stand is None:
            raise ValueError("BAI calculator requires stand connected.")
        SIdm = self._bai_class_si_dm()  # H100 spruce (non-pine); boundary-nudged under flag

        if self.Site.region in ("North", "Central"):
            independent_vars = (
                -0.345933 * ba_quotient_chronic_mortality
                - 0.138015 * self.Site.herbs_grasses_no_field_layer
                - 0.650878e-01 * self.Site.Bilberry_or_Cowberry
                - 0.175149e-01 * self.Site.latitude
                - 0.570035e-03 * self.Site.altitude
                + 0.151318 * self.Site.tax77
            )
            if SIdm < 160:
                if not self.Site.thinned:
                    dependent_vars = (
                        +0.865166e-01 * self.ba
                        + 0.755603 * _safe_log(self.ba)
                        - 0.806548e-03 * self.stems
                        + 0.275974 * _safe_log(self.stems)
                        - 0.540881e-02 * self.age
                        - 0.117056 * _safe_log(self.age)
                        - 0.187866e-01 * self.ba_other_species
                        - 1.18519
                    )
                else:
                    dependent_vars = (
                        +0.865166e-01 * self.ba
                        + 0.755603 * _safe_log(self.ba)
                        - 0.806548e-03 * self.stems
                        + 0.275974 * _safe_log(self.stems)
                        - 0.540881e-02 * self.age
                        - 0.117056 * _safe_log(self.age)
                        - 0.187866e-01 * self.ba_other_species
                        - 0.952398
                    )
            elif SIdm < 200:
                if not self.Site.thinned:
                    dependent_vars = (
                        -0.129773e-01 * self.ba
                        + 0.989525 * _safe_log(self.ba)
                        - 0.715363e-04 * self.stems
                        + 0.490676e-01 * _safe_log(self.stems)
                        + 0.218728e-02 * self.age
                        - 0.944317 * _safe_log(self.age)
                        - 0.143834e-01 * self.ba_other_species
                        + 2.78296
                    )
                else:
                    dependent_vars = (
                        -0.129773e-01 * self.ba
                        + 0.989525 * _safe_log(self.ba)
                        - 0.715363e-04 * self.stems
                        + 0.490676e-01 * _safe_log(self.stems)
                        + 0.218728e-02 * self.age
                        - 0.944317 * _safe_log(self.age)
                        - 0.143834e-01 * self.ba_other_species
                        + 2.87671
                    )
            elif SIdm < 240:
                if not self.Site.thinned:
                    dependent_vars = (
                        +0.517826e-01 * self.ba
                        + 0.768565 * _safe_log(self.ba)
                        - 0.381320e-03 * self.stems
                        + 0.201267 * _safe_log(self.stems)
                        + 0.131078e-02 * self.age
                        - 0.831523 * _safe_log(self.age)
                        - 0.122796e-01 * self.ba_other_species
                        + 1.65650
                    )
                else:
                    dependent_vars = (
                        +0.517826e-01 * self.ba
                        + 0.768565 * _safe_log(self.ba)
                        - 0.381320e-03 * self.stems
                        + 0.201267 * _safe_log(self.stems)
                        + 0.131078e-02 * self.age
                        - 0.831523 * _safe_log(self.age)
                        - 0.122796e-01 * self.ba_other_species
                        + 1.59209
                    )
            else:
                if not self.Site.thinned:
                    dependent_vars = (
                        +0.243920e-02 * self.ba
                        + 0.857832 * _safe_log(self.ba)
                        - 0.949555e-04 * self.stems
                        + 0.192173 * _safe_log(self.stems)
                        - 0.292753e-02 * self.age
                        - 0.570009 * _safe_log(self.age)
                        - 0.240816e-01 * self.ba_other_species
                        + 0.916942
                    )
                else:
                    dependent_vars = (
                        +0.243920e-02 * self.ba
                        + 0.857832 * _safe_log(self.ba)
                        - 0.949555e-04 * self.stems
                        + 0.192173 * _safe_log(self.stems)
                        - 0.292753e-02 * self.age
                        - 0.570009 * _safe_log(self.age)
                        - 0.240816e-01 * self.ba_other_species
                        + 1.17865
                    )
            self.bai5 = exp(dependent_vars + independent_vars + 0.1648)
            return

        independent_vars = (
            -1.20049 * ba_quotient_chronic_mortality
            - 0.367064 * ba_quotient_acute_mortality
            + 0.125048 * self.Site.thinned_5y
            + 0.246684 * self.Site.fertilised
            + 0.141955 * self.Site.herbs_grasses_no_field_layer
            + 0.354866e-01 * self.Site.latitude
            - 0.361988e-03 * self.Site.altitude
        )
        if SIdm < 240:
            if not self.Site.thinned:
                dependent_vars = (
                    +0.857153 * _safe_log(self.ba)
                    - 0.541853e-04 * self.stems
                    + 0.152684 * _safe_log(self.stems)
                    - 0.803085e-02 * self.age
                    - 0.570230 * _safe_log(self.age)
                    - 0.100518 * _safe_log(self.ba_other_species)
                    - 1.93895
                )
            else:
                dependent_vars = (
                    +0.857153 * _safe_log(self.ba)
                    - 0.541853e-04 * self.stems
                    + 0.152684 * _safe_log(self.stems)
                    - 0.803085e-02 * self.age
                    - 0.570230 * _safe_log(self.age)
                    - 0.100518 * _safe_log(self.ba_other_species)
                    - 2.01960
                )
        elif SIdm < 280:
            if not self.Site.thinned:
                dependent_vars = (
                    +0.794405 * _safe_log(self.ba)
                    - 0.247009e-04 * self.stems
                    + 0.202344 * _safe_log(self.stems)
                    - 0.250423e-02 * self.age
                    - 0.669629 * _safe_log(self.age)
                    - 0.101205 * _safe_log(self.ba_other_species)
                    - 1.93895
                )
            else:
                dependent_vars = (
                    +0.794405 * _safe_log(self.ba)
                    - 0.247009e-04 * self.stems
                    + 0.202344 * _safe_log(self.stems)
                    - 0.250423e-02 * self.age
                    - 0.669629 * _safe_log(self.age)
                    - 0.101205 * _safe_log(self.ba_other_species)
                    - 2.01960
                )
        elif SIdm < 320:
            if not self.Site.thinned:
                dependent_vars = (
                    +0.782374 * _safe_log(self.ba)
                    - 0.125111e-03 * self.stems
                    + 0.239626 * _safe_log(self.stems)
                    - 0.787146e-03 * self.age
                    - 0.733575 * _safe_log(self.age)
                    - 0.823802e-01 * _safe_log(self.ba_other_species)
                    - 1.93895
                )
            else:
                dependent_vars = (
                    +0.782374 * _safe_log(self.ba)
                    - 0.125111e-03 * self.stems
                    + 0.239626 * _safe_log(self.stems)
                    - 0.787146e-03 * self.age
                    - 0.733575 * _safe_log(self.age)
                    - 0.823802e-01 * _safe_log(self.ba_other_species)
                    - 2.01960
                )
        else:
            if not self.Site.thinned:
                dependent_vars = (
                    +0.771398 * _safe_log(self.ba)
                    + 0.427071e-04 * self.stems
                    + 0.167037 * _safe_log(self.stems)
                    - 0.190695e-02 * self.age
                    - 0.587696 * _safe_log(self.age)
                    - 0.113489 * _safe_log(self.ba_other_species)
                    - 1.93895
                )
            else:
                dependent_vars = (
                    +0.771398 * _safe_log(self.ba)
                    + 0.427071e-04 * self.stems
                    + 0.167037 * _safe_log(self.stems)
                    - 0.190695e-02 * self.age
                    - 0.587696 * _safe_log(self.age)
                    - 0.113489 * _safe_log(self.ba_other_species)
                    - 2.01960
                )
        self.bai5 = exp(dependent_vars + independent_vars + 0.1734)


class BeechEngineCohort(EngineStandPart):
    """Beech cohort ported from the legacy EkoBeech formulas."""

    MORT_INDEX = 3

    def _bai_diameter_caps(self):
        """ProdMod2 BEECH_DIAMETER_COEFFS basal-area / stem limits for the BAI inputs."""
        si = self._bai_class_si_dm()
        return (40.0, 1600.0) if si < 310 else (44.0, 2000.0)

    def __init__(
        self,
        ba,
        stems,
        age,
        stand,
        site,
        species: TreeName | str | None = None,
    ):
        """Create a beech cohort tied to the given site."""
        super().__init__(
            ba,
            stems,
            age,
            species or TreeSpecies.Sweden.fagus_sylvatica,
            site,
        )
        if stand is not None:
            self.register_stand(stand)

    def get_volume(self, ba=None, qmd=None, age=None, stems=None, hk=None):
        """Compute beech volume for the given stand state."""
        if self.stand is None:
            raise ValueError("Volume calculator requires stand connected.")
        ba = self.ba if ba is None else ba
        qmd = self.qmd if qmd is None else qmd
        age = self.age if age is None else age
        stems = self.stems if stems is None else stems
        hk = self.hk if hk is None else hk
        SIdm = self._site_index_dm()
        b1 = -0.02
        b2 = -2.3
        F4age = 1 - exp(b1 * age)
        F4basal_area = 1 - exp(b2 * ba)
        lnVolume = (
            -0.111600e-01 * ba
            + 1.30527 * _safe_log(ba)
            - 0.676190 * F4basal_area
            + 0.490740 * F4age
            - 0.151930 * _safe_log(stems)
            - 0.572600e-01 * _safe_log(SIdm)
            + 0.628000e-01 * self.Site.thinned
            + 0.203927e-02 * hk
            + 2.85509
        )
        return exp(lnVolume + 0.0392)

    def get_bai5(self, ba_quotient_chronic_mortality=0.0, ba_quotient_acute_mortality=0.0):
        """Compute beech basal-area increment over five years."""
        if self.stand is None:
            raise ValueError("BAI calculator requires stand connected.")
        # SI drives both the class and the linear ``0.162579e-2 * SIdm`` term; for beech
        # (non-pine) this is H100 spruce, boundary-nudged under broadleaf_growth_prodmod.
        SIdm = self._bai_class_si_dm()

        independent_vars = -0.862301 * ba_quotient_acute_mortality + 0.162579e-02 * SIdm + 0.538943

        if SIdm < 310:
            if not self.Site.thinned:
                dependent_vars = (
                    +0.948126 * _safe_log(self.ba)
                    + 0.563620e-01 * _safe_log(self.stems)
                    - 0.751665 * _safe_log(self.age)
                    - 0.163302e-01 * self.ba_other_species
                )
            else:
                dependent_vars = (
                    +0.948126 * _safe_log(self.ba)
                    + 0.563620e-01 * _safe_log(self.stems)
                    - 0.751665 * _safe_log(self.age)
                    - 0.163302e-01 * self.ba_other_species
                    + 0.887110e-01
                )
        else:
            if not self.Site.thinned:
                dependent_vars = (
                    +0.821914 * _safe_log(self.ba)
                    + 0.102770 * _safe_log(self.stems)
                    - 0.753735 * _safe_log(self.age)
                    - 0.163641e-01 * self.ba_other_species
                )
            else:
                dependent_vars = (
                    +0.821914 * _safe_log(self.ba)
                    + 0.102770 * _safe_log(self.stems)
                    - 0.753735 * _safe_log(self.age)
                    - 0.163641e-01 * self.ba_other_species
                    + 0.887110e-01
                )

        self.bai5 = exp(dependent_vars + independent_vars + 0.1379)


class OakEngineCohort(EngineStandPart):
    """Oak cohort ported from the legacy EkoOak formulas."""

    MORT_INDEX = 4

    def _bai_diameter_caps(self):
        """ProdMod2 OAK_DIAMETER_COEFFS basal-area / stem limits for the BAI inputs."""
        si = self._bai_class_si_dm()
        return (40.0, 2000.0) if si < 280 else (44.0, 2000.0)

    def __init__(
        self,
        ba,
        stems,
        age,
        stand,
        site,
        species: TreeName | str | None = None,
    ):
        """Create an oak cohort tied to the given site."""
        super().__init__(
            ba,
            stems,
            age,
            species or TreeSpecies.Sweden.quercus_robur,
            site,
        )
        if stand is not None:
            self.register_stand(stand)

    def get_volume(self, ba=None, qmd=None, age=None, stems=None, hk=None):
        """Compute oak volume for the given stand state."""
        if self.stand is None:
            raise ValueError("Volume calculator requires stand connected.")
        ba = self.ba if ba is None else ba
        qmd = self.qmd if qmd is None else qmd
        age = self.age if age is None else age
        stems = self.stems if stems is None else stems
        hk = self.hk if hk is None else hk
        SIdm = self._site_index_dm()
        b1 = -0.055
        b2 = -2.3
        F4age = 1 - exp(b1 * age)
        F4basal_area = 1 - exp(b2 * ba)
        lnVolume = (
            -0.106300e-01 * ba
            + 1.27353 * _safe_log(ba)
            - 0.463790 * F4basal_area
            + 0.801580 * F4age
            - 0.157080 * _safe_log(stems)
            + 0.159030 * _safe_log(SIdm)
            + 0.503200e-01 * self.Site.thinned
            + 0.188030e-02 * hk
            + 1.40608
        )
        return exp(lnVolume + 0.0756)

    def get_bai5(self, ba_quotient_chronic_mortality=0.0, ba_quotient_acute_mortality=0.0):
        """Compute oak basal-area increment over five years."""
        if self.stand is None:
            raise ValueError("BAI calculator requires stand connected.")
        SIdm = self._bai_class_si_dm()  # H100 spruce (non-pine); boundary-nudged under flag

        # Ekö 1985 Tabell 4i (oak) gives K = -0.609667 (verified against the scan).
        # ProdMod2's OAK_BAI_COEFFICIENTS stores +0.60966656 -- a ProdMod2 sign bug
        # (every other oak coefficient matches to 6 digits). The dissertation value is
        # the default; broadleaf_growth_prodmod flips to +0.609667 to reproduce
        # ProdMod2's own example-workbook outputs (which carry the bug).
        oak_k = 0.609667 if self.Site.broadleaf_growth_prodmod else -0.609667
        independent_vars = -0.389169 * ba_quotient_acute_mortality + oak_k
        if SIdm < 280:
            dependent_vars = (
                +0.896599 * _safe_log(self.ba)
                + 0.199354 * _safe_log(self.stems)
                - 0.842665 * _safe_log(self.age)
                - 0.146432e-01 * self.ba_other_species
            )
        elif SIdm < 320:
            dependent_vars = (
                +0.847420 * _safe_log(self.ba)
                + 0.144495 * _safe_log(self.stems)
                - 0.727278 * _safe_log(self.age)
                - 0.222990e-01 * self.ba_other_species
            )
        else:
            dependent_vars = (
                +0.851362 * _safe_log(self.ba)
                + 0.128100 * _safe_log(self.stems)
                - 0.667346 * _safe_log(self.age)
                - 0.199705e-01 * self.ba_other_species
            )
        self.bai5 = exp(dependent_vars + independent_vars + 0.1618)


__all__ = [
    "_engine_cohort_factory",
    "SpruceEngineCohort",
    "PineEngineCohort",
    "BirchEngineCohort",
    "BroadleafEngineCohort",
    "BeechEngineCohort",
    "OakEngineCohort",
]
