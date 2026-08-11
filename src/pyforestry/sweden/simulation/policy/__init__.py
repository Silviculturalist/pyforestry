"""Scenario and management policy rulesets for Sweden.

The values are Sweden's; what the fields mean and how an unknown
scenario id is handled is :mod:`pyforestry.simulation.policy`, because the two
regions had answered both questions differently.
"""

from .management_rulesets import (
    management_intensity,
    management_plan,
    supported_management_scenarios,
)
from .scenario_rulesets import scenario_forcings, supported_scenarios

__all__ = [
    "management_intensity",
    "management_plan",
    "scenario_forcings",
    "supported_management_scenarios",
    "supported_scenarios",
]
