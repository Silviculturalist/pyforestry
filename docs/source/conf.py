import os
import sys

import pypandoc

# Ensure pandoc is available for nbsphinx and put it on PATH when possible.
pandoc_path = None
try:
    pandoc_path = pypandoc.get_pandoc_path()
except OSError:
    try:
        pypandoc.download_pandoc()
        pandoc_path = pypandoc.get_pandoc_path()
    except Exception:
        pandoc_path = None

if pandoc_path:
    os.environ["PATH"] = os.pathsep.join(
        [
            os.path.dirname(pandoc_path),
            os.environ.get("PATH", ""),
        ]
    )

# 1. Tell Sphinx where to find your code and expose it to executed notebooks
src_dir = os.path.abspath("../../src")
sys.path.insert(0, src_dir)
os.environ["PYTHONPATH"] = os.pathsep.join(
    [
        src_dir,
        os.environ.get("PYTHONPATH", ""),
    ]
)

# -- Project information -----------------------------------------------------
project = "pyforestry"
author = "Carl Vigren"
# Pull version/version info from your package if you want:
# from your_package import __version__ as release

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",  # for docstrings
    "sphinx.ext.napoleon",  # Google/NumPy style docstrings
    "sphinx.ext.viewcode",  # add links to highlighted source
    "nbsphinx",  # for notebooks
]
# templates_path = ['_templates']  # if you have custom Jinja2 templates
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "notebooks/_archive/**"]

# "Units:" is this codebase's own docstring section, used 86 times in
# biomass/marklund_1988.py alone. Napoleon does not know it, so reST saw a plain
# paragraph followed by an indented block and raised "Unexpected indentation" for
# every one of them. Declaring it parses the section instead of erroring, and
# keeps the wording the transcriptions were verified against.
# Aliased to Parameters rather than declared with "params_style": that style
# consumed only the first entry, so the 25 single-entry sections parsed and all
# 61 multi-entry ones still errored on their second line.
napoleon_custom_sections = [("Units", "Parameters")]

# Classes here are largely dataclasses that document their fields in an
# "Attributes:" docstring section. Napoleon rendered that section as standalone
# attribute descriptions, while autodoc separately documented the same fields as
# members -- so each one was registered twice (209 "duplicate object
# description" warnings). Emitting them as :ivar: fields describes them in place,
# on the class, which is also where a reader expects a dataclass's fields.
napoleon_use_ivar = True

autodoc_default_options = {
    "members": True,  # include all public members
    "undoc-members": True,  # also include members without docstrings
    "show-inheritance": True,  # for classes, show base classes
    "exclude-members": (
        "DBH,TOTAL,code,measurement_height_m,over_bark,precision,"
        "latitude,longitude,fn,reference_age,species"
    ),
}

# Execute notebooks so GitHub Pages gets static output.
nbsphinx_execute = os.environ.get("NBSPHINX_EXECUTE", "always")
# Fail the build if cells error out.
nbsphinx_allow_errors = os.environ.get("NBSPHINX_ALLOW_ERRORS", "0") == "1"

# -- Options for HTML output -------------------------------------------------
html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
html_extra_path = ["../versions.json"]

# Configure version switcher so users can toggle between dev/stable docs.
DOCS_VERSION = os.environ.get("DOCS_VERSION", "dev")
html_theme_options = {
    "navbar_end": ["theme-switcher", "version-switcher"],
    "switcher": {
        "version_match": DOCS_VERSION,
        "json_url": "../versions.json",
    },
}


def _skip_imported_members(app, what, name, obj, skip, options):
    """Skip members that originate from a different module to avoid duplicates."""
    module_name = app.env.temp_data.get("autodoc:module")
    if not module_name:
        return skip
    obj_module = getattr(obj, "__module__", "")
    if obj_module and obj_module != module_name:
        return True
    return skip


def setup(app):
    app.connect("autodoc-skip-member", _skip_imported_members)
