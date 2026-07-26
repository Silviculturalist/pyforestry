"""Eko 1985 engine expressed on the canonical simulation runtime.

The Eko 1985 growth system runs on top of the package's shared simulation
primitives rather than a bespoke container:

- cohorts are carried as
  :class:`~pyforestry.simulation.stand_composite.StandPart` model views inside a
  :class:`~pyforestry.simulation.stand_composite.StandComposite` (the canonical
  part registry, aggregation, RNG, and telemetry);
- the five-year whole-stand growth step runs as an :class:`Eko1985GrowthStage`
  inside a :class:`~pyforestry.simulation.stage_runtime.StageRuntime`;
- thinning is dispatched as a
  :class:`~pyforestry.simulation.stand_composite.StandAction` over the composite.

``EngineStand`` remains a thin Eko-specific facade over that runtime, preserving
the historical call surface (``grow``/``thin``/``stand_ba``/``parts``/``get_qmd``/
``get_mai``/``_volume_for``) used by
:class:`~pyforestry.sweden.systems.eko1985.model.Eko1985Stand`.

Eko 1985 growth couples every cohort to every other cohort through competition
(``HK``) and cross-species mortality, so the update is intrinsically a
whole-stand operation computed from a single pre-growth snapshot; mortality is
part of that growth equation and therefore lives inside the growth stage rather
than a separate disturbance stage.
"""

from __future__ import annotations

from math import pi
from typing import Mapping

from pyforestry.base.helpers import TreeName, TreeSpecies
from pyforestry.simulation.stage_runtime import Stage, StageRuntime
from pyforestry.simulation.stand_composite import StandAction, StandComposite, StandPart

from .site_context import EkoStandSite, _coerce_species, _safe_sum

# ---------------------------------------------------------------------------
# Natural-mortality coefficients for the HUGIN natural-avgång functions used by
# Ekö's growth simulator. Scientific source: Bengtsson, G. (1979) "Plan för
# projekt 'Naturlig avgång' inom projekt Hugin" (SLU, stencil), as applied in the
# HUGIN system (cf. Hägglund, B. 1981a), reached via the container thesis
# Ekö, P.-M. (1985) Rapport nr 16, institutionen för skogsskötsel, SLU, Umeå.
# (There is no joint "Bengtsson & Hägglund 1981" paper; Ekö 1985 cites the two
# separately.)
# The coefficients were transcribed from the ProdMod2 program (Eko's simulator;
# recovered C++ source) -- an implementation reference, not a scientific citation.
# Both the chronic (self-thinning / crowding) and acute ("other") five-year
# fractions are ``(increment/100) * polynomial`` clamped at zero. Species index:
# pine, spruce, birch, beech, oak, other broadleaf. Mortality localisation is
# binary and groups Central WITH South (keyed on ``localisation != 0``): index
# 0 = North, 1 = Central/South. (Growth and volume use three distinct regions.)
# NB: this binary grouping is verified in the recovered ProdMod2 C++ source
# (SpeciesData_CalculateMortality.cpp) and against the PRODMOD example workbooks
# (see test_eko_1985_prodmod.py). Other reimplementations may split the regions
# differently; do NOT change the grouping to match them without re-checking the
# ProdMod2 stem counts.
# ---------------------------------------------------------------------------
# chronic = scale * (c0 + c1*BA + c2*BA^2 + c3*stems + c4*stems^2)   [stems capped]
_MORT_CHRONIC = (
    (
        (0.0314, -0.006877, 0.0002056, 0.00002684, -5.092e-9),
        (-0.06766, -0.001283, 0.00007748, 0.0001441, -1.839e-8),
    ),  # pine
    (
        (-0.002748, 0.0004493, 0.00002515, 0.0, 0.0),
        (0.01235, -0.002749, 0.00008214, 0.00002457, -4.498e-9),
    ),  # spruce
    ((-0.02513, 0.005489, 0.0, 0.0, 0.0), (0.04, 0.0, 0.0, 0.0, 0.0)),  # birch
    ((0.0, 0.0, 0.0, 0.0, 0.0), (-0.007277, -0.002456, 0.0001923, 0.0, 0.0)),  # beech
    ((0.0, 0.0, 0.0, 0.0, 0.0), (-0.007277, -0.002456, 0.0001923, 0.0, 0.0)),  # oak
    ((0.0, 0.0, 0.0, 0.0, 0.0), (-0.007277, -0.002456, 0.0001923, 0.0, 0.0)),  # other
)
# acute = scale * (a0 + a1*age_class)  -- only spruce (North) is age-class dependent
_MORT_ACUTE = (
    ((0.14, 0.0), (0.38, 0.0)),  # pine
    ((-0.0002363, 0.0250275), (0.36, 0.0)),  # spruce
    ((0.35, 0.0), (0.46, 0.0)),  # birch
    ((0.35, 0.0), (0.46, 0.0)),  # beech
    ((0.35, 0.0), (0.46, 0.0)),  # oak
    ((0.35, 0.0), (0.46, 0.0)),  # other
)
# stem cap applied before the chronic polynomial: (North/Central, South)
_MORT_STEM_CAP = {0: (2700.0, 4000.0), 1: (2800.0, 2800.0)}


