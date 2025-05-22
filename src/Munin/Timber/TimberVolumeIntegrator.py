from Munin.Taper.Taper import Taper
import numpy as np
from scipy.integrate import quad

class TimberVolumeIntegrator:
    """
    A utility class for calculating the integrated volume of a timber log between two heights using a taper function.
    """

    @staticmethod
    def cylinder_volume_integrand(height, timber, taper_class):
        """
        Calculate the cross-sectional area (πr^2) at a given height.

        :param height: Height at which to compute the diameter and area.
        :param timber: The Timber object (e.g., timber_birch).
        :param taper_class: The Taper class (e.g., TimberEdgrenDiameter).
        :return: Cross-sectional area at the given height.
        """
        diameter = taper_class.get_diameter_at_height(timber, height_m=height)
        radius = diameter / 200 #cm to m
        return np.pi * (radius ** 2)

    @staticmethod
    def integrate_volume(height1, height2, timber, taper_class):
        """
        Integrate the volume of the cylinder between two heights.

        :param height1: The lower bound of integration.
        :param height2: The upper bound of integration.
        :param timber: The Timber object (e.g., timber_birch).
        :param taper_class: The Taper class (e.g., TimberEdgrenDiameter).
        :return: The integrated volume (m3)
        """
        volume, _ = quad(
            TimberVolumeIntegrator.cylinder_volume_integrand, height1, height2,
            args=(timber, taper_class)
        )
        return volume