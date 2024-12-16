from setuptools import setup, find_packages

setup(
    name="Munin",
    version="0.1",
    author="Carl Vigren",
    author_email="carl.vigren@slu.se",
    url = "https://github.com/Silviculturalist/Munin",
    packages=['Munin']+find_packages(),
    include_package_data=True,
    package_data={
        "Munin.Geo.Humidity": ["humidity.shp"],
        "Munin.Geo.Climate": ["Klimat.shp"],
        "Munin.Geo.Coastline": ["SwedishCoastLine_NE_medium_clipped.shp"],
        "Munin.Geo.Counties" : ["RT_Dlanskod.shp"] 
    },
    python_requires = ">3.10",
    install_requires = [
        "geopandas",
        "shapely",
        "pyproj"
    ]
)
