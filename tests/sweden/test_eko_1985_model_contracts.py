"""What the Ekö (1985) adapter resolves, and what it refuses to guess at.

The engine had tests; the adapter around it had the happy path only. Everything
here is a way the runtime can hand this model an incomplete stand -- a site it has
to find, cohort ages under a key it has to recognise, total-only metrics, a
tree-list context -- and either the adapter resolves it or it says which piece is
missing. A model that silently substitutes an age or a site index answers a
different question from the one it was asked.
"""

from __future__ import annotations

import pytest

from pyforestry.base.helpers.primitives import SiteBase, StandBasalArea, Stems
from pyforestry.base.helpers.stand import Stand
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.sweden.site import Sweden, SwedishSite
from pyforestry.sweden.systems.eko1985 import Eko1985Model, Eko1985SiteContext

SPRUCE = TreeSpecies.Sweden.picea_abies
PINE = TreeSpecies.Sweden.pinus_sylvestris


def _site_context() -> Eko1985SiteContext:
    return Eko1985SiteContext(
        latitude=62.0,
        longitude=18.0,
        altitude=120.0,
        vegetation=13,
        soil_moisture=3,
        spruce_site_index=20.0,
        pine_site_index=20.0,
    )


class _SiteDemo(SwedishSite):
    """Concrete site wrapper (implements the abstract SiteBase hook)."""

    def compute_attributes(self) -> None:
        """Populate the derived Swedish site attributes."""
        SwedishSite.__post_init__(self)

    def __post_init__(self) -> None:
        """Defer the Swedish derivation to :meth:`compute_attributes`."""
        SiteBase.__post_init__(self)


def _swedish_site() -> SwedishSite:
    return _SiteDemo(
        latitude=62.0,
        longitude=18.0,
        altitude=120.0,
        field_layer=Sweden.FieldLayer.BILBERRY,
        soil_moisture=Sweden.SoilMoistureEnum.MESIC,
        soil_texture=Sweden.SoilTextureTill.SANDY,
    )


def _stand(*, per_species: bool = True, site=None) -> Stand:
    stand = Stand(site=site) if site is not None else Stand()
    ba = {}
    stems = {}
    if per_species:
        ba[SPRUCE] = StandBasalArea(10.0, species=SPRUCE, precision=0.0)
        ba[PINE] = StandBasalArea(8.0, species=PINE, precision=0.0)
        stems[SPRUCE] = Stems(800.0, species=SPRUCE, precision=0.0)
        stems[PINE] = Stems(600.0, species=PINE, precision=0.0)
    ba["TOTAL"] = StandBasalArea(18.0, species=None, precision=0.0)
    stems["TOTAL"] = Stems(1400.0, species=None, precision=0.0)
    stand._metric_estimates = {"BasalArea": ba, "Stems": stems}
    return stand


class TestResolvingTheSite:
    def test_a_swedish_site_on_the_stand_is_converted(self) -> None:
        """The runtime carries a ``SwedishSite``; this model wants its own context."""
        model = Eko1985Model()
        ctx = model.build_context(_stand(site=_swedish_site()), cohort_ages={"TOTAL": 40.0})

        resolved = ctx.attrs["eko_site_context"]
        assert isinstance(resolved, Eko1985SiteContext)
        # Wrapped, not flattened: the context reads what it needs off the site
        # rather than copying fields that would then be able to disagree.
        assert resolved.swedish_site is not None
        assert resolved.swedish_site.latitude == pytest.approx(62.0)

    def test_the_stand_attribute_is_read_when_nothing_else_says(self) -> None:
        stand = _stand()
        stand.attrs["eko_1985_site_context"] = _site_context()

        ctx = Eko1985Model().build_context(stand, cohort_ages={"TOTAL": 40.0})

        assert ctx.attrs["eko_site_context"] is stand.attrs["eko_1985_site_context"]

    def test_an_argument_wins_over_the_stand(self) -> None:
        stand = _stand(site=_swedish_site())
        explicit = _site_context()

        ctx = Eko1985Model().build_context(
            stand, site_context=explicit, cohort_ages={"TOTAL": 40.0}
        )

        assert ctx.attrs["eko_site_context"] is explicit

    def test_a_stand_with_no_site_anywhere_is_refused(self) -> None:
        """Ekö's functions are site-index driven; there is no neutral site."""
        with pytest.raises(ValueError, match="Eko1985SiteContext or SwedishSite"):
            Eko1985Model().build_context(_stand(), cohort_ages={"TOTAL": 40.0})


