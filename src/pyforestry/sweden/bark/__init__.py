"""Public interface for bark thickness models for Swedish species."""

from .hannrup_2004 import (
    Hannrup_2004_bark_picea_abies_sweden,
    Hannrup_2004_bark_pinus_sylvestris_sweden,
)
from .soderberg_1992 import soderberg_1992_bark_thickness_bh_mm

__all__ = [
    "Hannrup_2004_bark_picea_abies_sweden",
    "Hannrup_2004_bark_pinus_sylvestris_sweden",
    "soderberg_1992_bark_thickness_bh_mm",
]
