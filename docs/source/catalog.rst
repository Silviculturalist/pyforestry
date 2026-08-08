.. _catalog:

Model catalog
=============

``pyforestry`` collects many growth, yield, volume, bark, biomass, and
site-index models. The :mod:`pyforestry.catalog` module lets you discover them
without already knowing the import path or citation.

.. code-block:: python

    from pyforestry import catalog

    catalog.find(domain="volume", species="Picea abies")  # volume models for spruce
    catalog.search("brandel")                              # by id / author / title
    catalog.describe("brandel_1990_volume").source         # citation
    catalog.domains()                                      # ['bark', 'biomass', ...]
    catalog.regions()                                      # ['norway', 'sweden']

Discovery is driven by each model's module-level ``DESCRIPTOR`` (see
:class:`pyforestry.base.contracts.FormulaModuleDescriptor` and the convenience
:class:`pyforestry.base.contracts.FormulaDescriptor`). The full list of
discoverable models is on the :doc:`model_index` page.

API reference
-------------

.. sphinx-apidoc also generates api/pyforestry.rst, which documents this same
   module, so without :no-index: every catalog object is described twice. The
   generated page keeps the index entries because cross-references elsewhere
   resolve against it; this curated page still renders the full API.

.. automodule:: pyforestry.catalog
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:
