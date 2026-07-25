import math

import pytest

from pyforestry.base.helpers import CircularPlot, Stand, Tree, TreeSpecies
from pyforestry.base.helpers.primitives import (
    Age,
    QuadraticMeanDiameter,
    SiteIndexValue,
    StandBasalArea,
    Stems,
)
from pyforestry.norway.blocks import Maleki2022Config, Maleki2022GrowthModel
from pyforestry.norway.blocks.maleki_2022 import Maleki2022ModelNorway
from pyforestry.norway.growth.maleki_2022 import (
    Maleki2022Species,
    maleki_2022_basal_area_projection,
    maleki_2022_height_trajectory,
    maleki_2022_ingrowth_count,
    maleki_2022_ingrowth_probability,
    maleki_2022_stand_volume,
    maleki_2022_stem_density,
    maleki_2022_stem_survival,
)


def _si_h40(age_years: float = 40.0) -> SiteIndexValue:
    return SiteIndexValue(
        value=20.0,
        reference_age=Age.TOTAL(age_years),
        species={TreeSpecies.Norway.picea_abies},
        fn=_si_h40,
    )


@pytest.mark.parametrize(
    ("species", "expected_species"),
    [
        (Maleki2022Species.NORWAY_SPRUCE, TreeSpecies.Norway.picea_abies),
        (Maleki2022Species.SCOTS_PINE, TreeSpecies.Norway.pinus_sylvestris),
        (Maleki2022Species.BROADLEAVES, None),
    ],
)
def test_stand_volume_paths(species, expected_species):
    volume = maleki_2022_stand_volume(
        species,
        dominant_height_m=18.0,
        basal_area=StandBasalArea(22.0),
        age=Age.TOTAL(40.0),
    )
    assert volume > 0.0
    assert volume.species == expected_species

    with pytest.raises(ValueError):
        maleki_2022_stand_volume(species, 18.0, 22.0, Age.TOTAL(0.0))

    with pytest.raises(ValueError):
        maleki_2022_stand_volume("unknown", 18.0, 22.0, Age.TOTAL(40.0))


def test_stem_survival_and_density_paths():
    stems_same = maleki_2022_stem_survival(
        "norway_spruce",
        age1=Age.TOTAL(30.0),
        age2=Age.TOTAL(30.0),
        stems1=Stems(1200.0),
        si_h40=_si_h40(),
    )
    assert stems_same == pytest.approx(1200.0)

    stems_zero = maleki_2022_stem_survival(
        "norway_spruce",
        age1=Age.TOTAL(0.0),
        age2=Age.TOTAL(10.0),
        stems1=Stems(1200.0),
        si_h40=_si_h40(),
    )
    assert stems_zero == 0.0

    with pytest.raises(ValueError):
        maleki_2022_stem_survival(
            "norway_spruce",
            age1=Age.TOTAL(40.0),
            age2=Age.TOTAL(30.0),
            stems1=Stems(1200.0),
            si_h40=_si_h40(),
        )

    density = maleki_2022_stem_density(
        "scots_pine",
        age1=Age.TOTAL(25.0),
        age2=Age.TOTAL(35.0),
        stems1=Stems(1100.0),
        si_h40=_si_h40(),
    )
    assert density > 0.0


def test_stem_survival_matches_published_equation():
    """Pin survival to Maleki (2022) eq. (5): N1*(A2/A1)^b1*exp(b2 - (SI/1000)*(A2-A1)^b3).

    Guards against the transcription in which ``b2`` multiplied (rather than being
    an additive intercept subtracted from) the site/age term, which spuriously made
    surviving stems *increase* with age.
    """
    import math

    b1, b2, b3 = 0.6159, -0.0312, 1.0602  # Norway spruce survival coefficients
    si = 20.0  # _si_h40() value
    a1, a2, n1 = 30.0, 40.0, 1200.0
    expected = n1 * (a2 / a1) ** b1 * math.exp(b2 - (si / 1000.0) * (a2 - a1) ** b3)

    result = maleki_2022_stem_survival(
        "norway_spruce",
        age1=Age.TOTAL(a1),
        age2=Age.TOTAL(a2),
        stems1=Stems(n1),
        si_h40=_si_h40(),
    )
    assert float(result) == pytest.approx(expected, rel=1e-9)
    # Survival must not exceed the starting stem count (fails under the '*' form).
    assert float(result) < n1


