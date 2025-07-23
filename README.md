# pyforestry

[![CI](https://github.com/Silviculturalist/pyforestry/actions/workflows/ci.yml/badge.svg?event=push)](https://github.com/Silviculturalist/pyforestry/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/Silviculturalist/pyforestry/branch/main/graph/badge.svg?token=2C3Z6NXHA4)](https://codecov.io/gh/Silviculturalist/pyforestry)
![Docstring Coverage](.docstring_coverage.svg)

## Documentation
[Available online](https://silviculturalist.github.io/pyforestry/)

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
from pyforestry.base.helpers import CircularPlot, Tree, Stand, parse_tree_species

plot = CircularPlot(id=1, radius_m=5.0, trees=[
    Tree(species=parse_tree_species("picea abies"), diameter_cm=20),
])
stand = Stand(plots=[plot])
print(stand.BasalArea.TOTAL.value)
```

## Contributing
Please see the [contributing guidelines](CONTRIBUTING.md) for tips on setting up your development
environment and submitting pull requests.

## License
`pyforestry` is distributed under the terms of the [MIT License](LICENSE).
