from Munin.Timber.Timber import Timber
from typing import Optional, Union
import numpy as np
import numpy.typing as npt

class Taper:
    '''
    General Taper class for subimplementations of different tapers.
    '''
    def __init__(self, timber: Timber, taper_subclass_instance: 'Taper'):
        """
        :param timber: A Timber object
        :param taper_subclass_instance: An already-initialized instance of a Taper subclass
        """
        self.timber = timber
        self.timber.validate()

        self.taper = taper_subclass_instance
        # The subclass instance should have already validated the timber object.

    def get_diameter_at_height(self, height_m: float) -> float:
        """
        Returns diameter under bark (cm) at a given height (m) from stump.
        This calls your subclass taper.get_diameter_at_height function.
        """
        stump_height_m = 0.0 if self.timber.stump_height_m is None else self.timber.stump_height_m
        h = height_m + stump_height_m
        if h < 0 or h > self.timber.height_m:
            return 0.0
        
        # --- CORRECTED CALL: No longer passes self.timber ---
        diam_cm = self.taper.get_diameter_at_height(h)
        
        if diam_cm is None:
            return 0.0
        return diam_cm

    def get_diameter_vectorised(self, h_array: Union[npt.ArrayLike, np.ndarray]) -> np.ndarray:
        # --- CORRECTED: Vectorize the wrapper method to ensure height checks are applied ---
        f = np.vectorize(self.get_diameter_at_height, otypes=[np.float32])
        return f(h_array)

    def get_height_at_diameter(self, diameter: float) -> float:
        """
        Returns the height (m above stump) at which the tree reaches the specified diameter (cm).
        """
        # --- CORRECTED CALL: No longer passes self.timber ---
        height_above_ground = self.taper.get_height_at_diameter(diameter)

        stump_height = 0.0 if self.timber.stump_height_m is None else self.timber.stump_height_m

        if height_above_ground is None:
            return 0.0
            
        # Return height above stump
        return height_above_ground - stump_height

    def volume_section(self, h1_m: float, h2_m: float) -> float:
        """
        Integrate volume (m^3) from h1_m to h2_m above stump.
        """
        from Munin.Timber.TimberVolumeIntegrator import TimberVolumeIntegrator #Local import to break circular dependency
        if h2_m <= h1_m:
            return 0.0
        
        # The integrator now works with the stateful taper instance.
        return TimberVolumeIntegrator.integrate_volume(h1_m, h2_m, self)