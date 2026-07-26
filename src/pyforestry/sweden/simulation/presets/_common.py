"""Common preset implementation for Sweden simulation scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

from pyforestry.base.contracts import SourceReference
from pyforestry.simulation.presets import ScenarioPresetBase
from pyforestry.sweden.simulation.policy import management_plan, scenario_factors

RulesetFn = Callable[..., Any]


def _stable_seed(*parts: object) -> int:
    """Create a deterministic seed from arbitrary preset-identifying parts."""
    token = "|".join(str(part) for part in parts)
    digest = sha256(token.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) & 0x7FFFFFFF


@dataclass(frozen=True)
class SwedenScenarioPreset(ScenarioPresetBase):
    """Minimal simulation preset contract implementation for Sweden scenarios.

    Shared guard-policy, artifact, and identity behaviour is inherited from
    :class:`~pyforestry.simulation.presets.ScenarioPresetBase`; only the
    Sweden-specific seed, stage ordering, rulesets, and provenance live here.
    """

    preset_id: str
    scenario_id: str
    _required_artifacts: tuple[str, ...]

    def seed_strategy(self, **kwargs: Any) -> int:
        """Derive a deterministic scenario seed from preset and global seed."""
        global_seed = int(kwargs["global_seed"])
        return _stable_seed(self.preset_id, self.scenario_id, global_seed)

    def stages(self) -> Sequence[str]:
        """Return the default ordered stage sequence for Sweden presets."""
        return ("growth", "disturbance", "valuation")

    def rulesets(self) -> Mapping[str, RulesetFn]:
        """Return bound management/scenario ruleset callables for this preset."""
        return {
            "management": partial(management_plan, self.scenario_id),
            "scenario": partial(scenario_factors, self.scenario_id),
        }

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance for this preset (there is none)."""
        return SourceReference(
            author="(none)",
            year=0,
            title=f"Sweden scenario preset: {self.preset_id}",
            note=(
                "A scenario configuration authored in pyforestry, not a publication: "
                "it selects management and scenario rulesets and cites nothing. "
                "year=0 is a sentinel for 'not applicable', not a citation date. The "
                "science belongs to the models the scenario drives, each of which "
                "carries its own provenance."
            ),
        )
