import numpy as np

class Soderberg1986BAI5:
    """
    A collection of functions for calculating the 5-year basal area increment (BAI) of individual trees in Sweden
    based on the methods described in Söderberg (1986).
    """

    @staticmethod
    def oak_southern_sweden(DBH_cm, DBH_largest_tree_on_plot_cm, BA_tree_m2, BA_m2_ha, age, thinned, last_thinned, aspect, maritime):
        """
        Calculate the 5-year basal area increment for Oak in southern Sweden.

        Args:
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            BA_tree_m2 (float): Basal area of the tree in m².
            BA_m2_ha (float): Total basal area on the plot in m²/ha.
            age (int): Tree age at breast height.
            thinned (bool): Whether the stand was thinned (True) or not (False).
            last_thinned (int): Number of growing seasons since last thinning.
            aspect (int): Aspect of the site (1 to 8, 0 if not applicable).
            maritime (bool): Whether the site is in a maritime climatic region.

        Returns:
            float: Predicted basal area increment during 5 years in m².
        """
        basal_area_of_tree_cm2 = BA_tree_m2 * 10000
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        north = 1 if aspect in [8, 1, 2, 3] else 0
        south = 1 if aspect in [4, 5, 6, 7] else 0

        if not thinned:
            thinning = -0.05827 * BA_m2_ha + 0.007703 * (BA_m2_ha ** 2)
        elif last_thinned < 5:
            thinning = -0.048067 * BA_m2_ha + 0.0067014 * (BA_m2_ha ** 2)
        else:
            thinning = -0.03596 * BA_m2_ha + 0.0034773 * (BA_m2_ha ** 2)

        result = np.exp(
            +0.10683 * np.log(basal_area_of_tree_cm2)
            - 0.42896 * (np.log(basal_area_of_tree_cm2) / (age + 10))
            + 0.16232 * (1 / (age + 10))
            - 0.15683 * ((1 / (age + 10)) ** 2)
            + thinning
            + 0.29030 * diameter_quotient
            + 0.25426 * north
            + 0.22321 * south
            + 0.13856 * maritime
            - 0.37307
        ) / 10000  # Convert cm² to m²
        return result

    @staticmethod
    def beech_southern_sweden(DBH_cm, DBH_largest_tree_on_plot_cm, BA_tree_m2, BA_Pine_m2_ha, BA_Birch_m2_ha, BA_m2_ha, SI_species, SI100, age, thinned, last_thinned, latitude, altitude, divided_plot=0):
        """
        Calculate the 5-year basal area increment for Beech in southern Sweden.

        Args:
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            BA_tree_m2 (float): Basal area of the tree in m².
            BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
            BA_Birch_m2_ha (float): Basal area of Birch on the plot in m²/ha.
            BA_m2_ha (float): Total basal area on the plot in m²/ha.
            SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
            SI100 (float): Site Index H100 in meters.
            age (int): Tree age at breast height.
            thinned (bool): Whether the stand was thinned (True) or not (False).
            last_thinned (int): Number of growing seasons since last thinning.
            latitude (float): Latitude in degrees.
            altitude (float): Altitude in meters above sea level.
            divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.

        Returns:
            float: Predicted basal area increment during 5 years in m².
        """
        basal_area_of_tree_cm2 = BA_tree_m2 * 10000
        spruce = 1 if SI_species == "Picea abies" else 0
        pine = 1 if SI_species == "Pinus sylvestris" else 0
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        BA_quotient_Birch = BA_Birch_m2_ha / BA_m2_ha

        if not thinned:
            thinning = -0.040446 * BA_m2_ha + 0.0052343 * (BA_m2_ha ** 2)
        elif last_thinned < 5:
            thinning = -0.017664 * BA_m2_ha
        else:
            thinning = -0.035227 * BA_m2_ha + 0.0040499 * (BA_m2_ha ** 2)

        result = np.exp(
            +0.15936 * np.log(basal_area_of_tree_cm2)
            - 0.0051911 * BA_tree_m2
            + 0.090769 * (1 / (age + 10))
            - 0.062604 * ((1 / (age + 10)) ** 2)
            + thinning
            - 0.27505 * diameter_quotient
            + 0.12066 * (diameter_quotient ** 2)
            + 0.10086 * BA_quotient_Pine
            + 0.068754 * BA_quotient_Birch
            + 0.0015978 * spruce * SI100 * 10
            + 0.00033566 * pine * SI100 * 10
            - 0.012884 * altitude
            + 0.0022650 * latitude * altitude
            + 0.035174 * divided_plot
            - 0.50158
        ) / 10000  # Convert cm² to m²
        return result

    @staticmethod
    def spruce_southern_sweden_under_65(DBH_cm, DBH_largest_tree_on_plot_cm, BA_tree_m2, BA_Pine_m2_ha, BA_Spruce_m2_ha, BA_Birch_m2_ha, BA_m2_ha, age, thinned, last_thinned, SI100, SI_species, aspect, soil_moisture, county, peatland=0, divided_plot=0, fertilised_plot=0, plot_inventoried_76_77=0):
        """
        Calculate the 5-year basal area increment for Norway Spruce in southern Sweden (under 65 years old).

        Args:
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            BA_tree_m2 (float): Basal area of the tree in m².
            BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
            BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
            BA_Birch_m2_ha (float): Basal area of Birch on the plot in m²/ha.
            BA_m2_ha (float): Total basal area on the plot in m²/ha.
            age (int): Tree age at breast height.
            thinned (bool): Whether the stand was thinned (True) or not (False).
            last_thinned (int): Number of growing seasons since last thinning.
            SI100 (float): Site Index H100 in meters.
            SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
            aspect (int): Aspect of the site (1 to 8, 0 if not applicable).
            soil_moisture (int): Soil moisture class (1 to 5).
            county (str): County name.
            peatland (int, optional): Whether the plot is peatland (1) or not (0). Defaults to 0.
            divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.
            fertilised_plot (int, optional): Whether the plot is fertilised (1) or not (0). Defaults to 0.
            plot_inventoried_76_77 (int, optional): Whether the plot was inventoried in 1976-77 (1) or not (0). Defaults to 0.

        Returns:
            float: Predicted basal area increment during 5 years in m².
        """
        basal_area_of_tree_cm2 = BA_tree_m2 * 10000
        spruce = 1 if SI_species == "Picea abies" else 0
        pine = 1 if SI_species == "Pinus sylvestris" else 0
        moist = 1 if soil_moisture > 3 else 0
        dry = 1 if soil_moisture == 1 else 0
        north = 1 if aspect in [8, 1, 2, 3] else 0
        south = 1 if aspect in [4, 5, 6, 7] else 0
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
        BA_quotient_Birch = BA_Birch_m2_ha / BA_m2_ha
        region5 = 1 if county in ["Blekinge", "Kristianstad"    , "Malmöhus", "Västra Götaland", "Halland", "Gotland"] else 0

        if not thinned:
            thinning = -0.061903 * BA_m2_ha + 0.0067406 * (BA_m2_ha ** 2)
        elif last_thinned < 5:
            thinning = -0.051359 * BA_m2_ha + 0.0045834 * (BA_m2_ha ** 2)
        else:
            thinning = -0.060125 * BA_m2_ha + 0.0065807 * (BA_m2_ha ** 2)

        result = np.exp(
            +0.12995 * np.log(basal_area_of_tree_cm2)
            - 0.00032205 * basal_area_of_tree_cm2
            - 0.42745 * (np.log(basal_area_of_tree_cm2) / (age + 10))
            + 0.13002 * (1 / (age + 10))
            - 0.088771 * ((1 / (age + 10)) ** 2)
            + thinning
            - 0.044756 * diameter_quotient
            - 0.019273 * BA_quotient_Pine
            - 0.042807 * BA_quotient_Spruce
            - 0.030893 * BA_quotient_Birch
            + 0.00021660 * spruce * SI100 * 10
            + 0.00070422 * pine * SI100 * 10
            + 0.055118 * peatland
            - 0.010323 * dry
            + 0.0045389 * moist
            - 0.011319 * north
            - 0.0079993 * south
            + 0.0098700 * region5
            + 0.0063629 * divided_plot
            + 0.0037888 * fertilised_plot
            - 0.034626
        ) / 10000  # Convert cm² to m²
        return result


    @staticmethod
    def spruce_southern_sweden_over_45(DBH_cm, DBH_largest_tree_on_plot_cm, BA_tree_m2, BA_Pine_m2_ha, BA_Spruce_m2_ha, BA_Birch_m2_ha, BA_m2_ha, age, thinned, last_thinned, SI100, SI_species, aspect, soil_moisture, county, peatland=0, divided_plot=0, fertilised_plot=0):
        """
        Calculate the 5-year basal area increment for Norway Spruce in southern Sweden (over 45 years old).

        Args:
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            BA_tree_m2 (float): Basal area of the tree in m².
            BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
            BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
            BA_Birch_m2_ha (float): Basal area of Birch on the plot in m²/ha.
            BA_m2_ha (float): Total basal area on the plot in m²/ha.
            age (int): Tree age at breast height.
            thinned (bool): Whether the stand was thinned (True) or not (False).
            last_thinned (int): Number of growing seasons since last thinning.
            SI100 (float): Site Index H100 in meters.
            SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
            aspect (int): Aspect of the site (1 to 8, 0 if not applicable).
            soil_moisture (int): Soil moisture class (1 to 5).
            county (str): County name.
            peatland (int, optional): Whether the plot is peatland (1) or not (0). Defaults to 0.
            divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.
            fertilised_plot (int, optional): Whether the plot is fertilised (1) or not (0). Defaults to 0.

        Returns:
            float: Predicted basal area increment during 5 years in m².
        """
        basal_area_of_tree_cm2 = BA_tree_m2 * 10000
        spruce = 1 if SI_species == "Picea abies" else 0
        pine = 1 if SI_species == "Pinus sylvestris" else 0
        moist = 1 if soil_moisture > 3 else 0
        dry = 1 if soil_moisture == 1 else 0
        north = 1 if aspect in [8, 1, 2, 3] else 0
        south = 1 if aspect in [4, 5, 6, 7] else 0
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
        BA_quotient_Birch = BA_Birch_m2_ha / BA_m2_ha
        region5 = 1 if county in ["Blekinge", "Kristianstad", "Malmöhus", "Västra Götaland", "Halland", "Gotland"] else 0

        if not thinned:
            thinning = -0.057054 * BA_m2_ha + 0.0068177 * (BA_m2_ha ** 2)
        elif last_thinned < 5:
            thinning = -0.054388 * BA_m2_ha + 0.0068291 * (BA_m2_ha ** 2)
        else:
            thinning = -0.055215 * BA_m2_ha + 0.0067161 * (BA_m2_ha ** 2)

        result = np.exp(
            +0.10064 * np.log(basal_area_of_tree_cm2)
            + 0.16664 * (1 / (age + 10))
            - 0.29572 * ((1 / (age + 10)) ** 2)
            + thinning
            + 0.13696 * diameter_quotient
            - 0.12015 * (diameter_quotient ** 2)
            - 0.035992 * BA_quotient_Pine
            - 0.055521 * BA_quotient_Spruce
            - 0.070004 * BA_quotient_Birch
            + 0.00057152 * spruce * SI100 * 10
            + 0.00066865 * pine * SI100 * 10
            + 0.073311 * peatland
            - 0.019658 * dry
            + 0.0069787 * moist
            - 0.010264 * north
            - 0.010337 * south
            + 0.0054467 * region5
            + 0.0035977 * divided_plot
            + 0.0058978 * fertilised_plot
            - 0.029605
        ) / 10000  # Convert cm² to m²
        return result

    @staticmethod
    def pine_southern_sweden_under_65(DBH_cm, DBH_largest_tree_on_plot_cm, BA_tree_m2, BA_Pine_m2_ha, BA_m2_ha, age, thinned, last_thinned, SI100, SI_species, soil_moisture, county, peatland=0, divided_plot=0, fertilised_plot=0, plot_inventoried_76_77=0):
        """
        Calculate the 5-year basal area increment for Scots Pine in southern Sweden (under 65 years old).

        Args:
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            BA_tree_m2 (float): Basal area of the tree in m².
            BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
            BA_m2_ha (float): Total basal area on the plot in m²/ha.
            age (int): Tree age at breast height.
            thinned (bool): Whether the stand was thinned (True) or not (False).
            last_thinned (int): Number of growing seasons since last thinning.
            SI100 (float): Site Index H100 in meters.
            SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
            soil_moisture (int): Soil moisture class (1 to 5).
            county (str): County name.
            peatland (int, optional): Whether the plot is peatland (1) or not (0). Defaults to 0.
            divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.
            fertilised_plot (int, optional): Whether the plot is fertilised (1) or not (0). Defaults to 0.
            plot_inventoried_76_77 (int, optional): Whether the plot was inventoried in 1976-77 (1) or not (0). Defaults to 0.

        Returns:
            float: Predicted basal area increment during 5 years in m².
        """
        basal_area_of_tree_cm2 = BA_tree_m2 * 10000
        spruce = 1 if SI_species == "Picea abies" else 0
        pine = 1 if SI_species == "Pinus sylvestris" else 0
        dry = 1 if soil_moisture == 1 else 0
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        south_eastern_county = 1 if county in ["Stockholm", "Södermanland", "Uppsala", "Östergötland", "Kalmar", "Västmanland"] else 0

        if not thinned:
            thinning = -0.054687 * BA_m2_ha + 0.0066494 * (BA_m2_ha ** 2)
        elif last_thinned < 5:
            thinning = -0.058141 * BA_m2_ha + 0.0087783 * (BA_m2_ha ** 2)
        else:
            thinning = -0.061332 * BA_m2_ha + 0.0081506 * (BA_m2_ha ** 2)

        result = np.exp(
            +0.14888 * np.log(basal_area_of_tree_cm2)
            - 0.001004 * basal_area_of_tree_cm2
            - 0.99781 * (np.log(basal_area_of_tree_cm2) / (age + 10))
            + 0.14020 * (1 / (age + 10))
            - 0.75718 * ((1 / (age + 10)) ** 2)
            + thinning
            - 0.16288 * diameter_quotient
            + 0.19800 * BA_quotient_Pine
            + 0.000944 * spruce * SI100 * 10
            + 0.00060341 * pine * SI100 * 10
            + 0.34176 * peatland
            - 0.12513 * dry
            + 0.10167 * south_eastern_county
            + 0.092116 * divided_plot
            + 0.12979 * fertilised_plot
            + 0.0087499 * plot_inventoried_76_77
            - 0.49333
        ) / 10000  # Convert cm² to m²
        return result

    @staticmethod
    def birch_southern_sweden_under_65(DBH_cm, DBH_largest_tree_on_plot_cm, BA_tree_m2, BA_Pine_m2_ha, BA_Spruce_m2_ha, BA_m2_ha, age, thinned, last_thinned, SI100, SI_species, soil_moisture, county, divided_plot=0, fertilised_plot=0):
        """
        Calculate the 5-year basal area increment for Birch in southern Sweden (under 65 years old).

        Args:
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            BA_tree_m2 (float): Basal area of the tree in m².
            BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
            BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
            BA_m2_ha (float): Total basal area on the plot in m²/ha.
            age (int): Tree age at breast height.
            thinned (bool): Whether the stand was thinned (True) or not (False).
            last_thinned (int): Number of growing seasons since last thinning.
            SI100 (float): Site Index H100 in meters.
            SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
            soil_moisture (int): Soil moisture class (1 to 5).
            county (str): County name.
            divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.
            fertilised_plot (int, optional): Whether the plot is fertilised (1) or not (0). Defaults to 0.

        Returns:
            float: Predicted basal area increment during 5 years in m².
        """
        basal_area_of_tree_cm2 = BA_tree_m2 * 10000
        spruce = 1 if SI_species == "Picea abies" else 0
        pine = 1 if SI_species == "Pinus sylvestris" else 0
        moist = 1 if soil_moisture > 3 else 0
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
        south_eastern_county = 1 if county in ["Stockholm", "Södermanland", "Uppsala", "Östergötland", "Kalmar", "Västmanland"] else 0

        if not thinned:
            thinning = -0.050494 * BA_m2_ha + 0.0079803 * (BA_m2_ha ** 2)
        elif last_thinned < 5:
            thinning = -0.031238 * BA_m2_ha
        else:
            thinning = -0.049770 * BA_m2_ha + 0.0046417 * (BA_m2_ha ** 2)

        result = np.exp(
            +0.10731 * np.log(basal_area_of_tree_cm2)
            - 0.57527 * (np.log(basal_area_of_tree_cm2) / (age + 10))
            + 0.14600 * (1 / (age + 10))
            - 0.10335 * ((1 / (age + 10)) ** 2)
            + thinning
            + 0.15895 * diameter_quotient
            - 0.086151 * (diameter_quotient ** 2)
            + 0.086278 * BA_quotient_Pine
            + 0.028913 * BA_quotient_Spruce
            + 0.0014656 * spruce * SI100 * 10
            + 0.0015297 * pine * SI100 * 10
            + 0.10583 * moist
            - 0.095624 * south_eastern_county
            + 0.18366 * divided_plot
            + 0.073270 * fertilised_plot
            - 0.47436
        ) / 10000  # Convert cm² to m²
        return result

    @staticmethod
    def pine_southern_sweden_over_45(DBH_cm, DBH_largest_tree_on_plot_cm, BA_tree_m2, BA_Pine_m2_ha, BA_m2_ha, age, thinned, last_thinned, SI100, SI_species, soil_moisture, latitude, altitude, peatland=0, divided_plot=0, fertilised_plot=0, plot_inventoried_76_77=0):
        """
        Calculate the 5-year basal area increment for Scots Pine in southern Sweden (over 45 years old).

        Args:
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            BA_tree_m2 (float): Basal area of the tree in m².
            BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
            BA_m2_ha (float): Total basal area on the plot in m²/ha.
            age (int): Tree age at breast height.
            thinned (bool): Whether the stand was thinned (True) or not (False).
            last_thinned (int): Number of growing seasons since last thinning.
            SI100 (float): Site Index H100 in meters.
            SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
            soil_moisture (int): Soil moisture class (1 to 5).
            latitude (float): Latitude in degrees.
            altitude (float): Altitude in meters above sea level.
            peatland (int, optional): Whether the plot is peatland (1) or not (0). Defaults to 0.
            divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.
            fertilised_plot (int, optional): Whether the plot is fertilised (1) or not (0). Defaults to 0.
            plot_inventoried_76_77 (int, optional): Whether the plot was inventoried in 1976-77 (1) or not (0). Defaults to 0.

        Returns:
            float: Predicted basal area increment during 5 years in m².
        """
        basal_area_of_tree_cm2 = BA_tree_m2 * 10000
        spruce = 1 if SI_species == "Picea abies" else 0
        pine = 1 if SI_species == "Pinus sylvestris" else 0
        dry = 1 if soil_moisture == 1 else 0
        south = 1 if latitude < 60 else 0
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha

        if not thinned:
            thinning = -0.038635 * BA_m2_ha + 0.0042831 * (BA_m2_ha ** 2)
        elif last_thinned < 5:
            thinning = -0.035844 * BA_m2_ha + 0.0042792 * (BA_m2_ha ** 2)
        else:
            thinning = -0.037468 * BA_m2_ha + 0.0036891 * (BA_m2_ha ** 2)

        result = np.exp(
            +0.085280 * np.log(basal_area_of_tree_cm2)
            - 0.0014702 * basal_area_of_tree_cm2
            + 0.14841 * (1 / (age + 10))
            - 0.27409 * ((1 / (age + 10)) ** 2)
            + thinning
            + 0.19038 * diameter_quotient
            - 0.13080 * (diameter_quotient ** 2)
            + 0.18171 * BA_quotient_Pine
            + 0.008721 * spruce * SI100 * 10
            + 0.0075936 * pine * SI100 * 10
            + 0.029166 * peatland
            - 0.00008185 * latitude * altitude
            - 0.11758 * dry
            - 0.073811 * south
            + 0.11152 * divided_plot
            + 0.10516 * fertilised_plot
            + 0.040410 * plot_inventoried_76_77
            - 0.30557
        ) / 10000  # Convert cm² to m²
        return result

    @staticmethod
    def birch_southern_sweden_over_45(DBH_cm, DBH_largest_tree_on_plot_cm, BA_tree_m2, BA_Pine_m2_ha, BA_Spruce_m2_ha, BA_Birch_m2_ha, BA_m2_ha, age, thinned, last_thinned, SI100, SI_species, soil_moisture, county, divided_plot=0, fertilised_plot=0, plot_inventoried_76_77=0):
        """
        Calculate the 5-year basal area increment for Birch in southern Sweden (over 45 years old).

        Args:
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            BA_tree_m2 (float): Basal area of the tree in m².
            BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
            BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
            BA_Birch_m2_ha (float): Basal area of Birch on the plot in m²/ha.
            BA_m2_ha (float): Total basal area on the plot in m²/ha.
            age (int): Tree age at breast height.
            thinned (bool): Whether the stand was thinned (True) or not (False).
            last_thinned (int): Number of growing seasons since last thinning.
            SI100 (float): Site Index H100 in meters.
            SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
            soil_moisture (int): Soil moisture class (1 to 5).
            county (str): County name.
            divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.
            fertilised_plot (int, optional): Whether the plot is fertilised (1) or not (0). Defaults to 0.
            plot_inventoried_76_77 (int, optional): Whether the plot was inventoried in 1976-77 (1) or not (0). Defaults to 0.

        Returns:
            float: Predicted basal area increment during 5 years in m².
        """
        basal_area_of_tree_cm2 = BA_tree_m2 * 10000
        spruce = 1 if SI_species == "Picea abies" else 0
        pine = 1 if SI_species == "Pinus sylvestris" else 0
        moist = 1 if soil_moisture > 3 else 0
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
        BA_quotient_Birch = BA_Birch_m2_ha / BA_m2_ha

        south_eastern_county = 1 if county in ["Stockholm", "Södermanland", "Uppsala", "Östergötland", "Kalmar", "Västmanland"] else 0

        if not thinned:
            thinning = -0.032163 * BA_m2_ha + 0.0032234 * (BA_m2_ha ** 2)
        elif last_thinned < 5:
            thinning = -0.035013 * BA_m2_ha + 0.0040031 * (BA_m2_ha ** 2)
        else:
            thinning = -0.037450 * BA_m2_ha + 0.0044980 * (BA_m2_ha ** 2)

        result = np.exp(
            +0.086066 * np.log(basal_area_of_tree_cm2)
            + 0.76322 * (1 / (age + 10))
            + thinning
            + 0.16702 * diameter_quotient
            - 0.080138 * (diameter_quotient ** 2)
            + 0.067104 * BA_quotient_Pine
            + 0.045025 * BA_quotient_Spruce
            + 0.024659 * BA_quotient_Birch
            + 0.0017333 * spruce * SI100 * 10
            + 0.0022591 * pine * SI100 * 10
            + 0.12044 * moist
            - 0.11905 * south_eastern_county
            + 0.13061 * divided_plot
            + 0.19571 * fertilised_plot
            + 0.20698 * plot_inventoried_76_77
            - 0.37239
        ) / 10000  # Convert cm² to m²
        return result

    @staticmethod
    def broadleaves_southern_sweden(DBH_cm, DBH_largest_tree_on_plot_cm, BA_tree_m2, BA_Pine_m2_ha, BA_Spruce_m2_ha, BA_Birch_m2_ha, BA_m2_ha, age, thinned, last_thinned, aspect, latitude, divided_plot=0):
        """
        Calculate the 5-year basal area increment for Broadleaves in southern Sweden.

        Args:
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            BA_tree_m2 (float): Basal area of the tree in m².
            BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
            BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
            BA_Birch_m2_ha (float): Basal area of Birch on the plot in m²/ha.
            BA_m2_ha (float): Total basal area on the plot in m²/ha.
            age (int): Tree age at breast height.
            thinned (bool): Whether the stand was thinned (True) or not (False).
            last_thinned (int): Number of growing seasons since last thinning.
            aspect (int): Aspect of the site (1 to 8, 0 if not applicable).
            latitude (float): Latitude in degrees.
            divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.

        Returns:
            float: Predicted basal area increment during 5 years in m².
        """
        basal_area_of_tree_cm2 = BA_tree_m2 * 10000
        north = 1 if aspect in [8, 1, 2, 3] else 0
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
        BA_quotient_Birch = BA_Birch_m2_ha / BA_m2_ha

        if not thinned:
            thinning = -0.057341 * BA_m2_ha + 0.0072742 * (BA_m2_ha ** 2)
        elif last_thinned < 5:
            thinning = -0.034258 * BA_m2_ha + 0.0015713 * (BA_m2_ha ** 2)
        else:
            thinning = -0.074100 * BA_m2_ha + 0.014893 * (BA_m2_ha ** 2)

        result = np.exp(
            +0.12426 * np.log(basal_area_of_tree_cm2)
            - 0.0038067 * BA_tree_m2
            + 0.086923 * (1 / (age + 10))
            - 0.049647 * ((1 / (age + 10)) ** 2)
            + thinning
            - 0.14061 * diameter_quotient
            + 0.085103 * (diameter_quotient ** 2)
            + 0.032525 * BA_quotient_Pine
            + 0.024568 * BA_quotient_Spruce
            + 0.020104 * BA_quotient_Birch
            + 0.0049305 * latitude
            - 0.14761 * north
            + 0.10352 * divided_plot
            - 0.63258
        ) / 10000  # Convert cm² to m²
        return result

