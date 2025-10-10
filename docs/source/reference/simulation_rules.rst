Simulation rules engine
=======================

The rules engine coordinates conditional actions that can operate on individual
stands or groups of stands. Rules are evaluated against immutable
:class:`~pyforestry.simulation.StandState` objects produced by the
:class:`~pyforestry.simulation.TreeCheckpointer` so predicate logic always sees a
stable snapshot of the current state.

Core abstractions
-----------------

.. autoclass:: pyforestry.simulation.Rule
   :members:

.. autoclass:: pyforestry.simulation.RuleAction
   :members:

.. autoclass:: pyforestry.simulation.RuleDecision
   :members:

.. autoclass:: pyforestry.simulation.RuleSet
   :members:

Example
-------

The example below demonstrates how to thin the largest tree whenever total stem
counts exceed a threshold.

.. code-block:: python

   from pyforestry.simulation import Rule, RuleAction, RuleSet

   def overstocked(state):
       return state.metric_estimates["Stems"]["TOTAL"] > 250

   def remove_largest(manager, stand_id, state):
       record = manager._require_stand(stand_id)  # application code would wrap this helper
       first_plot = state.plots[0]
       record.stand.thin_trees(uids=[first_plot.tree_uids[0]])

   ruleset = RuleSet(
       name="thinning",
       rules=[
           Rule(
               name="remove-largest",
               predicate=overstocked,
               actions=[RuleAction(name="thin", callback=remove_largest)],
           )
       ],
       scope={"tags": ["thinning"]},
   )

   manager.register_ruleset("thinning", ruleset)
