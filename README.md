[![CI](https://github.com/Silviculturalist/pyforestry/actions/workflows/ci.yml/badge.svg?event=push)](https://github.com/Silviculturalist/pyforestry/actions/workflows/ci.yml) [![codecov](https://codecov.io/gh/Silviculturalist/pyforestry/branch/main/graph/badge.svg?token=2C3Z6NXHA4)](https://codecov.io/gh/Silviculturalist/pyforestry) ![Docstring Coverage](.docstring_coverage.svg)

## Documentation: [Available](https://silviculturalist.github.io/pyforestry/)

This package is currently under *very early* development.
Use at your own risk. 

Any corrections, comments, suggestions are greatly appreciated.

## Introduction


`pyforestry` is a Python package for forest science, providing a standardized, open-source collection of models and functions. Many forest simulators are difficult to replicate, incur a language barrier, are hard to access, and use inconsistent units and variable names. By standardizing these components in a modern framework, we can easily swap out data, functions, and simulation models, or run them side-by-side for validation and comparison.

## Installation

You can install the latest development version of `pyforestry` directly from GitHub using `pip`.

```bash
pip install git+[https://github.com/](https://github.com/)<Silviculturalist>/pyforestry.git
```

## Goal
The goal of this GitHub repository is to be a center to:

-   Digitalise legacy forest science functions and models.
-   Review, discuss, validate, and update these functions in an open, collaborative environment.
-   Maintain robust version control and clear, accessible documentation.

We are developing object-oriented structures for trees, stands, sites, and treatments, allowing pyforestry to grow into a stand-alone simulator. As the project progresses, we envision it becoming part of a larger ecosystem of open-source tools for forest science, with standardized variable names and a shared philosophy, welcoming contributions from all over the world.

## Why pyforestry?

This package aims to remedy several issues found in earlier stand simulators:
-   Modern Documentation: Python docstrings, combined with tools like Sphinx, create documentation that is structured, discoverable, and integrated with the code.
-   Open-Source Collaboration: Issues can be identified, discussed, and solved transparently by the community through GitHub.
-   No "Black Boxes": The user has full control and visibility over all processes and calculations.
-   Future-Proof: By using a popular, modern language and open standards, the material is less at risk of becoming obsolete due to technical issues.
-   Trust and Transparency: Trust in the collection is built and maintained through its open-source nature.

# What's included?

The package includes:

-   Tutorials and Examples: Jupyter Notebooks and other guides demonstrating usage.
-   Modules and Functions: A growing collection of functions for forest growth and yield.
-   Documentation: Every function and class is documented with examples. The documentation is available online and searchable.
-   Data: So far, mostly older published datasets for testing and validation.