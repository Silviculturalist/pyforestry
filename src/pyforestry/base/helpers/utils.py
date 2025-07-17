from typing import Union


def enum_code(value: Union[int, float, bool, str]) -> Union[int, float, bool, str]:
    """Return numeric or label from an enum member or dataclass."""
    if hasattr(value, "value"):
        inner = value.value
        if hasattr(inner, "label"):
            return inner.label
        if hasattr(inner, "code"):
            return inner.code
    if hasattr(value, "label"):
        return value.label
    if hasattr(value, "code"):
        return value.code
    return value