def _species_label(species: TreeName) -> str:
    """Return the Swedish label used by the legacy engine for a tree species."""
    if species in {TreeSpecies.Sweden.picea_abies}:
        return "Gran"
    if species in {TreeSpecies.Sweden.pinus_sylvestris, TreeSpecies.Sweden.pinus_contorta}:
        return "Tall"
    if species.genus.name.lower() == "betula":
        return "Björk"
    if species.genus.name.lower() == "fagus":
        return "Bok"
    if species.genus.name.lower() == "quercus":
        return "Ek"
    return "Öv.löv"


def _resolve_removal(part: "EngineStandPart", removals: Mapping) -> float:
    """Return the requested basal-area removal (m2/ha) for ``part``'s species."""
    key_variants = (
        part.species,
        part.species.full_name,
        part.species.full_name.lower(),
        part.species.code,
        part.trädslag,
        part.trädslag.lower(),
    )
    for key in key_variants:
        if key in removals:
            return float(removals[key])
    return 0.0


class Eko1985GrowthStage(Stage):
    """Whole-stand Eko 1985 growth step expressed as a StageRuntime stage.

    Eko 1985 growth couples every cohort to every other cohort, so the five-year
    update is computed once for the whole stand from a single pre-growth snapshot
    rather than independently per part. :meth:`StageRuntime.run_cycle` invokes
    :meth:`run` once per part; the stage performs the whole-stand step on the
    first invocation after :meth:`arm` and is otherwise inert, which keeps the
    simultaneous-update semantics (and numeric parity with the legacy engine)
    intact regardless of how many parts the cycle iterates.
    """

    name = "growth"
    order = 10

    def __init__(self, stand: "EngineStand") -> None:
        """Bind the stage to its owning :class:`EngineStand` facade."""
        super().__init__()
        self._stand = stand
        self._years = 5.0
        self._apply_mortality = True
        self._armed = False
        self.last_period: dict[str, list[dict[str, float]]] = {}

    def arm(self, years: float, apply_mortality: bool) -> None:
        """Schedule a whole-stand step for the next :meth:`StageRuntime.run_cycle`."""
        self._years = float(years)
        self._apply_mortality = bool(apply_mortality)
        self._armed = True

    def run(self, part, module, rng=None) -> None:
        """Execute the armed whole-stand step exactly once per cycle."""
        if not self._armed:
            return
        self._armed = False
        self.last_period = self._grow_whole_stand(module.composite)

    def _grow_whole_stand(self, composite: StandComposite) -> dict[str, list[dict[str, float]]]:
        """Advance every cohort by ``self._years`` from a shared pre-growth snapshot."""
        stand = self._stand
        years = self._years
        apply_mortality = self._apply_mortality
        parts = [holder.model_view for holder in composite.parts]

        stand._assign_current_state_metrics()

        start_state = []
        for p in parts:
            vol0 = p.get_volume(ba=p.ba, qmd=p.qmd, age=p.age, stems=p.stems, hk=p.hk)
            start_state.append(
                {
                    "part": p,
                    "ba": p.ba,
                    "stems": p.stems,
                    "age": p.age,
                    "qmd": p.qmd,
                    "vol": vol0,
                }
            )
            p.vol0 = vol0

        mortality = []
        apply_caps = bool(getattr(stand.Site, "broadleaf_growth_prodmod", False))
        for p in parts:
            if apply_mortality:
                baq_crowd, _dead_qmd_c, baq_other, _dead_qmd_o = p.get_mortality(increment=years)
            else:
                baq_crowd = baq_other = 0.0
            # ProdMod2 parity: clamp the BAI's own basal area / stem inputs to the
            # fitting-domain diameter limits. Applied around the call and restored so
            # the (uncapped) state still drives mortality, competition and the update.
            ba_saved, stems_saved = p.ba, p.stems
            if apply_caps:
                caps = p._bai_diameter_caps()
                if caps is not None:
                    p.ba = min(p.ba, caps[0])
                    p.stems = min(p.stems, caps[1])
            p.get_bai5(
                ba_quotient_chronic_mortality=baq_crowd,
                ba_quotient_acute_mortality=baq_other,
            )
            p.ba, p.stems = ba_saved, stems_saved
            mortality.append(
                {
                    "q_crowd": baq_crowd,
                    "q_other": baq_other,
                    "q_total": baq_crowd + baq_other,
                }
            )

        next_state = []
        for idx, p in enumerate(parts):
            q_total = mortality[idx]["q_total"] if apply_mortality else 0.0
            if apply_mortality:
                next_ba = (1.0 - q_total) * p.ba + p.bai5
                next_stems = (1.0 - q_total) * p.stems
                next_age = p.age + years
            else:
                next_ba = p.ba
                next_stems = p.stems
                next_age = p.age
            next_qmd = stand.get_qmd(next_ba, next_stems)
            next_state.append(
                {
                    "part": p,
                    "ba": next_ba,
                    "stems": next_stems,
                    "age": next_age,
                    "qmd": next_qmd,
                }
            )

        for idx, _p in enumerate(parts):
            ba_other = _safe_sum(ns["ba"] for j, ns in enumerate(next_state) if j != idx)
            N_other = _safe_sum(ns["stems"] for j, ns in enumerate(next_state) if j != idx)
            qmd_other = stand.get_qmd(ba_other, N_other)
            hk_next = (qmd_other / (next_state[idx]["qmd"] or 1e-9)) * ba_other
            next_state[idx]["hk"] = hk_next

        for idx, p in enumerate(parts):
            ns = next_state[idx]
            ns["vol"] = p.get_volume(
                ba=ns["ba"],
                qmd=ns["qmd"],
                age=ns["age"],
                stems=ns["stems"],
                hk=ns["hk"],
            )
            ns["volume_increment"] = ns["vol"] - start_state[idx]["vol"]

        period: dict[str, list[dict[str, float]]] = {}
        for idx, p in enumerate(parts):
            ns = next_state[idx]
            p.gross_volume_increment = ns["volume_increment"]
            p.volume_increment = ns["volume_increment"]
            p.ba = ns["ba"]
            p.stems = ns["stems"]
            p.qmd = ns["qmd"]
            p.age = ns["age"]
            p.hk = ns.get("hk", p.hk)
            p.vol = ns["vol"]
            key = p.trädslag
            period.setdefault(key, []).append(
                {
                    "N1": p.stems,
                    "ba1": p.ba,
                    "qmd1": p.qmd,
                    "vol1": p.vol,
                    "N0": start_state[idx]["stems"],
                    "ba0": start_state[idx]["ba"],
                    "qmd0": start_state[idx]["qmd"],
                    "vol0": start_state[idx]["vol"],
                }
            )

        stand._assign_current_state_metrics()
        return period