@staticmethod
def spruce_northern_sweden_under_65(
    DBH_cm,
    DBH_largest_tree_on_plot_cm,
    BA_tree_m2,
    BA_Pine_m2_ha,
    BA_Spruce_m2_ha,
    BA_m2_ha,
    age,
    thinned,
    last_thinned,
    SI100,
    SI_species,
    aspect,
    latitude,
    altitude,
    peatland=0,
    divided_plot=0,
    fertilised_plot=0,
    plot_inventoried_76_77=0
):
    """
    Calculate the 5-year basal area increment for Norway Spruce in northern Sweden (under 65 years old).

    Args:
        DBH_cm (float): Diameter at breast height in cm.
        DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
        BA_tree_m2 (float): Basal area of the tree in m².
        BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
        BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
        BA_m2_ha (float): Total basal area on the plot in m²/ha.
        age (int): Tree age at breast height.
        thinned (bool): Whether the stand was thinned (True) or not (False).
        last_thinned (int): Number of growing seasons since last thinning.
        SI100 (float): Site Index H100 in meters.
        SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
        aspect (int): Aspect of the site (1 to 8, 0 if not applicable).
        latitude (float): Latitude in degrees.
        altitude (float): Altitude in meters above sea level.
        peatland (int, optional): Whether the plot is peatland (1) or not (0). Defaults to 0.
        divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.
        fertilised_plot (int, optional): Whether the plot is fertilised (1) or not (0). Defaults to 0.
        plot_inventoried_76_77 (int, optional): Whether the plot was inventoried in 1976-77 (1) or not (0). Defaults to 0.

    Returns:
        float: Predicted basal area increment during 5 years in m².
    """
    basal_area_of_tree_cm2 = BA_tree_m2 * 10000
    spruce = 1 if SI_species == "Picea abies" else 0
    pine = 1 if SI_species == "Pinus sylvestris" else 0
    diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
    BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
    BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
    south = 1 if aspect in [4, 5, 6, 7] else 0

    if not thinned:
        thinning = -0.03609 * BA_m2_ha + 0.0036083 * (BA_m2_ha ** 2)
    elif last_thinned < 5:
        thinning = -0.03211 * BA_m2_ha + 0.0051283 * (BA_m2_ha ** 2)
    else:
        thinning = -0.022616 * BA_m2_ha + 0.00046227 * (BA_m2_ha ** 2)

    result = np.exp(
        +0.11503 * np.log(basal_area_of_tree_cm2)
        - 0.0065032 * basal_area_of_tree_cm2
        + 0.70512 * (1 / (age + 10))
        - 0.31435 * ((1 / (age + 10)) ** 2)
        + thinning
        - 0.87521 * diameter_quotient
        + 0.49368 * (diameter_quotient ** 2)
        - 0.27401 * BA_quotient_Pine
        - 0.33472 * BA_quotient_Spruce
        + 0.0011976 * spruce * SI100 * 10  # Convert m to dm
        + 0.0011935 * pine * SI100 * 10    # Convert m to dm
        + 0.23003 * peatland
        - 0.044234 * altitude
        + 0.00076409 * latitude * altitude
        + 0.054128 * south
        + 0.048618 * divided_plot
        + 0.15556 * fertilised_plot
        + 0.084235 * plot_inventoried_76_77
        - 28.683
    ) / 10000  # Convert cm² to m²

    return result

