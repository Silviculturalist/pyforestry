"""Rule system enabling conditional actions on stands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Iterable, List, Mapping, Sequence

from .state import StandState

__all__ = ["RuleAction", "Rule", "RuleSet", "RuleDecision"]


@dataclass(slots=True)
class RuleAction:
    """Encapsulates an executable action triggered by a rule."""

    name: str
    callback: Callable[["SimulationManager", str, StandState], None]
    metadata: Mapping[str, Any] | None = None

    def execute(self, manager: "SimulationManager", stand_id: str, state: StandState) -> None:
        self.callback(manager, stand_id, state)


@dataclass(slots=True)
class RuleDecision:
    """Outcome of evaluating a rule."""

    rule: "Rule"
    actions_executed: Sequence[str]


@dataclass(slots=True)
class Rule:
    """A predicate plus actions to run when it evaluates to ``True``."""

    name: str
    predicate: Callable[[StandState], bool]
    actions: Sequence[RuleAction]
    priority: int = 0
    stop_on_match: bool = True

    def applies(self, state: StandState) -> bool:
        return self.predicate(state)


@dataclass
class RuleSet:
    """Collection of rules with shared evaluation configuration."""

    name: str
    rules: Sequence[Rule]
    scope: Mapping[str, Iterable[str]] | None = None
    mode: str = "first"

    def _sorted_rules(self) -> List[Rule]:
        return sorted(self.rules, key=lambda rule: rule.priority, reverse=True)

    def targets(self, stand_id: str, stand_tags: Iterable[str]) -> bool:
        if not self.scope:
            return True
        explicit = set(self.scope.get("stands", ()))
        tag_scope = set(self.scope.get("tags", ()))
        if explicit and stand_id in explicit:
            return True
        if tag_scope and set(stand_tags) & tag_scope:
            return True
        return not explicit and not tag_scope

    def evaluate(
        self,
        manager: "SimulationManager",
        stand_id: str,
        state: StandState,
        stand_tags: Iterable[str] = (),
    ) -> List[RuleDecision]:
        if not self.targets(stand_id, stand_tags):
            return []

        decisions: List[RuleDecision] = []
        for rule in self._sorted_rules():
            if not rule.applies(state):
                continue
            executed: List[str] = []
            for action in rule.actions:
                action.execute(manager, stand_id, state)
                executed.append(action.name)
            decisions.append(RuleDecision(rule=rule, actions_executed=tuple(executed)))
            if rule.stop_on_match or self.mode == "first":
                break
        return decisions


if TYPE_CHECKING:  # pragma: no cover
    from .manager import SimulationManager
