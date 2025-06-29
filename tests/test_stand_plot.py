import pytest
from shapely.geometry import Point, Polygon
import random

from Munin.Helpers import (
    CircularPlot,
    Diameter_cm,
    Stand,
    parse_tree_species,
    RepresentationTree,
    AngleCount,
    AngleCountAggregator,
    Position,
    TreeSpecies,
    Stems,
    StandBasalArea,
    AtomicVolume,
    CompositeVolume
)
import math
from pyproj import CRS

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
    st = Stand(polygon=poly,crs=CRS('EPSG:3006'))
    assert st.area_ha is not None
    assert math.isclose(st.area_ha, 1.0, rel_tol=1e-3)

def test_stand_polygon_mismatch_value_error():
    """Check that a mismatch in user area_ha vs. polygon area triggers a ValueError."""
    poly = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])  # 10000 m² => 1 ha
    with pytest.raises(ValueError, match='Polygon area is 1.00 ha, but you set area_ha=2.00 ha.'):
        st = Stand(polygon=poly, crs=CRS('EPSG:3006'), area_ha=2.0)


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

def test_metric_value_property():
    ba = StandBasalArea(30.0, species=parse_tree_species('picea abies'), precision=2.5)
    s = Stems(100, species=parse_tree_species('picea abies'), precision=5)
    # Using the .value property we added
    assert ba.value == 30.0
    assert s.value == 100

# --- AngleCount add_observation tests ---
def test_angle_count_add_observation():
    sp1 = parse_tree_species("picea abies")
    ac = AngleCount(ba_factor=2.0, value=[1], species=[sp1], point_id="P1")
    ac.add_observation(sp1, 2)
    # Expecting 1 + 2 = 3 for the first (and only) species entry
    assert ac.value[0] == 3

# --- AngleCount merging tests ---
def test_angle_count_merging():
    sp1 = parse_tree_species("picea abies")
    ac1 = AngleCount(ba_factor=2.0, value=[4], species=[sp1], point_id="P1")
    ac2 = AngleCount(ba_factor=2.0, value=[6], species=[sp1], point_id="P1")
    aggregator = AngleCountAggregator(records=[ac1, ac2])
    merged = aggregator.merge_by_point_id()
    # Merging by averaging: (4 + 6) / 2 = 5
    assert len(merged) == 1
    merged_record = merged[0]
    assert math.isclose(merged_record.value[0], 5)

# --- Aggregate stand metrics tests ---
def test_aggregate_stand_metrics():
    sp1 = parse_tree_species("picea abies")
    sp2 = parse_tree_species("pinus sylvestris")
    # Create two AngleCount records with different values and distinct point_ids.
    ac1 = AngleCount(ba_factor=2.0, value=[4, 2], species=[sp1, sp2], point_id="P1")
    ac2 = AngleCount(ba_factor=2.0, value=[6, 3], species=[sp1, sp2], point_id="P2")
    aggregator = AngleCountAggregator(records=[ac1, ac2])
    ba_dict, stems_dict = aggregator.aggregate_stand_metrics()
    # For sp1: counts = [4, 6] → mean = 5, variance = 1.
    # Basal area = 5*2 = 10; precision = sqrt(1)*2 = 2.
    assert math.isclose(ba_dict[sp1].value, 10.0)
    assert math.isclose(ba_dict[sp1].precision, 2.0)
    # For sp2: counts = [2, 3] → mean = 2.5, variance = 0.25.
    # Basal area = 2.5*2 = 5; precision = sqrt(0.25)*2 = 1.
    assert math.isclose(ba_dict[sp2].value, 5.0)
    assert math.isclose(ba_dict[sp2].precision, 1.0)
    # For Stems, raw counts are used.
    assert math.isclose(stems_dict[sp1].value, 5.0)
    assert math.isclose(stems_dict[sp1].precision, 1.0)
    assert math.isclose(stems_dict[sp2].value, 2.5)
    assert math.isclose(stems_dict[sp2].precision, math.sqrt(0.25))
    # Check that overall "TOTAL" is present.
    assert "TOTAL" in ba_dict and "TOTAL" in stems_dict

# --- Volume conversion tests ---
def test_volume_conversion():
    vol = AtomicVolume(1, region="Sweden", species="Picea_abies",type='m3sk')
    # 1 m3 = 1000 dm3
    assert math.isclose(vol.to('dm3'), 1000, rel_tol=1e-6)

# --- Dominant height measurement test ---
def test_get_dominant_height():
    sp = parse_tree_species("picea abies")
    # Create three trees with heights.
    tree1 = RepresentationTree(species=sp, diameter_cm=30, height_m=20)
    tree2 = RepresentationTree(species=sp, diameter_cm=35, height_m=22)
    tree3 = RepresentationTree(species=sp, diameter_cm=25, height_m=18)
    # Two plots with the same area (radius_m=10)
    plot1 = CircularPlot(id=1, radius_m=10, trees=[tree1, tree2])
    plot2 = CircularPlot(id=2, radius_m=10, trees=[tree1, tree3])
    st = Stand(plots=[plot1, plot2])
    dominant_height = st.get_dominant_height()
    assert dominant_height is not None
    assert dominant_height > 0

# --- Negative diameter test ---
def test_negative_diameter_error():
    with pytest.raises(ValueError):
        Diameter_cm(-5)

