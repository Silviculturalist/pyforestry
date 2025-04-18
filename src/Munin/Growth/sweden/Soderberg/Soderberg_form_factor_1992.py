import math

class Soderberg1992FormFactor:
    """
    Class containing static methods for calculating the form factor of individual trees in Sweden 
    (Söderberg 1992). These methods calculate tree form factors for different species and regions 
    using species-specific models.

    Source: 
        Söderberg, U. (1992) Funktioner för skogsindelning: Höjd,
        formhöjd och barktjocklek för enskilda träd. / Functions for forest
        management: Height, form height and bark thickness of individual trees. 
        Report 52. Dept. of Forest Survey. Swedish University of Agricultural Sciences. 
        ISSN 0348-0496.

    """
    @staticmethod
    def southern_spruce(SI100_Pine, distance_to_coast_km, DBH_cm, DBH_largest_tree_on_plot_cm, total_age, BA_Pine_m2, 
                        BA_Spruce_m2, BA_Birch_m2, BA_m2, latitude, altitude, divided_plot=0):
        """
        Calculates the form factor for Norway Spruce in Southern Sweden.

        Args:
            SI100_Pine (float): Site index for Scots Pine (SI100) in dm.
            distance_to_coast_km (float): Distance to the nearest coast in kilometers.
            DBH_cm (float): Diameter at breast height (DBH) over bark in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Pine_m2 (float): Basal area of Scots Pine on the plot in m².
            BA_Spruce_m2 (float): Basal area of Norway Spruce on the plot in m².
            BA_Birch_m2 (float): Basal area of Birch on the plot in m².
            BA_m2 (float): Total basal area on the plot in m².
            latitude (float): Latitude of the stand in decimal degrees.
            altitude (float): Altitude of the stand in meters.
            divided_plot (int, optional): 1 if the plot is divided, 0 otherwise. Defaults to 0.

        Returns:
            float: The calculated form factor.
        """
        BA_quotient_Pine = BA_Pine_m2 / BA_m2
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        BA_quotient_Birch = BA_Birch_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        close_to_coast = 1 if distance_to_coast_km < 50 else 0
        
        return math.exp(
            -0.20201E3 * (1 / (DBH_cm * 10 + 50)) +
            0.16550E4 * ((1 / (DBH_cm * 10 + 50)) ** 2) +
            0.39114E-2 * total_age -
            0.24311E-4 * (total_age ** 2) +
            0.10805E-2 * SI100_Pine * 10 +
            0.15779E-2 * altitude -
            0.26825E-4 * latitude * altitude -
            0.25400E0 * diameter_quotient +
            0.10089E0 * BA_quotient_Pine +
            0.27052E0 * BA_quotient_Spruce +
            0.64203E-1 * BA_quotient_Birch -
            0.53712E-1 * divided_plot -
            0.79867E-1 * close_to_coast +
            0.23991E1 +
            0.01156
        )

    @staticmethod
    def southern_pine(SI100_Pine, distance_to_coast_km, DBH_cm, DBH_largest_tree_on_plot_cm, total_age, BA_Pine_m2, 
                       BA_Spruce_m2, BA_Birch_m2, BA_m2, latitude, altitude, divided_plot=0, county=None):
        """
        Calculates the form factor for Scots Pine in Southern Sweden.

        Args:
            SI100_Pine (float): Site index for Scots Pine (SI100) in dm.
            distance_to_coast_km (float): Distance to the nearest coast in kilometers.
            DBH_cm (float): Diameter at breast height (DBH) over bark in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Pine_m2 (float): Basal area of Scots Pine on the plot in m².
            BA_Spruce_m2 (float): Basal area of Norway Spruce on the plot in m².
            BA_Birch_m2 (float): Basal area of Birch on the plot in m².
            BA_m2 (float): Total basal area on the plot in m².
            latitude (float): Latitude of the stand in decimal degrees.
            altitude (float): Altitude of the stand in meters.
            divided_plot (int, optional): 1 if the plot is divided, 0 otherwise. Defaults to 0.
            county (str, optional): County name for the stand.

        Returns:
            float: The calculated form factor.
        """
        BA_quotient_Pine = BA_Pine_m2 / BA_m2
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        BA_quotient_Birch = BA_Birch_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        close_to_coast = 1 if distance_to_coast_km < 50 else 0
        south_eastern_county = 1 if county in ["Stockholm", "Södermanland", "Uppsala", "Östergötland", "Kalmar", "Västmanland"] else 0

        return math.exp(
            -0.24722E3 * (1 / (DBH_cm * 10 + 50)) +
            0.96476E4 * ((1 / (DBH_cm * 10 + 50)) ** 2) +
            0.64050E-2 * total_age -
            0.33916E-4 * (total_age ** 2) +
            0.16113E-2 * SI100_Pine * 10 -
            0.57111E-2 * altitude +
            0.98668E-4 * latitude * altitude +
            0.17639E0 * diameter_quotient -
            0.30930E0 * (diameter_quotient ** 2) +
            0.18507E0 * BA_quotient_Pine +
            0.27249E0 * BA_quotient_Spruce +
            0.12120E0 * BA_quotient_Birch +
            0.21324E-1 * south_eastern_county -
            0.62357E-1 * divided_plot -
            0.19831E0 * close_to_coast +
            0.19624E1 +
            0.01080
        )

    @staticmethod
    def southern_oak(SI100_Pine, DBH_cm, DBH_largest_tree_on_plot_cm, total_age, BA_Spruce_m2, BA_m2, latitude, altitude, 
                     divided_plot=0, county=None):
        """
        Calculates the form factor for Oak in Southern Sweden using Söderberg's method.

        Args:
            SI100_Pine (float): Site index for Scots Pine (SI100) in dm.
            DBH_cm (float): Diameter at breast height (DBH) over bark in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Spruce_m2 (float): Basal area of Norway Spruce on the plot in m².
            BA_m2 (float): Total basal area on the plot in m².
            latitude (float): Latitude of the stand in decimal degrees.
            altitude (float): Altitude of the stand in meters.
            divided_plot (int, optional): 1 if the plot is divided, 0 otherwise. Defaults to 0.
            county (str, optional): County name for the stand.

        Returns:
            float: The calculated form factor for Oak in Southern Sweden.
        """
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        south_eastern_county = 1 if county in ["Stockholm", "Södermanland", "Uppsala", "Östergötland", "Kalmar", "Västmanland"] else 0
        region5 = 1 if county in ["Blekinge", "Kristianstad", "Malmöhus", "Västra Götaland", "Halland", "Gotland"] else 0

        return math.exp(
            -0.24454E3 * (1 / (DBH_cm * 10 + 50)) +
            0.77370E4 * ((1 / (DBH_cm * 10 + 50)) ** 2) +
            0.25633E-2 * total_age -
            0.16976E-4 * (total_age ** 2) +
            0.13153E-2 * SI100_Pine * 10 -
            0.56851E-5 * latitude * altitude -
            0.29397E0 * diameter_quotient +
            0.82213E-1 * BA_quotient_Spruce +
            0.26924E0 * south_eastern_county -
            0.65403E-2 * region5 -
            0.77845E-1 * divided_plot +
            0.25409E1 +
            0.01960
        )
    
    @staticmethod
    def southern_broadleaves(SI100_Pine, DBH_cm, DBH_largest_tree_on_plot_cm, total_age, BA_Pine_m2, BA_Spruce_m2, BA_Birch_m2, 
                             BA_m2, latitude, altitude, divided_plot=0):
        """
        Calculates the form factor for Broadleaves in Southern Sweden using Söderberg's method. 

        Args:
            SI100_Pine (float): Site index for Scots Pine (SI100) in dm.
            DBH_cm (float): Diameter at breast height (DBH) over bark in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Pine_m2 (float): Basal area of Scots Pine on the plot in m².
            BA_Spruce_m2 (float): Basal area of Norway Spruce on the plot in m².
            BA_Birch_m2 (float): Basal area of Birch on the plot in m².
            BA_m2 (float): Total basal area on the plot in m².
            latitude (float): Latitude of the stand in decimal degrees.
            altitude (float): Altitude of the stand in meters.
            divided_plot (int, optional): 1 if the plot is divided, 0 otherwise. Defaults to 0. 

        Returns:
            float: The calculated form factor for Broadleaves in Southern Sweden.
        """
        BA_quotient_Pine = BA_Pine_m2 / BA_m2
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        BA_quotient_Birch = BA_Birch_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm

        return math.exp(
            -0.15868E3 * (1 / (DBH_cm * 10 + 50)) +
            0.30541E4 * ((1 / (DBH_cm * 10 + 50)) ** 2) +
            0.45148E-2 * total_age -
            0.34685E-4 * (total_age ** 2) +
            0.83659E-3 * SI100_Pine * 10 -
            0.11257E-1 * altitude +
            0.19625E-3 * latitude * altitude -
            0.16890E0 * diameter_quotient -
            0.18665E0 * BA_quotient_Pine +
            0.93429E-1 * BA_quotient_Spruce -
            0.74098E-1 * BA_quotient_Birch -
            0.47553E-1 * divided_plot +
            0.22560E1 +
            ((0.200 ** 2) / 2)
        )

    @staticmethod
    def southern_birch(SI100_Pine, DBH_cm, DBH_largest_tree_on_plot_cm, total_age, BA_Pine_m2, BA_Spruce_m2, BA_Birch_m2, 
                        BA_m2, latitude, altitude, divided_plot=0, county=None):
        """
        Calculates the form factor for Birch in Southern Sweden using Söderberg's method.

        Args:
            SI100_Pine (float): Site index for Scots Pine (SI100) in dm.
            DBH_cm (float): Diameter at breast height (DBH) over bark in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Pine_m2 (float): Basal area of Scots Pine on the plot in m².
            BA_Spruce_m2 (float): Basal area of Norway Spruce on the plot in m².
            BA_Birch_m2 (float): Basal area of Birch on the plot in m².
            BA_m2 (float): Total basal area on the plot in m².
            latitude (float): Latitude of the stand in decimal degrees.
            altitude (float): Altitude of the stand in meters.
            divided_plot (int, optional): 1 if the plot is divided, 0 otherwise. Defaults to 0.
            county (str, optional): County name for the stand.

        Returns:
            float: The calculated form factor for Birch in Southern Sweden.
        """
        BA_quotient_Pine = BA_Pine_m2 / BA_m2
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        BA_quotient_Birch = BA_Birch_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        south_eastern_county = 1 if county in ["Stockholm", "Södermanland", "Uppsala", "Östergötland", "Kalmar", "Västmanland"] else 0

        return math.exp(
            -0.10414E3 * (1 / (DBH_cm * 10 + 50)) -
            0.26202E4 * ((1 / (DBH_cm * 10 + 50)) ** 2) +
            0.15775E-2 * total_age -
            0.10844E-4 * (total_age ** 2) +
            0.94915E-3 * SI100_Pine * 10 -
            0.10506E-1 * altitude +
            0.18430E-3 * latitude * altitude -
            0.32432E0 * diameter_quotient -
            0.49356E-1 * BA_quotient_Pine +
            0.12381E0 * BA_quotient_Spruce +
            0.11830E0 * BA_quotient_Birch +
            0.45225E-1 * south_eastern_county -
            0.68294E-1 * divided_plot +
            0.22298E1 +
            0.02000
        )


    @staticmethod
    def southern_beech(SI100_Pine, DBH_cm, DBH_largest_tree_on_plot_cm, total_age, BA_Spruce_m2, BA_m2, latitude, altitude, 
                        divided_plot=0, county=None):
        """
        Calculates the form factor for Beech in Southern Sweden using Söderberg's method.

        Args:
            SI100_Pine (float): Site index for Scots Pine (SI100) in dm.
            DBH_cm (float): Diameter at breast height (DBH) over bark in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Spruce_m2 (float): Basal area of Norway Spruce on the plot in m².
            BA_m2 (float): Total basal area on the plot in m².
            latitude (float): Latitude of the stand in decimal degrees.
            altitude (float): Altitude of the stand in meters.
            divided_plot (int, optional): 1 if the plot is divided, 0 otherwise. Defaults to 0.
            county (str, optional): County name for the stand.

        Returns:
            float: The calculated form factor for Beech in Southern Sweden.
        """
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        south_eastern_county = 1 if county in ["Stockholm", "Södermanland", "Uppsala", "Östergötland", "Kalmar", "Västmanland"] else 0
        region5 = 1 if county in ["Blekinge", "Kristianstad", "Malmöhus", "Västra Götaland", "Halland", "Gotland"] else 0

        return math.exp(
            -0.10532E3 * (1 / (DBH_cm * 10 + 50)) +
            0.65517E-2 * total_age -
            0.16776E-4 * (total_age ** 2) -
            0.52081E-3 * SI100_Pine * 10 -
            0.42320E-5 * latitude * altitude +
            0.14651E0 * diameter_quotient +
            0.20009E0 * BA_quotient_Spruce +
            0.19265E0 * south_eastern_county -
            0.16720E0 * region5 -
            0.17627E0 * divided_plot +
            0.20763E1 +
            0.01638
        )

    @staticmethod
    def northern_pine(SI100_Pine, distance_to_coast_km, DBH_cm, DBH_largest_tree_on_plot_cm, total_age, BA_Pine_m2, BA_m2, 
                       latitude, altitude, divided_plot=0):
        """
        Calculates the form factor for Scots Pine in Northern Sweden using Söderberg's method.

        Args:
            SI100_Pine (float): Site index for Scots Pine (SI100) in dm.
            distance_to_coast_km (float): Distance to the nearest coast in kilometers.
            DBH_cm (float): Diameter at breast height (DBH) over bark in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Pine_m2 (float): Basal area of Scots Pine on the plot in m².
            BA_m2 (float): Total basal area on the plot in m².
            latitude (float): Latitude of the stand in decimal degrees.
            altitude (float): Altitude of the stand in meters.
            divided_plot (int, optional): 1 if the plot is divided, 0 otherwise. Defaults to 0.

        Returns:
            float: The calculated form factor for Scots Pine in Northern Sweden.
        """
        BA_quotient_Pine = BA_Pine_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        close_to_coast = 1 if distance_to_coast_km < 50 else 0

        return math.exp(
            -0.24776E3 * (1 / (DBH_cm * 10 + 50)) +
            0.75785E4 * ((1 / (DBH_cm * 10 + 50)) ** 2) +
            0.52773E-2 * total_age -
            0.24395E-4 * (total_age ** 2) +
            0.10773E-2 * SI100_Pine * 10 -
            0.15516E-1 * latitude -
            0.43763E-5 * latitude * altitude -
            0.36728E0 * diameter_quotient +
            0.56762E-1 * (diameter_quotient ** 2) +
            0.74321E-1 * BA_quotient_Pine -
            0.52502E-1 * divided_plot -
            0.59471E-1 * close_to_coast +
            0.36491E1 +
            0.00832
        )

    @staticmethod
    def northern_central_spruce(SI100_Pine, distance_to_coast_km, DBH_cm, DBH_largest_tree_on_plot_cm, total_age, BA_Pine_m2, 
                                BA_Spruce_m2, BA_m2, latitude, altitude, divided_plot=0):
        """
        Calculates the form factor for Norway Spruce in Northern and Central Sweden using Söderberg's method.

        Args:
            SI100_Pine (float): Site index for Scots Pine (SI100) in dm.
            distance_to_coast_km (float): Distance to the nearest coast in kilometers.
            DBH_cm (float): Diameter at breast height (DBH) over bark in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Pine_m2 (float): Basal area of Scots Pine on the plot in m².
            BA_Spruce_m2 (float): Basal area of Norway Spruce on the plot in m².
            BA_m2 (float): Total basal area on the plot in m².
            latitude (float): Latitude of the stand in decimal degrees.
            altitude (float): Altitude of the stand in meters.
            divided_plot (int, optional): 1 if the plot is divided, 0 otherwise. Defaults to 0.

        Returns:
            float: The calculated form factor for Norway Spruce in Northern and Central Sweden.
        """
        BA_quotient_Pine = BA_Pine_m2 / BA_m2
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        close_to_coast = 1 if distance_to_coast_km < 50 else 0

        return math.exp(
            -0.21522E3 * (1 / (DBH_cm * 10 + 50)) +
            0.32488E4 * ((1 / (DBH_cm * 10 + 50)) ** 2) +
            0.40044E-2 * total_age -
            0.20320E-4 * (total_age ** 2) +
            0.11681E-2 * SI100_Pine * 10 -
            0.11238E-1 * latitude +
            0.57508E-3 * altitude -
            0.14149E-4 * latitude * altitude -
            0.21199E0 * diameter_quotient +
            0.58171E-1 * BA_quotient_Pine +
            0.10093E0 * BA_quotient_Spruce -
            0.35409E-1 * divided_plot -
            0.66759E-1 * close_to_coast +
            0.32511E1 +
            0.01140
        )

    @staticmethod
    def northern_central_broadleaves(SI100_Pine, distance_to_coast_km, DBH_cm, DBH_largest_tree_on_plot_cm, total_age, BA_Spruce_m2, 
                                     BA_Birch_m2, BA_m2, latitude, altitude, divided_plot=0):
        """
        Calculates the form factor for Broadleaves in Northern and Central Sweden using Söderberg's method.

        Args:
            SI100_Pine (float): Site index for Scots Pine (SI100) in dm.
            distance_to_coast_km (float): Distance to the nearest coast in kilometers.
            DBH_cm (float): Diameter at breast height (DBH) over bark in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Spruce_m2 (float): Basal area of Norway Spruce on the plot in m².
            BA_Birch_m2 (float): Basal area of Birch on the plot in m².
            BA_m2 (float): Total basal area on the plot in m².
            latitude (float): Latitude of the stand in decimal degrees.
            altitude (float): Altitude of the stand in meters.
            divided_plot (int, optional): 1 if the plot is divided, 0 otherwise. Defaults to 0.

        Returns:
            float: The calculated form factor for Broadleaves in Northern and Central Sweden.
        """
        BA_quotient_Birch = BA_Birch_m2 / BA_m2
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        close_to_coast = 1 if distance_to_coast_km < 50 else 0

        return math.exp(
            -0.12623E3 * (1 / (DBH_cm * 10 + 50)) +
            0.42804E-2 * total_age -
            0.25316E-4 * (total_age ** 2) +
            0.16703E-2 * SI100_Pine * 10 -
            0.32185E-1 * latitude -
            0.27431E-4 * altitude -
            0.85686E-1 * diameter_quotient +
            0.68224E-1 * BA_quotient_Spruce -
            0.51989E-1 * BA_quotient_Birch -
            0.77704E-1 * divided_plot +
            0.13794E0 * close_to_coast +
            0.39069E1 +
            ((0.188 ** 2) / 2)
        )

    @staticmethod
    def northern_central_birch(SI100_Pine, DBH_cm, DBH_largest_tree_on_plot_cm, total_age, BA_Pine_m2, BA_Spruce_m2, BA_m2, 
                                latitude, altitude, divided_plot=0):
        """
        Calculates the form factor for Birch in Northern and Central Sweden using Söderberg's method.

        Args:
            SI100_Pine (float): Site index for Scots Pine (SI100) in dm.
            DBH_cm (float): Diameter at breast height (DBH) over bark in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Pine_m2 (float): Basal area of Scots Pine on the plot in m².
            BA_Spruce_m2 (float): Basal area of Norway Spruce on the plot in m².
            BA_m2 (float): Total basal area on the plot in m².
            latitude (float): Latitude of the stand in decimal degrees.
            altitude (float): Altitude of the stand in meters.
            divided_plot (int, optional): 1 if the plot is divided, 0 otherwise. Defaults to 0.

        Returns:
            float: The calculated form factor for Birch in Northern and Central Sweden.
        """
        BA_quotient_Pine = BA_Pine_m2 / BA_m2
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm

        return math.exp(
            -0.23369E3 * (1 / (DBH_cm * 10 + 50)) +
            0.66940E4 * ((1 / (DBH_cm * 10 + 50)) ** 2) +
            0.32512E-2 * total_age -
            0.22072E-4 * (total_age ** 2) +
            0.86739E-3 * SI100_Pine * 10 -
            0.20822E-1 * latitude -
            0.74028E-5 * latitude * altitude -
            0.38620E0 * diameter_quotient +
            0.70742E-1 * (diameter_quotient ** 2) -
            0.82056E-1 * BA_quotient_Pine -
            0.21952E-1 * BA_quotient_Spruce -
            0.39112E-1 * divided_plot +
            0.41540E1 +
            0.01232
        )

    @staticmethod
    def central_pine(SI100_Pine, distance_to_coast_km, DBH_cm, DBH_largest_tree_on_plot_cm, total_age, BA_Pine_m2, BA_Spruce_m2, 
                     BA_Birch_m2, BA_m2, latitude, altitude, divided_plot=0):
        """
        Calculates the form factor for Scots Pine in Central Sweden using Söderberg's method.

        Args:
            SI100_Pine (float): Site index for Scots Pine (SI100) in dm.
            distance_to_coast_km (float): Distance to the nearest coast in kilometers.
            DBH_cm (float): Diameter at breast height (DBH) over bark in cm.
            DBH_largest_tree_on_plot_cm (float): DBH of the largest tree on the plot in cm.
            total_age (int): Total age of the stand.
            BA_Pine_m2 (float): Basal area of Scots Pine on the plot in m².
            BA_Spruce_m2 (float): Basal area of Norway Spruce on the plot in m².
            BA_Birch_m2 (float): Basal area of Birch on the plot in m².
            BA_m2 (float): Total basal area on the plot in m².
            latitude (float): Latitude of the stand in decimal degrees.
            altitude (float): Altitude of the stand in meters.
            divided_plot (int, optional): 1 if the plot is divided, 0 otherwise. Defaults to 0.

        Returns:
            float: The calculated form factor for Scots Pine in Central Sweden.
        """
        BA_quotient_Pine = BA_Pine_m2 / BA_m2
        BA_quotient_Spruce = BA_Spruce_m2 / BA_m2
        BA_quotient_Birch = BA_Birch_m2 / BA_m2
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        close_to_coast = 1 if distance_to_coast_km < 50 else 0

        return math.exp(
            -0.25627E3 * (1 / (DBH_cm * 10 + 50)) +
            0.77018E4 * ((1 / (DBH_cm * 10 + 50)) ** 2) +
            0.47410E-2 * total_age -
            0.21793E-4 * (total_age ** 2) +
            0.13003E-2 * SI100_Pine * 10 +
            0.81039E-1 * latitude +
            0.75022E-2 * altitude -
            0.12694E-3 * latitude * altitude -
            0.50469E0 * diameter_quotient +
            0.10610E0 * (diameter_quotient ** 2) +
            0.15691E0 * BA_quotient_Pine +
            0.17465E0 * BA_quotient_Spruce +
            0.17342E0 * BA_quotient_Birch -
            0.48782E-1 * divided_plot -
            0.83240E-1 * close_to_coast -
            0.23076E1 +
            0.00756
        )

