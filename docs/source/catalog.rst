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

.. automodule:: pyforestry.catalog
   :members:
   :undoc-members:
   :show-inheritance:
