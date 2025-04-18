# Suggested Munin/Taper/__init__.py
from .Taper import Taper
# Assuming sweden/__init__.py exposes EdgrenNylinder1949
from .sweden import EdgrenNylinder1949
# Assuming norway/__init__.py exposes Hansen2023
from .norway import Hansen2023

__all__ = [
    'Taper',                # Base class
    'EdgrenNylinder1949',    # Specific Swedish taper class
    'Hansen2023'            # Specific Norwegian taper class
]