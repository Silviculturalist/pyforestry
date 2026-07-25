.. _architecture:

Architecture Overview
=====================

This page mirrors the package responsibility policy.

The canonical source of truth is ``ARCHITECTURE.md`` at the repository root.
If this page and ``ARCHITECTURE.md`` diverge, ``ARCHITECTURE.md`` governs.

Purpose and Non-Goals
---------------------

Purpose
^^^^^^^

The architecture policy defines ownership boundaries so simulation composition
is scalable, reproducible, and responsibilities remain explicit.

Non-goals
^^^^^^^^^

This policy is not:

* A formula catalog.
* A full migration pull request.
* A runtime implementation specification.

Five Contexts and Ownership
---------------------------

Context 1: Data Contract Context
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Owns:
  * Shared data structures, primitives, and unit-bearing contracts.
* Must define:
  * Stable type-level contracts consumed by formulas and simulation runtimes.
* Must not define:
  * Scenario sequencing and orchestration policy.
* Primary package paths:
  * ``src/pyforestry/base/helpers/``
  * ``src/pyforestry/base/helpers/primitives/``

Context 2: Formula Context
^^^^^^^^^^^^^^^^^^^^^^^^^^

* Owns:
  * Scientific equations, coefficients, and model-local guards.
* Must define:
  * Explicit equation interfaces with unit-bearing inputs and outputs.
* Must not define:
  * Global seed policy, stage ordering, or scenario rulesets.
* Primary package paths:
  * Domain packages outside ``*/blocks`` and ``*/simulation``.
  * Example: ``src/pyforestry/sweden/mortality/``
  * Example: ``src/pyforestry/sweden/siteindex/``
  * Example: ``src/pyforestry/sweden/volume/``

Context 3: Block Context (regional ``/blocks``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Owns:
  * Composable building blocks for regional model families.
  * ``GrowthModel`` adapters that compose domain equations into simulation-facing APIs.
  * Self-contained published model systems (for example Eko 1985, Eriksson 1976).
* Must define:
  * Simulation-facing interfaces binding runtime contracts to domain equations.
* Must not define:
  * New equation internals (these belong in domain packages).
  * Long-lived orchestration policy or scenario rulesets.
* Primary package paths:
  * ``src/pyforestry/<region>/blocks/``
  * Current concrete example: ``src/pyforestry/sweden/blocks/``

Context 4: Simulation Policy + Runtime Context
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Owns:
  * Runtime orchestration, staging, dispatch behavior, rulesets, and seed policy.
* Must define:
  * Temporal stepping and operation ordering.
  * Non-formula environment constraints and cross-model guards.
* Must not define:
  * Region-specific equation internals.
* Primary package paths:
  * ``src/pyforestry/base/simulation/``
  * ``src/pyforestry/simulation/``
  * Target regional presets/orchestration: ``src/pyforestry/<region>/simulation/``

Context 5: Integration/Application Context
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Owns:
  * Notebook/app composition, scenario setup, and external integrations.
* Must define:
  * Consumer-facing execution wiring and environment-specific glue.
* Must not define:
  * New reusable formula internals or core runtime contracts.
* Primary package paths:
  * ``docs/source/notebooks/``
  * External applications consuming ``pyforestry``

Hard Rules
----------

The following rules are mandatory:

1. Global seed MUST be defined in simulation policy/global context.
2. Species group definitions outside formula internals MUST be defined in simulation context.
3. Function selection and invocation timing MUST be defined in simulation context.
4. Operation order outside formula bodies MUST be defined in simulation context.
5. Orchestration managers MUST NOT live outside simulation context packages.
6. Non-formula environment constraints, including clamping, MUST belong to simulation context.
7. Rulesets MUST be defined and applied in simulation global context.

``/blocks`` Policy
------------------

* ``src/pyforestry/<region>/blocks/`` contains composable building blocks:
  ``GrowthModel`` adapters and self-contained published model systems.
* New equation internals MUST NOT be placed directly in ``blocks/``;
  individual equations belong in domain packages (``growth/``, ``mortality/``,
  etc.) and are composed by blocks.
* Blocks contain real adapter or model-system code; no facade delegation stubs
  remain.

Transitional Exceptions
-----------------------

No active transitional exceptions are currently registered.

Completed migrations:

* All Sweden ``/models`` modules extracted and relocated to domain packages
  or ``/blocks/``.
* Mortality orchestration moved from ``sweden/mortality/manager.py`` to
  ``sweden/simulation/mortality/engine.py``.
* ``/models`` renamed to ``/blocks`` across Sweden and Norway.

Active package paths:

* Regional simulation presets/orchestration: ``src/pyforestry/<region>/simulation/``.
* Shared orchestration runtime: ``src/pyforestry/simulation/`` and
  ``src/pyforestry/base/simulation/``.

Dispatch and Single-Responsibility Rules
----------------------------------------

* There MUST be one dispatch layer per concern:
  * Formula dispatch.
  * Simulation-stage dispatch.
  * Scenario-policy dispatch.
* A module MUST NOT own both scientific equation internals and scenario
  orchestration policy.

Examples
^^^^^^^^

Allowed:

* Equation implementation in
  ``src/pyforestry/sweden/mortality/root_rot_thor_stahl_stenlid_2005.py`` with
  scenario orchestration in ``src/pyforestry/simulation/`` or
  ``src/pyforestry/sweden/simulation/``.

Disallowed:

* A single module that both maintains scientific coefficients and controls
  global stage/ruleset orchestration.

Play-Ready Regional Simulation Presets
--------------------------------------

Runnable regional presets MUST live under ``src/pyforestry/<region>/simulation/``.

Minimum preset contract:

* Seed handling:
  * Accept and persist global seed strategy.
* Stage/ruleset declaration:
  * Declare stages and rulesets explicitly.
* Operation ordering:
  * Declare execution order outside formula internals.
* Environment guards:
  * Apply non-formula constraints in simulation policy.

Migration Guardrails
--------------------

* New work MUST follow the target architecture immediately.
* Legacy modules MAY remain temporarily but MUST NOT expand non-compliant responsibilities.
* Refactors SHOULD preserve public API behavior unless explicitly announced.
* This policy governs architecture boundaries and does not itself change runtime API signatures.