class EngineStand:
    """Thin Eko 1985 facade over a :class:`StandComposite` + :class:`StageRuntime`."""

    def __init__(self, parts: list["EngineStandPart"], site: EkoStandSite):
        """Wire cohorts into a StandComposite and a growth-staged StageRuntime."""
        self.parts = parts
        self.Site = site
        self.volume_scale: float | None = None

        stand_parts: list[StandPart] = []
        seen: set[str] = set()
        for idx, cohort in enumerate(self.parts):
            base = getattr(cohort.species, "full_name", None) or f"cohort_{idx}"
            name = base if base not in seen else f"{base}#{idx}"
            seen.add(name)
            stand_parts.append(StandPart(name=name, model_view=cohort))
        self.composite = StandComposite(stand_parts, model_id="eko_1985")
        self._growth_stage = Eko1985GrowthStage(self)
        self.module = StageRuntime(self.composite, stages=(self._growth_stage,))

        for p in self.parts:
            p.register_stand(self)
        self._assign_current_state_metrics()

    @staticmethod
    def get_qmd(ba: float, stems: float) -> float:
        """Return quadratic mean diameter (cm) from basal area and stems."""
        if ba <= 0.0 or stems <= 0.0:
            return 0.0
        return (ba * 40000.0 / (pi * stems)) ** 0.5

    @staticmethod
    def get_mai(volume: float, total_age: float) -> float:
        """Return mean annual increment from volume and age."""
        return volume / total_age

    def _competition_metrics(self) -> None:
        """Compute competition metrics (QMD, HK) for all cohorts."""
        for p in self.parts:
            p.qmd = self.get_qmd(p.ba, p.stems)
        for p in self.parts:
            ba_other = _safe_sum(q.ba for q in self.parts if q is not p)
            N_other = _safe_sum(q.stems for q in self.parts if q is not p)
            p.ba_other_species = ba_other
            p.qmd_other_species = self.get_qmd(ba_other, N_other)
            denom = p.qmd if p.qmd > 0 else 1e-9
            p.hk = (p.qmd_other_species / denom) * ba_other

    def _assign_current_state_metrics(self) -> None:
        """Recompute competition metrics, volumes, and stand totals."""
        self._competition_metrics()
        # Provide current totals before volume calls for species that reference stand_ba.
        self.stand_ba = _safe_sum(p.ba for p in self.parts)
        self.StandStems = _safe_sum(p.stems for p in self.parts)
        for p in self.parts:
            p.vol = p.get_volume(ba=p.ba, qmd=p.qmd, age=p.age, stems=p.stems, hk=p.hk)
        self.stand_ba = _safe_sum(p.ba for p in self.parts)
        self.StandStems = _safe_sum(p.stems for p in self.parts)
        self.stand_vol = _safe_sum(p.vol for p in self.parts)

    def _volume_for(
        self, part: "EngineStandPart", ba=None, qmd=None, age=None, stems=None, hk=None
    ):
        """Compute a volume for a cohort with optional overrides."""
        ba = part.ba if ba is None else ba
        age = part.age if age is None else age
        stems = part.stems if stems is None else stems
        if qmd is None:
            qmd = self.get_qmd(ba, stems)
        if hk is None:
            ba_other = sum(q.ba for q in self.parts if q is not part)
            N_other = sum(q.stems for q in self.parts if q is not part)
            qmd_other = self.get_qmd(ba_other, N_other)
            hk = (qmd_other / qmd) * ba_other if qmd > 0 else 0.0
        return part.get_volume(ba=ba, qmd=qmd, age=age, stems=stems, hk=hk)

    def thin(self, removals: Mapping) -> None:
        """Apply constant-QMD thinning, dispatched as a StandAction over the composite."""

        def _apply_thin(part: StandPart) -> None:
            """Remove the requested basal area from a single cohort at constant QMD."""
            cohort = part.model_view
            ba_out = max(0.0, min(_resolve_removal(cohort, removals), cohort.ba))
            if ba_out > 0.0 and cohort.qmd > 0:
                stems_out = ba_out / (pi * (cohort.qmd / 200.0) ** 2)
                cohort.ba -= ba_out
                cohort.stems = max(0.0, cohort.stems - stems_out)

        action = StandAction(name="thin_basal_area", handler=_apply_thin)
        self.composite.dispatch([action], policy="broadcast")
        self._assign_current_state_metrics()

    def grow(self, years: float = 5.0, apply_mortality: bool = True):
        """Advance the stand by ``years`` via the growth stage's whole-stand step."""
        self._growth_stage.arm(years, apply_mortality)
        self.module.run_cycle()
        return self._growth_stage.last_period

    def grow5(self, apply_mortality: bool = True):
        """Five-year convenience wrapper around :meth:`grow`."""
        return self.grow(years=5, apply_mortality=apply_mortality)


