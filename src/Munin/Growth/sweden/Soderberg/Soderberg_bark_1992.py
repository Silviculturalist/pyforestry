import math

class Soderberg1992DoubleBark:
    """
    This class provides methods to calculate double bark thickness for individual trees 
    in southern and northern Sweden based on the Soderberg (1992) model.
    
    The methods in this class apply to different species and regional divisions based on 
    factors like tree diameter, age, basal area, and location characteristics such as 
    distance to the coast, altitude, and latitude.
    """
    
    @staticmethod
    def southern_spruce(SI100_Pine, distance_to_coast_km, DBH_cm, DBH_largest_tree_on_plot_cm,
                        total_age, BA_Pine_m2_ha, BA_Spruce_m2_ha, BA_Birch_m2_ha, BA_m2_ha, 
                        latitude, altitude, divided_plot=0):
        """
        Calculate the double bark thickness for Norway Spruce in southern Sweden.
        
        Args:
            SI100_Pine (float): Site index for Pine.
            distance_to_coast_km (float): Distance to the coast in kilometers.
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Pine_m2_ha (float): Basal area in m^2/ha for Pine.
            BA_Spruce_m2_ha (float): Basal area in m^2/ha for Spruce.
            BA_Birch_m2_ha (float): Basal area in m^2/ha for Birch.
            BA_m2_ha (float): Total basal area in m^2/ha on the plot.
            latitude (float): Latitude in degrees.
            altitude (float): Altitude in meters.
            divided_plot (int, optional): 0 for full plots, 1 for divided plots. Defaults to 0.

        Returns:
            float: Double bark thickness in mm.
        """
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        BA_quotient_Birch = BA_Birch_m2_ha / BA_m2_ha
        BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        close_to_coast = 1 if distance_to_coast_km < 50 else 0
        
        return math.exp(
            -0.30355E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.13763E5 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.23539E-4 * (total_age ** 2) -
            0.13014E-2 * SI100_Pine * 10 -
            0.10863E-1 * altitude +
            0.19027E-3 * latitude * altitude +
            0.30230E0 * diameter_quotient +
            0.68055E-1 * BA_quotient_Pine -
            0.10406E0 * BA_quotient_Spruce +
            0.62182E-1 * BA_quotient_Birch +
            0.27539E-1 * divided_plot +
            0.23053E0 * close_to_coast +
            0.36138E1 +
            0.03001  # correction for logarithmic bias
        )

    @staticmethod
    def southern_pine(SI100_Pine, distance_to_coast_km, DBH_cm,
                      total_age, BA_Pine_m2_ha, BA_Birch_m2_ha, BA_m2_ha, latitude, altitude,
                      divided_plot=0, county=None):
        """
        Calculate the double bark thickness for Pine in southern Sweden.

        Args:
            SI100_Pine (float): Site index for Pine.
            distance_to_coast_km (float): Distance to the coast in kilometers.
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Pine_m2_ha (float): Basal area in m^2/ha for Pine.
            BA_Birch_m2_ha (float): Basal area in m^2/ha for Birch.
            BA_m2_ha (float): Total basal area in m^2/ha on the plot.
            latitude (float): Latitude in degrees.
            altitude (float): Altitude in meters.
            divided_plot (int, optional): 0 for full plots, 1 for divided plots. Defaults to 0.
            county (str, optional): Name of the county for region-specific calculations.

        Returns:
            float: Double bark thickness in mm.
        """
        BA_quotient_Birch = BA_Birch_m2_ha / BA_m2_ha
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        close_to_coast = 1 if distance_to_coast_km < 50 else 0
        south_eastern_county = 1 if county in ["Stockholm", "Södermanland", "Uppsala", "Östergötland", "Kalmar", "Västmanland"] else 0
        
        return math.exp(
            -0.38360E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.13442E5 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.20965E-2 * total_age -
            0.88795E-5 * (total_age ** 2) -
            0.74698E-3 * SI100_Pine * 10 +
            0.10185E-1 * altitude -
            0.17023E-3 * latitude * altitude -
            0.24281E-1 * BA_quotient_Pine -
            0.49230E-1 * BA_quotient_Birch +
            0.57067E-1 * south_eastern_county +
            0.24619E-1 * divided_plot +
            0.19141E0 * close_to_coast +
            0.47240E1 +
            0.02832  # correction for logarithmic bias
        )
    
    @staticmethod
    def southern_oak(DBH_cm, total_age,county,divided_plot):
        south_eastern_county = 1 if county in ['Stockholm','Södermanland','Uppsala','Östergötland','Kalmar','Västmanland'] else 0

        return math.exp(
        -0.29605E3*(1/((DBH_cm*10)+50))#Diameter cm should be in mm.
        +0.87235E4*((1/((DBH_cm*10)+50))**2) #Diameter cm should be in mm.
        +0.22680E-2*total_age
        -0.24349E0*south_eastern_county
        +0.44474E-1*divided_plot
        +0.39521E1
        +0.02354 #correction for logarithmic bias, appendix 5.
        )
    
    @staticmethod
    def southern_beech(DBH_cm, total_age, county, DBH_largest_tree_on_plot_cm):
        """
        Calculate the double bark thickness for Oak in southern Sweden.

        Args:
            DBH_cm (float): Diameter at breast height in cm.
            total_age (int): Total age of the stand.
            county (str): Name of the county for region-specific calculations.

        Returns:
            float: Double bark thickness in mm.
        """
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        region5 = 1 if county in ["Blekinge", "Kristianstad", "Malmöhus", "Västra Götaland", "Halland", "Gotland"] else 0

        return math.exp(
            -0.17387E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.22597E-2 * total_age +
            0.16350E0 * diameter_quotient -
            0.26953E0 * region5 +
            0.24822E1 +
            0.03251  # correction for logarithmic bias
        )

    @staticmethod
    def northern_spruce(SI100_Pine, distance_to_coast_km, DBH_cm, DBH_largest_tree_on_plot_cm,
                        total_age, BA_Pine_m2_ha, BA_m2_ha, latitude, altitude):
        """
        Calculate the double bark thickness for Norway Spruce in northern Sweden.

        Args:
            SI100_Pine (float): Site index for Pine.
            distance_to_coast_km (float): Distance to the coast in kilometers.
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Pine_m2_ha (float): Basal area in m^2/ha for Pine.
            BA_m2_ha (float): Total basal area in m^2/ha on the plot.
            latitude (float): Latitude in degrees.
            altitude (float): Altitude in meters.

        Returns:
            float: Double bark thickness in mm.
        """
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        close_to_coast = 1 if distance_to_coast_km < 50 else 0
        
        return math.exp(
            -0.40225E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.15037E5 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.44577E-3 * total_age -
            0.15147E-3 * SI100_Pine * 10 -
            0.13581E-1 * latitude -
            0.16395E-5 * latitude * altitude +
            0.88075E-1 * diameter_quotient -
            0.11552E-1 * (diameter_quotient ** 2) -
            0.69739E-1 * BA_quotient_Pine -
            0.82879E-1 * close_to_coast +
            0.53324E1 +
            0.02691  # correction for logarithmic bias
        )

    @staticmethod
    def northern_birch(SI100_Pine, DBH_cm, DBH_largest_tree_on_plot_cm, total_age,
                       BA_Pine_m2_ha, BA_m2_ha, latitude, altitude):
        """
        Calculate the double bark thickness for Birch in northern Sweden.

        Args:
            SI100_Pine (float): Site index for Pine.
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Pine_m2_ha (float): Basal area in m^2/ha for Pine.
            BA_m2_ha (float): Total basal area in m^2/ha on the plot.
            latitude (float): Latitude in degrees.
            altitude (float): Altitude in meters.

        Returns:
            float: Double bark thickness in mm.
        """
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm

        return math.exp(
            -0.37131E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.13012E5 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.19655E-2 * total_age -
            0.71109E-3 * SI100_Pine * 10 +
            0.86881E-2 * latitude +
            0.62991E-5 * latitude * altitude +
            0.17146E0 * diameter_quotient +
            0.18594E0 * BA_quotient_Pine +
            0.31740E1 +
            0.04292  # correction for logarithmic bias
        )

    @staticmethod
    def central_spruce(SI100_Pine, distance_to_coast_km, DBH_cm, DBH_largest_tree_on_plot_cm,
                       total_age, BA_Spruce_m2_ha, BA_m2_ha, latitude, altitude):
        """
        Calculate the double bark thickness for Norway Spruce in central Sweden.

        Args:
            SI100_Pine (float): Site index for Pine.
            distance_to_coast_km (float): Distance to the coast in kilometers.
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Spruce_m2_ha (float): Basal area in m^2/ha for Spruce.
            BA_m2_ha (float): Total basal area in m^2/ha on the plot.
            latitude (float): Latitude in degrees.
            altitude (float): Altitude in meters.

        Returns:
            float: Double bark thickness in mm.
        """
        BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        close_to_coast = 1 if distance_to_coast_km < 50 else 0
        
        return math.exp(
            -0.39422E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.14040E5 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.30388E-3 * total_age -
            0.92527E-3 * SI100_Pine * 10 -
            0.64192E-1 * latitude -
            0.31573E-3 * altitude +
            0.12632E0 * diameter_quotient -
            0.46079E-1 * (diameter_quotient ** 2) +
            0.58621E-1 * BA_quotient_Spruce -
            0.94391E-1 * close_to_coast +
            0.86428E1 +
            0.02622  # correction for logarithmic bias
        )

    @staticmethod
    def central_birch(DBH_cm, DBH_largest_tree_on_plot_cm, total_age,
                      BA_Birch_m2_ha, BA_m2_ha, distance_to_coast_km, divided_plot=0):
        """
        Calculate the double bark thickness for Birch in central Sweden.

        Args:
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Birch_m2_ha (float): Basal area in m^2/ha for Birch.
            BA_m2_ha (float): Total basal area in m^2/ha on the plot.
            distance_to_coast_km (float): Distance to the coast in kilometers.


        Returns:
            float: Double bark thickness in mm.
        """
        BA_quotient_Birch = BA_Birch_m2_ha / BA_m2_ha
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        close_to_coast = 1 if distance_to_coast_km < 50 else 0

        return math.exp(
            -0.17562E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.49609E-2 * total_age +
            0.26968E0 * diameter_quotient +
            0.29703E0 * BA_quotient_Birch -
            0.77013E-1 * divided_plot +
            0.86920E-1 * close_to_coast +
            0.28446E1 +
            0.075272  # correction for Baskerville 1972
        )

    @staticmethod
    def central_oak(DBH_cm, total_age, county, divided_plot):
        """
        Calculate the double bark thickness for Oak in central Sweden.

        Args:
            DBH_cm (float): Diameter at breast height in cm.
            total_age (int): Total age of the stand.
            county (str): Name of the county for region-specific calculations.
            divided_plot (int): 0 for full plots, 1 for divided plots.

        Returns:
            float: Double bark thickness in mm.
        """
        region5 = 1 if county in ["Blekinge", "Kristianstad", "Malmöhus", "Västra Götaland", "Halland", "Gotland"] else 0

        return math.exp(
            -0.29605E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.87235E4 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.22680E-2 * total_age -
            0.24349E0 * region5 +
            0.44474E-1 * divided_plot +
            0.39521E1 +
            0.02354  # correction for logarithmic bias
        )

    @staticmethod
    def northern_central_spruce(SI100_Pine, distance_to_coast_km, DBH_cm, DBH_largest_tree_on_plot_cm,
                                total_age, BA_Pine_m2_ha, BA_m2_ha, latitude, divided_plot=0):
        """
        Calculate the double bark thickness for Norway Spruce in northern or central Sweden.

        Args:
            SI100_Pine (float): Site index for Pine.
            distance_to_coast_km (float): Distance to the coast in kilometers.
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Pine_m2_ha (float): Basal area in m^2/ha for Pine.
            BA_m2_ha (float): Total basal area in m^2/ha on the plot.
            latitude (float): Latitude in degrees.
            divided_plot (int, optional): 0 for full plots, 1 for divided plots. Defaults to 0.

        Returns:
            float: Double bark thickness in mm.
        """
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        close_to_coast = 1 if distance_to_coast_km < 50 else 0

        return math.exp(
            -0.23633E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.78784E4 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.13589E-2 * total_age +
            0.62227E-5 * (total_age ** 2) -
            0.15491E-2 * SI100_Pine * 10 +
            0.28379E-1 * latitude +
            0.35929E0 * diameter_quotient +
            0.57123E-1 * BA_quotient_Pine +
            0.20245E-1 * divided_plot -
            0.71409E-1 * close_to_coast +
            0.16604E1 +
            0.02808  # correction for logarithmic bias
        )

    @staticmethod
    def northern_central_birch(SI100_Pine, DBH_cm, DBH_largest_tree_on_plot_cm, total_age,
                               BA_Pine_m2_ha, BA_m2_ha, latitude, altitude):
        """
        Calculate the double bark thickness for Birch in northern or central Sweden.

        Args:
            SI100_Pine (float): Site index for Pine.
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Pine_m2_ha (float): Basal area in m^2/ha for Pine.
            BA_m2_ha (float): Total basal area in m^2/ha on the plot.
            latitude (float): Latitude in degrees.
            altitude (float): Altitude in meters.

        Returns:
            float: Double bark thickness in mm.
        """
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm

        return math.exp(
            -0.37131E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.13012E5 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.19655E-2 * total_age -
            0.71109E-3 * SI100_Pine * 10 +
            0.86881E-2 * latitude +
            0.62991E-5 * latitude * altitude +
            0.17146E0 * diameter_quotient +
            0.18594E0 * BA_quotient_Pine +
            0.31740E1 +
            0.04292  # correction for logarithmic bias
        )

    @staticmethod
    def southern_broadleaves(SI100_Pine, DBH_cm, total_age):
        """
        Calculate the double bark thickness for Broadleaves in southern Sweden.

        Args:
            SI100_Pine (float): Site index for Pine.
            DBH_cm (float): Diameter at breast height in cm.
            total_age (int): Total age of the stand.

        Returns:
            float: Double bark thickness in mm.
        """
        return math.exp(
            -0.34144E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.97900E4 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.31101E-2 * total_age -
            0.22562E-4 * (total_age ** 2) -
            0.21013E-2 * SI100_Pine * 10 +
            0.45835E1 +
            0.044402  # Baskerville 1972, logarithmic correction not included in appendix 5
        )

    @staticmethod
    def southern_birch(SI100_Pine, DBH_cm, DBH_largest_tree_on_plot_cm, total_age,
                       BA_Pine_m2_ha, BA_Birch_m2_ha, BA_m2_ha, latitude, altitude, county):
        """
        Calculate the double bark thickness for Birch in southern Sweden.

        Args:
            SI100_Pine (float): Site index for Pine.
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Pine_m2_ha (float): Basal area in m^2/ha for Pine.
            BA_Birch_m2_ha (float): Basal area in m^2/ha for Birch.
            BA_m2_ha (float): Total basal area in m^2/ha on the plot.
            latitude (float): Latitude in degrees.
            altitude (float): Altitude in meters.
            county (str): Name of the county for region-specific calculations.

        Returns:
            float: Double bark thickness in mm.
        """
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        BA_quotient_Birch = BA_Birch_m2_ha / BA_m2_ha
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        south_eastern_county = 1 if county in ["Stockholm", "Södermanland", "Uppsala", "Östergötland", "Kalmar", "Västmanland"] else 0

        return math.exp(
            -0.64799E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.33167E5 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.14517E-2 * total_age -
            0.50779E-3 * SI100_Pine * 10 +
            0.54445E-2 * altitude -
            0.99383E-4 * latitude * altitude +
            0.13804E0 * diameter_quotient +
            0.88745E-1 * BA_quotient_Pine -
            0.14772E0 * BA_quotient_Birch -
            0.51335E-1 * south_eastern_county +
            0.50104E1 +
            0.04440  # correction for logarithmic bias
        )

    @staticmethod
    def southern_beech(DBH_cm, DBH_largest_tree_on_plot_cm, total_age, county):
        """
        Calculate the double bark thickness for Beech in southern Sweden.

        Args:
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            county (str): Name of the county for region-specific calculations.

        Returns:
            float: Double bark thickness in mm.
        """
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        region5 = 1 if county in ["Blekinge", "Kristianstad", "Malmöhus", "Västra Götaland", "Halland", "Gotland"] else 0

        return math.exp(
            -0.17387E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.22597E-2 * total_age +
            0.16350E0 * diameter_quotient -
            0.26953E0 * region5 +
            0.24822E1 +
            0.03251  # correction for logarithmic bias
        )

    @staticmethod
    def northern_pine(SI100_Pine, distance_to_coast_km, DBH_cm, DBH_largest_tree_on_plot_cm,
                      total_age, BA_Pine_m2_ha, BA_m2_ha, latitude, altitude):
        """
        Calculate the double bark thickness for Pine in northern Sweden.

        Args:
            SI100_Pine (float): Site index for Pine.
            distance_to_coast_km (float): Distance to the coast in kilometers.
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Pine_m2_ha (float): Basal area in m^2/ha for Pine.
            BA_m2_ha (float): Total basal area in m^2/ha on the plot.
            latitude (float): Latitude in degrees.
            altitude (float): Altitude in meters.

        Returns:
            float: Double bark thickness in mm.
        """
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        close_to_coast = 1 if distance_to_coast_km < 50 else 0

        return math.exp(
            -0.40225E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.15037E5 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.44577E-3 * total_age -
            0.15147E-3 * SI100_Pine * 10 -
            0.13581E-1 * latitude -
            0.16395E-5 * latitude * altitude +
            0.88075E-1 * diameter_quotient -
            0.11552E-1 * (diameter_quotient ** 2) -
            0.69739E-1 * BA_quotient_Pine -
            0.82879E-1 * close_to_coast +
            0.53324E1 +
            0.02691  # correction for logarithmic bias
        )

    @staticmethod
    def central_pine(SI100_Pine, distance_to_coast_km, DBH_cm, DBH_largest_tree_on_plot_cm,
                     total_age, BA_Spruce_m2_ha, BA_m2_ha, latitude, altitude):
        """
        Calculate the double bark thickness for Pine in central Sweden.

        Args:
            SI100_Pine (float): Site index for Pine.
            distance_to_coast_km (float): Distance to the coast in kilometers.
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Spruce_m2_ha (float): Basal area in m^2/ha for Spruce.
            BA_m2_ha (float): Total basal area in m^2/ha on the plot.
            latitude (float): Latitude in degrees.
            altitude (float): Altitude in meters.

        Returns:
            float: Double bark thickness in mm.
        """
        BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        close_to_coast = 1 if distance_to_coast_km < 50 else 0

        return math.exp(
            -0.39422E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.14040E5 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +
            0.30388E-3 * total_age -
            0.92527E-3 * SI100_Pine * 10 -
            0.64192E-1 * latitude -
            0.31573E-3 * altitude +
            0.12632E0 * diameter_quotient -
            0.46079E-1 * (diameter_quotient ** 2) +
            0.58621E-1 * BA_quotient_Spruce -
            0.94391E-1 * close_to_coast +
            0.86428E1 +
            0.02622  # correction for logarithmic bias
        )

    @staticmethod
    def northern_central_broadleaves(distance_to_coast_km, DBH_cm, DBH_largest_tree_on_plot_cm,
                                     total_age, BA_Birch_m2_ha, BA_m2_ha, divided_plot=0):
        """
        Calculate the double bark thickness for Broadleaves in northern or central Sweden.

        Args:
            distance_to_coast_km (float): Distance to the coast in kilometers.
            DBH_cm (float): Diameter at breast height in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Birch_m2_ha (float): Basal area in m^2/ha for Birch.
            BA_m2_ha (float): Total basal area in m^2/ha on the plot.
            divided_plot (int, optional): 0 for full plots, 1 for divided plots. Defaults to 0.

        Returns:
            float: Double bark thickness in mm.
        """
        BA_quotient_Birch = BA_Birch_m2_ha / BA_m2_ha
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        close_to_coast = 1 if distance_to_coast_km < 50 else 0

        return math.exp(
            -0.17562E3 * (1 / ((DBH_cm * 10) + 50)) +
            0.49609E-2 * total_age +
            0.26968E0 * diameter_quotient +
            0.29703E0 * BA_quotient_Birch -
            0.77013E-1 * divided_plot +
            0.86920E-1 * close_to_coast +
            0.28446E1 +
            0.075272  # correction for Baskerville 1972
        )