@staticmethod
def pine_northern_sweden_under_65(
    DBH_cm,
    DBH_largest_tree_on_plot_cm,
    BA_tree_m2,
    BA_Spruce_m2_ha,
    BA_m2_ha,
    age,
    thinned,
    last_thinned,
    SI100,
    SI_species,
    latitude,
    aspect,
    soil_moisture,
    divided_plot=0,
    fertilised_plot=0,
    plot_inventoried_76_77=0
):
    """
    Calculate the 5-year basal area increment for Scots Pine in northern Sweden (under 65 years old).

    Args:
        DBH_cm (float): Diameter at breast height in cm.
        DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
        BA_tree_m2 (float): Basal area of the tree in m².
        BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
        BA_m2_ha (float): Total basal area on the plot in m²/ha.
        age (int): Tree age at breast height.
        thinned (bool): Whether the stand was thinned (True) or not (False).
        last_thinned (int): Number of growing seasons since last thinning.
        SI100 (float): Site Index H100 in meters.
        SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
        latitude (float): Latitude in degrees.
        aspect (int): Aspect of the site (1 to 8, 0 if not applicable).
        soil_moisture (int): Soil moisture class (1 to 5).
        divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.
        fertilised_plot (int, optional): Whether the plot is fertilised (1) or not (0). Defaults to 0.
        plot_inventoried_76_77 (int, optional): Whether the plot was inventoried in 1976-77 (1) or not (0). Defaults to 0.

    Returns:
        float: Predicted basal area increment during 5 years in m².
    """
    basal_area_of_tree_cm2 = BA_tree_m2 * 10000
    north = 1 if aspect in [8, 1, 2, 3] else 0
    south = 1 if aspect in [4, 5, 6, 7] else 0
    spruce = 1 if SI_species == "Picea abies" else 0
    pine = 1 if SI_species == "Pinus sylvestris" else 0
    moist = 1 if soil_moisture > 3 else 0
    diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
    BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha

    if not thinned:
        thinning = -0.066243 * BA_m2_ha + 0.0075292 * (BA_m2_ha ** 2)
    elif last_thinned < 5:
        thinning = -0.0664 * BA_m2_ha + 0.0089623 * (BA_m2_ha ** 2)
    else:
        thinning = -0.054112 * BA_m2_ha + 0.0043791 * (BA_m2_ha ** 2)

    result = np.exp(
        +0.12199 * np.log(basal_area_of_tree_cm2)
        - 0.0012143 * basal_area_of_tree_cm2
        - 40.367 * (np.log(basal_area_of_tree_cm2) / (age + 10))
        + 0.77769 * (1 / (age + 10))
        - 0.19198 * ((1 / (age + 10)) ** 2)
        + thinning
        - 0.17016 * diameter_quotient
        + 0.31920 * BA_quotient_Spruce
        + 0.0024518 * spruce * SI100 * 10  # Convert m to dm
        + 0.0023361 * pine * SI100 * 10    # Convert m to dm
        + 13.028 * latitude
        - 0.099353 * (latitude ** 2)
        - 0.056156 * north
        + 0.12153 * south
        + 0.15605 * moist
        + 0.092899 * divided_plot
        + 0.099817 * fertilised_plot
        + 0.070382 * plot_inventoried_76_77
        - 45.954
    ) / 10000  # Convert cm² to m²

    return result

