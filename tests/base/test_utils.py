from dataclasses import dataclass

from pyforestry.base.helpers.utils import enum_code


@dataclass
class InnerCode:
    code: int


@dataclass
class OuterValueCode:
    value: InnerCode


@dataclass
class InnerLabel:
    label: str


@dataclass
class OuterValueLabel:
    value: InnerLabel


class ClimateZoneData:
    def __init__(self, label):
        self.code = 1
        self.label = label


class OuterClimate:
    def __init__(self, label):
        self.value = ClimateZoneData(label)


class ObjWithCode:
    def __init__(self, code):
        self.code = code


class ObjWithLabel:
    def __init__(self, label):
        self.label = label


def test_enum_code_from_value_code():
    obj = OuterValueCode(InnerCode(5))
    assert enum_code(obj) == 5


def test_enum_code_from_value_label():
    obj = OuterValueLabel(InnerLabel("foo"))
    assert enum_code(obj) == "foo"


def test_enum_code_climate_zone_like():
    obj = OuterClimate("bar")
    assert enum_code(obj) == "bar"


def test_enum_code_direct_attributes():
    assert enum_code(ObjWithCode(7)) == 7
    assert enum_code(ObjWithLabel("baz")) == "baz"


def test_enum_code_primitives():
    assert enum_code(3) == 3
    assert enum_code("hi") == "hi"


@dataclass
class InnerPlain:
    x: int


@dataclass
class OuterPlain:
    value: InnerPlain


def test_enum_code_no_code_or_label():
    inner = InnerPlain(1)
    outer = OuterPlain(inner)
    assert enum_code(outer) is outer
    assert enum_code(inner) is inner
