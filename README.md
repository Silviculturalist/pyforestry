# pyforestry

[![CI](https://github.com/Silviculturalist/pyforestry/actions/workflows/ci.yml/badge.svg?event=push)](https://github.com/Silviculturalist/pyforestry/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/Silviculturalist/pyforestry/branch/main/graph/badge.svg?token=2C3Z6NXHA4)](https://codecov.io/gh/Silviculturalist/pyforestry)
![Docstring Coverage](.docstring_coverage.svg)

## Documentation
[Available online](https://silviculturalist.github.io/pyforestry/)

- [Architecture responsibility and context boundary policy](ARCHITECTURE.md)
  defines package ownership boundaries and migration guardrails.
- [Architecture overview](https://silviculturalist.github.io/pyforestry/architecture.html)
  mirrors the architecture policy in the published documentation.

This package is currently under *very early* development.
Use at your own risk. Any corrections, comments, and suggestions are greatly appreciated.

`pyforestry` is a Python toolkit for forest science. It collects a variety of growth and yield models
and provides modern data structures for working with tree and stand information. By standardising
units and variable names across models we aim to make comparisons and validations straightforward.

## Features
- Object oriented helpers for trees, stands and circular plots
- Site index and climate utilities for Swedish forestry
- Timber pricing, taper and bucking functions
- Example notebooks and small reference datasets

## Installation
Install the latest development version directly from GitHub:

```bash
pip install git+https://github.com/Silviculturalist/pyforestry.git
```

For development work clone the repository and install with the optional `dev` dependencies:

```bash
git clone https://github.com/Silviculturalist/pyforestry.git
cd pyforestry
pip install -e .[dev]
```

## Quick example
```python
import pyforestry as pf

plot = pf.CircularPlot(id=1, radius_m=5.0, trees=[
    pf.Tree(species="picea abies", diameter_cm=20),
])
stand = pf.Stand(plots=[plot])
print(stand.BasalArea.TOTAL.value)
```

## Projecting a stand
One call runs a published growth model forward and hands back a table, the final
stand, and the citations behind both:

```python
import pyforestry as pf

result = pf.project(stand, model="elfving_2010", years=100, step=5, seed=42)

result.table        # a DataFrame, one row per step
result.stand        # the final state
result.provenance   # every component that was cited, by component id

pf.available_models()   # every name `model=` accepts
```

`step` defaults to the period the model was fitted for, so you only pass it when
you want something else. The stand you hand in is not modified, so the same stand
can be projected under several models and compared. For finer control, pass a
management `policy` or an explicit `pipeline` of steps; the typed constructors
(`Elfving2010Model`, `build_context`, `run_pipeline`) all remain available.

## Projecting from a site: composite pipelines

`project` advances a stand you already have. When you have a *site* instead and
want a stand reconstructed and grown through a whole published workflow —
regeneration, NYSKOG stand creation, young-stand growth, mortality, ingrowth,
height and bark, valuation — that is a composite pipeline. It builds its own
stand, which is why `project` cannot drive one:

```python
from pyforestry.sweden.simulation.presets import get_pipeline

pipeline = get_pipeline("elfving_2010_composite")
table = pipeline.run_projection(site=site, n_steps=20)

pf.available_pipelines()   # every name `get_pipeline` accepts
```

The two namespaces are deliberately distinct: `"elfving_2010"` is the single-tree
growth model, `"elfving_2010_composite"` the workflow that drives it alongside
nine other published models.

## Finding a model
With 60+ growth, yield, volume, bark, biomass, and site-index models, the model
catalog lets you discover them without knowing the import path or citation:

```python
from pyforestry import catalog

catalog.find(domain="volume", species="Picea abies")  # volume models for spruce
catalog.search("brandel")                              # by id / author / title
catalog.describe("brandel_1990_volume").source         # citation
catalog.regions()                                      # ['norway', 'sweden']
```

## Contributing
Please see the [contributing guidelines](CONTRIBUTING.md) for tips on setting up your development
environment and submitting pull requests.

## Sponsors
This project has been sponsored by [Digital Impact North](https://www.digitalimpactnorth.se).

![Digital Impact North](docs/images/DIN_logotyp_primar_gron.png)

## License
`pyforestry` is distributed under the terms of the [MIT License](LICENSE).
