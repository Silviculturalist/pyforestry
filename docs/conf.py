import os
import sys
# 1. Tell Sphinx where to find your code:
sys.path.insert(0, os.path.abspath('../src'))

# -- Project information -----------------------------------------------------
project = 'MyProject'
author = 'Your Name'
# Pull version/version info from your package if you want:
# from your_package import __version__ as release

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',    # for docstrings
    'sphinx.ext.napoleon',   # Google/NumPy style docstrings
    'sphinx.ext.viewcode',   # add links to highlighted source
]
#templates_path = ['_templates']  # if you have custom Jinja2 templates
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
html_theme = 'alabaster'  # or 'sphinx_rtd_theme', etc.
html_static_path = ['_static']
