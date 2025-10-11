Simulation framework
====================

The :mod:`pyforestry.simulation` package provides the primitives required to
build deterministic growth simulations. It introduces immutable snapshot data
structures, checkpoint utilities and the orchestration manager that coordinates
modules, rules and seed policies.

State snapshots
---------------

.. autoclass:: pyforestry.simulation.TreeState
   :members:

.. autoclass:: pyforestry.simulation.PlotState
   :members:

.. autoclass:: pyforestry.simulation.StandState
   :members:

Checkpointing
-------------

.. autoclass:: pyforestry.simulation.TreeCheckpointer
   :members:

.. autoclass:: pyforestry.simulation.SimulationCheckpoint
   :members:

Growth modules
--------------

.. autoclass:: pyforestry.simulation.GrowthModule
   :members:

.. autoclass:: pyforestry.simulation.ModelResult
   :members:

Simulation manager
------------------

.. autoclass:: pyforestry.simulation.SimulationManager
   :members:

Seed policies
-------------

.. autoclass:: pyforestry.simulation.SeedPolicy
   :members:

.. autoclass:: pyforestry.simulation.FixedSeedPolicy
   :members:

.. autoclass:: pyforestry.simulation.PerModuleOffsetPolicy
   :members:

.. autoclass:: pyforestry.simulation.RollingSeedPolicy
   :members:

Quick start example
-------------------

.. code-block:: python

   from pyforestry.base.helpers import CircularPlot, Stand, Tree
   from pyforestry.base.helpers.primitives.cartesian_position import Position
   from pyforestry.simulation import GrowthModule, SimulationManager

   # Define a very small stand
   trees = [Tree(uid="t1", species="picea abies", diameter_cm=32, age=40)]
   plot = CircularPlot(id="p1", radius_m=5.0, position=Position(0, 0), trees=trees)
   stand = Stand(area_ha=1.0, plots=[plot])

   # Implement a trivial growth model
   class IncrementDiameter:
       level = "tree"
       time_step = 1.0
       requires_checkpoint = False
       required_tree_fields = ("diameter_cm",)
       required_stand_fields = ()

       def __init__(self, increment: float = 1.0) -> None:
           self.increment = increment

       def validate_inputs(self, stand_state, tree_states) -> None:
           for tree_state in tree_states:
               if tree_state.diameter_cm is None:
                   raise ValueError("Missing diameter")

       def initialize(self, context=None) -> None:
           pass

       def step(self, years, rng, stand_state, tree_states):
           deltas = {tree.uid: {"diameter_cm": years * self.increment} for tree in tree_states}
           return ModelResult(tree_deltas=deltas)

       def finalize(self) -> None:
           pass

   module = GrowthModule(IncrementDiameter, config={"increment": 2.0})
   manager = SimulationManager()
   manager.register_stand("demo", stand, modules=[module])
   manager.start_run()
   manager.run(years=1.0, stand_ids=["demo"])

   print(stand.plots[0].trees[0].diameter_cm)  # 34.0
