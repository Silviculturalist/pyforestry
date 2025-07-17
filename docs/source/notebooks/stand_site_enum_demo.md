# Stand metrics and site enums

This notebook shows how to work with circular plots, site enums, and site index models.


```python
from pyforestry.base.helpers import CircularPlot, RepresentationTree, Stand, parse_tree_species

plot1 = CircularPlot(id=1, radius_m=5.0, trees=[
    RepresentationTree(species=parse_tree_species('picea abies'), diameter_cm=20),
    RepresentationTree(species=parse_tree_species('pinus sylvestris'), diameter_cm=25),
])
plot2 = CircularPlot(id=2, radius_m=5.0, trees=[
    RepresentationTree(species=parse_tree_species('picea abies'), diameter_cm=30),
])
stand = Stand(plots=[plot1, plot2])
stand.BasalArea.TOTAL.value, stand.Stems.TOTAL.value

```

Site enums help provide structured parameters.


```python
from pyforestry.base.helpers import enum_code
from pyforestry.sweden.site.enums import Sweden

enum_code(Sweden.SoilMoistureEnum.DRY), enum_code(Sweden.County.UPPSALA)

```


```python
from pyforestry.sweden.siteindex.sis.hagglund_lundmark_1979 import Hagglund_Lundmark_1979_SIS

sis = Hagglund_Lundmark_1979_SIS(
    species='Picea abies',
    latitude=60,
    altitude=100,
    soil_moisture=Sweden.SoilMoistureEnum.MESIC,
    ground_layer=Sweden.BottomLayer.FRESH_MOSS,
    vegetation=Sweden.FieldLayer.BILBERRY,
    soil_texture=Sweden.SoilTextureTill.SANDY,
    climate_code=Sweden.ClimateZone.K1,
    lateral_water=Sweden.SoilWater.SELDOM_NEVER,
    soil_depth=Sweden.SoilDepth.DEEP,
    incline_percent=5,
    aspect=0,
    nfi_adjustments=True,
    dlan=Sweden.County.UPPSALA,
    peat=False,
    gotland=False,
    coast=False,
    limes_norrlandicus=False,
)
float(sis)

```

Geographic utilities and climate calculations.


```python
from pyforestry.sweden.geo import Moren_Perttu_radiation_1994, RetrieveGeoCode

RetrieveGeoCode.getDistanceToCoast(14.784528, 56.892405)
RetrieveGeoCode.getClimateCode(14.784528, 56.892405)

```


```python
calc = Moren_Perttu_radiation_1994(latitude=60, altitude=100, july_avg_temp=17, jan_avg_temp=-8)
calc.calculate_temperature_sum_1000m(threshold_temperature=5), calc.get_corrected_temperature_sum(threshold_temperature=5)

```
