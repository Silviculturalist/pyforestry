import math

class SoderbergDoubleBarkMM:
    """
    Double bark thickness calculations for individual trees in Sweden based on Söderberg (1986).
    """

    @staticmethod
    def central_sweden_pine(DBH_u_b_cm, age, latitude, altitude, soil_moisture, distance_to_coast_km, SI100):
        """
        Double bark thickness for Pine in Central Sweden.

        Parameters:
            DBH_u_b_cm (float): Diameter under bark of the tree in centimeters.
            age (float): Age at breast height of the tree in years.
            latitude (float): Latitude of the tree's location in degrees.
            altitude (float): Altitude of the tree's location in meters.
            soil_moisture (int): Soil moisture level, on a scale from 1 (dry) to 5 (very moist).
            distance_to_coast_km (float): Distance to the nearest coast in kilometers.
            SI100 (float): Site Index H100, representing expected height in meters at age 100.

        Returns:
            float: Double bark thickness in millimeters.
        """
        far_from_coast = 1 if distance_to_coast_km > 50 else 0
        dry = 1 if soil_moisture == 1 else 0
        B1 = 1 if 14.1 <= SI100 <= 22.0 else 0
        B2 = 1 if SI100 >= 22.1 else 0

        return math.exp(
            +0.99156 * 10 ** -2 * (DBH_u_b_cm * 10) -
            0.13367 * 10 ** -4 * ((DBH_u_b_cm * 10) ** 2) +
            0.33766 * 10 ** -2 * age -
            0.13367 * 10 ** -4 * (age ** 2) -
            0.56911 * 10 ** -1 * latitude +
            0.15138 * 10 ** -2 * altitude -
            0.29419 * 10 ** -4 * latitude * altitude -
            0.23967 * 10 ** -1 * dry +
            0.11524 * far_from_coast -
            0.11249 * 10 ** -1 * B1 -
            0.55964 * 10 ** -1 * B2 +
            5.1825
        )

    @staticmethod
    def central_sweden_spruce(DBH_u_b_cm, age, soil_moisture, distance_to_coast_km, SI100):
        """
        Double bark thickness for Spruce in Central Sweden.

        Parameters:
            DBH_u_b_cm (float): Diameter under bark of the tree in centimeters.
            age (float): Age at breast height of the tree in years.
            soil_moisture (int): Soil moisture level, on a scale from 1 (dry) to 5 (very moist).
            distance_to_coast_km (float): Distance to the nearest coast in kilometers.
            SI100 (float): Site Index H100, representing expected height in meters at age 100.

        Returns:
            float: Double bark thickness in millimeters.


        """
        far_from_coast = 1 if distance_to_coast_km > 50 else 0
        dry = 1 if soil_moisture == 1 else 0

        return math.exp(
            +0.55670 * 10 ** -2 * (DBH_u_b_cm * 10) -
            0.52109 * 10 ** -5 * ((DBH_u_b_cm * 10) ** 2) +
            0.45036 * 10 ** -2 * age -
            0.58820 * 10 ** -5 * (age ** 2) -
            0.15400 * 10 ** -2 * (SI100 * 10) +
            0.88803 * 10 ** -1 * dry +
            0.96139 * 10 ** -1 * far_from_coast +
            1.73903
        )

    @staticmethod
    def northern_central_sweden_birch(DBH_u_b_cm, age, latitude, vegetation, soil_moisture, SI100):
        """
        Double bark thickness for Birch in Northern and Central Sweden.

        Parameters:
            DBH_u_b_cm (float): Diameter under bark of the tree in cm.
            age (float): Age at breast height of the tree.
            latitude (float): Latitude in degrees.
            vegetation (int): Vegetation code (1-18).
            soil_moisture (int): Soil moisture level (1-5).
            SI100 (float): Site Index H100, m.

        Returns:
            float: Double bark thickness in mm.
        """
        dry = 1 if soil_moisture == 1 else 0
        herb = 1 if vegetation < 7 else 0
        B1 = 1 if 14.1 <= SI100 <= 18.0 else 0
        B2 = 1 if SI100 >= 18.1 else 0

        return math.exp(
            +0.82582 * 10 ** -2 * (DBH_u_b_cm * 10) -
            0.75897 * 10 ** -5 * ((DBH_u_b_cm * 10) ** 2) +
            0.89957 * 10 ** -2 * age -
            0.22729 * 10 ** -4 * (age ** 2) -
            0.60489 * latitude +
            0.47242 * 10 ** -2 * (latitude ** 2) -
            0.42615 * 10 ** -1 * herb +
            0.24851 * dry -
            0.75997 * 10 ** -1 * B1 -
            0.13227 * B2 +
            20.421
        )

    @staticmethod
    def northern_central_sweden_broadleaves(DBH_u_b_cm, age, latitude, altitude, distance_to_coast_km, SI100):
        """
        Double bark thickness for Broadleaves in Northern and Central Sweden.

        Parameters:
            DBH_u_b_cm (float): Diameter under bark of the tree in cm.
            age (float): Age at breast height of the tree.
            latitude (float): Latitude in degrees.
            distance_to_coast_km (float): Distance to Swedish Coast in km. 
            SI100 (float): Site Index H100, m.

        Returns:
            float: Double bark thickness in mm.
        """
        far_from_coast = 1 if distance_to_coast_km > 50 else 0
        B2 = 1 if SI100 >= 22.1 else 0

        return math.exp(
            +0.59990 * 10 ** -2 * (DBH_u_b_cm * 10) +
            0.13983 * 10 ** -1 * age -
            0.38181 * 10 ** -4 * (age ** 2) +
            0.24932 * 10 ** -1 * latitude +
            0.24780 * 10 ** -2 * altitude -
            0.74190 * 10 ** -1 * (altitude ** 0.5) -
            0.18749 * far_from_coast +
            0.16729 * B2 +
            0.49494 * 10 ** -1
        )

    @staticmethod
    def northern_sweden_pine(DBH_u_b_cm, age, latitude, altitude, soil_moisture, distance_to_coast_km, vegetation, SI100):
        """
        Double bark thickness for Pine in Northern Sweden.

        Parameters:
            DBH_u_b_cm (float): Diameter under bark of the tree in cm.
            age (float): Age at breast height of the tree.
            latitude (float): Latitude in degrees.
            altitude (float): Meters above sea level
            soil_moisture (int): Soil moisture level (1-5).
            distance_to_coast_km (float): Distance to Swedish Coast in km. 
            vegetation (int): Vegetation code (1-18).
            SI100 (float): Site Index H100, m.

        Returns:
            float: Double bark thickness in mm.
        """
        far_from_coast = 1 if distance_to_coast_km > 50 else 0
        herb = 1 if vegetation < 7 else 0
        dry = 1 if soil_moisture == 1 else 0
        B1 = 1 if 14.1 <= SI100 <= 22.0 else 0
        B2 = 1 if SI100 >= 22.1 else 0

        return math.exp(
            +0.10562 * 10 ** -1 * (DBH_u_b_cm * 10) -
            0.13895 * 10 ** -4 * ((DBH_u_b_cm * 10) ** 2) +
            0.21565 * 10 ** -2 * age -
            0.54700 * 10 ** -5 * (age ** 2) -
            0.30599 * 10 ** -1 * latitude -
            0.57487 * 10 ** -3 * altitude +
            0.73755 * 10 ** -5 * latitude * altitude -
            0.47475 * 10 ** -1 * dry +
            0.61779 * 10 ** -1 * far_from_coast +
            0.59693 * 10 ** -1 * herb -
            0.44162 * 10 ** -1 * B1 -
            0.57575 * 10 ** -1 * B2 +
            3.48671
        )

    @staticmethod
    def northern_sweden_spruce(DBH_u_b_cm, age, latitude, soil_moisture, SI100):
        """
        Double bark thickness for Spruce in Northern Sweden.
        
        Parameters:
            DBH_u_b_cm (float): Diameter under bark of the tree in cm.
            age (float): Age at breast height of the tree.
            latitude (float): Latitude in degrees.
            soil_moisture (int): Soil moisture level (1-5).
            SI100 (float): Site Index H100, m.

        Returns:
            float: Double bark thickness in mm.
        """
        dry = 1 if soil_moisture == 1 else 0
        moist = 1 if soil_moisture > 3 else 0

        return math.exp(
            +0.55670 * 10 ** -2 * (DBH_u_b_cm * 10) -
            0.52109 * 10 ** -5 * ((DBH_u_b_cm * 10) ** 2) +
            0.45036 * 10 ** -2 * age -
            0.58820 * 10 ** -5 * (age ** 2) -
            0.15400 * 10 ** -2 * (SI100 * 10) -
            0.20080 * 10 ** -1 * latitude +
            0.11903 * moist +
            0.55123
        )

    @staticmethod
    def southern_sweden_birch(DBH_u_b_cm, age, latitude, altitude, vegetation, soil_moisture, SI100):
        """
        Double bark thickness for Birch in Southern Sweden.

        Parameters:
            DBH_u_b_cm (float): Diameter under bark of the tree in cm.
            age (float): Age at breast height of the tree.
            latitude (float): Latitude in degrees.
            altitude (float): Altitude in meters.
            vegetation (int): Vegetation type according to Swedish National Forest Inventory.
            soil_moisture (int): Soil moisture level (1-5).
            SI100 (float): Site Index H100, m.

        Returns:
            float: Double bark thickness in mm.
        """
        dry = 1 if soil_moisture == 1 else 0
        herb = 1 if vegetation < 7 else 0
        B2 = 1 if SI100 >= 18.1 else 0

        return math.exp(
            +0.10551 * 10 ** -1 * (DBH_u_b_cm * 10) -
            0.10367 * 10 ** -4 * ((DBH_u_b_cm * 10) ** 2) +
            0.35263 * 10 ** -2 * age +
            2.4541 * latitude -
            0.21789 * 10 ** -1 * (latitude ** 2) -
            0.15337 * 10 ** -1 * altitude +
            0.25626 * 10 ** -3 * latitude * altitude -
            0.13123 * herb +
            0.17776 * dry -
            0.57322 * 10 ** -1 * B2 -
            67.617
        )

    @staticmethod
    def southern_sweden_broadleaves(DBH_u_b_cm, age, latitude, soil_moisture, vegetation):
        """
        Double bark thickness for Broadleaves in Southern Sweden.

        Parameters:
            DBH_u_b_cm (float): Diameter under bark of the tree in cm.
            age (float): Age at breast height of the tree.
            latitude (float): Latitude in degrees.
            soil_moisture (int): Soil moisture level (1-5).
            vegetation (int): Vegetation type according to Swedish National Forest Inventory.

        Returns:
            float: Double bark thickness in mm.
        """
        herb = 1 if vegetation < 7 else 0
        moist = 1 if soil_moisture > 3 else 0

        return math.exp(
            +0.99684 * 10 ** -2 * (DBH_u_b_cm * 10) -
            0.13735 * 10 ** -4 * ((DBH_u_b_cm * 10) ** 2) +
            0.75334 * 10 ** -2 * age -
            0.32951 * 10 ** -4 * (age ** 2) +
            1.8722 * latitude -
            0.15950 * 10 ** -1 * (latitude ** 2) -
            0.91041 * 10 ** -1 * herb +
            0.29149 * moist -
            53.455
        )

    @staticmethod
    def sweden_beech(DBH_u_b_cm, age, latitude):
        """
        Double bark thickness for Beech in Sweden.

        Parameters:
            DBH_u_b_cm (float): Diameter under bark of the tree in cm.
            age (float): Age at breast height of the tree.
            latitude (float): Latitude in degrees.

        Returns:
            float: Double bark thickness in mm.
        """
        return math.exp(
            +0.56775 * 10 ** -2 * (DBH_u_b_cm * 10) -
            0.53487 * 10 ** -5 * ((DBH_u_b_cm * 10) ** 2) +
            0.36356 * 10 ** -2 * age +
            0.15406 * latitude -
            7.8258
        )

    @staticmethod
    def sweden_oak(DBH_u_b_cm, age, latitude):
        """
        Double bark thickness for Oak in Sweden.

        Parameters:
            DBH_u_b_cm (float): Diameter under bark of the tree in cm.
            age (float): Age at breast height of the tree.
            latitude (float): Latitude in degrees.

        Returns:
            float: Double bark thickness in mm.
        """
        return math.exp(
            +0.64773 * 10 ** -2 * (DBH_u_b_cm * 10) -
            0.63950 * 10 ** -5 * ((DBH_u_b_cm * 10) ** 2) +
            0.95725 * 10 ** -2 * age -
            0.54041 * 10 ** -4 * (age ** 2) +
            3.2234 * latitude -
            0.27582 * 10 ** -1 * (latitude ** 2) -
            92.368
        )

    @staticmethod
    def sweden_betula_pendula(DBH_u_b_cm, age, latitude, vegetation, soil_moisture, SI100, distance_to_coast_km):
        """
        Double bark thickness for Betula pendula in Sweden.

        Parameters:
            DBH_u_b_cm (float): Diameter under bark of the tree in cm.
            age (float): Age at breast height of the tree.
            latitude (float): Latitude in degrees.
            vegetation (int): Vegetation type according to Swedish National Forest Inventory.
            soil_moisture (int): Soil moisture level (1-5).
            SI100 (float): Site Index H100, m.
            distance_to_coast_km (float): Distance to the nearest coast in km.

        Returns:
            float: Double bark thickness in mm.
        """
        dry = 1 if soil_moisture == 1 else 0
        moist = 1 if soil_moisture > 3 else 0
        herb = 1 if vegetation < 7 else 0
        far_from_coast = 1 if distance_to_coast_km > 50 else 0
        B3 = 1 if SI100 >= 26.1 else 0

        return math.exp(
            +0.12948 * 10 ** -1 * (DBH_u_b_cm * 10) -
            0.15211 * 10 ** -4 * ((DBH_u_b_cm * 10) ** 2) +
            0.56088 * 10 ** -2 * age -
            0.17412 * 10 ** -4 * (age ** 2) -
            0.42668 * 10 ** -1 * latitude -
            0.10724 * herb +
            0.57244 * dry -
            0.43211 * moist +
            0.12738 * far_from_coast -
            0.88281 * 10 ** -1 * B3 +
            3.4646
        )

    @staticmethod
    def sweden_betula_pubescens(DBH_u_b_cm, age, latitude, vegetation, soil_moisture, SI100):
        """
        Double bark thickness for Betula pubescens in Sweden.

        Parameters:
            DBH_u_b_cm (float): Diameter under bark of the tree in cm.
            age (float): Age at breast height of the tree.
            latitude (float): Latitude in degrees.
            vegetation (int): Vegetation type according to Swedish National Forest Inventory.
            soil_moisture (int): Soil moisture level (1-5).
            SI100 (float): Site Index H100, m.
            distance_to_coast_km (float): Distance to the nearest coast in km.

        Returns:
            float: Double bark thickness in mm.
        """
        dry = 1 if soil_moisture == 1 else 0
        herb = 1 if vegetation < 7 else 0
        B1 = 1 if 14.1 <= SI100 <= 18.0 else 0
        B2 = 1 if SI100 >= 18.1 else 0

        return math.exp(
            +0.83895 * 10 ** -2 * (DBH_u_b_cm * 10) -
            0.92737 * 10 ** -5 * ((DBH_u_b_cm * 10) ** 2) +
            0.70117 * 10 ** -2 * age -
            0.10746 * 10 ** -4 * (age ** 2) -
            0.54713 * latitude +
            0.42428 * 10 ** -2 * (latitude ** 2) -
            0.52477 * 10 ** -1 * herb +
            0.24091 * dry -
            0.64082 * 10 ** -1 * B1 -
            0.12616 * B2 +
            18.769
        )

    @staticmethod
    def southern_sweden_spruce(DBH_u_b_cm, age, latitude, soil_moisture, SI100):
        """
        Double bark thickness for Spruce in Southern Sweden.

        Parameters:
            DBH_u_b_cm (float): Diameter under bark of the tree in cm.
            age (float): Age at breast height of the tree.
            latitude (float): Latitude in degrees.
            soil_moisture (int): Soil moisture level (1-5).
            SI100 (float): Site Index H100, m.

        Returns:
            float: Double bark thickness in mm.
        """
        moist = 1 if soil_moisture > 3 else 0

        return math.exp(
            +0.55670 * 10 ** -2 * (DBH_u_b_cm * 10) -
            0.52109 * 10 ** -5 * ((DBH_u_b_cm * 10) ** 2) +
            0.45036 * 10 ** -2 * age -
            0.58820 * 10 ** -5 * (age ** 2) -
            0.15400 * 10 ** -2 * (SI100 * 10) -
            0.20080 * 10 ** -1 * latitude +
            0.11903 * moist +
            0.76203
        )

    @staticmethod
    def southern_sweden_pine(DBH_u_b_cm, age, latitude, altitude, soil_moisture, vegetation, continental, SI100):
        """
        Double bark thickness for Pine in Southern Sweden.

        Parameters:
            DBH_u_b_cm (float): Diameter under bark of the tree in cm.
            age (float): Age at breast height of the tree.
            latitude (float): Latitude in degrees.
            altitude (float): Altitude in meters.
            soil_moisture (int): Soil moisture level (1-5).
            vegetation (int): Vegetation type according to Swedish National Forest Inventory.
            continental (bool): Whether the plot is situated in a continental climatic region.
            SI100 (float): Site Index H100, m.

        Returns:
            float: Double bark thickness in mm.
        """
        dry = 1 if soil_moisture == 1 else 0
        herb = 1 if vegetation < 7 else 0
        B1 = 1 if 14.1 <= SI100 <= 22.0 else 0
        B2 = 1 if SI100 >= 22.1 else 0

        return math.exp(
            +0.84207 * 10 ** -2 * (DBH_u_b_cm * 10) -
            0.10834 * 10 ** -4 * ((DBH_u_b_cm * 10) ** 2) +
            0.62648 * 10 ** -2 * age -
            0.25723 * 10 ** -4 * (age ** 2) +
            5.22630 * latitude -
            0.44767 * 10 ** -1 * (latitude ** 2) +
            0.21438 * 10 ** -1 * altitude -
            0.37426 * 10 ** -3 * latitude * altitude -
            0.20067 * 10 ** -1 * dry +
            0.15725 * 10 ** -1 * herb -
            0.30724 * 10 ** -1 * continental -
            0.37919 * 10 ** -1 * B1 -
            0.59201 * 10 ** -1 * B2 -
            150.42
        )
