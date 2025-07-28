Helpers Overview
================

This page provides a short summary of the most common helper classes
found in ``pyforestry.base.helpers``.  They are used throughout the
examples and tests to represent trees, plots and derived metrics.

* ``Tree`` -- represents a single tree with optional species,
  position and measurement attributes.
* ``CircularPlot`` -- describes a sample plot with a radius or
  known area and holds a list of ``Tree`` objects.
* ``Stand`` -- a container for multiple plots with convenience
  accessors such as ``Stand.BasalArea``.

See the API reference for full details.