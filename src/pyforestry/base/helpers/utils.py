from typing import Union


def enum_code(value: Union[int, float, bool, str]) -> Union[int, float, bool, str]:
    """Return numeric or label from an enum member or dataclass."""
    if hasattr(value, "value"):
        inner = value.value
        if hasattr(inner, "code"):
            if inner.__class__.__name__ == "ClimateZoneData":
                return inner.label
            return inner.code
        if hasattr(inner, "label"):
            return inner.label
    if hasattr(value, "code"):
        if value.__class__.__name__ == "ClimateZoneData":
            return value.label
        return value.code
    if hasattr(value, "label"):
        return value.label
    return value