def test_ingrowth_count_and_probability_paths():
    spruce_count = maleki_2022_ingrowth_count("norway_spruce", basal_area=StandBasalArea(18.0))
    pine_count = maleki_2022_ingrowth_count("scots_pine", basal_area=StandBasalArea(18.0))
    broad_count = maleki_2022_ingrowth_count("broadleaves", qmd=QuadraticMeanDiameter(20.0))
    assert spruce_count >= 0.0
    assert pine_count >= 0.0
    assert broad_count >= 0.0

    with pytest.raises(ValueError):
        maleki_2022_ingrowth_count("broadleaves", basal_area=StandBasalArea(10.0))
    with pytest.raises(ValueError):
        maleki_2022_ingrowth_count("scots_pine", qmd=QuadraticMeanDiameter(15.0))

    assert maleki_2022_ingrowth_probability("norway_spruce", -1.0, 100.0) == 0.0
    prob = maleki_2022_ingrowth_probability(
        "broadleaves",
        QuadraticMeanDiameter(18.0),
        Stems(900.0),
    )
    assert 0.0 <= prob <= 1.0


def test_height_and_basal_area_projection_paths():
    for species, b1 in [
        ("norway_spruce", 39.5764),
        ("scots_pine", 43.6698),
        ("broadleaves", 36.6501),
    ]:
        same = maleki_2022_height_trajectory(species, 18.0, Age.TOTAL(30.0), Age.TOTAL(30.0))
        assert same == pytest.approx(18.0)

        # A stand already at the asymptote height b1 stays there (site variable X = 0).
        asym = maleki_2022_height_trajectory(species, b1, Age.TOTAL(30.0), Age.TOTAL(40.0))
        assert asym == pytest.approx(b1)

    with pytest.raises(ValueError):
        maleki_2022_basal_area_projection(
            "norway_spruce",
            StandBasalArea(18.0),
            Age.TOTAL(50.0),
            Age.TOTAL(45.0),
            _si_h40(),
            Stems(1000.0),
            Stems(900.0),
        )

    same_ba = maleki_2022_basal_area_projection(
        "norway_spruce",
        StandBasalArea(18.0),
        Age.TOTAL(40.0),
        Age.TOTAL(40.0),
        _si_h40(),
        Stems(1000.0),
        Stems(900.0),
    )
    assert same_ba == pytest.approx(18.0)

    zero_ba = maleki_2022_basal_area_projection(
        "norway_spruce",
        StandBasalArea(18.0),
        Age.TOTAL(35.0),
        Age.TOTAL(40.0),
        _si_h40(),
        Stems(0.0),
        Stems(900.0),
    )
    assert zero_ba == 0.0

    with pytest.warns(UserWarning):
        projected = maleki_2022_basal_area_projection(
            "scots_pine",
            StandBasalArea(16.0),
            Age.TOTAL(35.0),
            Age.TOTAL(45.0),
            _si_h40(age_years=50.0),
            Stems(1100.0),
            Stems(950.0),
        )
    assert projected >= 0.0


def test_height_trajectory_is_gada_consistent_and_invertible():
    # Maleki eq. (1) is a GADA site-index form: the site variable X is recovered
    # from (H1, A1) and reused at A2, so it must be monotonic in age and a
    # forward-then-back round trip must recover H1 exactly. The pre-fix
    # transcription (b2/H1 and b2/phi in place of b2*H1 and b2*phi) failed this --
    # e.g. H=6 @40 projected to 10.8 @40 and 12.4 @20 (higher when younger).
    for species in ("norway_spruce", "scots_pine", "broadleaves"):
        for h1, a1 in [(6.0, 40.0), (17.0, 55.0), (25.0, 70.0)]:
            ref, young, old = Age.TOTAL(a1), Age.TOTAL(a1 - 20.0), Age.TOTAL(a1 + 20.0)
            younger = maleki_2022_height_trajectory(species, h1, ref, young)
            older = maleki_2022_height_trajectory(species, h1, ref, old)
            assert 0.0 < younger < h1 < older  # height rises monotonically with age
            back = maleki_2022_height_trajectory(species, younger, young, ref)
            assert back == pytest.approx(h1, rel=1e-9)  # base-age invariant round trip


