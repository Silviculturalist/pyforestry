from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pytest

from pyforestry.simulation import GrowthModule, GrowthRegistry
from pyforestry.simulation import growth_module as growth_module_mod
from pyforestry.sweden.models.elfving_hagglund_1975 import ElfvingHagglundInitialStand


class DummyModel:
    def __init__(self, foo: int, bar: float = 1.0) -> None:
        self.foo = foo
        self.bar = bar


@dataclass
class DummySchema:
    foo: int
    bar: float = 1.0


def test_create_instance_validates_dataclass_schema():
    module = GrowthModule(DummyModel, parameter_schema=DummySchema)

    instance = module.create_instance(foo=10)

    assert isinstance(instance, DummyModel)
    assert instance.foo == 10
    assert instance.bar == pytest.approx(1.0)


def test_missing_required_parameter_raises_value_error():
    module = GrowthModule(DummyModel, parameter_schema=DummySchema)

    with pytest.raises(ValueError) as exc:
        module.create_instance()

    assert "foo" in str(exc.value)


def test_unknown_argument_is_rejected():
    module = GrowthModule(DummyModel, parameter_schema=DummySchema)

    with pytest.raises(ValueError):
        module.create_instance(foo=1, baz=2)


def test_registry_resolves_by_name_and_tags():
    module = GrowthModule(
        ElfvingHagglundInitialStand,
        name="elfving_initial",
        capability_tags={"sweden", "initial", "stand"},
    )
    registry = GrowthRegistry()
    registry.register(module, aliases=["sweden.initial"], family="sweden")

    resolved = registry.get("elfving_initial")
    assert resolved is module

    tag_matches = registry.find_by_tags({"initial"})
    assert module in tag_matches

    family_modules = list(registry.iter_family("sweden"))
    assert family_modules == [module]


def test_register_family_prefixes_names():
    module_a = GrowthModule(DummyModel, name="dummy_a")
    module_b = GrowthModule(DummyModel, name="dummy_b")
    registry = GrowthRegistry()

    registered = registry.register_family(
        "demo", {"a": module_a, "b": module_b}, prefix_names=True
    )

    assert set(registered.keys()) == {"demo.a", "demo.b"}
    assert registry.get("demo.a") is module_a
    assert registry.get("demo.b") is module_b


def test_register_family_without_prefix_and_description_helpers():
    module = GrowthModule(
        DummyModel,
        name="dummy",
        description="Demo module",
        capability_tags={"tag"},
        metadata={"source": "unit-test"},
    )
    registry = GrowthRegistry()

    registered = registry.register_family("demo", [("dummy", module)], prefix_names=False)

    assert registered == {"dummy": module}
    assert registry.describe()["families"]["demo"] == ["dummy"]
    assert registry.describe()["modules"]["dummy"]["name"] == "dummy"
    assert module.describe()["metadata"] == {"source": "unit-test"}


def test_registry_duplicate_and_overwrite_behaviour():
    module = GrowthModule(DummyModel, name="duplicate")
    registry = GrowthRegistry()

    registry.register(module, name="duplicate")
    with pytest.raises(KeyError):
        registry.register(module, name="duplicate")

    registry.register(module, name="duplicate", overwrite=True)
    module.name = ""
    with pytest.raises(ValueError):
        registry.register(module)
    with pytest.raises(KeyError) as exc:
        registry.get("missing")
    assert "Unknown module" in str(exc.value)


def test_registry_find_by_tags_variants():
    module_one = GrowthModule(DummyModel, capability_tags={"alpha", "beta"})
    module_two = GrowthModule(DummyModel, capability_tags={"beta"})
    module_three = GrowthModule(DummyModel, capability_tags={"gamma"})
    registry = GrowthRegistry()
    registry.register(module_one, name="one")
    registry.register(module_two, name="two")
    registry.register(module_three, name="three")

    assert registry.find_by_tags({"alpha"}) == [module_one]
    assert set(registry.find_by_tags({"beta"}, match_all=False)) == {
        module_one,
        module_two,
    }
    assert set(registry.find_by_tags(set())) == {
        module_one,
        module_two,
        module_three,
    }
    assert list(registry.iter_family("missing")) == []


def test_module_validators_are_invoked():
    calls: list[int] = []

    def validator(params: Mapping[str, Any]) -> None:
        calls.append(params["foo"])
        if params["foo"] < 0:
            raise ValueError("foo must be positive")

    module = GrowthModule(DummyModel, parameter_schema=DummySchema, validators=[validator])

    module.create_instance(foo=1)
    with pytest.raises(ValueError):
        module.create_instance(foo=-1)

    assert calls == [1, -1]


