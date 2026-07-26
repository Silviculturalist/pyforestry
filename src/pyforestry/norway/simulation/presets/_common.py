"""Common base for Norwegian scenario presets."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

from pyforestry.base.contracts import SourceReference
from pyforestry.norway.simulation.policy import management_plan, scenario_factors
from pyforestry.simulation.presets import ScenarioPresetBase

RulesetFn = Callable[..., Mapping[str, float]]

REQUIRED_ARTIFACTS = (
    "run_manifest.json",
    "scenario_summary.json",
)


def _stable_seed(preset_id: str, scenario_id: str, global_seed: int) -> int:
    """Derive a deterministic seed from preset, scenario, and global seed."""
    payload = f"{preset_id}:{scenario_id}:{global_seed}"
    return int(sha256(payload.encode()).hexdigest()[:8], 16)


@dataclass(frozen=True)
class NorwayScenarioPreset(ScenarioPresetBase):
    """Minimal simulation preset contract for Norway scenarios.

    Shared guard-policy, artifact, and identity behaviour is inherited from
    :class:`~pyforestry.simulation.presets.ScenarioPresetBase`; only the
    Norway-specific seed, stage ordering, rulesets, and provenance live here.
    """

    preset_id: str
    scenario_id: str
    _required_artifacts: tuple[str, ...] = field(default=REQUIRED_ARTIFACTS)

    def seed_strategy(self, **kwargs: Any) -> int:
        """Return a deterministic seed for a run."""
        global_seed = int(kwargs["global_seed"])
        return _stable_seed(self.preset_id, self.scenario_id, global_seed)

    def stages(self) -> Sequence[str]:
        """Return the ordered stage identifiers for execution."""
        return ("growth",)

    def rulesets(self) -> Mapping[str, RulesetFn]:
        """Return scenario rulesets keyed by concern."""
        return {
            "management": partial(management_plan, self.scenario_id),
            "scenario": partial(scenario_factors, self.scenario_id),
        }

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance for this preset."""
        return SourceReference(
            author="(none)",
            year=0,
            title=f"Norway scenario preset: {self.preset_id}",
            note=(
                "A scenario configuration authored in pyforestry, not a publication: "
                "it selects management and scenario rulesets and cites nothing. "
                "year=0 is a sentinel for 'not applicable', not a citation date. The "
                "science belongs to the models the scenario drives, each of which "
                "carries its own provenance."
            ),
        )
