import pytest

from pyforestry.base.helpers.primitives import AtomicVolume, Diameter_cm
from pyforestry.base.helpers.tree_species import TreeSpecies
from pyforestry.norway.volume import (
    braastad_1966_birch_volume_norway,
    brantseg_1967_volume_scots_pine_norway,
    opdahl_1989_volume_aspen_norway,
    vestjordet_1967_volume_norway_spruce_norway,
    vestjordet_1967_volume_tree_top,
)
from pyforestry.norway.volume.vestjordet_1967 import default_bark_thickness_for_species


def test_brantseg_volume_branches_and_metadata():
    low = brantseg_1967_volume_scots_pine_norway(15.0, 10.0)
    high = brantseg_1967_volume_scots_pine_norway(15.0, 20.0)
    under = brantseg_1967_volume_scots_pine_norway(
        15.0,
        20.0,
        bark_thickness_cm=1.0,
        with_bark=False,
    )
    assert isinstance(low, AtomicVolume)
    assert low.region == "Norway"
    assert low.type == "m3sk"
    assert low.species == TreeSpecies.Norway.pinus_sylvestris.full_name
    assert low.value > 0
    assert high.value > low.value
    assert under.value > 0
    with pytest.raises(ValueError):
        brantseg_1967_volume_scots_pine_norway(1.0, 10.0)
    with pytest.raises(TypeError):
        brantseg_1967_volume_scots_pine_norway(10.0, "10")  # type: ignore[arg-type]

    with pytest.warns(UserWarning):
        by_diameter_obj = brantseg_1967_volume_scots_pine_norway(
            15.0,
            Diameter_cm(20.0, over_bark=True, measurement_height_m=2.0),
        )
    assert by_diameter_obj.value > 0.0

    with pytest.raises(ValueError):
        brantseg_1967_volume_scots_pine_norway(15.0, Diameter_cm(20.0, over_bark=False))
    with pytest.raises(TypeError):
        brantseg_1967_volume_scots_pine_norway(
            15.0,
            20.0,
            bark_thickness_cm="x",  # type: ignore[arg-type]
            with_bark=False,
        )
    with pytest.raises(ValueError):
        brantseg_1967_volume_scots_pine_norway(
            15.0,
            20.0,
            bark_thickness_cm=-1.0,
            with_bark=False,
        )
    assert (
        brantseg_1967_volume_scots_pine_norway(
            15.0,
            20.0,
            bark_thickness_cm=25.0,
            with_bark=False,
        ).value
        == 0.0
    )
    assert brantseg_1967_volume_scots_pine_norway(15.0, 0.0).value == 0.0
    with pytest.raises(ValueError):
        brantseg_1967_volume_scots_pine_norway(15.0, -1.0)


def test_braastad_volume_species_and_zero_paths():
    species = TreeSpecies.Norway.betula_pendula
    volume = braastad_1966_birch_volume_norway(20.0, Diameter_cm(25.0), species)
    assert isinstance(volume, AtomicVolume)
    assert volume.species == species.full_name
    assert volume.value > 0

    zero = braastad_1966_birch_volume_norway(
        20.0,
        5.0,
        species,
        bark_thickness_cm=10.0,
        with_bark=False,
    )
    assert zero.value == 0.0

    with pytest.raises(ValueError):
        braastad_1966_birch_volume_norway(20.0, 10.0, TreeSpecies.Norway.picea_abies)
    with pytest.raises(TypeError):
        braastad_1966_birch_volume_norway(20.0, 10.0, species, bark_thickness_cm="1")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        braastad_1966_birch_volume_norway(20.0, Diameter_cm(10.0, over_bark=False), species)
    with pytest.warns(UserWarning):
        by_diameter_obj = braastad_1966_birch_volume_norway(
            20.0,
            Diameter_cm(20.0, over_bark=True, measurement_height_m=2.0),
            species,
        )
    assert by_diameter_obj.value > 0.0
    with pytest.raises(TypeError):
        braastad_1966_birch_volume_norway(20.0, object(), species)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        braastad_1966_birch_volume_norway(20.0, -1.0, species)
    with pytest.raises(ValueError):
        braastad_1966_birch_volume_norway(1.0, 10.0, species)
    with pytest.raises(ValueError):
        braastad_1966_birch_volume_norway(
            20.0,
            10.0,
            species,
            bark_thickness_cm=-1.0,
            with_bark=False,
        )
    assert braastad_1966_birch_volume_norway(20.0, 0.0, species).value == 0.0