@staticmethod
def spruce_northern_sweden_over_45(
    DBH_cm,
    DBH_largest_tree_on_plot_cm,
    BA_tree_m2,
    BA_Pine_m2_ha,
    BA_Spruce_m2_ha,
    BA_m2_ha,
    age,
    thinned,
    last_thinned,
    SI100,
    SI_species,
    aspect,
    soil_moisture,
    latitude,
    altitude,
    peatland=0,
    divided_plot=0,
    fertilised_plot=0,
    plot_inventoried_76_77=0
):
    """
    Calculate the 5-year basal area increment for Norway Spruce in northern Sweden (over 45 years old).

    Args:
        DBH_cm (float): Diameter at breast height in cm.
        DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
        BA_tree_m2 (float): Basal area of the tree in m².
        BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
        BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
        BA_m2_ha (float): Total basal area on the plot in m²/ha.
        age (int): Tree age at breast height.
        thinned (bool): Whether the stand was thinned (True) or not (False).
        last_thinned (int): Number of growing seasons since last thinning.
        SI100 (float): Site Index H100 in meters.
        SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
        aspect (int): Aspect of the site (1 to 8, 0 if not applicable).
        soil_moisture (int): Soil moisture class (1 to 5).
        latitude (float): Latitude in degrees.
        altitude (float): Altitude in meters above sea level.
        peatland (int, optional): Whether the plot is peatland (1) or not (0). Defaults to 0.
        divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.
        fertilised_plot (int, optional): Whether the plot is fertilised (1) or not (0). Defaults to 0.
        plot_inventoried_76_77 (int, optional): Whether the plot was inventoried in 1976-77 (1) or not (0). Defaults to 0.

    Returns:
        float: Predicted basal area increment during 5 years in m².
    """
    basal_area_of_tree_cm2 = BA_tree_m2 * 10000
    spruce = 1 if SI_species == "Picea abies" else 0
    pine = 1 if SI_species == "Pinus sylvestris" else 0
    dry = 1 if soil_moisture == 1 else 0
    north = 1 if aspect in [8, 1, 2, 3] else 0
    diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
    BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
    BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha

    if not thinned:
        thinning = -0.025065 * BA_m2_ha + 0.0017057 * (BA_m2_ha ** 2)
    elif last_thinned < 5:
        thinning = -0.079174 * BA_m2_ha - 0.0018978 * (BA_m2_ha ** 2)
    else:
        thinning = -0.013173 * BA_m2_ha - 0.0019558 * (BA_m2_ha ** 2)

    result = np.exp(
        +0.10342 * np.log(basal_area_of_tree_cm2)
        - 0.0013099 * basal_area_of_tree_cm2
        + 1.6924 * (1 / (age + 10))
        - 3.6209 * ((1 / (age + 10)) ** 2)
        + thinning
        - 0.20862 * diameter_quotient
        - 0.40424 * BA_quotient_Pine
        - 0.30212 * BA_quotient_Spruce
        + 0.0012081 * spruce * SI100 * 10  # Convert m to dm
        + 0.0015637 * pine * SI100 * 10    # Convert m to dm
        + 0.12818 * peatland
        + 9.297 * latitude
        - 0.071427 * (latitude ** 2)
        + 0.000115 * altitude
        - 0.05392 * north
        - 0.14903 * dry
        + 0.1267 * divided_plot
        + 0.18797 * fertilised_plot
        + 0.036126 * plot_inventoried_76_77
        - 33.523
    ) / 10000  # Convert cm² to m²

    return result

