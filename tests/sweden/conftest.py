"""Make this directory importable so tests can share a plain helper module.

``--import-mode=importlib`` (required, because the region test suites share
basenames) deliberately does not put a test file's own directory on ``sys.path``.
That is right for test modules and inconvenient for a helper that is not one:
``_elfving_2010_baseline_scenarios`` defines the pinned projection scenarios and is
imported both by the parity test here and by
``scripts/pin_elfving_2010_baseline.py``, so it has to live somewhere both can
reach.
"""

import sys
from pathlib import Path

_HERE = str(Path(__file__).parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
