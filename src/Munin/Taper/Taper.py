# Taper superclass
from Munin.Timber.Timber import Timber
from typing import Optional, Union
import numpy as np
import numpy.typing as npt

class Taper:
    '''
    General Taper class for subimplementations of different tapers.
    '''
    def __init__(self,timber,taper):
        """
        :param timber A Timber object
        :param taper a Taper subclass 
        """
        self.timber = timber
        self.timber.validate() #Ensure object is valid

        self.taper = taper
        self.taper.validate(timber) #Ensure compatibility of taper and timber class.


    def get_diameter_at_height(self, height_m: float) -> float:
        """
        Returns diameter under bark (cm) at a given height (m) from stump.
        This calls your subclass taper.get_diameter_at_height function. 
        """
        # Make sure we don't go below stump or above the actual tree:
        h = height_m + self.timber.stump_height_m
        if h < 0:
            return 0.0
        if h > self.timber.height_m:
            return 0.0
        diam_cm = self.taper.get_diameter_at_height(self.timber, h)
        if diam_cm is None:
            return 0.0
        return diam_cm
    
    def get_diameter_vectorised(self, h_array: Union[npt.ArrayLike, np.ndarray]) -> np.ndarray:
        f = np.vectorize(lambda h: self.taper.get_diameter_at_height(self.timber, h), otypes=[np.float32])
        return f(h_array)
    
    def get_height_at_diameter(self, diameter: float) -> float:
        """
        Returns the height (m above stump) at which the tree reaches the specified diameter (cm).
        Delegates to the subclass implementation of taper.get_height_at_diameter.
        """
        return self.taper.get_height_at_diameter(self.timber, diameter)


    def volume_section(self, h1_m: float, h2_m: float) -> float:
        """
        Integrate volume (m^3) from h1_m to h2_m above stump.
        """
        from Munin.Timber.TimberVolumeIntegrator import TimberVolumeIntegrator  # local import to break circular dependency
        if h2_m <= h1_m:
            return 0.0
        # Adjust to absolute heights if you're adding a stump offset:
        abs_h1 = h1_m + self.timber.stump_height_m
        abs_h2 = h2_m + self.timber.stump_height_m

        # clamp to 0..treeHeight
        abs_h1 = max(0.0, abs_h1)
        abs_h2 = min(self.timber.height_m, abs_h2)
        if abs_h2 <= abs_h1:
            return 0.0

        return TimberVolumeIntegrator.integrate_volume(abs_h1, abs_h2, self.timber, self.taper)
