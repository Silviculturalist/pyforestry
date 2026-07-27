"""Shared scaffolding for regional scenario configurations.

A scenario configuration is not a simulator. It is a frozen record of a seed
strategy, an ordered list of stage names, ruleset callables and a required-artifact
list -- the inputs a run *would* take. The runnable things in this package are the
composite pipelines in ``<region>/simulation/presets/`` and
:func:`pyforestry.project`; see :class:`ScenarioConfig` for what this tier does and
does not do.

Sweden and Norway each had their own near-copy of this file. The two differed in
ways that were not decisions: one class was called ``ScenarioConfig`` and the other
``NorwayScenarioPreset`` (the rename that separated "configuration" from "pipeline"
reached one region), their ``RulesetFn`` aliases disagreed, their
``REQUIRED_ARTIFACTS`` lived in different modules, and each carried its own
``_stable_seed`` -- one joining on ``"|"`` and masking to 31 bits, the other joining
on ``":"`` and taking half as many hex digits. Nothing scientific distinguishes
them; a seed derivation that differs by region is a difference that will be read
as meaningful.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Callable, Mapping, Sequence

from pyforestry.base.contracts import Describable, SourceReference
from pyforestry.simulation.contracts import SimulationPreset

#: A ruleset maps a scenario id to the factors that scenario applies.
RulesetFn = Callable[..., Mapping[str, float]]


def stable_seed(*parts: object) -> int:
    """Derive a deterministic non-negative seed from arbitrary identifying parts.

    Args:
        *parts: Values identifying the run -- preset id, scenario id, global seed.

    Returns:
        A stable seed in ``[0, 2**31)``, the same for the same parts on any
        platform and in any process.
    """
    token = "|".join(str(part) for part in parts)
    return int(sha256(token.encode("utf-8")).hexdigest()[:16], 16) & 0x7FFFFFFF


@dataclass(frozen=True)
class ScenarioConfig(SimulationPreset):
    """A region's scenario configuration: seeds, stage names, rulesets, artifacts.

    **This runs nothing.** ``stages()`` is a list of names recorded into a
    manifest, ``rulesets()`` and ``guard_policy()` have no runtime caller, and the
    artifact harness that consumes it fills its outputs with a synthetic random
    walk. Treat its output as a schema fixture. The runnable simulators are the
    composite pipelines and :func:`pyforestry.project`.

    A region subclasses this to declare its own stages, rulesets and identity;
    everything else -- the seed derivation, the guard flags, the artifact
    accessor, the provenance sentinel -- is shared, and was duplicated per region
    with unexplained divergences before.

    Args:
        preset_id: Identifies the configuration, e.g. ``"sweden_minimal"``.
        scenario_id: Identifies the scenario within it, e.g. ``"baseline"``.
        region: The region this configuration belongs to, used in its provenance.
        required_artifacts_: Artifact filenames a run under this configuration
            must emit. Trailing underscore because
            :meth:`required_artifacts` is the accessor the contract names.
    """

    preset_id: str
    scenario_id: str
    region: str
    required_artifacts_: tuple[str, ...] = ()

    # --- Seeding -------------------------------------------------------------

    def seed_strategy(self, **kwargs: Any) -> int:
        """Derive this scenario's deterministic seed from the run's global seed.

        Args:
            **kwargs: Must contain ``global_seed``.

        Returns:
            A seed stable across processes and platforms.
        """
        return stable_seed(self.preset_id, self.scenario_id, int(kwargs["global_seed"]))

    # --- Declarations a region supplies --------------------------------------

    def stages(self) -> Sequence[str]:
        """Return the ordered stage identifiers a run would execute.

        Raises:
            NotImplementedError: Always; a region declares its own stages.
        """
        raise NotImplementedError(f"{type(self).__name__} must declare its stages.")

    def rulesets(self) -> Mapping[str, RulesetFn]:
        """Return scenario rulesets keyed by concern.

        Raises:
            NotImplementedError: Always; a region declares its own rulesets.
        """
        raise NotImplementedError(f"{type(self).__name__} must declare its rulesets.")

    # --- Shared behaviour ----------------------------------------------------

    def guard_policy(self) -> Mapping[str, object]:
        """Return non-formula guard policy flags a run would apply."""
        return {
            "clamp_net_volume_to_zero": True,
            "reject_negative_inputs": True,
        }

    def required_artifacts(self) -> Sequence[str]:
        """Return the artifact names required by this configuration."""
        return self.required_artifacts_

    @property
    def component_id(self) -> str:
        """Stable identifier (``<preset_id>/<scenario_id>``)."""
        return f"{self.preset_id}/{self.scenario_id}"

    @property
    def components(self) -> Sequence[Describable]:
        """Describable components composed by this configuration.

        Empty: a configuration selects rulesets, it does not compose models. The
        science belongs to whatever a runtime would drive with it.
        """
        return ()

    @property
    def source(self) -> SourceReference:
        """Bibliographic provenance for this configuration (there is none)."""
        return SourceReference(
            author="(none)",
            year=0,
            title=f"{self.region} scenario configuration: {self.preset_id}",
            note=(
                "A scenario configuration authored in pyforestry, not a publication: "
                "it selects management and scenario rulesets and cites nothing. "
                "year=0 is a sentinel for 'not applicable', not a citation date. The "
                "science belongs to the models the scenario drives, each of which "
                "carries its own provenance."
            ),
        )


#: Historic name for :class:`ScenarioConfig`. It described a base class that
#: subclasses had to complete with three undeclared attributes; those are fields
#: on :class:`ScenarioConfig` now.
ScenarioConfigBase = ScenarioConfig

__all__ = ["RulesetFn", "ScenarioConfig", "ScenarioConfigBase", "stable_seed"]