@staticmethod
def pine_northern_sweden_over_45(
    DBH_cm,
    DBH_largest_tree_on_plot_cm,
    BA_tree_m2,
    BA_Spruce_m2_ha,
    BA_Birch_m2_ha,
    BA_m2_ha,
    age,
    thinned,
    last_thinned,
    SI100,
    SI_species,
    latitude,
    altitude,
    aspect,
    soil_moisture,
    peatland=0,
    divided_plot=0,
    fertilised_plot=0,
    plot_inventoried_76_77=0
):
    """
    Calculate the 5-year basal area increment for Scots Pine in northern Sweden (over 45 years old).

    Args:
        DBH_cm (float): Diameter at breast height in cm.
        DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
        BA_tree_m2 (float): Basal area of the tree in m².
        BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
        BA_Birch_m2_ha (float): Basal area of Birch on the plot in m²/ha.
        BA_m2_ha (float): Total basal area on the plot in m²/ha.
        age (int): Tree age at breast height.
        thinned (bool): Whether the stand was thinned (True) or not (False).
        last_thinned (int): Number of growing seasons since last thinning.
        SI100 (float): Site Index H100 in meters.
        SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
        latitude (float): Latitude in degrees.
        altitude (float): Altitude in meters above sea level.
        aspect (int): Aspect of the site (1 to 8, 0 if not applicable).
        soil_moisture (int): Soil moisture class (1 to 5).
        peatland (int, optional): Whether the plot is peatland (1) or not (0). Defaults to 0.
        divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.
        fertilised_plot (int, optional): Whether the plot is fertilised (1) or not (0). Defaults to 0.
        plot_inventoried_76_77 (int, optional): Whether the plot was inventoried in 1976-77 (1) or not (0). Defaults to 0.

    Returns:
        float: Predicted basal area increment during 5 years in m².
    """
    basal_area_of_tree_cm2 = BA_tree_m2 * 10000
    north = 1 if aspect in [8, 1, 2, 3] else 0
    south = 1 if aspect in [4, 5, 6, 7] else 0
    spruce = 1 if SI_species == "Picea abies" else 0
    pine = 1 if SI_species == "Pinus sylvestris" else 0
    dry = 1 if soil_moisture == 1 else 0
    diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
    BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
    BA_quotient_Birch = BA_Birch_m2_ha / BA_m2_ha

    if not thinned:
        thinning = -0.062615 * BA_m2_ha + 0.0070095 * (BA_m2_ha ** 2)
    elif last_thinned < 5:
        thinning = -0.04842 * BA_m2_ha + 0.0046192 * (BA_m2_ha ** 2)
    else:
        thinning = -0.052634 * BA_m2_ha + 0.0053348 * (BA_m2_ha ** 2)

    result = np.exp(
        +0.10633 * np.log(basal_area_of_tree_cm2)
        - 0.0053052 * basal_area_of_tree_cm2
        + 1.5859 * (1 / (age + 10))
        - 3.6056 * ((1 / (age + 10)) ** 2)
        + thinning
        - 0.31676 * diameter_quotient
        + 0.28762 * BA_quotient_Spruce
        + 0.34134 * BA_quotient_Birch
        + 0.0030746 * spruce * SI100 * 10  # Convert m to dm
        + 0.0027871 * pine * SI100 * 10    # Convert m to dm
        + 0.39932 * peatland
        - 0.061609 * latitude
        - 0.0076913 * altitude
        + 0.00011708 * latitude * altitude
        - 0.05345 * north
        + 0.053028 * south
        - 0.048108 * dry
        + 0.14839 * divided_plot
        + 0.12531 * fertilised_plot
        + 0.10107 * plot_inventoried_76_77
        + 0.63632
    ) / 10000  # Convert cm² to m²

    return result