def test_module_without_schema_enforces_constructor_requirements():
    class NeedsValue:
        def __init__(self, value: int, other: float = 0.5) -> None:
            self.value = value
            self.other = other

    module = GrowthModule(NeedsValue)

    with pytest.raises(ValueError) as exc:
        module.create_instance()

    assert "value" in str(exc.value)


def test_module_type_checks_and_signature_property():
    module = GrowthModule(DummyModel, parameter_schema=DummySchema)

    assert "foo" in str(module.signature)
    assert module.name == "dummy_model"

    with pytest.raises(TypeError):
        GrowthModule(42)  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        GrowthModule(DummyModel, parameter_schema=int)  # type: ignore[arg-type]


def test_validate_parameters_reports_unknown_arguments():
    module = GrowthModule(DummyModel)

    with pytest.raises(ValueError):
        module.validate_parameters(foo=1, baz=2)


def test_pydantic_like_schema_support(monkeypatch: pytest.MonkeyPatch):
    class FakeValidationError(Exception):
        pass

    class FakeBase:
        def __init__(self, **data: Any) -> None:
            self.data = data

        def model_dump(self) -> Mapping[str, Any]:
            return self.data

    class FakeSchema(FakeBase):
        pass

    monkeypatch.setattr(growth_module_mod, "_PydanticBaseModel", FakeBase)
    monkeypatch.setattr(growth_module_mod, "_PydanticValidationError", FakeValidationError)

    module = GrowthModule(DummyModel, parameter_schema=FakeSchema)

    instance = module.create_instance(foo=7)
    assert isinstance(instance, DummyModel)
    assert module._schema_kind == "pydantic"


def test_pydantic_like_validation_error(monkeypatch: pytest.MonkeyPatch):
    class FakeValidationError(Exception):
        pass

    class FakeBase:
        def __init__(self, **data: Any) -> None:
            if "foo" not in data:
                raise FakeValidationError("foo required")
            self.data = data

        def dict(self) -> Mapping[str, Any]:
            return self.data

    class FakeSchema(FakeBase):
        pass

    monkeypatch.setattr(growth_module_mod, "_PydanticBaseModel", FakeBase)
    monkeypatch.setattr(growth_module_mod, "_PydanticValidationError", FakeValidationError)

    module = GrowthModule(DummyModel, parameter_schema=FakeSchema)

    with pytest.raises(ValueError) as exc:
        module.create_instance()

    assert "foo required" in str(exc.value)


def test_pydantic_like_schema_without_dump(monkeypatch: pytest.MonkeyPatch):
    class FakeBase:
        def __init__(self, **data: Any) -> None:
            self.data = data

    class FakeSchema(FakeBase):
        pass

    monkeypatch.setattr(growth_module_mod, "_PydanticBaseModel", FakeBase)
    monkeypatch.setattr(growth_module_mod, "_PydanticValidationError", ValueError)

    module = GrowthModule(DummyModel, parameter_schema=FakeSchema)

    params = module.validate_parameters(foo=2)
    assert params == {"foo": 2}


def test_varargs_signature_is_supported():
    class VarArgsModel:
        def __init__(self, value: int, *args: Any, **kwargs: Any) -> None:
            self.value = value

    module = GrowthModule(VarArgsModel)

    params = module.validate_parameters(value=3)
    assert params == {"value": 3}
    sig = module.signature
    first_param = next(iter(sig.parameters.values()))
    assert not module._is_required_parameter("self", first_param)
    assert not module._is_required_parameter("args", sig.parameters["args"])
    assert not module._is_required_parameter("kwargs", sig.parameters["kwargs"])


def test_pydantic_like_schema_dict(monkeypatch: pytest.MonkeyPatch):
    class FakeBase:
        def __init__(self, **data: Any) -> None:
            self.data = data

        def dict(self) -> Mapping[str, Any]:
            return self.data

    class FakeSchema(FakeBase):
        pass

    monkeypatch.setattr(growth_module_mod, "_PydanticBaseModel", FakeBase)
    monkeypatch.setattr(growth_module_mod, "_PydanticValidationError", ValueError)

    module = GrowthModule(DummyModel, parameter_schema=FakeSchema)

    params = module.validate_parameters(foo=5)
    assert params == {"foo": 5}
