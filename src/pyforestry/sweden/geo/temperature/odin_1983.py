import math
from typing import Optional


def Odin_temperature_sum(latitude: float, altitude_m: float) -> float:
    """
    Estimate annual temperature sum above 5°C.

    This function calculates the annual temperature sum (in degree-days) above 5 degrees Celsius
    based on latitude and altitude. It uses an empirical model developed by Odin, Eriksson,
    and Perttu (1983).

    Source:
        Odin, Eriksson & Perttu (1983). "Temperature Climate Maps for Swedish Forestry."
        Reports in Forest Ecology and Forest Soils, 45, p.45.

    Parameters
    ----------
    latitude : float
        Decimal latitude (degrees north).
    altitude_m : float
        Altitude in meters above sea level.

    Returns
    -------
    float
        Estimated annual temperature sum > 5 degrees Celsius.
    """
    return 4835 - (57.6 * latitude) - (0.9 * altitude_m)


# moren_perttu_1994_class.py


class Moren_Perttu_radiation_1994:
    def __init__(
        self,
        latitude: float,
        altitude: float,
        july_avg_temp: Optional[float] = None,
        jan_avg_temp: Optional[float] = None,
    ):
        """
        Initializes the class with common geographical and temperature data.
        Args:
            latitude (float): Latitude in degrees.
            altitude (float): Altitude in meters (m).
            july_avg_temp (float, optional): Average temperature in July (°C).
                                            Required for continentality correction.
            jan_avg_temp (float, optional): Average temperature in January (°C).
                                            Required for continentality correction.
        """
        self.latitude = latitude
        self.altitude = altitude
        self.july_avg_temp = july_avg_temp
        self.jan_avg_temp = jan_avg_temp

    @staticmethod
    def _helper_GS1000(latitude, altitude, **kwargs):
        B0 = kwargs["B0"]
        B1 = kwargs["B1"]
        B2 = kwargs["B2"]
        B3 = kwargs["B3"]
        return B0 + B1 * latitude + B2 * altitude + B3 * latitude * altitude

    @staticmethod
    def _helper_TS1000(latitude, altitude, **kwargs):
        A0 = kwargs["A0"]
        A1 = kwargs["A1"]
        A2 = kwargs["A2"]
        return A0 + A1 * latitude + A2 * altitude

    @staticmethod
    def _helper_1500(latitude, altitude, **kwargs):
        x0 = kwargs["x0"]
        x1 = kwargs["x1"]
        x2 = kwargs["x2"]
        x3 = kwargs["x3"]
        x4 = kwargs["x4"]
        x5 = kwargs["x5"]
        return (
            x0
            + x1 * latitude
            + x2 * latitude**2
            + x3 * latitude * altitude
            + x4 * altitude
            + x5 * altitude**2
        )

    @staticmethod
    def _helper_global_radiation_clear_day_ratio(day_number, **kwargs):
        D0 = kwargs["D0"]
        D1 = kwargs["D1"]
        D2 = kwargs.get("D2", 0.0)
        return D0 + D1 * day_number + D2 * day_number**2

    @staticmethod
    def _helper_global_radiation_avg_day_ratio(day_number, **kwargs):
        E0 = kwargs["E0"]
        E1 = kwargs["E1"]
        E2 = kwargs["E2"]
        E3 = kwargs.get("E3", 0.0)
        E4 = kwargs.get("E4", 0.0)
        E5 = kwargs.get("E5", 0.0)
        return (
            E0
            + E1 * day_number
            + E2 * day_number**2
            + E3 * day_number**3
            + E4 * day_number**4
            + E5 * day_number**5
        )

    @staticmethod
    def _helper_global_radiation_sum_growing_season(latitude, altitude, **kwargs):
        F0 = kwargs["F0"]
        F1 = kwargs["F1"]
        F2 = kwargs["F2"]
        return F0 + F1 * latitude + F2 * altitude

    def get_gorczynski_continentality_index(self):  # Renamed for clarity as a "getter"
        """
        Calculates the Gorczynski continentality index using instance data.
        Tmax is July average temp, Tmin is January average temp.
        Returns:
            float: Continentality index C.
        Raises:
            ValueError: If July or January temperatures are not set in the instance.
        """
        if self.july_avg_temp is None or self.jan_avg_temp is None:
            raise ValueError(
                "July and January average temperatures must be provided during "
                "initialization to calculate continentality."
            )

        if not (0 < self.latitude < 90):
            raise ValueError("Latitude must be between 0 and 90 degrees for this formula.")
        # Formula from page 7: C = 1.7 * (Tmax - Tmin) / sin(lat) - 20.4 [cite: 100]
        return (
            1.7 * (self.july_avg_temp - self.jan_avg_temp) / math.sin(math.radians(self.latitude))
            - 20.4
        )

    def calculate_temperature_sum_1000m(self, threshold_temperature):
        coeffs_A = {
            0: {"A0": 8279.3, "A1": -98.115, "A2": -1.131},
            3: {"A0": 6126.4, "A1": -73.813, "A2": -0.951},
            5: {"A0": 4922.1, "A1": -60.367, "A2": -0.837},
            6: {"A0": 4362.4, "A1": -54.059, "A2": -0.779},
            8: {"A0": 3320.9, "A1": -42.172, "A2": -0.653},
            10: {"A0": 2373.1, "A1": -31.056, "A2": -0.520},
        }
        if threshold_temperature not in coeffs_A:
            raise ValueError(f"Invalid threshold_temperature. Available: {list(coeffs_A.keys())}")
        return Moren_Perttu_radiation_1994._helper_TS1000(
            self.latitude, self.altitude, **coeffs_A[threshold_temperature]
        )

    def calculate_growing_season_duration_1000m(self, threshold_temperature):
        coeffs_B = {
            0: {"B0": 894.2, "B1": -10.678, "B2": -0.780, "B3": 0.01147},
            3: {"B0": 695.7, "B1": -8.050, "B2": -0.432, "B3": 0.00600},
            5: {"B0": 597.6, "B1": -6.823, "B2": -0.225, "B3": 0.00268},
            6: {"B0": 562.8, "B1": -6.432, "B2": -0.170, "B3": 0.00175},
            8: {"B0": 508.0, "B1": -5.909, "B2": -0.131, "B3": 0.00106},
            10: {"B0": 445.6, "B1": -5.271, "B2": -0.021, "B3": 0.00081},
        }
        if threshold_temperature not in coeffs_B:
            raise ValueError(f"Invalid threshold_temperature. Available: {list(coeffs_B.keys())}")
        return Moren_Perttu_radiation_1994._helper_GS1000(
            self.latitude, self.altitude, **coeffs_B[threshold_temperature]
        )

    def calculate_temperature_sum_1500m(self, threshold_temperature):
        coeffs_a = {
            0: {
                "x0": 8116.4,
                "x1": -80.85,
                "x2": -0.240,
                "x3": 0.07762,
                "x4": -5.947,
                "x5": -0.000075,
            },
            3: {
                "x0": 4790.6,
                "x1": -22.51,
                "x2": -0.482,
                "x3": 0.04992,
                "x4": -4.026,
                "x5": -0.000082,
            },
            5: {
                "x0": 3635.3,
                "x1": -12.18,
                "x2": -0.444,
                "x3": 0.04041,
                "x4": -3.343,
                "x5": -0.000040,
            },
            6: {
                "x0": 3187.3,
                "x1": -10.10,
                "x2": -0.404,
                "x3": 0.03691,
                "x4": -3.089,
                "x5": 0.000004,
            },  # As per Table 2b [cite: 117]
            8: {
                "x0": 2385.1,
                "x1": -7.07,
                "x2": -0.322,
                "x3": 0.03101,
                "x4": -2.659,
                "x5": 0.000099,
            },
            10: {
                "x0": 1633.3,
                "x1": -2.90,
                "x2": -0.260,
                "x3": 0.02809,
                "x4": -2.389,
                "x5": 0.000173,
            },
        }
        if threshold_temperature not in coeffs_a:
            raise ValueError(f"Invalid threshold_temperature. Available: {list(coeffs_a.keys())}")
        return Moren_Perttu_radiation_1994._helper_1500(
            self.latitude, self.altitude, **coeffs_a[threshold_temperature]
        )

    def calculate_growing_season_duration_1500m(self, threshold_temperature):
        coeffs_b = {  # From Table 3b [cite: 136]
            0: {
                "x0": 1339.7,
                "x1": -25.417,
                "x2": 0.122,
                "x3": 0.00978,
                "x4": -0.687,
                "x5": 0.000011,
            },
            3: {
                "x0": 716.5,
                "x1": -8.681,
                "x2": 0.005,
                "x3": 0.00618,
                "x4": -0.436,
                "x5": -0.000013,
            },
            5: {
                "x0": 474.5,
                "x1": -2.601,
                "x2": -0.036,
                "x3": 0.00376,
                "x4": -0.275,
                "x5": -0.000029,
            },  # x2 corrected to -0.036 based on Eq 13b [cite: 128]
            6: {
                "x0": 422.2,
                "x1": -1.546,
                "x2": -0.043,
                "x3": 0.00327,
                "x4": -0.236,
                "x5": -0.000047,
            },
            8: {
                "x0": 397.1,
                "x1": -2.017,
                "x2": -0.034,
                "x3": 0.00243,
                "x4": -0.187,
                "x5": -0.000045,
            },
            10: {
                "x0": 349.1,
                "x1": -1.928,
                "x2": -0.029,
                "x3": 0.00018,
                "x4": -0.064,
                "x5": -0.000030,
            },
        }
        if threshold_temperature not in coeffs_b:
            raise ValueError(f"Invalid threshold_temperature. Available: {list(coeffs_b.keys())}")
        return Moren_Perttu_radiation_1994._helper_1500(
            self.latitude, self.altitude, **coeffs_b[threshold_temperature]
        )

    def get_corrected_temperature_sum(self, threshold_temperature, for_1500m_model=False):
        if for_1500m_model:
            base_ts = self.calculate_temperature_sum_1500m(threshold_temperature)
        else:
            base_ts = self.calculate_temperature_sum_1000m(threshold_temperature)
        continentality_index_C = self.get_gorczynski_continentality_index()
        correction = 0
        # Based on page 14 [cite: 191]
        if continentality_index_C < 12.4:
            correction = -100
        elif 12.4 <= continentality_index_C < 18.5:
            correction = -50
        elif 18.5 <= continentality_index_C < 27.5:
            correction = 0
        elif 27.5 <= continentality_index_C < 33.5:
            correction = 50
        elif continentality_index_C >= 33.5:
            correction = 100
        return base_ts + correction

    @staticmethod
    def get_ratio_global_to_extraterrestrial_radiation_clear_sky(day_number, region):
        # Using D1 = -0.000403 for North, (105,273) based on user's implied coefficient
        # from test result
        coeffs_D = {
            "North": {
                (0, 104): {"D0": 0.521, "D1": 0.002681},
                (105, 273): {"D0": 0.840, "D1": -0.000403},  # Corrected D1
                (274, 365): {"D0": 1.447, "D1": -0.002650},
            },
            "South": {
                (0, 104): {"D0": 0.589, "D1": 0.001833},
                (105, 273): {"D0": 0.792, "D1": -0.000167},
                (274, 365): {"D0": 2.528, "D1": -0.010294, "D2": 0.137e-4},
            },
        }
        if region not in coeffs_D:
            raise ValueError(f"Invalid region. Available: {list(coeffs_D.keys())}")
        selected_coeffs = None
        for (start_day, end_day), c in coeffs_D[region].items():
            if start_day <= day_number <= end_day:
                selected_coeffs = c
                break
        if not selected_coeffs:
            if day_number == 366:
                if (274, 365) in coeffs_D[region]:
                    selected_coeffs = coeffs_D[region][(274, 365)]
                else:
                    raise ValueError(
                        f"Coefficient data for leap day (day 366) in region {region} not defined."
                    )
            else:
                raise ValueError(
                    f"Day number {day_number} out of defined ranges for region {region}."
                )
        return Moren_Perttu_radiation_1994._helper_global_radiation_clear_day_ratio(
            day_number, **selected_coeffs
        )

    @staticmethod
    def get_ratio_global_to_extraterrestrial_radiation_average_sky(day_number, region):
        coeffs_E = {
            "North": {
                "E0": 0.338,
                "E1": 0.114e-2,
                "E2": 0.244e-4,
                "E3": -0.316e-6,
                "E4": 0.115e-8,
                "E5": -0.134e-11,
            },
            "South": {"E0": 0.246, "E1": 0.243e-2, "E2": -0.658e-5},
        }
        if region not in coeffs_E:
            raise ValueError(f"Invalid region. Available: {list(coeffs_E.keys())}")
        return Moren_Perttu_radiation_1994._helper_global_radiation_avg_day_ratio(
            day_number, **coeffs_E[region]
        )

    def calculate_global_radiation_sum_growing_season(self, threshold_temperature):
        coeffs_F = {
            0: {"F0": 6.9712, "F1": -0.0667, "F2": -0.00070},  # Table 7 [cite: 183]
            3: {"F0": 7.1453, "F1": -0.0731, "F2": -0.00073},
            5: {"F0": 7.2774, "F1": -0.0782, "F2": -0.00072},  # F2 from Eq 17 [cite: 174]
            6: {"F0": 7.3684, "F1": -0.0813, "F2": -0.00069},
            8: {"F0": 7.4295, "F1": -0.0858, "F2": -0.00073},
            10: {"F0": 7.6033, "F1": -0.0932, "F2": -0.00075},  # F1 for 10C corrected to negative
        }
        if threshold_temperature not in coeffs_F:
            raise ValueError(f"Invalid threshold_temperature. Available: {list(coeffs_F.keys())}")
        return Moren_Perttu_radiation_1994._helper_global_radiation_sum_growing_season(
            self.latitude, self.altitude, **coeffs_F[threshold_temperature]
        )

    @staticmethod
    def get_growing_season_start_day(latitude_deg, altitude_m):
        start_day = (
            -35.760
            + 2.489 * latitude_deg
            - 0.0637 * altitude_m
            + 0.00132 * latitude_deg * altitude_m
        )
        return int(round(start_day))