@staticmethod
def birch_northern_central_sweden_under_65(
    DBH_cm,
    DBH_largest_tree_on_plot_cm,
    BA_tree_m2,
    BA_Pine_m2_ha,
    BA_Spruce_m2_ha,
    BA_Birch_m2_ha,
    BA_m2_ha,
    age,
    thinned,
    last_thinned,
    vegetation,
    aspect,
    altitude,
    soil_moisture,
    county,
    peatland=0,
    divided_plot=0,
    fertilised_plot=0,
    plot_inventoried_76_77=0
):
    """
    Calculate the 5-year basal area increment for Birch in northern and central Sweden (under 65 years old).

    Args:
        DBH_cm (float): Diameter at breast height in cm.
        DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
        BA_tree_m2 (float): Basal area of the tree in m².
        BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
        BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
        BA_Birch_m2_ha (float): Basal area of Birch on the plot in m²/ha.
        BA_m2_ha (float): Total basal area on the plot in m²/ha.
        age (int): Tree age at breast height.
        thinned (bool): Whether the stand was thinned (True) or not (False).
        last_thinned (int): Number of growing seasons since last thinning.
        vegetation (int): Vegetation type (1 to 18).
        aspect (int): Aspect of the site (1 to 8, 0 if not applicable).
        altitude (float): Altitude in meters above sea level.
        soil_moisture (int): Soil moisture class (1 to 5).
        county (str): County name.
        peatland (int, optional): Whether the plot is peatland (1) or not (0). Defaults to 0.
        divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.
        fertilised_plot (int, optional): Whether the plot is fertilised (1) or not (0). Defaults to 0.
        plot_inventoried_76_77 (int, optional): Whether the plot was inventoried in 1976-77 (1) or not (0). Defaults to 0.

    Returns:
        float: Predicted basal area increment during 5 years in m².
    """
    basal_area_of_tree_cm2 = BA_tree_m2 * 10000
    moist = 1 if soil_moisture > 3 else 0
    north = 1 if aspect in [8, 1, 2, 3] else 0
    herb = 1 if vegetation < 7 else 0
    diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
    BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
    BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
    BA_quotient_Birch = BA_Birch_m2_ha / BA_m2_ha

    if not thinned:
        thinning = -0.072642 * BA_m2_ha + 0.011651 * (BA_m2_ha ** 2)
    elif last_thinned < 5:
        thinning = -0.045533 * BA_m2_ha + 0.0042222 * (BA_m2_ha ** 2)
    else:
        thinning = -0.051405 * BA_m2_ha + 0.0054316 * (BA_m2_ha ** 2)

    result = np.exp(
        +0.10356 * np.log(basal_area_of_tree_cm2)
        + 1.1677 * (1 / (age + 10))
        - 10.643 * ((1 / (age + 10)) ** 2)
        + thinning
        - 0.23670 * diameter_quotient
        - 0.69019 * BA_quotient_Pine
        - 0.55953 * BA_quotient_Spruce
        - 0.71412 * BA_quotient_Birch
        + 0.22859 * peatland
        + 0.0028355 * altitude
        - 0.16805 * north
        + 0.13365 * herb
        + 0.13661 * moist
        + 0.045906 * divided_plot
        + 0.10209 * fertilised_plot
        + 0.24457 * plot_inventoried_76_77
        - 2.5124
    ) / 10000  # Convert cm² to m²

    return result

@staticmethod
def birch_northern_central_sweden_over_45(
    DBH_cm,
    DBH_largest_tree_on_plot_cm,
    BA_tree_m2,
    BA_Pine_m2_ha,
    BA_Spruce_m2_ha,
    BA_Birch_m2_ha,
    BA_m2_ha,
    age,
    thinned,
    last_thinned,
    vegetation,
    aspect,
    latitude,
    soil_moisture,
    county,
    peatland=0,
    divided_plot=0,
    fertilised_plot=0,
    plot_inventoried_76_77=0
):
    """
    Calculate the 5-year basal area increment for Birch in northern and central Sweden (over 45 years old).

    Args:
        DBH_cm (float): Diameter at breast height in cm.
        DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
        BA_tree_m2 (float): Basal area of the tree in m².
        BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
        BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
        BA_Birch_m2_ha (float): Basal area of Birch on the plot in m²/ha.
        BA_m2_ha (float): Total basal area on the plot in m²/ha.
        age (int): Tree age at breast height.
        thinned (bool): Whether the stand was thinned (True) or not (False).
        last_thinned (int): Number of growing seasons since last thinning.
        vegetation (int): Vegetation type (1 to 18).
        aspect (int): Aspect of the site (1 to 8, 0 if not applicable).
        latitude (float): Latitude in degrees.
        soil_moisture (int): Soil moisture class (1 to 5).
        county (str): County name.
        peatland (int, optional): Whether the plot is peatland (1) or not (0). Defaults to 0.
        divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.
        fertilised_plot (int, optional): Whether the plot is fertilised (1) or not (0). Defaults to 0.
        plot_inventoried_76_77 (int, optional): Whether the plot was inventoried in 1976-77 (1) or not (0). Defaults to 0.

    Returns:
        float: Predicted basal area increment during 5 years in m².
    """
    basal_area_of_tree_cm2 = BA_tree_m2 * 10000
    moist = 1 if soil_moisture > 3 else 0
    north = 1 if aspect in [8, 1, 2, 3] else 0
    herb = 1 if vegetation < 7 else 0
    diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
    BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
    BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
    BA_quotient_Birch = BA_Birch_m2_ha / BA_m2_ha

    if not thinned:
        thinning = -0.064159 * BA_m2_ha + 0.0096451 * (BA_m2_ha ** 2)
    elif last_thinned < 5:
        thinning = -0.016802 * BA_m2_ha + 0.0034084 * (BA_m2_ha ** 2)
    else:
        thinning = -0.040875 * BA_m2_ha + 0.0022925 * (BA_m2_ha ** 2)

    result = np.exp(
        +0.10653 * np.log(basal_area_of_tree_cm2)
        + 2.0031 * (1 / (age + 10))
        - 40.583 * ((1 / (age + 10)) ** 2)
        + thinning
        - 1.4923 * diameter_quotient
        + 0.80965 * (diameter_quotient ** 2)
        - 0.80277 * BA_quotient_Pine
        - 0.66805 * BA_quotient_Spruce
        - 0.62539 * BA_quotient_Birch
        + 0.35839 * peatland
        + 10.530 * latitude
        - 0.081380 * (latitude ** 2)
        - 0.19078 * north
        + 0.11808 * herb
        + 0.21901 * moist
        + 0.18760 * divided_plot
        + 0.10200 * fertilised_plot
        + 0.15176 * plot_inventoried_76_77
        - 36.815
    ) / 10000  # Convert cm² to m²

    return result

