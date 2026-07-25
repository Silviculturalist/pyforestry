"""Swedish regeneration quality equations.

Regeneration stocking (SLH) is Elfving (1992), in :mod:`elfving_1992`. The
young-stand quality (W / ASINW) derived from stocking is Elfving (1982) and
lives with the Hugin/NYSKOG functions in
:mod:`pyforestry.sweden.blocks.elfving_1982`.
"""

from .elfving_1992 import Elfving1992Regeneration

__all__ = [
    "Elfving1992Regeneration",
]
