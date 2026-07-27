"""Norway's scenario configuration.

Norway ships no composite pipeline yet, so unlike
:mod:`pyforestry.sweden.simulation.presets` this package holds only the
configuration tier -- a frozen record of seeds, stage names and rulesets that
runs nothing.
"""

from ._common import ScenarioConfig
from .baseline import build_baseline_scenario_config

__all__ = ["ScenarioConfig", "build_baseline_scenario_config"]