class EngineStandPart:
    """Minimal cohort base for the Eko 1985 engine (carried as a StandPart view)."""

    def __init__(
        self,
        ba: float,
        stems: float,
        age: float,
        species: TreeName | str,
        site: EkoStandSite,
    ):
        """Initialize engine cohort state."""
        self.ba = float(ba)
        self.stems = float(stems)
        self.age = float(age)
        self.species = _coerce_species(species)
        self.trädslag = _species_label(self.species)
        self.Site = site
        self.stand = None
        self.qmd = EngineStand.get_qmd(self.ba, self.stems)
        self.qmd_other_species = 0.0
        self.ba_other_species = 0.0
        self.ba_quotient_acute_mortality = 0.0
        self.hk = 0.0
        self.vol = 0.0
        self.bai5 = 0.0
        self.volume_increment = 0.0
        self.gross_volume_increment = 0.0

    @property
    def basal_area(self) -> float:
        """Expose basal area (m2/ha) under the StandPart metric attribute name."""
        return self.ba

    def register_stand(self, stand: EngineStand) -> None:
        """Attach the cohort to its parent stand."""
        self.stand = stand

    def _default_site_index_m(self) -> float:
        """Species' H100 site index (m): H100 spruce for every species except pine.

        Ekö 1985 expresses the site-index variable in every growth and volume function
        as H100 pine (dm) for pine and H100 spruce (dm) for all other species -- a site
        property, not a per-cohort value (verified from the Tabell 4/10 column headers
        "SI H100 gran"). :class:`PineEngineCohort` overrides this to return H100 pine.
        """
        return float(self.Site.H100_Spruce or 0.0)

    def _site_index_dm(self) -> float:
        """Return the H100 site index (dm) this cohort's Ekö 1985 functions use.

        The dissertation site-index variable: H100 spruce (dm) for every species
        except pine (H100 pine). See :meth:`_default_site_index_m`.
        """
        return float(self._default_site_index_m() or 0.0) * 10.0

    def _bai_class_si_dm(self) -> float:
        """H100 site index (dm) used to pick the basal-area-increment SI-class.

        This is :meth:`_site_index_dm`. Under ``Site.broadleaf_growth_prodmod`` a
        boundary SI is nudged (-1e-6) into the lower class to match ProdMod2's
        ``SI > limit`` upgrade test: the dissertation prints lower-inclusive ranges
        (``220<=SI<260``), so a value exactly on a boundary belongs to the higher class
        by default and this shift is a ProdMod2-only detail.
        """
        si = self._site_index_dm()
        if getattr(self.Site, "broadleaf_growth_prodmod", False):
            si -= 1e-6
        return si

    def _bai_diameter_caps(self) -> tuple[float, float] | None:
        """Return ``(basal_area_cap m2/ha, stem_cap /ha)`` for the BAI inputs, or None.

        ProdMod2 (``get_diameter_limit``) clamps a cohort's basal area and stem count
        to the fitting-domain limits for its species/region/thinning/SI-class before
        evaluating the growth function. The engine applies this only under
        ``Site.broadleaf_growth_prodmod``; the base returns ``None`` (no cap) and
        broadleaf cohorts override with the ProdMod2 limit tables.
        """
        return None

    def get_volume(self, ba, qmd, age, stems, hk):  # pragma: no cover - overridden
        """Compute volume from basal area, QMD, age, stems, and HK."""
        raise NotImplementedError

    #: species row into the mortality coefficient tables (set by each subclass)
    MORT_INDEX: int | None = None

    def get_mortality(self, increment: int = 5):
        """Return the five-year natural-mortality fractions (chronic, acute).

        Transcribed from the ProdMod2 program (HUGIN natural-avgang functions;
        Bengtsson 1979, cf. Haegglund 1981a, via Eko 1985): both fractions are
        ``(increment/100) * polynomial`` clamped at zero. The chronic term uses
        basal area and a capped stem count; the acute term uses an age class
        derived from the *largest* breast-height age in the stand (only spruce is
        age-class sensitive). Localisation is binary: North vs Central/South.

        The second and fourth return values are the mean diameters of the removed
        trees, kept for interface compatibility; the growth stage ignores them.
        """
        if self.stand is None:
            raise ValueError("Mortality calculator requires stand connected.")
        idx = self.MORT_INDEX
        loc = 0 if self.Site.region == "North" else 1
        scale = increment / 100.0

        stems = self.stems
        cap = _MORT_STEM_CAP.get(idx)
        if cap is not None:
            stems = min(stems, cap[loc])
        c = _MORT_CHRONIC[idx][loc]
        chronic = scale * (
            c[0] + c[1] * self.ba + c[2] * self.ba**2 + c[3] * stems + c[4] * stems**2
        )
        chronic = max(chronic, 0.0)

        max_age = max((p.age for p in self.stand.parts), default=self.age)
        age_class = min(int(max_age / 10.0) + 1, 17)
        a = _MORT_ACUTE[idx][loc]
        acute = max(scale * (a[0] + a[1] * age_class), 0.0)

        return chronic, 0.9 * self.qmd, acute, self.qmd

    def get_bai5(self, ba_quotient_chronic_mortality=0.0, ba_quotient_acute_mortality=0.0):
        """Compute basal-area increment over five years."""
        raise NotImplementedError


__all__ = ["Eko1985GrowthStage", "EngineStand", "EngineStandPart"]
