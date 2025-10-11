"""Growth model protocol and module factory."""

from __future__ import annotations

from dataclasses import dataclass, field
from inspect import Parameter, Signature, signature
from typing import Any, ClassVar, Dict, Literal, Mapping, Protocol, Sequence

import numpy as np

from .state import StandState, TreeState, TreeStateSequence

__all__ = ["GrowthModelProtocol", "ModelResult", "GrowthModule"]


@dataclass(slots=True)
class ModelResult:
    """Container capturing the outcome of a growth model step."""

    tree_deltas: Mapping[str | int | None, Mapping[str, float]] = field(default_factory=dict)
    stand_deltas: Mapping[str, float] = field(default_factory=dict)
    metadata: Mapping[str, Any] | None = None

    def merge(self, other: "ModelResult") -> "ModelResult":
        """Combine two results, giving precedence to ``other`` on conflicts."""

        merged_tree: Dict[str | int | None, Dict[str, float]] = {
            key: dict(value) for key, value in self.tree_deltas.items()
        }
        for uid, deltas in other.tree_deltas.items():
            merged_tree.setdefault(uid, {}).update(deltas)

        merged_stand = dict(self.stand_deltas)
        merged_stand.update(other.stand_deltas)

        merged_metadata = dict(self.metadata or {})
        merged_metadata.update(other.metadata or {})
        return ModelResult(merged_tree, merged_stand, merged_metadata)


class GrowthModelProtocol(Protocol):
    """Structural protocol implemented by growth models."""

    level: ClassVar[Literal["tree", "stand"]]
    time_step: ClassVar[float]
    requires_checkpoint: ClassVar[bool]
    required_tree_fields: ClassVar[Sequence[str]]
    required_stand_fields: ClassVar[Sequence[str]]

    def __init__(self, **kwargs: Any) -> None: ...

    def validate_inputs(self, stand_state: StandState, tree_states: TreeStateSequence) -> None: ...

    def initialize(self, context: Mapping[str, Any] | None = None) -> None: ...

    def step(
        self,
        years: float,
        rng: np.random.Generator,
        stand_state: StandState,
        tree_states: TreeStateSequence,
    ) -> ModelResult: ...

    def finalize(self) -> None: ...


def _normalise_class_attr(cls: type, name: str, default: Any) -> Any:
    value = getattr(cls, name, None)
    return default if value is None else value


class GrowthModule:
    """Factory responsible for validating and instantiating growth models."""

    def __init__(
        self,
        model_cls: type[GrowthModelProtocol],
        *,
        name: str | None = None,
        config: Mapping[str, Any] | None = None,
    ) -> None:
        self.model_cls = model_cls
        self.name = name or model_cls.__name__
        self.config: Dict[str, Any] = dict(config or {})
        self.level: Literal["tree", "stand"] = _normalise_class_attr(model_cls, "level", "tree")
        self.time_step: float = float(_normalise_class_attr(model_cls, "time_step", 1.0))
        self.requires_checkpoint: bool = bool(
            _normalise_class_attr(model_cls, "requires_checkpoint", False)
        )
        self.required_tree_fields = tuple(
            _normalise_class_attr(model_cls, "required_tree_fields", ())
        )
        self.required_stand_fields = tuple(
            _normalise_class_attr(model_cls, "required_stand_fields", ())
        )
        self._constructor_signature: Signature = signature(model_cls)
        self._validate_config()

    def _validate_config(self) -> None:
        """Ensure provided configuration keys are accepted by the model."""

        parameters = {
            name
            for name, param in self._constructor_signature.parameters.items()
            if param.kind in (Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY)
        }
        unexpected = set(self.config) - parameters
        if unexpected:
            raise TypeError(
                f"Configuration for {self.name} contains unexpected keys: {sorted(unexpected)}"
            )

    def schema(self) -> Mapping[str, str]:
        """Expose constructor parameter information for documentation."""

        return {
            name: str(param.annotation)
            for name, param in self._constructor_signature.parameters.items()
            if param.kind in (Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY)
        }

    @classmethod
    def from_config(
        cls, model_cls: type[GrowthModelProtocol], config: Mapping[str, Any]
    ) -> "GrowthModule":
        """Create a module from configuration dictionary."""

        return cls(model_cls=model_cls, config=config)

    def _enrich_kwargs(self, **dependencies: Any) -> Dict[str, Any]:
        merged = dict(self.config)
        for key, value in dependencies.items():
            if key in self._constructor_signature.parameters:
                merged[key] = value
        return merged

    def instantiate(self, **dependencies: Any) -> GrowthModelProtocol:
        """Materialise the growth model, injecting dependencies as required."""

        kwargs = self._enrich_kwargs(**dependencies)
        instance = self.model_cls(**kwargs)
        return instance

    def metadata(self) -> Mapping[str, Any]:
        """Return metadata describing the module."""

        return {
            "name": self.name,
            "level": self.level,
            "time_step": self.time_step,
            "requires_checkpoint": self.requires_checkpoint,
            "required_tree_fields": self.required_tree_fields,
            "required_stand_fields": self.required_stand_fields,
        }

    def validate_inputs(
        self,
        stand_state: StandState,
        tree_states: TreeStateSequence,
        *,
        instance: GrowthModelProtocol | None = None,
    ) -> GrowthModelProtocol:
        """Ensure that snapshot data satisfies the model requirements."""

        missing_tree_fields = self._missing_tree_fields(tree_states)
        if missing_tree_fields:
            raise ValueError(
                f"Tree snapshots for module {self.name} are missing fields:"
                f" {sorted(missing_tree_fields)}"
            )

        missing_stand_fields = self._missing_stand_fields(stand_state)
        if missing_stand_fields:
            raise ValueError(
                f"Stand snapshot for module {self.name} is missing fields:"
                f" {sorted(missing_stand_fields)}"
            )

        model = instance or self.instantiate()
        model.validate_inputs(stand_state, tree_states)
        return model

    def _missing_tree_fields(self, tree_states: Sequence[TreeState]) -> set[str]:
        if not self.required_tree_fields:
            return set()
        missing: set[str] = set()
        for field_name in self.required_tree_fields:
            for tree_state in tree_states:
                if getattr(tree_state, field_name, None) is None:
                    missing.add(field_name)
                    break
        return missing

    def _missing_stand_fields(self, stand_state: StandState) -> set[str]:
        if not self.required_stand_fields:
            return set()
        missing: set[str] = set()
        for field_name in self.required_stand_fields:
            if getattr(stand_state, field_name, None) in (None, {}):
                missing.add(field_name)
        return missing