def test_opdahl_volume_paths():
    species = TreeSpecies.Norway.populus_tremula
    low_height = opdahl_1989_volume_aspen_norway(1.0, 20.0, species)
    assert low_height.value == 0.0

    with pytest.warns(UserWarning):
        under = opdahl_1989_volume_aspen_norway(20.0, 20.0, species, with_bark=False)
    assert under.value >= 0.0

    with pytest.raises(ValueError):
        opdahl_1989_volume_aspen_norway(20.0, 20.0, TreeSpecies.Norway.picea_abies)
    with pytest.raises(TypeError):
        opdahl_1989_volume_aspen_norway(
            20.0,
            20.0,
            species,
            bark_thickness_cm="x",
            with_bark=False,
        )  # type: ignore[arg-type]
    with pytest.warns(UserWarning):
        by_diameter_obj = opdahl_1989_volume_aspen_norway(
            20.0,
            Diameter_cm(20.0, over_bark=True, measurement_height_m=2.0),
            species,
        )
    assert by_diameter_obj.value > 0.0
    with pytest.raises(ValueError):
        opdahl_1989_volume_aspen_norway(20.0, Diameter_cm(20.0, over_bark=False), species)
    with pytest.raises(TypeError):
        opdahl_1989_volume_aspen_norway(20.0, object(), species)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        opdahl_1989_volume_aspen_norway(20.0, -1.0, species)
    with pytest.raises(ValueError):
        opdahl_1989_volume_aspen_norway(
            20.0,
            20.0,
            species,
            bark_thickness_cm=-1.0,
            with_bark=False,
        )
    assert (
        opdahl_1989_volume_aspen_norway(
            20.0,
            10.0,
            species,
            bark_thickness_cm=20.0,
            with_bark=False,
        ).value
        == 0.0
    )
    assert opdahl_1989_volume_aspen_norway(20.0, 0.0, species).value == 0.0


def test_vestjordet_volume_branches_and_tree_top():
    species = TreeSpecies.Norway.picea_abies
    v1 = vestjordet_1967_volume_norway_spruce_norway(15.0, 9.0)
    v2 = vestjordet_1967_volume_norway_spruce_norway(15.0, 11.0)
    v3 = vestjordet_1967_volume_norway_spruce_norway(15.0, 15.0)
    v_ub = vestjordet_1967_volume_norway_spruce_norway(
        15.0,
        15.0,
        bark_thickness_cm=1.0,
        with_bark=False,
    )
    assert all(v.value >= 0.0 for v in (v1, v2, v3, v_ub))
    assert v3.value > v1.value

    top_spruce = vestjordet_1967_volume_tree_top(species, 20.0, 20.0, over_bark=True)
    top_spruce_ub = vestjordet_1967_volume_tree_top(species, 20.0, 20.0, over_bark=False)
    top_pine = vestjordet_1967_volume_tree_top(TreeSpecies.Norway.pinus_sylvestris, 20.0, 20.0)
    assert top_spruce.value > 0.0
    assert top_spruce_ub.value > 0.0
    assert top_pine.value > 0.0

    with pytest.raises(ValueError):
        vestjordet_1967_volume_tree_top(
            species,
            Diameter_cm(20.0, over_bark=False),
            20.0,
            over_bark=True,
        )
    with pytest.raises(ValueError):
        vestjordet_1967_volume_tree_top(species, 20.0, -1.0)
    with pytest.warns(UserWarning):
        top_spruce_warn = vestjordet_1967_volume_tree_top(
            species,
            Diameter_cm(20.0, over_bark=True, measurement_height_m=2.0),
            20.0,
            over_bark=True,
        )
    assert top_spruce_warn.value > 0.0
    with pytest.raises(TypeError):
        vestjordet_1967_volume_tree_top(species, object(), 20.0)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        vestjordet_1967_volume_tree_top(species, -1.0, 20.0)
    top_pine_ub = vestjordet_1967_volume_tree_top(
        TreeSpecies.Norway.pinus_sylvestris,
        20.0,
        20.0,
        over_bark=False,
    )
    assert top_pine_ub.value > 0.0

    with pytest.warns(UserWarning):
        v_warn = vestjordet_1967_volume_norway_spruce_norway(
            15.0,
            Diameter_cm(15.0, over_bark=True, measurement_height_m=2.0),
        )
    assert v_warn.value > 0.0
    with pytest.raises(ValueError):
        vestjordet_1967_volume_norway_spruce_norway(15.0, Diameter_cm(15.0, over_bark=False))
    with pytest.raises(TypeError):
        vestjordet_1967_volume_norway_spruce_norway(15.0, object())  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        vestjordet_1967_volume_norway_spruce_norway(15.0, -1.0)
    with pytest.raises(ValueError):
        vestjordet_1967_volume_norway_spruce_norway(1.0, 10.0)
    with pytest.raises(TypeError):
        vestjordet_1967_volume_norway_spruce_norway(
            15.0,
            15.0,
            bark_thickness_cm="x",  # type: ignore[arg-type]
            with_bark=False,
        )
    with pytest.raises(ValueError):
        vestjordet_1967_volume_norway_spruce_norway(
            15.0,
            15.0,
            bark_thickness_cm=-1.0,
            with_bark=False,
        )
    assert (
        vestjordet_1967_volume_norway_spruce_norway(
            15.0,
            10.0,
            bark_thickness_cm=20.0,
            with_bark=False,
        ).value
        == 0.0
    )
    assert vestjordet_1967_volume_norway_spruce_norway(15.0, 0.0).value == 0.0


def test_default_bark_thickness_by_species():
    spruce = default_bark_thickness_for_species(TreeSpecies.Norway.picea_abies, 20.0)
    pine = default_bark_thickness_for_species(TreeSpecies.Norway.pinus_sylvestris, 20.0)
    birch = default_bark_thickness_for_species(TreeSpecies.Norway.betula_pendula, 20.0)
    assert spruce >= 0
    assert pine >= 0
    assert birch >= 0