class TestResolvingCohortAges:
    @pytest.mark.parametrize("key", [SPRUCE, "Picea abies", "picea abies"])
    def test_a_species_age_is_found_under_any_spelling(self, key) -> None:
        """A ``TreeName`` or either case of its name all normalise to one key."""
        model = Eko1985Model(site_context=_site_context())

        ctx = model.build_context(_stand(per_species=False), cohort_ages={key: 42.0})

        assert ctx.state["cohort_ages"] == {"picea abies": pytest.approx(42.0)}

    def test_a_total_age_covers_every_species(self) -> None:
        """One age for the stand, where the cohorts are not aged separately."""
        model = Eko1985Model(site_context=_site_context())

        ctx = model.build_context(_stand(), cohort_ages={"total": 42.0})

        assert ctx.state["cohort_ages"] == {"TOTAL": pytest.approx(42.0)}
        model.update_step(ctx, 5.0)
        assert float(ctx.metrics["BasalArea"]["TOTAL"]) > 0.0

    def test_the_stand_attribute_supplies_the_ages_when_the_call_does_not(self) -> None:
        stand = _stand()
        stand.attrs["eko_1985_cohort_ages"] = {SPRUCE: 40.0, PINE: 45.0}

        ctx = Eko1985Model(site_context=_site_context()).build_context(stand)

        assert ctx.state["cohort_ages"]["picea abies"] == pytest.approx(40.0)

    def test_a_default_age_covers_a_species_the_map_does_not_name(self) -> None:
        model = Eko1985Model(site_context=_site_context(), default_age=37.0)

        ctx = model.build_context(_stand(), cohort_ages={SPRUCE: 40.0})
        model.update_step(ctx, 5.0)

        assert float(ctx.metrics["BasalArea"]["TOTAL"]) > 0.0

    def test_neither_an_age_nor_a_default_is_refused(self) -> None:
        with pytest.raises(ValueError, match="cohort_ages or default_age"):
            Eko1985Model(site_context=_site_context()).build_context(_stand())

    def test_a_species_with_no_age_and_no_default_is_named_in_the_error(self) -> None:
        model = Eko1985Model(site_context=_site_context())

        with pytest.raises(ValueError, match="pinus sylvestris"):
            model.build_context(_stand(), cohort_ages={SPRUCE: 40.0})


class TestTotalOnlyMetrics:
    def test_one_species_in_the_age_map_names_what_the_total_is(self) -> None:
        """An aggregate stand carries no species; the age map is where it is said."""
        model = Eko1985Model(site_context=_site_context())

        ctx = model.build_context(_stand(per_species=False), cohort_ages={SPRUCE: 40.0})
        model.update_step(ctx, 5.0)

        assert float(ctx.metrics["BasalArea"]["TOTAL"]) > 0.0

    def test_two_species_against_a_total_is_ambiguous_and_refused(self) -> None:
        model = Eko1985Model(site_context=_site_context())

        with pytest.raises(ValueError, match="single species"):
            model.build_context(_stand(per_species=False), cohort_ages={SPRUCE: 40.0, PINE: 45.0})

    def test_a_stand_with_no_basal_area_at_all_is_refused(self) -> None:
        """Refused by the base contract, before Ekö's own checks are reached."""
        stand = Stand()
        stand._metric_estimates = {"BasalArea": {}, "Stems": {}}

        with pytest.raises(ValueError, match="does not supply BasalArea"):
            Eko1985Model(site_context=_site_context()).build_context(
                stand, cohort_ages={SPRUCE: 40.0}
            )


class TestSteppingAndThinning:
    def test_a_non_aggregate_context_is_refused_rather_than_reinterpreted(self) -> None:
        model = Eko1985Model(site_context=_site_context())
        ctx = model.build_context(_stand(), cohort_ages={SPRUCE: 40.0, PINE: 45.0})
        ctx.mode = "tree_list"

        with pytest.raises(RuntimeError, match="aggregate inventory mode"):
            model.update_step(ctx, 5.0)

    def test_a_period_of_no_length_is_refused(self) -> None:
        model = Eko1985Model(site_context=_site_context())
        ctx = model.build_context(_stand(), cohort_ages={SPRUCE: 40.0, PINE: 45.0})

        with pytest.raises(ValueError, match="dt must be positive"):
            model.update_step(ctx, 0.0)

    def test_a_context_that_lost_its_ages_says_so(self) -> None:
        model = Eko1985Model(site_context=_site_context())
        ctx = model.build_context(_stand(), cohort_ages={SPRUCE: 40.0, PINE: 45.0})
        del ctx.state["cohort_ages"]

        with pytest.raises(ValueError, match="cohort_ages missing"):
            model.update_step(ctx, 5.0)

    def test_thinning_removes_basal_area_through_the_declared_action(self) -> None:
        model = Eko1985Model(site_context=_site_context())
        ctx = model.build_context(_stand(), cohort_ages={SPRUCE: 40.0, PINE: 45.0})
        before = float(ctx.metrics["BasalArea"]["TOTAL"])

        action = model.available_actions()["thin_basal_area"]
        action.fn(ctx, removals={SPRUCE: 3.0})

        assert float(ctx.metrics["BasalArea"]["TOTAL"]) < before
