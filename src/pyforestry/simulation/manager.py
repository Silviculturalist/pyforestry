"""Simulation manager orchestrating stands, modules and rules."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence

import numpy as np

from pyforestry.base.helpers import Stand

from .checkpoint import SimulationCheckpoint, TreeCheckpointer
from .growth import GrowthModule, ModelResult
from .rules import RuleSet
from .seeding import FixedSeedPolicy, SeedPolicy

__all__ = ["SimulationManager"]


@dataclass
class StandRecord:
    stand: Stand
    modules: List[GrowthModule] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


class SimulationManager:
    """Coordinate growth models, rule execution and checkpointing."""

    def __init__(
        self,
        *,
        checkpointer: TreeCheckpointer | None = None,
        seed_policy: SeedPolicy | None = None,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.checkpointer = checkpointer or TreeCheckpointer()
        self.seed_policy = seed_policy
        self.logger = logger
        self._stands: Dict[str, StandRecord] = {}
        self._rulesets: Dict[str, RuleSet] = {}
        self._history: Dict[str, List[SimulationCheckpoint]] = defaultdict(list)
        self._pending_events: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
        self._audit_log: List[str] = []

    def _audit(self, message: str) -> None:
        self._audit_log.append(message)
        if self.logger:
            self.logger(message)

    def register_stand(
        self,
        stand_id: str,
        stand: Stand,
        *,
        modules: Sequence[GrowthModule] | None = None,
        tags: Iterable[str] | None = None,
    ) -> None:
        if stand_id in self._stands:
            raise KeyError(f"Stand '{stand_id}' already registered")
        record = StandRecord(stand=stand, modules=list(modules or ()), tags=list(tags or ()))
        self._stands[stand_id] = record
        checkpoint = self.checkpointer.create_checkpoint(stand)
        self._history[stand_id].append(checkpoint)
        self._audit(f"Registered stand {stand_id} with {len(stand.plots)} plots")

    def add_modules(self, stand_id: str, modules: Sequence[GrowthModule]) -> None:
        record = self._require_stand(stand_id)
        record.modules.extend(modules)
        self._audit(f"Added {len(modules)} modules to stand {stand_id}")

    def register_ruleset(self, name: str, ruleset: RuleSet) -> None:
        self._rulesets[name] = ruleset
        self._audit(f"Registered ruleset '{name}'")

    def queue_event(self, stand_id: str, event: Mapping[str, Any]) -> None:
        self._pending_events[stand_id].append(dict(event))

    def start_run(self, seed_policy: SeedPolicy | None = None) -> None:
        if seed_policy is not None:
            self.seed_policy = seed_policy
        if self.seed_policy is None:
            self.seed_policy = FixedSeedPolicy(0)
        self.seed_policy.start_run()
        self._audit("Simulation run started")

    def run(
        self,
        years: float,
        *,
        stand_ids: Sequence[str] | None = None,
        checkpoint_interval: float | None = None,
    ) -> None:
        if self.seed_policy is None:
            self.start_run()
        ids = stand_ids or tuple(self._stands.keys())
        for stand_id in ids:
            self._run_stand(stand_id, years, checkpoint_interval)

    def _run_stand(self, stand_id: str, years: float, checkpoint_interval: float | None) -> None:
        record = self._require_stand(stand_id)
        stand = record.stand
        elapsed = 0.0
        for module in record.modules:
            stand_state = self.checkpointer.capture_stand_state(stand)
            tree_states = self.checkpointer.capture_tree_states(stand)
            model = module.instantiate()
            module.validate_inputs(stand_state, tree_states, instance=model)
            context = {"stand_id": stand_id, "manager": self}
            model.initialize(context)
            rng = (
                self.seed_policy.generator(stand_id, module.name)
                if self.seed_policy
                else np.random.default_rng()
            )
            result = model.step(years, rng, stand_state, tree_states)
            self._apply_model_result(stand, result)
            model.finalize()
            self._apply_rules(stand_id)
            elapsed += module.time_step
            if checkpoint_interval is None or elapsed >= checkpoint_interval:
                self._record_checkpoint(stand_id, module)
                elapsed = 0.0

    def _apply_model_result(self, stand: Stand, result: ModelResult) -> None:
        tree_lookup: Dict[str | int | None, Any] = {}
        for plot in stand.plots:
            for tree in plot.trees:
                tree_lookup[tree.uid] = tree
        for uid, deltas in (result.tree_deltas or {}).items():
            tree = tree_lookup.get(uid)
            if tree is None:
                continue
            for attr, delta in deltas.items():
                current = getattr(tree, attr, None)
                if current is None:
                    setattr(tree, attr, delta)
                else:
                    setattr(tree, attr, current + delta)
        for attr, delta in (result.stand_deltas or {}).items():
            current = stand.attrs.get(attr)
            if current is None:
                stand.attrs[attr] = delta
            else:
                stand.attrs[attr] = current + delta
        if result.metadata:
            self._audit(f"Model metadata: {result.metadata}")
        stand._metric_estimates.clear()

    def _apply_rules(self, stand_id: str) -> None:
        if not self._rulesets:
            return
        record = self._require_stand(stand_id)
        stand = record.stand
        state = self.checkpointer.capture_stand_state(stand)
        for name, ruleset in self._rulesets.items():
            decisions = ruleset.evaluate(self, stand_id, state, stand_tags=record.tags)
            for decision in decisions:
                self._audit(f"Ruleset {name} applied rule {decision.rule.name} to {stand_id}")

    def _record_checkpoint(self, stand_id: str, module: GrowthModule) -> None:
        stand = self._require_stand(stand_id).stand
        checkpoint = self.checkpointer.create_checkpoint(
            stand,
            seed_state=self.seed_policy.snapshot() if self.seed_policy else {},
            active_modules=[module.name],
            pending_events=[dict(event) for event in self._pending_events.get(stand_id, ())],
            metadata={"module": module.name, "time_step": module.time_step},
        )
        self._history[stand_id].append(checkpoint)

    def _require_stand(self, stand_id: str) -> StandRecord:
        if stand_id not in self._stands:
            raise KeyError(f"Unknown stand '{stand_id}'")
        return self._stands[stand_id]

    def get_history(self, stand_id: str) -> Sequence[SimulationCheckpoint]:
        return tuple(self._history.get(stand_id, ()))

    def get_latest_checkpoint(self, stand_id: str) -> SimulationCheckpoint | None:
        history = self._history.get(stand_id)
        return history[-1] if history else None

    def restore_from_checkpoint(self, stand_id: str, checkpoint: SimulationCheckpoint) -> None:
        record = self._require_stand(stand_id)
        self.checkpointer.restore(record.stand, checkpoint)
        if self.seed_policy and checkpoint.seed_state:
            self.seed_policy.restore(checkpoint.seed_state)
        self._history[stand_id].append(checkpoint)
        self._audit(f"Restored stand {stand_id} from checkpoint")

    @property
    def audit_log(self) -> Sequence[str]:
        return tuple(self._audit_log)
