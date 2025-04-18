# Elfving 5-year basal area increment

import math

class Elfving_2010_IBM:

    @staticmethod
    def aspen_BAI5(diameter_cm,
              BA_sum_of_trees_with_larger_diameter, BA_Aspen, Basal_area_plot,
              Basal_area_stand, computed_tree_age, latitude, altitude,
              vegetation, uneven_aged, thinned=False,
              last_thinned=0, divided_plot=0, edge_effect=0):
        """
        Calculate the basal area increment for Aspen trees.

        @param diameter_cm: Diameter of the tree at breast height (1.3 m), in cm.
        @param BA_sum_of_trees_with_larger_diameter: Basal area sum of trees with larger diameters than the target tree, in m²/ha.
        @param BA_Aspen: Basal area of Aspen on the plot, in m²/ha.
        @param Basal_area_plot: Total basal area on the plot, in m²/ha.
        @param Basal_area_stand: Total basal area in the surrounding stand, in m²/ha.
        @param computed_tree_age: Estimated age of the tree at breast height.
        @param latitude: Latitude of the location, in decimal degrees.
        @param altitude: Altitude of the location, in meters above sea level.
        @param vegetation: Vegetation type code according to the Swedish National Forest Inventory.
        @param uneven_aged: Whether less than 80% of the main stand volume is within a 20-year age-span (True/False).
        @param thinned: Whether the plot has been thinned (True/False).
        @param last_thinned: Number of growth seasons since the plot was last thinned.
        @param divided_plot: Whether the plot has been divided (default: 0).
        @param edge_effect: Whether the plot is near an open area causing edge effects (default: 0).

        @return: The 5-year increment of basal area (in m²).
        @throws ValueError: If both `divided_plot` and `edge_effect` are set to 1.
        """

        if divided_plot == 1 and edge_effect == 1:
            raise ValueError("Both divided_plot and edge_effect cannot be 1 at the same time.")

        if uneven_aged:
            computed_tree_age *= 0.9

        BA_quotient_Aspen = BA_Aspen / Basal_area_plot
        rich = 1 if vegetation <= 9 else 0
        thinned_recently = 1 if thinned and last_thinned <= 10 else 0

        return (
            math.exp(
                0.9945 +
                1.9071 * math.log(diameter_cm + 1) -
                0.3313 * (diameter_cm / 10) -
                0.3040 * (BA_sum_of_trees_with_larger_diameter / (diameter_cm + 1)) -
                0.4058 * math.log(computed_tree_age + 20) -
                0.1981 * math.log(Basal_area_plot + 3) -
                0.5967 * math.sqrt(BA_quotient_Aspen) +
                0.4408 * (4835 - (57.6 * latitude) - (0.9 * altitude)) +
                0.4759 * rich +
                0.2143 * thinned_recently +
                0.2427 * math.log((Basal_area_plot + 1) / (Basal_area_stand + 1))
            ) / 10000
        )

    @staticmethod
    def beech_BAI5(diameter_cm,BA_sum_of_trees_with_larger_diameter, BA_Beech, Basal_area_plot,
              Basal_area_stand, computed_tree_age, latitude, SIS, divided_plot=0, edge_effect=0, uneven_aged=False,
              thinned=False, last_thinned=0):
        """
        Calculate the basal area increment for Beech trees.

        @param diameter_cm: Diameter of the tree at breast height (1.3 m), in cm.
        @param BA_sum_of_trees_with_larger_diameter: Basal area sum of trees with larger diameters than the target tree, in m²/ha.
        @param BA_Beech: Basal area of Beech on the plot, in m²/ha.
        @param Basal_area_plot: Total basal area on the plot, in m²/ha.
        @param Basal_area_stand: Total basal area in the surrounding stand, in m²/ha.
        @param computed_tree_age: Estimated age of the tree at breast height.
        @param latitude: Latitude of the location, in decimal degrees.
        @param SIS: Site Index predicted from Stand factors.
        @param divided_plot: Whether the plot has been divided (default: 0).
        @param edge_effect: Whether the plot is near an open area causing edge effects (default: 0).
        @param uneven_aged: Whether less than 80% of the main stand volume is within a 20-year age-span (True/False).
        @param thinned: Whether the plot has been thinned (True/False).
        @param last_thinned: Number of growth seasons since the plot was last thinned.

        @return: The 5-year increment of basal area (in m²).
        @throws ValueError: If both `divided_plot` and `edge_effect` are set to 1.
        """

        if divided_plot == 1 and edge_effect == 1:
            raise ValueError("Both divided_plot and edge_effect cannot be 1 at the same time.")

        if uneven_aged:
            computed_tree_age *= 0.9

        BA_quotient_Beech = BA_Beech / Basal_area_plot
        thinned_recently = 1 if thinned and last_thinned <= 10 else 0

        return (
            math.exp(
                1.7005 +
                2.5823 * math.log(diameter_cm + 1) -
                0.3758 * (diameter_cm / 10) -
                0.2079 * (BA_sum_of_trees_with_larger_diameter / (diameter_cm + 1)) -
                0.4478 * math.log(computed_tree_age + 20) -
                0.5348 * math.log(Basal_area_plot + 3) -
                0.9304 * math.sqrt(BA_quotient_Beech) -
                0.1906 * (latitude - 50) +
                0.3055 * (SIS / 10) +
                0.2200 * thinned_recently +
                0.2009 * divided_plot +
                0.2669 * math.log((Basal_area_plot + 1) / (Basal_area_stand + 1))
            ) / 10000
        )

    @staticmethod
    def birch_BAI5(diameter_cm,
              BA_sum_of_trees_with_larger_diameter, BA_Birch, Basal_area_plot,
              Basal_area_stand, computed_tree_age, latitude, altitude,
              vegetation, edge_effect=0, uneven_aged=False,
              fertilised=0, thinned=False, last_thinned=0):
        """
        Calculate the basal area increment for Birch trees.

        @param diameter_cm: Diameter of the tree at breast height (1.3 m), in cm.
        @param BA_sum_of_trees_with_larger_diameter: Basal area sum of trees with larger diameters than the target tree, in m²/ha.
        @param BA_Birch: Basal area of Birch on the plot, in m²/ha.
        @param Basal_area_plot: Total basal area on the plot, in m²/ha.
        @param Basal_area_stand: Total basal area in the surrounding stand, in m²/ha.
        @param computed_tree_age: Estimated age of the tree at breast height.
        @param latitude: Latitude of the location, in decimal degrees.
        @param altitude: Altitude of the location, in meters above sea level.
        @param vegetation: Vegetation type code according to the Swedish National Forest Inventory.
        @param edge_effect: Whether the plot is near an open area causing edge effects (default: 0).
        @param uneven_aged: Whether less than 80% of the main stand volume is within a 20-year age-span (True/False).
        @param fertilised: Whether the plot has been fertilised (default: 0).
        @param thinned: Whether the plot has been thinned (True/False).
        @param last_thinned: Number of growth seasons since the plot was last thinned.

        @return: The 5-year increment of basal area (in m²).
        """

        if uneven_aged:
            computed_tree_age *= 0.9

        BA_quotient_Birch = BA_Birch / Basal_area_plot
        rich = 1 if vegetation <= 9 else 0
        thinned_recently = 1 if thinned and last_thinned <= 10 else 0

        return (
            math.exp(
                5.9648 +
                1.2217 * math.log(diameter_cm + 1) -
                0.3998 * (BA_sum_of_trees_with_larger_diameter / (diameter_cm + 1)) -
                0.9226 * math.log(computed_tree_age + 20) +
                0.4772 * (4835 - (57.6 * latitude) - (0.9 * altitude)) -
                0.2090 * math.log(Basal_area_plot + 3) -
                0.5821 * math.sqrt(BA_quotient_Birch) -
                0.5386 * (4835 - (57.6 * latitude) - (0.9 * altitude)) +
                0.3439 * rich +
                0.3844 * (fertilised and vegetation < 12) +
                0.1814 * thinned_recently +
                0.2258 * edge_effect +
                0.1321 * math.log((Basal_area_plot + 1) / (Basal_area_stand + 1))
            ) / 10000
        )

    @staticmethod
    def noble_BAI5(diameter_cm, BA_sum_of_trees_with_larger_diameter, Basal_area_plot,
              Basal_area_stand, gotland=False, vegetation=0, thinned=False,
              last_thinned=0):
        """
        Calculate the basal area increment for Noble trees.

        @param diameter_cm: Diameter of the tree at breast height (1.3 m), in cm.
        @param BA_sum_of_trees_with_larger_diameter: Basal area sum of trees with larger diameters than the target tree, in m²/ha.
        @param Basal_area_plot: Total basal area on the plot, in m²/ha.
        @param Basal_area_stand: Total basal area in the surrounding stand, in m²/ha.
        @param gotland: Whether the plot is on the island of Gotland (default: False).
        @param vegetation: Vegetation type code according to the Swedish National Forest Inventory.
        @param thinned: Whether the plot has been thinned (True/False).
        @param last_thinned: Number of growth seasons since the plot was last thinned.

        @return: The 5-year increment of basal area (in m²).
        """


        herb = 1 if vegetation < 7 else 0
        thinned_recently = 1 if thinned and last_thinned <= 10 else 0

        return (
            math.exp(
                2.3316 +
                0.8250 * math.log(diameter_cm + 1) -
                0.2877 * (BA_sum_of_trees_with_larger_diameter / (diameter_cm + 1)) -
                0.4010 * math.log(Basal_area_plot + 3) -
                0.3809 * gotland +
                0.9397 * herb +
                0.2410 * thinned_recently +
                0.4676 * math.log((Basal_area_plot + 1) / (Basal_area_stand + 1))
            ) / 10000
        )

    @staticmethod
    def oak_BAI5(diameter_cm, BA_sum_of_trees_with_larger_diameter, BA_Oak, Basal_area_plot,
            Basal_area_stand, altitude, gotland=False, vegetation=0, thinned=False,
            last_thinned=0, edge_effect=0):
        
        """
        Calculate the basal area increment for Oak trees.

        @param diameter_cm: Diameter of the tree at breast height (1.3 m), in cm.
        @param BA_sum_of_trees_with_larger_diameter: Basal area sum of trees with larger diameters than the target tree, in m²/ha.
        @param BA_Oak: Basal area of Oak on the plot, in m²/ha.
        @param Basal_area_plot: Total basal area on the plot, in m²/ha.
        @param Basal_area_stand: Total basal area in the surrounding stand, in m²/ha.
        @param altitude: Altitude of the location, in meters above sea level.
        @param gotland: Whether the plot is on the island of Gotland (default: False).
        @param vegetation: Vegetation type code according to the Swedish National Forest Inventory.
        @param thinned: Whether the plot has been thinned (True/False).
        @param last_thinned: Number of growth seasons since the plot was last thinned.
        @param edge_effect: Whether the plot is near an open area causing edge effects (default: 0).

        @return: The 5-year increment of basal area (in m²).
        """


        BA_quotient_Oak = BA_Oak / Basal_area_plot
        rich = 1 if vegetation <= 9 else 0
        thinned_recently = 1 if thinned and last_thinned <= 10 else 0

        return (
            math.exp(
                1.9047 +
                1.3115 * math.log(diameter_cm + 1) -
                0.2640 * (BA_sum_of_trees_with_larger_diameter / (diameter_cm + 1)) -
                0.5056 * math.log(Basal_area_plot + 3) -
                0.6001 * math.sqrt(BA_quotient_Oak) -
                0.4615 * gotland +
                0.3833 * (altitude / 100) -
                0.1938 * ((altitude / 100) ** 2) +
                0.2635 * rich +
                0.1034 * thinned_recently +
                0.3551 * edge_effect +
                0.1897 * math.log((Basal_area_plot + 1) / (Basal_area_stand + 1))
            ) / 10000
        )

    @staticmethod
    def pine_BAI5(diameter_cm, Basal_area_weighted_mean_diameter_cm, BA_sum_of_trees_with_larger_diameter,
             BA_Pine, Basal_area_plot, Basal_area_stand, computed_tree_age,
             latitude, gotland=False, altitude=0, SIS=0, vegetation=0,
             divided_plot=0, edge_effect=0, uneven_aged=False, fertilised=0,
             thinned=False, last_thinned=0):
        """
        Calculate the basal area increment for Pine trees.

        @param diameter_cm: Diameter of the tree at breast height (1.3 m), in cm.
        @param Basal_area_weighted_mean_diameter_cm: Basal area weighted mean diameter of the trees on the plot, in cm.
        @param BA_sum_of_trees_with_larger_diameter: Basal area sum of trees with larger diameters than the target tree, in m²/ha.
        @param BA_Pine: Basal area of Pine on the plot, in m²/ha.
        @param Basal_area_plot: Total basal area on the plot, in m²/ha.
        @param Basal_area_stand: Total basal area in the surrounding stand, in m²/ha.
        @param computed_tree_age: Estimated age of the tree at breast height.
        @param latitude: Latitude of the location, in decimal degrees.
        @param gotland: Whether the plot is on the island of Gotland (default: False).
        @param altitude: Altitude of the location, in meters above sea level.
        @param SIS: Site Index predicted from Stand factors.
        @param vegetation: Vegetation type code according to the Swedish National Forest Inventory.
        @param divided_plot: Whether the plot has been divided (default: 0).
        @param edge_effect: Whether the plot is near an open area causing edge effects (default: 0).
        @param uneven_aged: Whether less than 80% of the main stand volume is within a 20-year age-span (True/False).
        @param fertilised: Whether the plot has been fertilised (default: 0).
        @param thinned: Whether the plot has been thinned (True/False).
        @param last_thinned: Number of growth seasons since the plot was last thinned.

        @return: The 5-year increment of basal area (in m²).
        @throws ValueError: If both `divided_plot` and `edge_effect` are set to 1.
        """


        if divided_plot == 1 and edge_effect == 1:
            raise ValueError("Both divided_plot and edge_effect cannot be 1 at the same time.")

        if uneven_aged:
            computed_tree_age *= 0.9

        BA_quotient_Pine = BA_Pine / Basal_area_plot
        rich = 1 if vegetation <= 9 else 0
        fertris = 1 if fertilised and vegetation < 12 else 0
        thinned_recently = 1 if thinned and last_thinned <= 10 else 0
        thinned_long_ago = 1 if thinned and 10 < last_thinned < 25 else 0

        return (
            math.exp(
                3.4176 +
                1.0149 * math.log(diameter_cm + 1) -
                0.3902 * (BA_sum_of_trees_with_larger_diameter / (diameter_cm + 1)) -
                0.7731 * math.log(computed_tree_age + 20) +
                0.2218 * (4835 - (57.6 * latitude) - (0.9 * altitude)) +
                0.1843 * (Basal_area_weighted_mean_diameter_cm / 10) -
                0.3145 * math.log(Basal_area_plot + 3) +
                0.1391 * ((1 - BA_quotient_Pine) ** 2) -
                0.0844 * gotland +
                0.1178 * ((4835 - (57.6 * latitude) - (0.9 * altitude)) ** 2) +
                1.0890 * (SIS / 10) -
                0.2164 * ((SIS ** 2) / 100) +
                0.1011 * rich +
                0.2790 * fertris +
                0.1245 * thinned_recently +
                0.0451 * thinned_long_ago +
                0.0487 * divided_plot +
                0.1368 * edge_effect +
                0.0842 * math.log((Basal_area_plot + 1) / (Basal_area_stand + 1))
            ) / 10000
        )

    @staticmethod
    def spruce_BAI5(diameter_cm, Basal_area_weighted_mean_diameter_cm, SS_diam, stems,
               BA_sum_of_trees_with_larger_diameter, BA_Spruce, BA_Pine, Basal_area_plot,
               Basal_area_stand, computed_tree_age, latitude, gotland=False, altitude=0,
               SIS=0, vegetation=0, divided_plot=0, edge_effect=0, uneven_aged=False,
               fertilised=0, thinned=False, last_thinned=0):
        """
        Calculate the basal area increment for Spruce trees.

        @param diameter_cm: Diameter of the tree at breast height (1.3 m), in cm.
        @param Basal_area_weighted_mean_diameter_cm: Basal area weighted mean diameter of the trees on the plot, in cm.
        @param SS_diam: Sum of Squared Diameters, in cm.
        @param stems: Number of stems per hectare.
        @param BA_sum_of_trees_with_larger_diameter: Basal area sum of trees with larger diameters than the target tree, in m²/ha.
        @param BA_Spruce: Basal area of Spruce on the plot, in m²/ha.
        @param BA_Pine: Basal area of Pine on the plot, in m²/ha.
        @param Basal_area_plot: Total basal area on the plot, in m²/ha.
        @param Basal_area_stand: Total basal area in the surrounding stand, in m²/ha.
        @param computed_tree_age: Estimated age of the tree at breast height.
        @param latitude: Latitude of the location, in decimal degrees.
        @param gotland: Whether the plot is on the island of Gotland (default: False).
        @param altitude: Altitude of the location, in meters above sea level.
        @param SIS: Site Index predicted from Stand factors.
        @param vegetation: Vegetation type code according to the Swedish National Forest Inventory.
        @param divided_plot: Whether the plot has been divided (default: 0).
        @param edge_effect: Whether the plot is near an open area causing edge effects (default: 0).
        @param uneven_aged: Whether less than 80% of the main stand volume is within a 20-year age-span (True/False).
        @param fertilised: Whether the plot has been fertilised (default: 0).
        @param thinned: Whether the plot has been thinned (True/False).
        @param last_thinned: Number of growth seasons since the plot was last thinned.

        @return: The 5-year increment of basal area (in m²).
        @throws ValueError: If both `divided_plot` and `edge_effect` are set to 1.
        """


        if divided_plot == 1 and edge_effect == 1:
            raise ValueError("Both divided_plot and edge_effect cannot be 1 at the same time.")

        if uneven_aged:
            computed_tree_age *= 0.9

        BA_quotient_Spruce = BA_Spruce / Basal_area_plot
        rich = 1 if vegetation <= 9 else 0
        fertris = 1 if fertilised and vegetation < 12 else 0
        thinned_recently = 1 if thinned and last_thinned <= 10 else 0

        return (
            math.exp(
                3.4360 +
                1.5163 * math.log(diameter_cm + 1) -
                0.1520 * (diameter_cm / 10) -
                0.4024 * (BA_sum_of_trees_with_larger_diameter / (diameter_cm + 1)) +
                0.1625 * (Basal_area_weighted_mean_diameter_cm / 10) * (1 - BA_quotient_Spruce) +
                0.4702 * (Basal_area_weighted_mean_diameter_cm / 10) * (((Basal_area_weighted_mean_diameter_cm - math.sqrt(SS_diam / stems)) / Basal_area_weighted_mean_diameter_cm) ** 3) -
                0.7789 * math.log(computed_tree_age + 20) +
                0.4034 * (4835 - (57.6 * latitude) - (0.9 * altitude)) +
                0.1914 * ((Basal_area_weighted_mean_diameter_cm ** 2) / 1000) -
                0.2342 * math.log(Basal_area_plot + 3) +
                0.1754 * ((1 - BA_quotient_Spruce) ** 2) -
                0.3264 * gotland -
                0.6923 * (4835 - (57.6 * latitude) - (0.9 * altitude)) +
                0.2568 * ((4835 - (57.6 * latitude) - (0.9 * altitude)) ** 2) +
                0.2903 * (SIS / 10) +
                0.1965 * rich +
                0.4034 * fertris +
                0.1309 * thinned_recently +
                0.0561 * divided_plot +
                0.1126 * edge_effect +
                0.0770 * math.log((Basal_area_plot + 1) / (Basal_area_stand + 1))
            ) / 10000
        )

    @staticmethod
    def trivial_BAI5(diameter_cm, BA_sum_of_trees_with_larger_diameter, Basal_area_plot,
                computed_tree_age, vegetation, SIS=0, uneven_aged=False,
                thinned=False, last_thinned=0):
        """
        Calculate the basal area increment for Trivial trees.

        @param diameter_cm: Diameter of the tree at breast height (1.3 m), in cm.
        @param BA_sum_of_trees_with_larger_diameter: Basal area sum of trees with larger diameters than the target tree, in m²/ha.
        @param Basal_area_plot: Total basal area on the plot, in m²/ha.
        @param computed_tree_age: Estimated age of the tree at breast height.
        @param vegetation: Vegetation type code according to the Swedish National Forest Inventory.
        @param SIS: Site Index predicted from Stand factors.
        @param uneven_aged: Whether less than 80% of the main stand volume is within a 20-year age-span (True/False).
        @param thinned: Whether the plot has been thinned (True/False).
        @param last_thinned: Number of growth seasons since the plot was last thinned.

        @return: The 5-year increment of basal area (in m²).
        """


        if uneven_aged:
            computed_tree_age *= 0.9

        herb = 1 if vegetation < 7 else 0
        thinned_recently = 1 if thinned and last_thinned <= 10 else 0

        return (
            math.exp(
                2.1108 +
                0.9418 * math.log(diameter_cm + 1) -
                0.2599 * (BA_sum_of_trees_with_larger_diameter / (diameter_cm + 1)) -
                0.3026 * math.log(computed_tree_age + 20) -
                0.2280 * math.log(Basal_area_plot + 3) +
                0.2595 * (SIS / 10) +
                0.4392 * herb +
                0.1561 * thinned_recently
            ) / 10000
        )