@staticmethod
def broadleaves_northern_central_sweden(
    BA_tree_m2,
    BA_Pine_m2_ha,
    BA_Spruce_m2_ha,
    BA_m2_ha,
    age,
    thinned,
    last_thinned,
    aspect,
    latitude,
    altitude,
    divided_plot=0,
    plot_inventoried_76_77=0
):
    """
    Calculate the 5-year basal area increment for Broadleaves in northern and central Sweden.

    Args:
        BA_tree_m2 (float): Basal area of the tree in m².
        BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
        BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
        BA_m2_ha (float): Total basal area on the plot in m²/ha.
        age (int): Tree age at breast height.
        thinned (bool): Whether the stand was thinned (True) or not (False).
        last_thinned (int): Number of growing seasons since last thinning.
        aspect (int): Aspect of the site (1 to 8, 0 if not applicable).
        latitude (float): Latitude in degrees.
        altitude (float): Altitude in meters above sea level.
        divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.
        plot_inventoried_76_77 (int, optional): Whether the plot was inventoried in 1976-77 (1) or not (0). Defaults to 0.

    Returns:
        float: Predicted basal area increment during 5 years in m².
    """
    basal_area_of_tree_cm2 = BA_tree_m2 * 10000
    north = 1 if aspect in [8, 1, 2, 3] else 0
    BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
    BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha

    if not thinned:
        thinning = -0.02732 * BA_m2_ha + 0.0032095 * (BA_m2_ha ** 2)
    elif last_thinned < 5:
        thinning = -0.019331 * BA_m2_ha
    else:
        thinning = 0

    result = np.exp(
        +0.11208 * np.log(basal_area_of_tree_cm2)
        + 4.8728 * (1 / (age + 10))
        + thinning
        - 0.47542 * BA_quotient_Pine
        + 0.24701 * BA_quotient_Spruce
        + 0.063271 * latitude
        - 0.000095194 * latitude * altitude
        - 0.27834 * north
        + 0.20279 * divided_plot
        + 0.088716 * plot_inventoried_76_77
        - 6.6924
    ) / 10000  # Convert cm² to m²

    return result

@staticmethod
def pine_central_sweden_over_45(DBH_cm, DBH_largest_tree_on_plot_cm, BA_tree_m2, BA_Spruce_m2_ha, BA_m2_ha, age, thinned, last_thinned, SI100, SI_species, latitude, altitude, soil_moisture, peatland=0, divided_plot=0, fertilised_plot=0, plot_inventoried_76_77=0):
    """
    Calculate the 5-year basal area increment for Scots Pine in central Sweden (over 45 years old).

    Args:
        DBH_cm (float): Diameter at breast height in cm.
        DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
        BA_tree_m2 (float): Basal area of the tree in m².
        BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
        BA_m2_ha (float): Total basal area on the plot in m²/ha.
        age (int): Tree age at breast height.
        thinned (bool): Whether the stand was thinned (True) or not (False).
        last_thinned (int): Number of growing seasons since last thinning.
        SI100 (float): Site Index H100 in meters.
        SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
        latitude (float): Latitude in degrees.
        altitude (float): Altitude in meters above sea level.
        soil_moisture (int): Soil moisture class (1 to 5).
        peatland (int, optional): Whether the plot is peatland (1) or not (0). Defaults to 0.
        divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.
        fertilised_plot (int, optional): Whether the plot is fertilised (1) or not (0). Defaults to 0.
        plot_inventoried_76_77 (int, optional): Whether the plot was inventoried in 1976-77 (1) or not (0). Defaults to 0.

    Returns:
        float: Predicted basal area increment during 5 years in m².
    """
    basal_area_of_tree_cm2 = BA_tree_m2 * 10000
    spruce = 1 if SI_species == "Picea abies" else 0
    pine = 1 if SI_species == "Pinus sylvestris" else 0
    moist = 1 if soil_moisture > 3 else 0
    diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
    BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha

    if not thinned:
        thinning = -0.058169 * BA_m2_ha + 0.0059532 * (BA_m2_ha ** 2)
    elif last_thinned < 5:
        thinning = -0.056116 * BA_m2_ha + 0.0081799 * (BA_m2_ha ** 2)
    else:
        thinning = -0.050915 * BA_m2_ha + 0.0043750 * (BA_m2_ha ** 2)

    result = np.exp(
        +0.090114 * np.log(basal_area_of_tree_cm2)
        - 0.000094211 * basal_area_of_tree_cm2
        + 0.16635 * (1 / (age + 10))
        - 0.42139 * ((1 / (age + 10)) ** 2)
        + thinning
        + 0.23240 * diameter_quotient
        - 0.16575 * (diameter_quotient ** 2)
        + 0.37660 * BA_quotient_Spruce
        + 0.00017996 * spruce * SI100 * 10  # m to dm
        + 0.00024084 * pine * SI100 * 10    # m to dm
        + 0.46113 * peatland
        - 0.029434 * altitude
        + 0.0047369 * latitude * altitude
        + 0.085870 * moist
        + 0.12523 * divided_plot
        + 0.11202 * fertilised_plot
        + 0.12541 * plot_inventoried_76_77
        - 0.33826
    ) / 10000  # Convert cm² to m²
    return result

@staticmethod
def pine_central_sweden_under_65(DBH_cm, DBH_largest_tree_on_plot_cm, BA_tree_m2, BA_Spruce_m2_ha, BA_m2_ha, age, thinned, last_thinned, SI100, SI_species, latitude, altitude, soil_moisture, peatland=0, divided_plot=0, fertilised_plot=0, plot_inventoried_76_77=0):
    """
    Calculate the 5-year basal area increment for Scots Pine in central Sweden (under 65 years old).

    Args:
        DBH_cm (float): Diameter at breast height in cm.
        DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
        BA_tree_m2 (float): Basal area of the tree in m².
        BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
        BA_m2_ha (float): Total basal area on the plot in m²/ha.
        age (int): Tree age at breast height.
        thinned (bool): Whether the stand was thinned (True) or not (False).
        last_thinned (int): Number of growing seasons since last thinning.
        SI100 (float): Site Index H100 in meters.
        SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
        latitude (float): Latitude in degrees.
        altitude (float): Altitude in meters above sea level.
        soil_moisture (int): Soil moisture class (1 to 5).
        peatland (int, optional): Whether the plot is peatland (1) or not (0). Defaults to 0.
        divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.
        fertilised_plot (int, optional): Whether the plot is fertilised (1) or not (0). Defaults to 0.
        plot_inventoried_76_77 (int, optional): Whether the plot was inventoried in 1976-77 (1) or not (0). Defaults to 0.

    Returns:
        float: Predicted basal area increment during 5 years in m².
    """
    basal_area_of_tree_cm2 = BA_tree_m2 * 10000
    spruce = 1 if SI_species == "Picea abies" else 0
    pine = 1 if SI_species == "Pinus sylvestris" else 0
    moist = 1 if soil_moisture > 3 else 0
    diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
    BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha

    if not thinned:
        thinning = -0.047256 * BA_m2_ha + 0.0049819 * (BA_m2_ha ** 2)
    elif last_thinned < 5:
        thinning = -0.034903 * BA_m2_ha + 0.0040225 * (BA_m2_ha ** 2)
    else:
        thinning = -0.030434 * BA_m2_ha + 0.0014407 * (BA_m2_ha ** 2)

    result = np.exp(
        +0.10932 * np.log(basal_area_of_tree_cm2)
        - 0.00045888 * basal_area_of_tree_cm2
        - 0.040552 * (np.log(basal_area_of_tree_cm2) / (age + 10))
        + 0.095220 * (1 / (age + 10))
        - 0.044511 * ((1 / (age + 10)) ** 2)
        + thinning
        + 0.23348 * diameter_quotient
        - 0.16233 * (diameter_quotient ** 2)
        + 0.33478 * BA_quotient_Spruce
        + 0.00025445 * spruce * SI100 * 10  # m to dm
        + 0.00080005 * pine * SI100 * 10    # m to dm
        + 0.17215 * peatland
        - 0.036525 * altitude
        + 0.0059703 * latitude * altitude
        + 0.13568 * moist
        + 0.16428 * divided_plot
        + 0.052583 * fertilised_plot
        + 0.19657 * plot_inventoried_76_77
        - 0.38356
    ) / 10000  # Convert cm² to m²
    return result

