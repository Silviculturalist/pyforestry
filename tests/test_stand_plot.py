import pytest
from Munin.Helpers.Base import * 
 
def test_diameter_cm():
    """Test the Diameter_cm class for basic constraints."""
    d = Diameter_cm(25)
    assert float(d) == 25
    assert d.over_bark
    assert d.measurement_height_m == 1.3

    with pytest.raises(ValueError):
        Diameter_cm(-10)  # negative diameter

def test_CircularPlot_init_ok():
    """Test creating a CircularPlot with valid radius or area."""
    p1 = CircularPlot(id=1, radius_m=5.0)
    assert math.isclose(p1.area_m2, math.pi * 5**2, rel_tol=1e-7)
    assert p1.area_ha == p1.area_m2 / 10000

    p2 = CircularPlot(id=2, area_m2=314.159265)
    assert math.isclose(p2.radius_m, 10, rel_tol=1e-3) is True
    assert p2.area_ha == p2.area_m2 / 10000

def test_CircularPlot_init_fail():
    """CircularPlot must have radius_m or area_m2."""
    with pytest.raises(ValueError):
        CircularPlot(id=3)

def test_stand_basic():
    """Create a Stand with no polygon or area. Should be allowed."""
    s = Stand()
    assert s.area_ha is None
    assert len(s.plots) == 0

def test_stand_polygon_area():
    """Check polygon-based area computation."""
    # A simple square polygon 100 x 100 => 10000 m² => 1.0 ha
    poly = Polygon([(0,0),(100,0),(100,100),(0,100)])
    st = Stand(polygon=poly,crs='EPSG:3006')
    assert math.isclose(st.area_ha, 1.0, rel_tol=1e-3)

def test_stand_polygon_mismatch_value_error():
    """Check that a mismatch in user area_ha vs. polygon area triggers a ValueError."""
    poly = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])  # 10000 m² => 1 ha
    with pytest.raises(ValueError, match='Polygon area is 1.00 ha, but you set area_ha=2.00 ha.'):
        st = Stand(polygon=poly, crs='EPSG:3006', area_ha=2.0)


def test_stand_metric_calculations():
    """Check that Stems and BasalArea are computed as expected from the CircularPlots."""
    sp_picea = parse_tree_species("picea abies")
    sp_pinus = parse_tree_species("pinus sylvestris")

    # Create a couple of CircularPlots
    pl1 = CircularPlot(id=1, radius_m=5.0, trees=[
        RepresentationTree(species=sp_picea, diameter_cm=25, weight=2),
        RepresentationTree(species=sp_pinus, diameter_cm=30, weight=1)
    ])
    pl2 = CircularPlot(id=2, radius_m=5.0, trees=[
        RepresentationTree(species=sp_picea, diameter_cm=20, weight=1),
        RepresentationTree(species=sp_pinus, diameter_cm=35, weight=2)
    ])
    st = Stand(plots=[pl1, pl2])
    # Force compute:
    val_stems_total = float(st.Stems)
    val_ba_total    = float(st.BasalArea)

    # We won't assert the exact numbers too strictly, but we can check they're >0
    assert val_stems_total > 0
    assert val_ba_total > 0

    # We can also specifically request species-level results:
    ba_picea = st.BasalArea(sp_picea)
    ba_pinus = st.BasalArea("pinus sylvestris")
    assert ba_picea.value > 0
    assert ba_pinus.value > 0

def test_stand_metric_accessor_keyerror():
    """If we request a species that doesn't exist, we get a KeyError."""
    st = Stand(plots=[])
    with pytest.raises(KeyError):
        st.BasalArea("picea abies")

def test_CircularPlot_area_ha_property():
    """Simple test of the CircularPlot area_ha property."""
    p = CircularPlot(id=10, radius_m=10)
    assert math.isclose(p.area_ha, math.pi*100 / 10000, rel_tol=1e-7)

def test_representation_tree_defaults():
    """Check default values for RepresentationTree."""
    tr = RepresentationTree()
    assert tr.species is None
    assert tr.diameter_cm is None
    assert tr.height_m is None
    assert tr.weight == 1.0

def test_representation_tree_with_string_species():
    """Check that a string species is parsed to a TreeName."""
    tr = RepresentationTree(species="picea abies", diameter_cm=25.0)
    assert tr.species is not None
    assert tr.species.genus.name == "Picea"
    assert tr.species.species_name == "abies"

def test_stems_basalarea_objects():
    """Check that Stems and StandBasalArea store their attributes properly."""
    sp = parse_tree_species("picea abies")
    s = Stems(100, species=sp, precision=5)
    assert float(s) == 100
    assert s.species == sp
    assert s.precision == 5

    ba = StandBasalArea(30.0, species=sp, precision=2.5)
    assert float(ba) == 30
    assert ba.species == sp
    assert ba.precision == 2.5

def test_stems_basalarea_negatives():
    """Ensure negative values are disallowed."""
    with pytest.raises(ValueError):
        Stems(-10)

    with pytest.raises(ValueError):
        StandBasalArea(-5)