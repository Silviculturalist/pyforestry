import math


class SoderbergFormFactor:
    """
    Calculates the form factor for individual trees in Sweden based on models
    from Söderberg (1986).

    References:
        Söderberg, U. (1986). Funktioner för skogliga produktionsprognoser -
        Tillväxt och formhöjd för enskilda träd av inhemska trädslag i Sverige.
        Swedish University of Agricultural Sciences, Report 14.

    Methods:
        sweden_oak: Calculates the form factor for Oak in Sweden.
        sweden_beech: Calculates the form factor for Beech in Sweden.
        southern_sweden_spruce: Calculates the form factor for Spruce in Southern Sweden.
        southern_sweden_pine: Calculates the form factor for Pine in Southern Sweden.
        central_sweden_pine: Calculates the form factor for Pine in Central Sweden.
        northern_sweden_pine: Calculates the form factor for Pine in Northern Sweden.
        northern_central_sweden_spruce: Calculates the form factor for Spruce in Northern and Central Sweden.
        northern_central_sweden_broadleaves: Calculates the form factor for Broadleaves in Northern and Central Sweden.
        southern_sweden_broadleaves: Calculates the form factor for Broadleaves in Southern Sweden.
        southern_sweden_birch: Calculates the form factor for Birch in Southern Sweden.
    """

    @staticmethod
    def sweden_oak(DBH_cm, DBH_largest_tree_on_plot_cm, BA_Beech_m2_ha, BA_Birch_m2_ha, BA_m2_ha, 
                   SI_species, SI100, age, vegetation, soil_moisture, lateral_water, altitude, 
                   divided_plot=0, county=""):
        """
        Calculates the form factor for Oak in Sweden.

        Args:
            DBH_cm (float): Diameter at breast height of the tree in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            BA_Beech_m2_ha (float): Basal area of Beech on the plot in m²/ha.
            BA_Birch_m2_ha (float): Basal area of Birch on the plot in m²/ha.
            BA_m2_ha (float): Basal area of all tree species on the plot in m²/ha.
            SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
            SI100 (float): Site Index H100 in meters.
            age (float): Age at breast height of the tree.
            vegetation (int): Vegetation type according to the Swedish National Forest Inventory.
            soil_moisture (int): Soil moisture level (1-5).
            lateral_water (int): Lateral water availability (1-5).
            altitude (float): Altitude of the plot in meters.
            divided_plot (int): Indicator if the plot is divided into parts (1 for divided, 0 otherwise).
            county (str): County of the plot.

        Returns:
            float: Form factor of the tree.
        """
        spruce = 1 if SI_species == "Picea abies" else 0
        pine = 1 if SI_species == "Pinus sylvestris" else 0
        BA_quotient_Beech = BA_Beech_m2_ha / BA_m2_ha
        BA_quotient_Birch = BA_Birch_m2_ha / BA_m2_ha
        seldom_lateral_water = 1 if lateral_water in [1, 2] else 0
        herb = 1 if vegetation < 7 else 0
        region5 = 1 if county in [
            "Blekinge", "Kristianstad", "Malmöhus", "Västra Götaland", "Halland", "Gotland"
        ] else 0
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        moist = 1 if soil_moisture > 3 else 0

        return math.exp(
            -0.27070E+03 * (1 / ((DBH_cm * 10) + 50)) +  # Diameter in mm
            +0.11454E+05 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +  # Diameter in mm
            -0.16097E-02 * ((1 / (age + 10)) ** 2) +
            -0.17742E-01 * (DBH_cm * 10 / age) +  # Diameter in mm
            +0.39008E-03 * spruce * SI100 * 10 +  # m to dm
            +0.36858E-03 * pine * SI100 * 10 +  # m to dm
            +0.15098E-01 * BA_m2_ha +
            -0.14109E-03 * (BA_m2_ha ** 2) +
            +0.57341E+00 * diameter_quotient +
            -0.52971E+00 * (diameter_quotient ** 2) +
            -0.31421E-03 * altitude +
            -0.91133E-01 * BA_quotient_Birch +
            +0.21363E+00 * BA_quotient_Beech +
            -0.12131E+00 * divided_plot +
            +0.64025E-01 * herb +
            +0.12112E+00 * moist +
            -0.65506E-01 * seldom_lateral_water +
            -0.38960E-01 * region5 +
            +0.25636E+01
        )

    @staticmethod
    def sweden_beech(DBH_cm, BA_Beech_m2_ha, BA_Oak_m2_ha, BA_m2_ha, SI100_Spruce, age, aspect, altitude, divided_plot=0):
        """
        Calculates the form factor for Beech in Sweden.

        Args:
            DBH_cm (float): Diameter at breast height of the tree in cm.
            BA_Beech_m2_ha (float): Basal area of Beech on the plot in m²/ha.
            BA_Oak_m2_ha (float): Basal area of Oak on the plot in m²/ha.
            BA_m2_ha (float): Basal area of all tree species on the plot in m²/ha.
            SI100_Spruce (float): Site Index H100 for Norway Spruce in meters.
            age (float): Age at breast height of the tree.
            aspect (int): Aspect of the plot (1–8 for directions, 0 for flat terrain).
            altitude (float): Altitude of the plot in meters.
            divided_plot (int): Indicator if the plot is divided into parts (1 for divided, 0 otherwise).

        Returns:
            float: Form factor of the tree.
        """
        BA_quotient_Beech = BA_Beech_m2_ha / BA_m2_ha
        BA_quotient_Oak = BA_Oak_m2_ha / BA_m2_ha
        north = 1 if aspect in [8, 1, 2, 3] else 0

        return math.exp(
            -0.21212E+03 * (1 / ((DBH_cm * 10) + 50)) +  # Diameter in mm
            +0.73868E+04 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +  # Diameter in mm
            -0.16097E+02 * (1 / (age + 10)) +
            +0.27278E+03 * ((1 / (age + 10)) ** 2) +
            -0.30178E-01 * (DBH_cm * 10 / age) +  # Diameter in mm
            +0.21615E-03 * SI100_Spruce * 10 +  # m to dm
            +0.14469E-01 * BA_m2_ha +
            -0.13999E-03 * (BA_m2_ha ** 2) +
            -0.30893E-05 * (altitude ** 2) +
            +0.17708E+00 * BA_quotient_Beech +
            -0.14122E+00 * BA_quotient_Oak +
            -0.13570E+00 * divided_plot +
            -0.86474E-01 * north +
            +0.27313E+01
        )

    @staticmethod
    def southern_sweden_spruce(DBH_cm, DBH_largest_tree_on_plot_cm, continental, maritime, BA_Spruce_m2_ha, BA_m2_ha, 
                               SI_species, SI100, age, aspect, latitude, altitude, lateral_water, divided_plot=0, county=""):
        """
        Calculates the form factor for Spruce in Southern Sweden.

        Args:
            DBH_cm (float): Diameter at breast height of the tree in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            continental (bool): Whether the plot is in a continental climate region.
            maritime (bool): Whether the plot is in a maritime climate region.
            BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
            BA_m2_ha (float): Basal area of all tree species on the plot in m²/ha.
            SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
            SI100 (float): Site Index H100 in meters.
            age (float): Age at breast height of the tree.
            aspect (int): Aspect of the plot (1–8 for directions, 0 for flat terrain).
            latitude (float): Latitude of the plot in degrees.
            altitude (float): Altitude of the plot in meters.
            lateral_water (int): Lateral water availability (1–5).
            divided_plot (int): Indicator if the plot is divided into parts (1 for divided, 0 otherwise).
            county (str): County of the plot.

        Returns:
            float: Form factor of the tree.
        """
        spruce = 1 if SI_species == "Picea abies" else 0
        pine = 1 if SI_species == "Pinus sylvestris" else 0
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
        north = 1 if aspect in [8, 1, 2, 3] else 0
        seldom_lateral_water = 1 if lateral_water in [1, 2] else 0

        south_eastern_county = 1 if county in [
            "Stockholm", "Södermanland", "Uppsala", "Östergötland", "Kalmar", "Västmanland"
        ] else 0

        value_constant = 0.27730E+01 if county != "Gotland" else ((0.27730E+01) - 0.089)

        return math.exp(
            -0.25255E+03 * (1 / ((DBH_cm * 10) + 50)) +  # Diameter in mm
            +0.52037E+04 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +  # Diameter in mm
            -0.79332E+01 * (1 / (age + 10)) +
            +0.15360E+03 * ((1 / (age + 10)) ** 2) +
            -0.25202E-02 * age +
            -0.50822E-01 * (DBH_cm * 10 / age) +  # Diameter in mm
            +0.95744E-03 * spruce * SI100 * 10 +  # m to dm
            +0.11126E-02 * pine * SI100 * 10 +  # m to dm
            +0.86560E-02 * BA_m2_ha +
            -0.68753E-04 * (BA_m2_ha ** 2) +
            +0.52388E+00 * diameter_quotient +
            -0.44192E+00 * (diameter_quotient ** 2) +
            +0.33543E-03 * altitude +
            -0.11486E-05 * (altitude ** 2) +
            +0.14504E+00 * BA_quotient_Spruce +
            +0.21586E-01 * continental +
            -0.18175E-01 * maritime +
            +0.16159E-01 * north +
            -0.51101E-01 * divided_plot +
            -0.14608E-01 * seldom_lateral_water +
            +0.17760E-01 * south_eastern_county +
            +value_constant
        )

    @staticmethod
    def southern_sweden_pine(DBH_cm, DBH_largest_tree_on_plot_cm, distance_to_coast_km, BA_Spruce_m2_ha, BA_m2_ha, 
                             SI_species, SI100, vegetation, age, latitude, altitude, county, maritime, soil_moisture, 
                             divided_plot=0, fertilised_plot=0):
        """
        Calculates the form factor for Pine in Southern Sweden.

        Args:
            DBH_cm (float): Diameter at breast height of the tree in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            distance_to_coast_km (float): Distance to the coast in kilometers.
            BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
            BA_m2_ha (float): Basal area of all tree species on the plot in m²/ha.
            SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
            SI100 (float): Site Index H100 in meters.
            vegetation (int): Vegetation type according to the Swedish National Forest Inventory.
            age (float): Age at breast height of the tree.
            latitude (float): Latitude of the plot in degrees.
            altitude (float): Altitude of the plot in meters.
            county (str): County of the plot.
            maritime (bool): Whether the plot is in a maritime climate region.
            soil_moisture (int): Soil moisture level (1-5).
            divided_plot (int): Indicator if the plot is divided into parts (1 for divided, 0 otherwise).
            fertilised_plot (int): Indicator if the plot is fertilised (1 for fertilised, 0 otherwise).

        Returns:
            float: Form factor of the tree.
        """
        spruce = 1 if SI_species == "Picea abies" else 0
        pine = 1 if SI_species == "Pinus sylvestris" else 0
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
        empetrum_calluna = 1 if vegetation in [15, 16] else 0
        herb = 1 if vegetation < 7 else 0
        close_to_coast = 1 if distance_to_coast_km < 50 else 0
        moist = 1 if soil_moisture > 3 else 0
        region5 = 1 if county in [
            "Blekinge", "Kristianstad", "Malmöhus", "Västra Götaland", "Halland", "Gotland"
        ] else 0

        return math.exp(
            -0.24437E+03 * (1 / ((DBH_cm * 10) + 50)) +  # Diameter in mm
            +0.96502E+04 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +  # Diameter in mm
            -0.14142E+02 * (1 / (age + 10)) +
            +0.16515E+03 * ((1 / (age + 10)) ** 2) +
            -0.26773E-02 * age +
            -0.41275E-01 * (DBH_cm * 10 / age) +  # Diameter in mm
            +0.12858E-02 * spruce * SI100 * 10 +  # m to dm
            +0.16419E-02 * pine * SI100 * 10 +  # m to dm
            +0.92576E-02 * BA_m2_ha +
            -0.89234E-04 * (BA_m2_ha ** 2) +
            +0.24741E+00 * diameter_quotient +
            -0.22097E+00 * (diameter_quotient ** 2) +
            -0.88419E+00 * latitude +
            +0.76429E-02 * (latitude ** 2) +
            -0.45527E-04 * altitude +
            -0.64779E-01 * divided_plot +
            -0.20583E-01 * herb +
            +0.37361E-01 * fertilised_plot +
            -0.21721E-01 * maritime +
            -0.30357E-01 * empetrum_calluna +
            -0.40200E-01 * moist +
            +0.11526E+00 * BA_quotient_Spruce +
            -0.28372E-01 * region5 +
            +0.28245E+02
        )

    @staticmethod
    def northern_sweden_pine(DBH_cm, DBH_largest_tree_on_plot_cm, distance_to_coast_km, BA_Pine_m2_ha, BA_Spruce_m2_ha, 
                             BA_m2_ha, SI_species, SI100, vegetation, age, latitude, altitude, aspect, soil_moisture, 
                             divided_plot=0):
        """
        Calculates the form factor for Pine in Northern Sweden.

        Args:
            DBH_cm (float): Diameter at breast height of the tree in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            distance_to_coast_km (float): Distance to the coast in kilometers.
            BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
            BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
            BA_m2_ha (float): Basal area of all tree species on the plot in m²/ha.
            SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
            SI100 (float): Site Index H100 in meters.
            vegetation (int): Vegetation type according to the Swedish National Forest Inventory.
            age (float): Age at breast height of the tree.
            latitude (float): Latitude of the plot in degrees.
            altitude (float): Altitude of the plot in meters.
            aspect (int): Aspect of the plot (1–8 for directions, 0 for flat terrain).
            soil_moisture (int): Soil moisture level (1-5).
            divided_plot (int): Indicator if the plot is divided into parts (1 for divided, 0 otherwise).

        Returns:
            float: Form factor of the tree.
        """
        spruce = 1 if SI_species == "Picea abies" else 0
        pine = 1 if SI_species == "Pinus sylvestris" else 0
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
        empetrum_calluna = 1 if vegetation in [15, 16] else 0
        close_to_coast = 1 if distance_to_coast_km < 50 else 0
        south = 1 if aspect in [4, 5, 6, 7] else 0
        moist = 1 if soil_moisture > 3 else 0

        return math.exp(
            -0.22799E+03 * (1 / ((DBH_cm * 10) + 50)) +  # Diameter in mm
            +0.66896E+04 * ((1 / ((DBH_cm * 10)) + 50) ** 2) +  # Diameter in mm
            -0.11349E+02 * (1 / (age + 10)) +
            +0.17205E+03 * ((1 / (age + 10)) ** 2) +
            -0.16672E-02 * age +
            -0.58581E-01 * (DBH_cm * 10 / age) +  # Diameter in mm
            +0.11750E-02 * spruce * SI100 * 10 +  # m to dm
            +0.11099E-02 * pine * SI100 * 10 +  # m to dm
            +0.97338E-02 * BA_m2_ha +
            -0.92807E-04 * (BA_m2_ha ** 2) +
            -0.94134E-01 * diameter_quotient +
            +0.11760E-01 * (diameter_quotient ** 2) +
            +0.43779E+00 * latitude +
            -0.34411E-02 * (latitude ** 2) +
            -0.19820E-06 * (altitude ** 2) +
            -0.20823E-01 * close_to_coast +
            -0.44766E-01 * divided_plot +
            -0.19262E-01 * empetrum_calluna +
            +0.20471E-01 * south +
            -0.18321E-01 * moist +
            +0.88735E-01 * BA_quotient_Pine +
            +0.43954E-01 * BA_quotient_Spruce +
            -0.11064E+02
        )

    @staticmethod
    def northern_central_sweden_spruce(DBH_cm, DBH_largest_tree_on_plot_cm, distance_to_coast_km, continental, 
                                       BA_Spruce_m2_ha, BA_Pine_m2_ha, BA_m2_ha, SI_species, SI100, vegetation, 
                                       age, aspect, latitude, altitude, soil_moisture, lateral_water, divided_plot=0):
        """
        Calculates the form factor for Spruce in Northern and Central Sweden.

        Args:
            DBH_cm (float): Diameter at breast height of the tree in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            distance_to_coast_km (float): Distance to the coast in kilometers.
            continental (bool): Whether the plot is in a continental climate region.
            BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
            BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
            BA_m2_ha (float): Basal area of all tree species on the plot in m²/ha.
            SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
            SI100 (float): Site Index H100 in meters.
            vegetation (int): Vegetation type according to the Swedish National Forest Inventory.
            age (float): Age at breast height of the tree.
            aspect (int): Aspect of the plot (1–8 for directions, 0 for flat terrain).
            latitude (float): Latitude of the plot in degrees.
            altitude (float): Altitude of the plot in meters.
            soil_moisture (int): Soil moisture level (1-5).
            lateral_water (int): Lateral water availability (1-5).
            divided_plot (int): Indicator if the plot is divided into parts (1 for divided, 0 otherwise).

        Returns:
            float: Form factor of the tree.
        """
        spruce = 1 if SI_species == "Picea abies" else 0
        pine = 1 if SI_species == "Pinus sylvestris" else 0
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        north = 1 if aspect in [8, 1, 2, 3] else 0
        herb = 1 if vegetation < 7 else 0
        close_to_coast = 1 if distance_to_coast_km < 50 else 0
        dry = 1 if soil_moisture == 1 else 0
        moist = 1 if soil_moisture > 3 else 0
        seldom_lateral_water = 1 if lateral_water in [1, 2] else 0

        return math.exp(
            -0.22860E+03 * (1 / ((DBH_cm * 10) + 50)) +  # Diameter in mm
            +0.48767E+04 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +  # Diameter in mm
            -0.81995E+01 * (1 / (age + 10)) +
            +0.17613E+03 * ((1 / (age + 10)) ** 2) +
            -0.13356E-02 * age +
            -0.40996E-01 * (DBH_cm * 10 / age) +  # Diameter in mm
            +0.73529E-03 * spruce * SI100 * 10 +  # m to dm
            +0.55197E-03 * pine * SI100 * 10 +  # m to dm
            +0.11655E-01 * BA_m2_ha +
            -0.10073E-03 * (BA_m2_ha ** 2) +
            +0.43924E+00 * diameter_quotient +
            -0.36956E+00 * (diameter_quotient ** 2) +
            -0.10855E-01 * latitude +
            +0.10401E-03 * altitude +
            -0.63246E-06 * (altitude ** 2) +
            +0.88430E-01 * BA_quotient_Pine +
            +0.89763E-01 * BA_quotient_Spruce +
            -0.46335E-01 * close_to_coast +
            +0.11849E-01 * continental +
            +0.20148E-01 * north +
            -0.46182E-01 * divided_plot +
            -0.11448E-01 * herb +
            -0.32981E-01 * dry +
            -0.10124E-01 * moist +
            -0.11366E-01 * seldom_lateral_water +
            +0.33240E+01
        )

    @staticmethod
    def northern_central_sweden_broadleaves(DBH_cm, DBH_largest_tree_on_plot_cm, maritime, BA_Spruce_m2_ha, 
                                            BA_m2_ha, SI_species, SI100, age, latitude, altitude, lateral_water, 
                                            divided_plot=0):
        """
        Calculates the form factor for Broadleaves in Northern and Central Sweden.

        Args:
            DBH_cm (float): Diameter at breast height of the tree in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            maritime (bool): Whether the plot is in a maritime climate region.
            BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
            BA_m2_ha (float): Basal area of all tree species on the plot in m²/ha.
            SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
            SI100 (float): Site Index H100 in meters.
            age (float): Age at breast height of the tree.
            latitude (float): Latitude of the plot in degrees.
            altitude (float): Altitude of the plot in meters.
            lateral_water (int): Lateral water availability (1–5).
            divided_plot (int): Indicator if the plot is divided into parts (1 for divided, 0 otherwise).

        Returns:
            float: Form factor of the tree.
        """
        spruce = 1 if SI_species == "Picea abies" else 0
        pine = 1 if SI_species == "Pinus sylvestris" else 0
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
        seldom_lateral_water = 1 if lateral_water in [1, 2] else 0

        return math.exp(
            -0.75461E+02 * (1 / ((DBH_cm * 10) + 50)) +  # Diameter in mm
            -0.22422E+02 * (1 / (age + 10)) +
            +0.23326E+03 * ((1 / (age + 10)) ** 2) +
            -0.34112E-02 * age +
            +0.93785E-03 * spruce * SI100 * 10 +  # m to dm
            +0.12420E-02 * pine * SI100 * 10 +  # m to dm
            +0.18241E-01 * BA_m2_ha +
            -0.16138E-03 * (BA_m2_ha ** 2) +
            +0.77488E+00 * diameter_quotient +
            -0.44199E+00 * (diameter_quotient ** 2) +
            -0.13223E-01 * latitude +
            -0.21817E-03 * altitude +
            +0.10235E+00 * BA_quotient_Spruce +
            -0.52928E-01 * divided_plot +
            +0.90171E-01 * maritime +
            -0.83195E-01 * seldom_lateral_water +
            +0.26801E+01
        )

    @staticmethod
    def northern_central_sweden_birch(DBH_cm, DBH_largest_tree_on_plot_cm, BA_Spruce_m2_ha, BA_Pine_m2_ha, BA_m2_ha, 
                                      SI_species, SI100, vegetation, aspect, age, latitude, altitude, soil_moisture, 
                                      lateral_water, fertilised_plot, divided_plot=0):
        """
        Calculates the form factor for Birch in Northern and Central Sweden.

        Args:
            DBH_cm (float): Diameter at breast height of the tree in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
            BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
            BA_m2_ha (float): Basal area of all tree species on the plot in m²/ha.
            SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
            SI100 (float): Site Index H100 in meters.
            vegetation (int): Vegetation type according to the Swedish National Forest Inventory.
            aspect (int): Aspect of the plot (1–8 for directions, 0 for flat terrain).
            age (float): Age at breast height of the tree.
            latitude (float): Latitude of the plot in degrees.
            altitude (float): Altitude of the plot in meters.
            soil_moisture (int): Soil moisture level (1-5).
            lateral_water (int): Lateral water availability (1–5).
            fertilised_plot (int): Indicator if the plot is fertilised (1 for fertilised, 0 otherwise).
            divided_plot (int): Indicator if the plot is divided into parts (1 for divided, 0 otherwise).

        Returns:
            float: Form factor of the tree.
        """
        spruce = 1 if SI_species == "Picea abies" else 0
        pine = 1 if SI_species == "Pinus sylvestris" else 0
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        north = 1 if aspect in [8, 1, 2, 3] else 0
        empetrum_calluna = 1 if vegetation in [15, 16] else 0
        dry = 1 if soil_moisture == 1 else 0
        moist = 1 if soil_moisture > 3 else 0
        seldom_lateral_water = 1 if lateral_water in [1, 2] else 0

        return math.exp(
            -0.18780E+03 * (1 / ((DBH_cm * 10) + 50)) +  # Diameter in mm
            +0.41264E+04 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +  # Diameter in mm
            +0.49071E+01 * (1 / (age + 10)) +
            -0.38410E-01 * (DBH_cm * 10 / age) +  # Diameter in mm
            +0.73517E-03 * spruce * SI100 * 10 +  # m to dm
            +0.58577E-03 * pine * SI100 * 10 +  # m to dm
            +0.16827E-01 * BA_m2_ha +
            -0.17158E-03 * (BA_m2_ha ** 2) +
            -0.32079E-01 * diameter_quotient +
            -0.17386E-01 * latitude +
            -0.14858E-03 * altitude +
            -0.44756E-06 * (altitude ** 2) +
            -0.42524E-01 * BA_quotient_Pine +
            -0.60774E-01 * BA_quotient_Spruce +
            -0.54917E-01 * divided_plot +
            +0.65036E-01 * fertilised_plot +
            -0.62793E-01 * dry +
            -0.24338E-01 * moist +
            -0.17656E-01 * seldom_lateral_water +
            -0.95882E-01 * empetrum_calluna +
            +0.34916E+01
        )

    @staticmethod
    def gotland_sweden_pine(DBH_cm, DBH_largest_tree_on_plot_cm, BA_Pine_m2_ha, BA_m2_ha, SI100_Spruce, age, altitude, 
                            divided_plot=0):
        """
        Calculates the form factor for Pine in Gotland, Sweden.

        Args:
            DBH_cm (float): Diameter at breast height of the tree in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
            BA_m2_ha (float): Basal area of all tree species on the plot in m²/ha.
            SI100_Spruce (float): Site Index H100 in meters for Norway Spruce.
            age (float): Age at breast height of the tree.
            altitude (float): Altitude of the plot in meters.
            divided_plot (int): Indicator if the plot is divided into parts (1 for divided, 0 otherwise).

        Returns:
            float: Form factor of the tree.
        """
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha

        return math.exp(
            -0.21146E+03 * (1 / ((DBH_cm * 10) + 50)) +  # Diameter in mm
            +0.71765E+04 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +  # Diameter in mm
            -0.62341E+01 * (1 / (age + 10)) +
            +0.15382E+03 * ((1 / (age + 10)) ** 2) +
            +0.39119E-03 * SI100_Spruce * 10 +  # m to dm
            +0.14818E-01 * BA_m2_ha +
            -0.12168E-03 * (BA_m2_ha ** 2) +
            -0.19266E+00 * (diameter_quotient ** 2) +
            +0.14934E-02 * altitude +
            -0.13057E+00 * divided_plot +
            -0.14060E+00 * BA_quotient_Pine +
            +0.23998E+01
        )

    @staticmethod
    def central_sweden_pine(DBH_cm, DBH_largest_tree_on_plot_cm, distance_to_coast_km, BA_Pine_m2_ha, BA_m2_ha, 
                            SI_species, SI100, age, latitude, altitude, soil_moisture, fertilised_plot, divided_plot=0):
        """
        Calculates the form factor for Pine in Central Sweden.

        Args:
            DBH_cm (float): Diameter at breast height of the tree in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            distance_to_coast_km (float): Distance to the coast in kilometers.
            BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
            BA_m2_ha (float): Basal area of all tree species on the plot in m²/ha.
            SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
            SI100 (float): Site Index H100 in meters.
            age (float): Age at breast height of the tree.
            latitude (float): Latitude of the plot in degrees.
            altitude (float): Altitude of the plot in meters.
            soil_moisture (int): Soil moisture level (1-5).
            fertilised_plot (int): Indicator if the plot is fertilised (1 for fertilised, 0 otherwise).
            divided_plot (int): Indicator if the plot is divided into parts (1 for divided, 0 otherwise).

        Returns:
            float: Form factor of the tree.
        """
        spruce = 1 if SI_species == "Picea abies" else 0
        pine = 1 if SI_species == "Pinus sylvestris" else 0
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        close_to_coast = 1 if distance_to_coast_km < 50 else 0
        moist = 1 if soil_moisture > 3 else 0

        return math.exp(
            -0.23404E+03 * (1 / ((DBH_cm * 10) + 50)) +  # Diameter in mm
            +0.75190E+04 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +  # Diameter in mm
            -0.13151E+02 * (1 / (age + 10)) +
            +0.17182E+03 * ((1 / (age + 10)) ** 2) +
            -0.15626E-02 * age +
            -0.33891E-01 * (DBH_cm * 10 / age) +  # Diameter in mm
            +0.11113E-02 * spruce * SI100 * 10 +  # m to dm
            +0.11987E-02 * pine * SI100 * 10 +  # m to dm
            +0.10184E-01 * BA_m2_ha +
            -0.90301E-04 * (BA_m2_ha ** 2) +
            -0.18661E+00 * diameter_quotient +
            +0.48146E-01 * (diameter_quotient ** 2) +
            +0.35143E+01 * latitude +
            -0.28628E-01 * (latitude ** 2) +
            -0.33545E-06 * (altitude ** 2) +
            -0.45949E-01 * close_to_coast +
            -0.46950E-01 * divided_plot +
            +0.11568E-01 * fertilised_plot +
            -0.12351E-01 * moist +
            -0.16899E-01 * BA_quotient_Pine +
            -0.104909E+03
        )

    @staticmethod
    def southern_sweden_broadleaves(DBH_cm, DBH_largest_tree_on_plot_cm, BA_Spruce_m2_ha, BA_m2_ha, SI_species, SI100, 
                                    age, latitude, vegetation, soil_moisture, aspect, divided_plot=0):
        """
        Calculates the form factor for Broadleaves in Southern Sweden.

        Args:
            DBH_cm (float): Diameter at breast height of the tree in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            BA_Spruce_m2_ha (float): Basal area of Spruce on the plot in m²/ha.
            BA_m2_ha (float): Basal area of all tree species on the plot in m²/ha.
            SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
            SI100 (float): Site Index H100 in meters.
            age (float): Age at breast height of the tree.
            latitude (float): Latitude of the plot in degrees.
            vegetation (int): Vegetation type according to the Swedish National Forest Inventory.
            soil_moisture (int): Soil moisture level (1-5).
            aspect (int): Aspect of the plot (1–8 for directions, 0 for flat terrain).
            divided_plot (int): Indicator if the plot is divided into parts (1 for divided, 0 otherwise).

        Returns:
            float: Form factor of the tree.
        """
        spruce = 1 if SI_species == "Picea abies" else 0
        pine = 1 if SI_species == "Pinus sylvestris" else 0
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        BA_quotient_Spruce = BA_Spruce_m2_ha / BA_m2_ha
        south = 1 if aspect in [4, 5, 6, 7] else 0
        herb = 1 if vegetation < 7 else 0
        moist = 1 if soil_moisture > 3 else 0

        return math.exp(
            -0.14927E+03 * (1 / ((DBH_cm * 10) + 50)) +  # Diameter in mm
            +0.37752E+04 * ((1 / ((DBH_cm * 10) + 50)) ** 2) +  # Diameter in mm
            -0.25858E+02 * ((1 / (age + 10)) ** 2) +
            +0.10999E-02 * spruce * SI100 * 10 +  # m to dm
            +0.10513E-02 * pine * SI100 * 10 +  # m to dm
            +0.11070E-01 * BA_m2_ha +
            -0.10669E-03 * (BA_m2_ha ** 2) +
            +0.28134E+00 * diameter_quotient +
            -0.29273E+00 * (diameter_quotient ** 2) +
            +0.22956E-01 * latitude +
            +0.75214E-01 * BA_quotient_Spruce +
            -0.72064E-01 * divided_plot +
            +0.10339E+00 * south +
            -0.27334E-01 * herb +
            -0.44593E-01 * moist +
            +0.58178E+00
        )

    @staticmethod
    def southern_sweden_birch(DBH_cm, DBH_largest_tree_on_plot_cm, maritime, BA_Birch_m2_ha, BA_Pine_m2_ha, BA_m2_ha, 
                              SI_species, SI100, vegetation, age, latitude, altitude, soil_moisture, divided_plot=0, fertilised_plot=0,
                              county=None):
        """
        Calculates the form factor for Birch in Southern Sweden.

        Args:
            DBH_cm (float): Diameter at breast height of the tree in cm.
            DBH_largest_tree_on_plot_cm (float): Diameter of the largest tree on the plot in cm.
            maritime (bool): Whether the plot is in a maritime climate region.
            BA_Birch_m2_ha (float): Basal area of Birch on the plot in m²/ha.
            BA_Pine_m2_ha (float): Basal area of Pine on the plot in m²/ha.
            BA_m2_ha (float): Basal area of all tree species on the plot in m²/ha.
            SI_species (str): Species for which SIH100 was estimated ('Picea abies' or 'Pinus sylvestris').
            SI100 (float): Site Index H100 in meters.
            vegetation (int): Vegetation type according to the Swedish National Forest Inventory.
            age (float): Age at breast height of the tree.
            latitude (float): Latitude of the plot in degrees.
            altitude (float): Altitude of the plot in meters.
            soil_moisture (int): Soil moisture level (1-5).
            divided_plot (int): Indicator if the plot is divided into parts (1 for divided, 0 otherwise).
            fertilised_plot (int): Indicator if the plot is fertilised (1 for fertilised, 0 otherwise).
            county (str): Name of the county.

        Returns:
            float: Form factor of the tree.
        """
        spruce = 1 if SI_species == "Picea abies" else 0
        pine = 1 if SI_species == "Pinus sylvestris" else 0
        diameter_quotient = DBH_cm / DBH_largest_tree_on_plot_cm
        BA_quotient_Pine = BA_Pine_m2_ha / BA_m2_ha
        BA_quotient_Birch = BA_Birch_m2_ha / BA_m2_ha
        herb = 1 if vegetation < 7 else 0
        empetrum_calluna = 1 if vegetation in [15, 16] else 0
        dry = 1 if soil_moisture == 1 else 0
        region5 = 1 if county in ["Blekinge", "Kristianstad", "Malmöhus", "Västra Götaland", "Halland", "Gotland"] else 0

        value_constant = 0.12148E+01 if county != "Gotland" else ((0.12148E+01) - 0.067)

        return math.exp(
            -0.14327E+03 * (1 / ((DBH_cm * 10) + 50)) +  # Diameter in mm
            +0.39558E+02 * (1 / (age + 10)) +
            -0.17589E-02 * age +
            -0.34887E-01 * (DBH_cm * 10 / age) +  # Diameter in mm
            +0.45798E-03 * spruce * SI100 * 10 +  # m to dm
            +0.50812E-03 * pine * SI100 * 10 +  # m to dm
            +0.11981E-01 * BA_m2_ha +
            -0.13693E-03 * (BA_m2_ha ** 2) +
            +0.13814E+00 * diameter_quotient +
            -0.25030E+00 * (diameter_quotient ** 2) +
            +0.22195E-01 * latitude +
            -0.26037E-05 * latitude * altitude +
            -0.63942E-01 * BA_quotient_Pine +
            +0.40774E-01 * BA_quotient_Birch +
            -0.56749E-01 * maritime +
            -0.73603E-01 * divided_plot +
            +0.12825E-01 * herb +
            -0.57647E-01 * dry +
            -0.17425E+00 * empetrum_calluna +
            -0.40860E-01 * region5 +
            +0.56214E-01 * fertilised_plot +
            +value_constant
        )