# Usage example
# result = ElfvingBAIncrement.aspen(diameter_cm=30, Basal_area_weighted_mean_diameter_cm=25, ...)
# print(result)

class Elfving_2004_stand_methods:
    """
    Class to implement static methods for the Elfving mortality and basal area development models.

    Methods:
        - basal_area_mortality_percent_spruce_pine_sweden: Calculate annual mortality percentage of basal area.
        - gmax_spruce_pine_sweden: Calculate the GMax for spruce and pine in Sweden.
        - ba_stand: Calculate basal area development for a stand using Elfving 2009 model.
    """

    @staticmethod
    def basal_area_mortality_percent_spruce_pine_sweden(
        dominant_height, H100, stems, thinning_proportion_ba_start, thinning_form=1
    ):
        """
        Calculate the annual mortality in percent of basal area at the start of the period.

        Args:
            dominant_height (float): Dominant height of the stand.
            H100 (float): Site Index H100.
            stems (float): Stems per hectare at period start.
            thinning_proportion_ba_start (float): Proportion of basal area thinned at start of period (0 - 0.8).
            thinning_form (int, optional): 1 if thinned from above or unthinned, otherwise 0. Default is 1.

        Returns:
            float: Annual mortality in percent of basal area.
        """
        dens = (stems * dominant_height ** 2) / 100000
        return (
            -0.4093
            + 0.02189 * H100
            + 0.005373 * (dens ** 2)
            + 0.3817 * dominant_height * (thinning_proportion_ba_start ** 3)
            + 0.01252 * dominant_height * thinning_form
        )

    @staticmethod
    def gmax_spruce_pine_sweden(dominant_height, H100, stems, latitude):
        """
        Calculate the GMax for spruce and pine in Sweden.

        Args:
            dominant_height (float): Dominant height of the stand.
            H100 (float): Site Index H100.
            stems (float): Stems per hectare at period start.
            latitude (float): Latitude in degrees N.

        Returns:
            float: GMax value.
        """
        return (
            -89.7
            + 2.47 * dominant_height
            + 0.0212 * ((dominant_height ** 3) / H100)
            + 0.834 * H100
            + 0.00350 * stems
            + 0.890 * latitude
        )

    @staticmethod
    def ba_stand(
        vegetation,
        stand_age,
        basal_area_conifer_m2_ha,
        basal_area_pine_m2_ha,
        basal_area_birch_m2_ha,
        basal_area_after_thinning,
        basal_area_before_thinning,
        stems_after_thinning,
        peatland,
        soil_moisture,
        SIS100,
        latitude,
        altitude,
        ditched,
        thinned,
        last_thinned,
    ):
        """
        Calculate the basal area development for a stand using Elfving 2009 model.

        Args:
            vegetation (int): Vegetation type code (1-18).
            stand_age (float): Age of the stand at the start of the period.
            basal_area_conifer_m2_ha (float): Conifer basal area in m2/ha.
            basal_area_pine_m2_ha (float): Pine basal area in m2/ha.
            basal_area_birch_m2_ha (float): Birch basal area in m2/ha.
            basal_area_after_thinning (float): Basal area after thinning in m2/ha.
            basal_area_before_thinning (float): Basal area before thinning in m2/ha.
            stems_after_thinning (float): Stems per hectare after thinning.
            peatland (bool): True if the plot is peatland, False otherwise.
            soil_moisture (int): Soil moisture type (1-5).
            SIS100 (float): Site Index SIS100.
            latitude (float): Latitude in degrees N.
            altitude (float): Altitude in meters above sea level.
            ditched (bool): True if a ditch is within 25m of the plot center, False otherwise.
            thinned (bool): True if the plot has been thinned, False otherwise.
            last_thinned (int): Number of growth seasons since the stand was last thinned.

        Returns:
            float: Predicted basal area.

        Raises:
            ValueError: If input parameters are out of bounds or invalid.
        """
        if vegetation not in range(1, 19):
            raise ValueError("Vegetation must be an integer between 1 and 18.")
        if thinned not in {True, False, 1, 0}:
            raise ValueError("Thinned must be a boolean or 1/0.")
        if ditched not in {True, False, 1, 0}:
            raise ValueError("Ditched must be a boolean or 1/0.")
        if peatland not in {True, False, 1, 0}:
            raise ValueError("Peatland must be a boolean or 1/0.")
        if soil_moisture not in range(1, 6):
            raise ValueError("Soil moisture must be an integer between 1 and 5.")

        # Adjust vegetation values
        vegetation = {
            1: 4, 2: 2.5, 3: 2, 4: 3, 5: 2.5, 6: 2, 7: 3, 8: 2.5, 9: 1.5, 10: -3,
            11: -3, 12: 1, 13: 0, 14: -0.5, 15: -3, 16: -5, 17: -0.5, 18: -1,
        }.get(vegetation)

        conifer_ba_proportion = (basal_area_conifer_m2_ha / basal_area_after_thinning) / stand_age
        pine_ba_proportion = basal_area_pine_m2_ha / basal_area_after_thinning
        birch_ba_proportion = basal_area_birch_m2_ha / basal_area_after_thinning

        peat_vegetation = vegetation if peatland else 0

        moist = 1 if soil_moisture == 4 else 0
        wet = 1 if soil_moisture == 5 else 0

        cold_climate = (-0.01 * ((4835 - 57.6 * latitude - 0.9 * altitude) - 300))

        thinned_recently = 1 if thinned and last_thinned <= 10 else 0
        thinned_long_ago = 1 if thinned and 10 < last_thinned <= 25 else 0

        stem_number_followed_quote = stems_after_thinning / (stems_after_thinning + 80)

        return math.exp(
            +0.366
            - 0.5842 * (stand_age)
            + 8.3740 * conifer_ba_proportion
            - 0.0237 * pine_ba_proportion * vegetation
            - 0.3192 * (birch_ba_proportion ** 2)
            - 10.8034 * cold_climate * birch_ba_proportion
            + 0.5002 * basal_area_after_thinning
            - 0.00632 * basal_area_before_thinning
            + 1.376 * stem_number_followed_quote
            + 0.0627 * vegetation
            - 0.0244 * peat_vegetation
            - 0.0498 * moist
            - 0.1807 * wet
            + 0.0109 * SIS100
            + 0.0542 * ditched
            + 0.1396 * thinned_recently
            + 0.0567 * thinned_long_ago
            - 0.06 * pine_ba_proportion
        )
