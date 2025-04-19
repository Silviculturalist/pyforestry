This package is currently under *very early* development.
Use at your own risk.

Any corrections, comments, suggestions are greatly appreciated.

Carl Vigren 2024-12-18

## Package Structure

The `Munin` package is organized into several submodules, generally categorized by forestry domain (e.g., Volume, SiteIndex, Growth) and often further subdivided by region (e.g., `sweden`, `norway`) or specific model authors.

* **`/src/Munin/`**: Root directory for the package source code.
    * **`/Bark/`**: Contains models for calculating bark thickness.
        * `/sweden/`: Swedish bark models (e.g., `Hannrup_2004.py`).
        * `/norway/`: Norwegian bark models (e.g., `Hansen_2023.py`, `Braastad_1966...py`).
    * **`/Biomass/`**: Contains models for estimating tree biomass components.
        * `/sweden/`: Swedish biomass models (e.g., `Marklund1988.py`, `Petersson_Stahl_2006.py`).
    * **`/Geo/`**: Geographic and climatic helper utilities and data. Includes functions for humidity, temperature sums, distance to coast, and retrieving climate/county codes.
        * `/Climate/`, `/Coastline/`, `/Counties/`, `/Humidity/`, `/Temperature/`: Subdirectories often containing shapefiles or specific model implementations (e.g., `Odin_1983.py`, `eriksson_1986.py`).
    * **`/Growth/`**: Contains models for predicting tree and stand growth (e.g., Basal Area Increment).
        * `/sweden/`: Swedish growth models, often organized by author (e.g., `/Soderberg/`, `/Elfving/`, `/Eko/`, `/Pettersson_1992.py`).
    * **`/Helpers/`**: Core data structures, base classes, and utility functions used throughout the package.
        * `Primitives.py`: Defines fundamental units and types like `Diameter_cm`, `AgeMeasurement`, `Volume`, `SiteIndexValue`, `Position`, `TreeName`, etc.
        * `Base.py`: Defines structures for representing plots and stands (e.g., `CircularPlot`, `Stand`, `RepresentationTree`).
        * `TreeSpecies.py`: Defines tree species taxonomy (`TreeName`, `TreeGenus`) and provides regional species lists (`TreeSpecies.Sweden`).
    * **`/Models/`**: Contains more complex, potentially integrated stand-level models.
        * `/norway/`: Norwegian models (e.g., `Kuehne_2022.py`).
    * **`/PriceList/`**: Functionality for handling timber price lists.
        * `/Data/`: Contains specific price list data (e.g., `Mellanskog_2013.py`).
        * `PriceList.py`: Defines the `Pricelist` structure.
    * **`/Site/`**: Classes for representing site conditions.
        * `SiteBase.py`: Abstract base class for site information.
        * `/sweden/`: Swedish site implementation (`SwedishSite.py`), including enums for vegetation, soil, county etc.
    * **`/SiteIndex/`**: Models for site index estimation and translation.
        * `/sweden/`: Swedish site index functions (e.g., `Hagglund_1970.py`, `Elfving_Kiviste_1997.py`). Includes submodules for SIS (Site Index from Site Factors) and translation between species.
        * `/norway/`: Norwegian site index functions (e.g., `Tveite_1976.py`, `Sharma_2011.py`, `Kuehne_2022.py`).
    * **`/Taper/`**: Functions defining tree stem taper.
        * `Taper.py`: Base class for taper models.
        * `/sweden/`: Swedish taper models (e.g., `EdgrenNylinder1949.py`).
        * `/norway/`: Norwegian taper models (e.g., `Hansen_2023.py`).
    * **`/Timber/`**: Classes for representing individual trees or logs.
        * `Timber.py`: Base `Timber` class.
        * `SweTimber.py`: Swedish-specific timber class.
        * `TimberVolumeIntegrator.py`: Utility for volume calculation via integration.
    * **`/TimberBucking/`**: Algorithms for optimizing timber cross-cutting.
        * `Bucker.py`: Base class for bucking algorithms.
        * `Nasberg_1985.py`: Implementation of Näsberg's algorithm.
    * **`/Volume/`**: Functions for calculating tree volume.
        * `/sweden/`: Swedish volume functions (e.g., `Brandel1990.py`, `Naslund1947.py`, `Eriksson_1973.py`).
        * `/norway/`: Norwegian volume functions (e.g., `Vestjordet_1967.py`, `Braastad_1966.py`).
    * `__init__.py`: Initializes the `Munin` package.

* **`/tests/`**: Contains unit tests for various modules (e.g., `test_volume.py`, `test_taper.py`, `test_SiteIndex.py` etc.).

## Naming Conventions

The package aims to follow these naming conventions:

* **Classes and Structures**: `CamelCase` (e.g., `SwedishSite`, `TimberPricelist`, `AgeMeasurement`).
* **Functions**: `snake_case` (e.g., `get_volume_log`, `calculate_humidity`, `parse_tree_species`). This includes functions exposed as methods on classes or wrappers (e.g., `Hagglund_1970.height_trajectory.picea_abies.northern_sweden`).
* **Constants and Enums**: `ALL_CAPS` (e.g., `NORTHERN_COUNTY_CODES`, `Age.TOTAL`, `PICEA_ABIES`).
* **Modules and Packages**: Generally `snake_case` or `CamelCase` (e.g., `Volume`, `SiteIndex`, `Helpers`, `Brandel1990.py`).

## Model Interfaces

Where appropriate, models providing similar functionality (e.g., site index calculation) are grouped. For example, site index functions might be accessible via interfaces like `Munin.SiteIndex.sweden.Hagglund_1970` or `Munin.SiteIndex.norway.Kuehne_2022`. Models themselves might be implemented in dedicated files within submodules, such as `Munin/Models/norway/Kuehne_2022.py`.