@staticmethod
def spruce_central_sweden_under_65(DBH_cm, DBH_largest_tree_on_plot_cm, BA_tree_m2, BA_Pine_m2_ha, BA_Spruce_m2_ha, BA_Birch_m2_ha, BA_m2_ha, age, thinned, last_thinned, SI100, SI_species, soil_moisture, latitude, altitude, peatland=0, divided_plot=0, fertilised_plot=0, plot_inventoried_76_77=0):
    """
    Calculate the 5-year basal area increment for Spruce in central Sweden (under 65 years old).

    Args:
        DBH_cm (float): Diameter at breast height in cm.
        DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
        BA_tree_m2 (float): Basal area of the tree in m².
        BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
        BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
        BA_Birch_m2_ha (float): Basal area of Birch on the plot in m²/ha.
        BA_m2_ha (float): Total basal area on the plot in m²/ha.
        age (int): Tree age at breast height.
        thinned (bool): Whether the stand was thinned (True) or not (False).
        last_thinned (int): Number of growing seasons since last thinning.
        SI100 (float): Site Index H100 in meters.
        SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
        soil_moisture (int): Soil moisture class (1 to 5).
        latitude (float): Latitude in degrees.
        altitude (float): Altitude in meters above sea level.
        peatland (int, optional): Whether the plot is peatland (1) or not (0). Defaults to 0.
        divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.
        fertilised_plot (int, optional): Whether the plot is fertilised (1) or not (0). Defaults to 0.
        plot_inventoried_76_77 (int, optional): Whether the plot was inventoried in 1976-77 (1) or not (0). Defaults to 0.

    Returns:
        float: Predicted basal area increment during 5 years in m².
    """
    basal_area_of_tree_cm2 = BA_tree_m2 * 10000
    spruce = 1 if SI_species == "Picea abies" else 0
    pine = 1 if SI_species == "Pinus sylvestris" else 0
    moist = 1 if soil_moisture > 3 else 0
    diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
    BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
    BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
    BA_quotient_Birch = BA_Birch_m2_ha / BA_m2_ha

    if not thinned:
        thinning = -0.049683 * BA_m2_ha + 0.0041229 * (BA_m2_ha ** 2)
    elif last_thinned < 5:
        thinning = -0.033745 * BA_m2_ha + 0.0021671 * (BA_m2_ha ** 2)
    else:
        thinning = -0.038862 * BA_m2_ha + 0.0017195 * (BA_m2_ha ** 2)

    result = np.exp(
        +0.14711 * np.log(basal_area_of_tree_cm2)
        - 0.0069197 * basal_area_of_tree_cm2
        - 0.079926 * (np.log(basal_area_of_tree_cm2) / (age + 10))
        + 0.12577 * (1 / (age + 10))
        - 0.053325 * ((1 / (age + 10)) ** 2)
        + thinning
        - 0.053502 * diameter_quotient
        - 0.063206 * BA_quotient_Pine
        - 0.059632 * BA_quotient_Spruce
        - 0.041666 * BA_quotient_Birch
        + 0.0017481 * spruce * SI100 * 10  # m to dm
        + 0.0027543 * pine * SI100 * 10    # m to dm
        + 0.24145 * peatland
        - 0.11600 * latitude
        + 0.097148 * (latitude ** 2)
        + 0.023556 * altitude
        - 0.00038030 * latitude * altitude
        + 0.13146 * moist
        + 0.064887 * divided_plot
        + 0.099316 * fertilised_plot
        + 0.076914 * plot_inventoried_76_77
        + 3.4171
    ) / 10000  # Convert cm² to m²
    return result

@staticmethod
def spruce_central_sweden_over_45(DBH_cm, DBH_largest_tree_on_plot_cm, BA_tree_m2, BA_Pine_m2_ha, BA_Spruce_m2_ha, BA_m2_ha, age, thinned, last_thinned, SI100, SI_species, soil_moisture, latitude, altitude, peatland=0, divided_plot=0, fertilised_plot=0):
    """
    Calculate the 5-year basal area increment for Spruce in central Sweden (over 45 years old).

    Args:
        DBH_cm (float): Diameter at breast height in cm.
        DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
        BA_tree_m2 (float): Basal area of the tree in m².
        BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
        BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
        BA_m2_ha (float): Total basal area on the plot in m²/ha.
        age (int): Tree age at breast height.
        thinned (bool): Whether the stand was thinned (True) or not (False).
        last_thinned (int): Number of growing seasons since last thinning.
        SI100 (float): Site Index H100 in meters.
        SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
        soil_moisture (int): Soil moisture class (1 to 5).
        latitude (float): Latitude in degrees.
        altitude (float): Altitude in meters above sea level.
        peatland (int, optional): Whether the plot is peatland (1) or not (0). Defaults to 0.
        divided_plot (int, optional): Whether the plot is divided (1) or full (0). Defaults to 0.
        fertilised_plot (int, optional): Whether the plot is fertilised (1) or not (0). Defaults to 0.

    Returns:
        float: Predicted basal area increment during 5 years in m².
    """
    basal_area_of_tree_cm2 = BA_tree_m2 * 10000
    spruce = 1 if SI_species == "Picea abies" else 0
    pine = 1 if SI_species == "Pinus sylvestris" else 0
    moist = 1 if soil_moisture > 3 else 0
    diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
    BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
    BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha

    if not thinned:
        thinning = -0.040724 * BA_m2_ha + 0.0028049 * (BA_m2_ha ** 2)
    elif last_thinned < 5:
        thinning = -0.032428 * BA_m2_ha + 0.0025540 * (BA_m2_ha ** 2)
    else:
        thinning = -0.033682 * BA_m2_ha + 0.0018766 * (BA_m2_ha ** 2)

    result = np.exp(
        +0.12252 * np.log(basal_area_of_tree_cm2)
        - 0.00053489 * basal_area_of_tree_cm2
        + 0.18789 * (1 / (age + 10))
        + 0.49425 * ((1 / (age + 10)) ** 2)
        + thinning
        - 0.081637 * diameter_quotient
        + 0.040139 * (diameter_quotient ** 2)
        - 0.030428 * BA_quotient_Pine
        - 0.018039 * BA_quotient_Spruce
        + 0.0022559 * spruce * SI100 * 10  # m to dm
        + 0.0032384 * pine * SI100 * 10    # m to dm
        + 0.37674 * peatland
        - 0.10388 * latitude
        + 0.087352 * (latitude ** 2)
        + 0.030944 * altitude
        - 0.00050260 * latitude * altitude
        + 0.11133 * moist
        + 0.090603 * divided_plot
        + 0.032526 * fertilised_plot
        + 3.0440
    ) / 10000  # Convert cm² to m²
    return result