def test_basal_area_projection_uses_single_b2_not_paper_typo():
    # Maleki (2022) Table 4 eq. (3) is PRINTED with a double-b2
    # (exp[ b2**(N2/N1) * b2 * (1 - (H1/H2)**b3) ]); that is a typesetting error.
    # pyforestry applies the corrected single linear-b2 form
    # (exp[ b2 * (N2/N1) * (1 - (H1/H2)**b3) ]), consistent with the Allen et al.
    # (2020) parent. This pins the corrected form and guards against the typo.
    species = Maleki2022Species.NORWAY_SPRUCE
    b1, b2, b3 = 0.4159, 2.0096, 0.7521
    g1, n1, n2 = 18.0, 1000.0, 850.0
    a1, a2 = Age.TOTAL(30.0), Age.TOTAL(60.0)

    # Reuse the model's own height trajectory (H40 = 20 m at reference age 40) so
    # the oracle isolates the basal-area equation form, not the height inputs.
    h1 = maleki_2022_height_trajectory(species, 20.0, Age.TOTAL(40.0), a1)
    h2 = maleki_2022_height_trajectory(species, 20.0, Age.TOTAL(40.0), a2)
    ratio_h, ratio_n = h1 / h2, n2 / n1

    single_b2 = (g1 ** (ratio_h**b1)) * math.exp(b2 * ratio_n * (1.0 - ratio_h**b3))
    double_b2 = (g1 ** (ratio_h**b1)) * math.exp((b2**ratio_n) * b2 * (1.0 - ratio_h**b3))

    projected = maleki_2022_basal_area_projection(
        species, StandBasalArea(g1), a1, a2, _si_h40(), Stems(n1), Stems(n2)
    )
    assert float(projected) == pytest.approx(single_b2, rel=1e-12)
    # Guard: the printed double-b2 typo yields a materially different number.
    assert float(projected) != pytest.approx(double_b2, rel=1e-6)


def test_maleki_model_facade_delegates():
    model = Maleki2022ModelNorway()

    direct = maleki_2022_stand_volume(
        Maleki2022Species.NORWAY_SPRUCE,
        dominant_height_m=18.0,
        basal_area=StandBasalArea(20.0),
        age=Age.TOTAL(40.0),
    )
    via_picea = model.picea_abies.get_stand_volume(18.0, StandBasalArea(20.0), Age.TOTAL(40.0))
    via_attr = model.norway_spruce.get_stand_volume(18.0, StandBasalArea(20.0), Age.TOTAL(40.0))
    assert float(direct) == pytest.approx(float(via_picea))
    assert float(direct) == pytest.approx(float(via_attr))

    pine_prob = model.pinus_sylvestris.get_ingrowth_probability(
        QuadraticMeanDiameter(17.0),
        Stems(850.0),
    )
    spruce_survival = model.norway_spruce.get_stem_survival(
        Age.TOTAL(30.0),
        Age.TOTAL(35.0),
        Stems(1000.0),
        _si_h40(),
    )
    pine_density = model.scots_pine.get_stem_density(
        Age.TOTAL(30.0),
        Age.TOTAL(35.0),
        Stems(1000.0),
        _si_h40(),
    )
    broad_height = model.broadleaves.get_height_trajectory(18.0, Age.TOTAL(30.0), Age.TOTAL(35.0))
    broad_ba = model.broadleaves.get_basal_area_projection(
        StandBasalArea(15.0),
        Age.TOTAL(30.0),
        Age.TOTAL(35.0),
        _si_h40(),
        Stems(900.0),
        Stems(850.0),
    )
    broad_count = model.broadleaves.get_ingrowth_count(qmd=QuadraticMeanDiameter(19.0))
    assert 0.0 <= pine_prob <= 1.0
    assert spruce_survival >= 0.0
    assert pine_density >= 0.0
    assert broad_height >= 0.0
    assert broad_ba >= 0.0
    assert broad_count >= 0.0


def test_maleki_growth_model_adapter_projection():
    stand = Stand(
        plots=[
            CircularPlot(
                id="p1",
                area_m2=400.0,
                trees=[
                    Tree(
                        species=TreeSpecies.Norway.picea_abies,
                        diameter_cm=20.0,
                        weight_n=80.0,
                    )
                ],
            )
        ]
    )
    model = Maleki2022GrowthModel(
        Maleki2022Config(
            species=Maleki2022Species.NORWAY_SPRUCE,
            h40_m=20.0,
            dominant_height_m=14.0,
            start_total_age_years=30.0,
        )
    )
    ctx = model.build_context(stand)

    model.update_step(ctx, dt=5.0)

    assert float(ctx.state["t"]) == pytest.approx(35.0)
    assert float(ctx.attrs["dominant_height_m"]) > 0.0
    assert float(ctx.attrs["stand_volume_m3_per_ha"]) >= 0.0
    assert float(ctx.metrics["BasalArea"]["TOTAL"]) >= 0.0
    assert float(ctx.metrics["Stems"]["TOTAL"]) >= 0.0
