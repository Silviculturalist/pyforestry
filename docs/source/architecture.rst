.. _architecture:

Architecture Overview
=====================

This page summarises the current helper layer that underpins most of
``pyforestry``'s data handling and sketches the aspirational simulation
architecture that future releases will introduce.

Helper data model
-----------------

At the heart of the helper layer are three core classes that organise tree- and
stand-level measurements:

* :class:`~pyforestry.base.helpers.tree.Tree` captures a single tree observation,
  including its spatial :class:`~pyforestry.base.helpers.primitives.Position`,
  :class:`~pyforestry.base.helpers.tree_species.TreeName` identifier, stem
  dimensions, and optional metadata. Lightweight validation converts string
  species names into canonical forms so they can be compared and aggregated
  reliably.
* :class:`~pyforestry.base.helpers.plot.CircularPlot` groups one or more trees
  that were measured on a circular sample plot. The class normalises area
  metadata (accepting either a radius or explicit area), tracks any
  angle-count tallies, and keeps an optional connection to the
  :class:`~pyforestry.base.helpers.primitives.SiteBase` where the plot was
  recorded.
* :class:`~pyforestry.base.helpers.stand.Stand` composes multiple plots and
  attaches them to an optional boundary polygon. When instantiated it
  calculates stand-level metrics—such as basal area and stem counts—via the
  embedded :class:`~pyforestry.base.helpers.stand.StandMetricAccessor`, ensuring
  that consumers can retrieve totals or species-specific values on demand.

These classes are intentionally declarative: they minimise behaviour in favour
of rich, well-typed records that downstream growth and yield models can
consume. Combined, they provide a baseline vocabulary for describing spatial
forest inventories, handling unit conversions, and validating data before it is
passed into model pipelines.

Simulation model views
----------------------

The :mod:`pyforestry.simulation` package now ships ``ModelView`` building
blocks that map directly onto the helper layer. ``StandMetricView`` adapts a
:class:`~pyforestry.base.helpers.stand.Stand` so that consumers can query
``BasalArea``, ``Stems`` and related accessors without needing to know the
implementation details of :class:`~pyforestry.base.helpers.stand.StandMetricAccessor`.
``InventoryView`` exposes a lightweight iterator façade over the stand's
:class:`~pyforestry.base.helpers.plot.CircularPlot` collection while
``SpatialTreeView`` focuses on the positional attributes carried by individual
:class:`~pyforestry.base.helpers.tree.Tree` instances.

These views provide the first bridge into the future simulation pipeline: they
package the rich helper data into read-only façades that the forthcoming
``SimulationManager`` can consume when orchestrating full scenario runs.

Future simulation architecture
------------------------------

While the helper layer focuses on tidy data structures, upcoming development is
concentrated on orchestration and presentation layers that will make it easier
to run scenario analyses.

* ``SimulationManager`` (conceptual) will coordinate model execution, link
  inventory data with parameter sets, and manage temporal sequencing of
  simulations.
* ``ModelView`` (conceptual) will provide a higher-level façade for presenting
  scenario outputs—either to notebooks, dashboards, or external services—while
  remaining agnostic to the underlying simulation engines.

The roadmap for these features will be tracked on GitHub under the
`roadmap issue label <https://github.com/Silviculturalist/pyforestry/issues?q=is%3Aissue+label%3Aroadmap>`_.
New issues outlining ``SimulationManager`` and ``ModelView`` responsibilities
will be published there so contributors can follow along and offer feedback.