# --- Multiple AngleCount objects in a CircularPlot ---
def test_multiple_angle_counts_in_plot():
    sp = parse_tree_species("picea abies")
    ac1 = AngleCount(ba_factor=2.0, value=[3], species=[sp], point_id="P1")
    ac2 = AngleCount(ba_factor=2.0, value=[5], species=[sp], point_id="P1")
    plot = CircularPlot(id=1, radius_m=5, AngleCount=[ac1, ac2])
    aggregator = AngleCountAggregator(records=plot.AngleCount)
    merged = aggregator.merge_by_point_id()
    # With averaging: (3 + 5) / 2 = 4.
    assert len(merged) == 1
    assert math.isclose(merged[0].value[0], 4)

# --- StandMetricAccessor species key error test ---
def test_stand_metric_accessor_species_keyerror():
    st = Stand(plots=[])
    with pytest.raises(ValueError):
        _ = st.BasalArea("nonexistent species")


# --- Test H-T estimator with RepresentationTrees ---

# Use the existing diameter-height relation from the bias function:
def compute_height(d_cm: float) -> float:
    d_m = d_cm / 100.0
    return 1.3 + (d_m ** 2) / ((1.1138 + 0.2075 * d_m) ** 2)

def test_random_plots_on_stand():
    # Define a rectangular stand (200 m x 100 m)
    stand_polygon = Polygon([(0, 0), (200, 0), (200, 100), (0, 100)])
    
    # Parameters for plots and species
    r = 7.62  # plot radius in meters
    n_plots = 10

    # Species information:
    # For pinus_sylvestris: mean diameter = 20 cm, density = 600 per ha.
    # For picea_abies: mean diameter = 10 cm, density = 1200 per ha.
    d_pinus = 20  # cm
    d_picea = 10  # cm
    h_pinus = compute_height(d_pinus)
    h_picea = compute_height(d_picea)
    density_pinus = 600   # trees per ha
    density_picea = 1200  # trees per ha

    plots = []
    for i in range(n_plots):
        # Randomly choose a plot center within the bounding box [0,200] x [0,100]
        x = random.uniform(0, 200)
        y = random.uniform(0, 100)
        pos = Position(x, y, 0)
        # Create a shapely circle for the plot
        circle = Point(x, y).buffer(r)
        area_circle = circle.area  # in m²
        # Compute the intersection area with the stand polygon
        intersection = circle.intersection(stand_polygon)
        intersection_area = intersection.area
        # Occlusion: fraction of plot outside the stand.
        occlusion = max(0.0,min(1 - (intersection_area / area_circle),0.9999))
        # Create the plot. (The constructor requires occlusion to be in [0, 1))
        plot = CircularPlot(id=i+1, position=pos, radius_m=r, occlusion=occlusion)
        
        # Calculate the effective plot area in hectares:
        plot_area_ha = plot.area_ha  # total plot area in ha
        effective_area_ha = plot_area_ha * (1 - occlusion)
        
        # Expected number of trees = density (trees/ha) * effective area (ha)
        # Round to nearest integer for simulation.
        n_pinus = int(round(density_pinus * effective_area_ha))
        n_picea = int(round(density_picea * effective_area_ha))
        
        # Create RepresentationTree objects for each species.
        trees = []
        for _ in range(n_pinus):
            trees.append(RepresentationTree(
                species=TreeSpecies.Sweden.pinus_sylvestris,
                diameter_cm=d_pinus,
                height_m=h_pinus,
                weight=1.0
            ))
        for _ in range(n_picea):
            trees.append(RepresentationTree(
                species=TreeSpecies.Sweden.picea_abies,
                diameter_cm=d_picea,
                height_m=h_picea,
                weight=1.0
            ))
        plot.trees = trees
        plots.append(plot)
    
    # Create the stand with the polygon and the generated plots.
    stand = Stand(plots=plots, polygon=stand_polygon)
    
    # Get the aggregated metrics via the accessors.
    # (Since plots supply AngleCount data? – In this test, we use tree data, so the _compute_ht_estimates method is used.)
    ba_accessor = stand.BasalArea
    stems_accessor = stand.Stems
    
    # Extract species-level metrics:
    ba_pinus = ba_accessor(TreeSpecies.Sweden.pinus_sylvestris)
    ba_picea = ba_accessor(TreeSpecies.Sweden.picea_abies)
    stems_pinus = stems_accessor(TreeSpecies.Sweden.pinus_sylvestris)
    stems_picea = stems_accessor(TreeSpecies.Sweden.picea_abies)
    ba_total = ba_accessor.TOTAL
    stems_total = stems_accessor.TOTAL
    
    top_height = stand.get_dominant_height()

    qmd_total = stand.QMD.TOTAL
    qmd_pinus = stand.QMD(TreeSpecies.Sweden.pinus_sylvestris)
    qmd_picea = stand.QMD(TreeSpecies.Sweden.picea_abies)
       
    # Basic assertions: all values should be > 0.
    assert ba_pinus.value > 0
    assert ba_picea.value > 0
    assert ba_total.value > 0
    assert stems_pinus.value > 0
    assert stems_picea.value > 0
    assert stems_total.value > 0
    assert top_height is not None
    assert top_height.value > 0
    assert qmd_total.value > 0
    assert qmd_total.precision >0 
    assert qmd_picea.value > 0
    assert qmd_picea.precision > 0
    assert qmd_pinus.value > 0
    assert qmd_pinus.precision > 0
