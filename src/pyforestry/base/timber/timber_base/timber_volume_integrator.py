import numpy as np
from scipy.integrate import quad

class TimberVolumeIntegrator:
    @staticmethod
    def cylinder_volume_integrand(height, taper_instance):
        """
        Calculate the cross-sectional area. Now takes a taper instance.
        """
        # timber object is no longer needed here
        diameter = taper_instance.get_diameter_at_height(height_m=height)
        if diameter is None:
            return 0.0
        radius = diameter / 200 #cm to m
        return np.pi * (radius ** 2)

    @staticmethod
    def integrate_volume(height1, height2, taper_instance):
        """
        Integrate the volume of the cylinder between two heights.
        """
        if height2 <= height1:
            return 0.0
            
        # The 'args' tuple now only contains the taper_instance
        volume, _ = quad(
            TimberVolumeIntegrator.cylinder_volume_integrand,
            height1,
            height2,
            args=(taper_instance),
            # Other parameters remain the same
            epsabs=1e-3, 
            limit=50
        )
        return volume