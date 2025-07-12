from typing import Optional
from pyforestry.timber import SweTimber

class NaslundVolume:
    @staticmethod
    def calculate(timber: SweTimber) -> float:
        timber.validate()
        if timber.region == "southern":
            if timber.species == "pinus sylvestris":
                return NaslundVolume._southern_pine_volume(timber)/1000
            elif timber.species == "picea abies":
                return NaslundVolume._southern_spruce_volume(timber)/1000
            elif timber.species in ["betula", "betula pendula", "betula pubescens"]:
                return NaslundVolume._southern_birch_volume(timber)/1000
        elif timber.region == "northern":
            if timber.species == "pinus sylvestris":
                return NaslundVolume._northern_pine_volume(timber)/1000
            elif timber.species == "picea abies":
                return NaslundVolume._northern_spruce_volume(timber)/1000
            elif timber.species in ["betula", "betula pendula", "betula pubescens"]:
                return NaslundVolume._northern_birch_volume(timber)/1000
        raise NotImplementedError(
            f"Volume calculation for {timber.species} in {timber.region} region is not implemented."
        )

    @staticmethod
    def _southern_pine_volume(timber: SweTimber) -> float:
        if timber.over_bark:
            if timber.crown_base_height_m and timber.double_bark_mm:
                return (
                    0.1193 * timber.diameter_cm**2
                    + 0.02574 * timber.height_m * timber.diameter_cm**2
                    + 0.007262 * timber.crown_base_height_m * timber.diameter_cm**2
                    + 0.004054 * timber.diameter_cm * timber.height_m**2
                    - 0.003112 * timber.diameter_cm * timber.height_m * timber.double_bark_mm
                )
            else:
                return (
                    0.1072 * timber.diameter_cm**2
                    + 0.02427 * timber.height_m * timber.diameter_cm**2
                    + 0.007315 * timber.diameter_cm * timber.height_m**2
                )
        else:
            if timber.crown_base_height_m and timber.double_bark_mm:
                return (
                    0.07141 * timber.diameter_cm**2
                    + 0.02580 * timber.height_m * timber.diameter_cm**2
                    + 0.009430 * timber.crown_base_height_m * timber.diameter_cm**2
                    + 0.003511 * timber.diameter_cm * timber.height_m**2
                    + 0.001052 * timber.diameter_cm * timber.height_m * timber.double_bark_mm
                )
            else:
                return (
                    0.06271 * timber.diameter_cm**2
                    + 0.03208 * timber.height_m * timber.diameter_cm**2
                    + 0.005725 * timber.diameter_cm * timber.height_m**2
                )

    @staticmethod
    def _southern_spruce_volume(timber: SweTimber) -> float:
        if timber.over_bark:
            if timber.crown_base_height_m:
                return (
                    0.1059 * timber.diameter_cm**2
                    + 0.01968 * timber.height_m * timber.diameter_cm**2
                    + 0.006168 * timber.crown_base_height_m * timber.diameter_cm**2
                    + 0.01468 * timber.diameter_cm * timber.height_m**2
                    - 0.04585 * timber.height_m**2
                )
            else:
                return (
                    0.1104 * timber.diameter_cm**2
                    + 0.01928 * timber.height_m * timber.diameter_cm**2
                    + 0.01815 * timber.diameter_cm * timber.height_m**2
                    - 0.04936 * timber.height_m**2
                )
        else:
            if timber.crown_base_height_m:
                return (
                    0.1039 * timber.diameter_cm**2
                    + 0.01959 * timber.height_m * timber.diameter_cm**2
                    + 0.005942 * timber.crown_base_height_m * timber.diameter_cm**2
                    + 0.01417 * timber.diameter_cm * timber.height_m**2
                    - 0.04332 * timber.height_m**2
                )
            else:
                return (
                    0.1076 * timber.diameter_cm**2
                    + 0.01929 * timber.height_m * timber.diameter_cm**2
                    + 0.01723 * timber.diameter_cm * timber.height_m**2
                    - 0.04615 * timber.height_m**2
                )

    @staticmethod
    def _southern_birch_volume(timber: SweTimber) -> float:
        if timber.over_bark:
            if timber.double_bark_mm:
                return (
                    0.09595 * timber.diameter_cm**2
                    + 0.02375 * timber.height_m * timber.diameter_cm**2
                    + 0.01221 * timber.diameter_cm * timber.height_m**2
                    - 0.03636 * timber.height_m**2
                    - 0.004605 * timber.diameter_cm * timber.height_m * timber.double_bark_mm
                )
            else:
                return (
                    0.1432 * timber.diameter_cm**2
                    + 0.008561 * timber.height_m * timber.diameter_cm**2
                    + 0.02180 * timber.diameter_cm * timber.height_m**2
                    - 0.06630 * timber.height_m**2
                )
        else:
            if timber.double_bark_mm:
                return (
                    0.08953 * timber.diameter_cm**2
                    + 0.02101 * timber.height_m * timber.diameter_cm**2
                    + 0.01171 * timber.diameter_cm * timber.height_m**2
                    - 0.03189 * timber.height_m**2
                    - 0.0007244 * timber.diameter_cm * timber.height_m * timber.double_bark_mm
                )
            else:
                return (
                    0.09944 * timber.diameter_cm**2
                    + 0.01862 * timber.height_m * timber.diameter_cm**2
                    + 0.01278 * timber.diameter_cm * timber.height_m**2
                    - 0.03544 * timber.height_m**2
                )

    @staticmethod
    def _northern_pine_volume(timber: SweTimber) -> float:
        if timber.over_bark:
            if timber.crown_base_height_m and timber.double_bark_mm:
                return (
                    0.1018 * timber.diameter_cm**2
                    + 0.03112 * timber.diameter_cm**2 * timber.height_m
                    + 0.007312 * timber.diameter_cm**2 * timber.crown_base_height_m
                    - 0.002906 * timber.diameter_cm * timber.height_m * timber.double_bark_mm
                )
            else:
                return (
                    0.09314 * timber.diameter_cm**2
                    + 0.03069 * timber.diameter_cm**2 * timber.height_m
                    + 0.002818 * timber.diameter_cm * timber.height_m**2
                )
        else:
            if timber.crown_base_height_m and timber.double_bark_mm:
                return (
                    0.06059 * timber.diameter_cm**2
                    + 0.03153 * timber.diameter_cm**2 * timber.height_m
                    + 0.007919 * timber.diameter_cm**2 * timber.crown_base_height_m
                    + 0.001773 * timber.diameter_cm * timber.height_m * timber.double_bark_mm
                )
            else:
                return (
                    0.05491 * timber.diameter_cm**2
                    + 0.03641 * timber.diameter_cm**2 * timber.height_m
                    + 0.002699 * timber.diameter_cm * timber.height_m**2
                )

    @staticmethod
    def _northern_spruce_volume(timber: SweTimber) -> float:
        if timber.over_bark:
            if timber.crown_base_height_m:
                return (
                    0.1102 * timber.diameter_cm**2
                    + 0.01648 * timber.diameter_cm**2 * timber.height_m
                    + 0.005901 * timber.diameter_cm**2 * timber.crown_base_height_m
                    + 0.01929 * timber.diameter_cm * timber.height_m**2
                    - 0.05565 * timber.height_m**2
                )
            else:
                return (
                    0.1202 * timber.diameter_cm**2
                    + 0.01504 * timber.diameter_cm**2 * timber.height_m
                    + 0.02341 * timber.diameter_cm * timber.height_m**2
                    - 0.06590 * timber.height_m**2
                )
        else:
            if timber.crown_base_height_m:
                return (
                    0.1057 * timber.diameter_cm**2
                    + 0.01658 * timber.diameter_cm**2 * timber.height_m
                    + 0.006267 * timber.diameter_cm**2 * timber.crown_base_height_m
                    + 0.01782 * timber.diameter_cm * timber.height_m**2
                    - 0.04681 * timber.height_m**2
                )
            else:
                return (
                    0.1153 * timber.diameter_cm**2
                    + 0.01522 * timber.diameter_cm**2 * timber.height_m
                    + 0.02170 * timber.diameter_cm * timber.height_m**2
                    - 0.05501 * timber.height_m**2
                )

    @staticmethod
    def _northern_birch_volume(timber: SweTimber) -> float:
        if timber.over_bark:
            if timber.crown_base_height_m and timber.double_bark_mm:
                return (
                    0.04192 * timber.diameter_cm**2
                    + 0.02927 * timber.diameter_cm**2 * timber.height_m
                    + 0.003263 * timber.diameter_cm**2 * timber.crown_base_height_m
                    + 0.003719 * timber.diameter_cm * timber.height_m**2
                    - 0.001692 * timber.diameter_cm * timber.height_m * timber.double_bark_mm
                )
            else:
                return (
                    0.03715 * timber.diameter_cm**2
                    + 0.02892 * timber.diameter_cm**2 * timber.height_m
                    + 0.004983 * timber.diameter_cm * timber.height_m**2
                )
        else:
            if timber.crown_base_height_m:
                return (
                    0.03328 * timber.diameter_cm**2
                    + 0.02876 * timber.diameter_cm**2 * timber.height_m
                    + 0.002991 * timber.diameter_cm**2 * timber.crown_base_height_m
                    + 0.003695 * timber.diameter_cm * timber.height_m**2
                )
            else:
                return (
                    0.02703 * timber.diameter_cm**2
                    + 0.03023 * timber.diameter_cm**2 * timber.height_m
                    + 0.004346 * timber.diameter_cm * timber.height_m**2
                )

