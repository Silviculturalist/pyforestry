"""Utilities for instantiating and organising growth model implementations.

The :class:`GrowthModule` class acts as a light-weight factory around an
underlying growth model class.  It provides structured metadata, optional input
validation hooks and a :meth:`create_instance` method that can be used by
simulation pipelines to safely instantiate configured models.

Wrapping existing models
========================
The factory is intentionally minimal so that existing model implementations can
be wrapped without code changes.  For example, the
:class:`~pyforestry.sweden.models.elfving_hagglund_1975.ElfvingHagglundInitialStand`
model exposes static helpers for estimating young stand properties.  It can be
wrapped as follows::

    from dataclasses import dataclass
    from pyforestry.simulation import GrowthModule, GrowthRegistry
    from pyforestry.sweden.models.elfving_hagglund_1975 import (
        ElfvingHagglundInitialStand,
    )

    @dataclass
    class StandConfig:
        latitude: float
        altitude: float
        dominant_height: float

    elfving_module = GrowthModule(
        ElfvingHagglundInitialStand,
        name="elfving_initial",
        description="Initial stand heuristics for Sweden (Elfving & Hägglund 1975)",
        parameter_schema=StandConfig,
        capability_tags={"sweden", "initial", "stand"},
    )

    registry = GrowthRegistry()
    registry.register(elfving_module)

    model = registry.get("elfving_initial").create_instance()

The registry handles name resolution and tag based discovery for higher-level
simulation orchestration.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import fields, is_dataclass
from inspect import Parameter, Signature, signature
from types import MappingProxyType
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    Type,
    TypeVar,
)

try:  # pragma: no cover - optional dependency detection
    from pydantic import BaseModel as _PydanticBaseModel
    from pydantic import ValidationError as _PydanticValidationError
except Exception:  # pragma: no cover - we treat pydantic as optional
    _PydanticBaseModel = None
    _PydanticValidationError = Exception

T = TypeVar("T")
Validator = Callable[[Mapping[str, Any]], None]


class GrowthModule(Generic[T]):
    """Factory and metadata wrapper for growth model implementations.

    Parameters
    ----------
    model_cls:
        The concrete class implementing the growth model.
    name:
        Optional canonical identifier.  Defaults to the model class name in
        snake case.
    description:
        Human readable description of the module.
    parameter_schema:
        Optional dataclass or :mod:`pydantic` model used to validate input
        arguments for :meth:`create_instance`.
    capability_tags:
        Informational tags describing the model (e.g. geography, species).
    metadata:
        Arbitrary metadata stored alongside the module definition.
    validators:
        Iterable of callables that receive the normalised keyword arguments prior
        to instantiation.  Validators may raise :class:`ValueError` to reject an
        input configuration.
    """

    model_cls: Type[T]
    name: str
    description: Optional[str]
    metadata: Mapping[str, Any]
    capability_tags: frozenset[str]
    validators: tuple[Validator, ...]

    def __init__(
        self,
        model_cls: Type[T],
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameter_schema: Optional[Type[Any]] = None,
        capability_tags: Optional[Iterable[str]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        validators: Optional[Iterable[Validator]] = None,
    ) -> None:
        if not isinstance(model_cls, type):
            raise TypeError("model_cls must be a class type")

        self.model_cls = model_cls
        self.name = name or self._default_name(model_cls.__name__)
        self.description = description
        self.capability_tags = frozenset(capability_tags or ())
        self.metadata = MappingProxyType(dict(metadata or {}))
        self.validators = tuple(validators or ())

        self._signature = self._resolve_signature(model_cls)
        self._schema_type = parameter_schema
        self._schema_kind = self._infer_schema_kind(parameter_schema)

    @staticmethod
    def _default_name(name: str) -> str:
        snake = []
        for char in name:
            if char.isupper() and snake:
                snake.append("_")
            snake.append(char.lower())
        return "".join(snake) or name

    @staticmethod
    def _resolve_signature(model_cls: Type[T]) -> Signature:
        try:
            sig = signature(model_cls)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise TypeError(f"Unable to inspect constructor for {model_cls!r}") from exc
        return sig

    @staticmethod
    def _infer_schema_kind(schema: Optional[Type[Any]]) -> Optional[str]:
        if schema is None:
            return None
        if is_dataclass(schema):
            return "dataclass"
        if (
            _PydanticBaseModel is not None
            and isinstance(schema, type)
            and issubclass(schema, _PydanticBaseModel)
        ):
            return "pydantic"
        raise TypeError("parameter_schema must be a dataclass or pydantic model")

    @property
    def signature(self) -> Signature:
        """Return the constructor signature for the wrapped model."""

        return self._signature

    def validate_parameters(self, **kwargs: Any) -> Dict[str, Any]:
        """Validate keyword arguments and return a normalised mapping.

        The validation workflow is as follows:

        1. If a ``parameter_schema`` was supplied, instantiate it to perform
           structural validation.  Dataclasses provide shape validation whereas
           :mod:`pydantic` models additionally perform runtime type checking when
           available.
        2. The constructor signature of ``model_cls`` is consulted to ensure that
           only supported arguments are provided and that mandatory arguments are
           present.
        3. User supplied ``validators`` are executed with the normalised keyword
           arguments.

        Returns
        -------
        dict
            Normalised keyword arguments that can safely be passed to
            :class:`model_cls`.
        """

        normalised = self._apply_schema(kwargs)
        bound = self._bind_arguments(normalised)
        required_missing = [
            name
            for name, param in self._signature.parameters.items()
            if self._is_required_parameter(name, param) and name not in bound.arguments
        ]
        if required_missing:
            raise ValueError("Missing required parameters: " + ", ".join(sorted(required_missing)))
        for validator in self.validators:
            validator(normalised)
        return normalised

    def _apply_schema(self, kwargs: Mapping[str, Any]) -> Dict[str, Any]:
        if self._schema_kind is None:
            return dict(kwargs)
        if self._schema_kind == "dataclass":
            try:
                schema_obj = self._schema_type(**kwargs)  # type: ignore[misc]
            except TypeError as exc:
                raise ValueError(str(exc)) from exc
            return {field.name: getattr(schema_obj, field.name) for field in fields(schema_obj)}
        if self._schema_kind == "pydantic":
            try:
                schema_obj = self._schema_type(**kwargs)  # type: ignore[misc]
            except _PydanticValidationError as exc:  # pragma: no cover - depends on pydantic
                raise ValueError(str(exc)) from exc
            if hasattr(schema_obj, "model_dump"):
                return schema_obj.model_dump()
            if hasattr(schema_obj, "dict"):
                return schema_obj.dict()
            return dict(kwargs)
        raise RuntimeError("Unsupported schema kind")  # pragma: no cover - defensive

    def _bind_arguments(self, kwargs: Mapping[str, Any]):
        try:
            return self._signature.bind_partial(**kwargs)
        except TypeError as exc:
            raise ValueError(str(exc)) from exc

    @staticmethod
    def _is_required_parameter(name: str, param: Parameter) -> bool:
        if name == "self":
            return False
        if param.kind in (Parameter.VAR_KEYWORD, Parameter.VAR_POSITIONAL):
            return False
        return param.default is Parameter.empty

    def create_instance(self, **kwargs: Any) -> T:
        """Instantiate the wrapped model after validating ``kwargs``."""

        params = self.validate_parameters(**kwargs)
        return self.model_cls(**params)

    def describe(self) -> Mapping[str, Any]:
        """Return a serialisable description of the module."""

        return {
            "name": self.name,
            "description": self.description,
            "capability_tags": sorted(self.capability_tags),
            "metadata": dict(self.metadata),
            "model": f"{self.model_cls.__module__}.{self.model_cls.__qualname__}",
        }


class GrowthRegistry:
    """Registry for organising and discovering growth modules."""

    def __init__(self) -> None:
        self._modules: Dict[str, GrowthModule[Any]] = {}
        self._families: Dict[str, set[str]] = defaultdict(set)

    def register(
        self,
        module: GrowthModule[Any],
        *,
        name: Optional[str] = None,
        aliases: Optional[Iterable[str]] = None,
        family: Optional[str] = None,
        overwrite: bool = False,
    ) -> GrowthModule[Any]:
        """Register ``module`` under ``name`` and optional ``aliases``."""

        resolved_name = name or module.name
        if not resolved_name:
            raise ValueError("A module name must be provided")
        self._store_module(resolved_name, module, overwrite)
        if aliases:
            for alias in aliases:
                self._store_module(alias, module, overwrite)
        if family:
            self._families[family].add(resolved_name)
        return module

    def _store_module(self, name: str, module: GrowthModule[Any], overwrite: bool) -> None:
        if not overwrite and name in self._modules:
            raise KeyError(f"A module named '{name}' is already registered")
        self._modules[name] = module

    def register_family(
        self,
        family: str,
        modules: Mapping[str, GrowthModule[Any]] | Iterable[tuple[str, GrowthModule[Any]]],
        *,
        prefix_names: bool = True,
        overwrite: bool = False,
    ) -> Mapping[str, GrowthModule[Any]]:
        """Register a collection of modules under a logical family name."""

        if isinstance(modules, Mapping):
            items = modules.items()
        else:
            items = list(modules)
        registered: Dict[str, GrowthModule[Any]] = {}
        for short_name, module in items:
            full_name = f"{family}.{short_name}" if prefix_names else short_name
            self.register(module, name=full_name, family=family, overwrite=overwrite)
            registered[full_name] = module
        return registered

    def get(self, name: str) -> GrowthModule[Any]:
        """Return the module registered under ``name``."""

        try:
            return self._modules[name]
        except KeyError as exc:
            raise KeyError(f"Unknown module '{name}'") from exc

    def find_by_tags(
        self, tags: Iterable[str], *, match_all: bool = True
    ) -> list[GrowthModule[Any]]:
        """Return modules matching the provided capability ``tags``."""

        query = frozenset(tags)
        if not query:
            return list(self._modules.values())
        matches: list[GrowthModule[Any]] = []
        for module in dict.fromkeys(self._modules.values()):
            if match_all and not query.issubset(module.capability_tags):
                continue
            if not match_all and module.capability_tags.isdisjoint(query):
                continue
            matches.append(module)
        return matches

    def iter_family(self, family: str) -> Iterator[GrowthModule[Any]]:
        """Yield modules that were registered under ``family``."""

        names = self._families.get(family, set())
        for name in names:
            yield self._modules[name]

    def describe(self) -> Mapping[str, Any]:
        """Return a serialisable snapshot of the registry."""

        families = {
            family: sorted(names)
            for family, names in sorted(self._families.items(), key=lambda item: item[0])
        }
        modules = {
            name: module.describe()
            for name, module in sorted(self._modules.items(), key=lambda item: item[0])
        }
        return {"families": families, "modules": modules}


__all__ = ["GrowthModule", "GrowthRegistry"]