class NaslundFormFactor:
    @staticmethod
    def calculate(
        species: str,
        height_m: float,
        diameter_cm: float,
        double_bark_mm: Optional[float] = None,
        crown_base_height_m: Optional[float] = None,
        over_bark: bool = True,
        region: str = "southern",
    ) -> float:
        if diameter_cm < 5:
            raise ValueError("Diameter must be larger than 5 cm.")

        species = species.lower()
        region = region.lower()

        if region not in ["northern", "southern"]:
            raise ValueError("Region must be 'northern' or 'southern'.")

        if species not in [
            "pinus sylvestris",
            "picea abies",
            "betula",
            "betula pendula",
            "betula pubescens",
        ]:
            raise ValueError(
                "Species must be one of: pinus sylvestris, picea abies, betula, betula pendula, betula pubescens."
            )

        if region == "southern":
            if species == "pinus sylvestris":
                return NaslundFormFactor._southern_pine_form_factor(
                    height_m, diameter_cm, double_bark_mm, crown_base_height_m, over_bark
                )
            elif species == "picea abies":
                return NaslundFormFactor._southern_spruce_form_factor(
                    height_m, diameter_cm, crown_base_height_m, over_bark
                )
            elif species in ["betula", "betula pendula", "betula pubescens"]:
                return NaslundFormFactor._southern_birch_form_factor(
                    height_m, diameter_cm, double_bark_mm, over_bark
                )
        elif region == "northern":
            if species == "pinus sylvestris":
                return NaslundFormFactor._northern_pine_form_factor(
                    height_m, diameter_cm, double_bark_mm, crown_base_height_m, over_bark
                )
            elif species == "picea abies":
                return NaslundFormFactor._northern_spruce_form_factor(
                    height_m, diameter_cm, crown_base_height_m, over_bark
                )
            elif species in ["betula", "betula pendula", "betula pubescens"]:
                return NaslundFormFactor._northern_birch_form_factor(
                    height_m, diameter_cm, double_bark_mm, crown_base_height_m, over_bark
                )

        raise NotImplementedError(
            f"Form factor calculation for {species} in {region} region is not implemented."
        )

    @staticmethod
    def _southern_pine_form_factor(
        height_m: float,
        diameter_cm: float,
        double_bark_mm: Optional[float],
        crown_base_height_m: Optional[float],
        over_bark: bool,
    ) -> float:
        if over_bark:
            if crown_base_height_m and double_bark_mm:
                K = ((height_m - crown_base_height_m) / height_m) * 100
                B = ((double_bark_mm / 10) / diameter_cm) * 100
                return (
                    420.16
                    + 1519.24 * (1 / height_m)
                    + 51.62 * (height_m / diameter_cm)
                    - 3.962 * B
                    - 0.9246 * K
                )/1000
            else:
                return (
                    308.97
                    + 1365.38 * (1 / height_m)
                    + 93.14 * (height_m / diameter_cm)
                )/1000
        else:
            if crown_base_height_m and double_bark_mm:
                K = ((height_m - crown_base_height_m) / height_m) * 100
                B = ((double_bark_mm / 10) / diameter_cm) * 100
                return (
                    448.53
                    + 909.21 * (1 / height_m)
                    + 44.71 * (height_m / diameter_cm)
                    + 1.339 * B
                    - 1.201 * K
                )/1000
            else:
                return (
                    408.49
                    + 798.46 * (1 / height_m)
                    + 72.89 * (height_m / diameter_cm)
                )/1000

    @staticmethod
    def _southern_spruce_form_factor(
        height_m: float,
        diameter_cm: float,
        crown_base_height_m: Optional[float],
        over_bark: bool,
    ) -> float:
        if over_bark:
            if crown_base_height_m:
                K = ((height_m - crown_base_height_m) / height_m) * 100
                return (
                    329.09
                    + 1348.92 * (1 / height_m)
                    + 186.94 * (height_m / diameter_cm)
                    - 583.74 * height_m / diameter_cm**2
                    - 0.7854 * K
                )/1000
            else:
                return (
                    245.09
                    + 1405.66 * (1 / height_m)
                    + 231.11 * (height_m / diameter_cm)
                    - 628.48 * height_m / diameter_cm**2
                )/1000
        else:
            if crown_base_height_m:
                K = ((height_m - crown_base_height_m) / height_m) * 100
                return (
                    325.04
                    + 1322.62 * (1 / height_m)
                    + 180.36 * (height_m / diameter_cm)
                    - 551.55 * height_m / diameter_cm**2
                    - 0.7566 * K
                )/1000
            else:
                return (
                    245.57
                    + 1369.89 * (1 / height_m)
                    + 219.34 * (height_m / diameter_cm)
                    - 587.65 * height_m / diameter_cm**2
                )/1000

    @staticmethod
    def _southern_birch_form_factor(
        height_m: float,
        diameter_cm: float,
        double_bark_mm: Optional[float],
        over_bark: bool,
    ) -> float:
        if over_bark:
            if double_bark_mm:
                B = ((double_bark_mm / 10) / diameter_cm) * 100
                return (
                    302.45
                    + 1221.63 * (1 / height_m)
                    + 155.44 * (height_m / diameter_cm)
                    - 462.95 * height_m / diameter_cm**2
                    - 5.864 * B
                )/1000
            else:
                return (
                    109.01
                    + 1823.03 * (1 / height_m)
                    + 277.56 * (height_m / diameter_cm)
                    - 844.17 * height_m / diameter_cm**2
                )/1000
        else:
            if double_bark_mm:
                B = ((double_bark_mm / 10) / diameter_cm) * 100
                return (
                    267.44
                    + 1139.98 * (1 / height_m)
                    + 149.04 * (height_m / diameter_cm)
                    - 406.04 * height_m / diameter_cm**2
                    - 0.9224 * B
                )/1000
            else:
                return (
                    237.03
                    + 1266.05 * (1 / height_m)
                    + 162.72 * (height_m / diameter_cm)
                    - 451.26 * height_m / diameter_cm**2
                )/1000

    @staticmethod
    def _northern_pine_form_factor(
        height_m: float,
        diameter_cm: float,
        double_bark_mm: Optional[float],
        crown_base_height_m: Optional[float],
        over_bark: bool,
    ) -> float:
        if over_bark:
            if crown_base_height_m and double_bark_mm:
                K = ((height_m - crown_base_height_m) / height_m) * 100
                B = ((double_bark_mm / 10) / diameter_cm) * 100
                return (
                    489.35
                    + 1296.11 * (1 / height_m)
                    - 3700 * B
                    - 0.9310 * K
                )/1000
            else:
                return (
                    390.81
                    + 1185.86 * (1 / height_m)
                    + 35.88 * (height_m / diameter_cm)
                )/1000
        else:
            if crown_base_height_m and double_bark_mm:
                K = ((height_m - crown_base_height_m) / height_m) * 100
                B = ((double_bark_mm / 10) / diameter_cm) * 100
                return (
                    502.22
                    + 771.5 * (1 / height_m)
                    + 2.257 * B
                    - 1.008 * K
                )/1000
            else:
                return (
                    463.55
                    + 699.14 * (1 / height_m)
                    + 34.36 * (height_m / diameter_cm)
                )/1000

    @staticmethod
    def _northern_spruce_form_factor(
        height_m: float,
        diameter_cm: float,
        crown_base_height_m: Optional[float],
        over_bark: bool,
    ) -> float:
        if over_bark:
            if crown_base_height_m:
                K = ((height_m - crown_base_height_m) / height_m) * 100
                return (
                    290.93
                    + 1346.06 * (1 / height_m)
                    + 226.83 * (height_m / diameter_cm)
                    - 595.98 * (height_m / diameter_cm**2)
                    - 0.7980 * K
                )/1000
            else:
                return (
                    193.84
                    + 1467.46 * (1 / height_m)
                    + 276.26 * (height_m / diameter_cm)
                    - 700.45 * (height_m / diameter_cm**2)
                )/1000
        else:
            if crown_base_height_m:
                K = ((height_m - crown_base_height_m) / height_m) * 100
                return (
                    306.60
                    + 1363.31 * (1 / height_m)
                    + 199.71 * (height_m / diameter_cm)
                    - 591.81 * (height_m / diameter_cm**2)
                    - 0.7403 * K
                )/1000
            else:
                return (
                    221.51
                    + 1431.21 * (1 / height_m)
                    + 244.14 * (height_m / diameter_cm)
                    - 652.09 * (height_m / diameter_cm**2)
                )/1000

    @staticmethod
    def _northern_birch_form_factor(
        height_m: float,
        diameter_cm: float,
        double_bark_mm: Optional[float],
        crown_base_height_m: Optional[float],
        over_bark: bool,
    ) -> float:
        if over_bark:
            if crown_base_height_m and double_bark_mm:
                K = ((height_m - crown_base_height_m) / height_m) * 100
                B = ((double_bark_mm / 10) / diameter_cm) * 100
                return (
                    414.20
                    + 533.74 * (1 / height_m)
                    + 47.35 * (height_m / diameter_cm)
                    - 2.154 * B
                    - 0.4154 * K
                )/1000
            else:
                return (
                    368.17
                    + 473 * (1 / height_m)
                    + 63.44 * (height_m / diameter_cm)
                )/1000
        else:
            if crown_base_height_m:
                K = ((height_m - crown_base_height_m) / height_m) * 100
                return (
                    404.30
                    + 423.71 * (1 / height_m)
                    + 47.05 * (height_m / diameter_cm)
                    - 0.3808 * K
                )/1000
            else:
                return (
                    384.88
                    + 344.14 * (1 / height_m)
                    + 55.34 * (height_m / diameter_cm)
                )/1000

