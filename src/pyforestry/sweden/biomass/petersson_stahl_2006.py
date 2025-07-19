import numpy as np


class PeterssonStahl2006:
    """Functions for below-ground biomass of birch, pine, and spruce in Sweden.

    This class implements a series of allometric functions to calculate the
    below-ground biomass (stump and roots) for several common tree species
    in Sweden: Betula (birch), Pinus sylvestris (Scots pine), and
    Picea abies (Norway spruce).

    The functions are based on the models developed by Petersson and Ståhl (2006).
    They allow for the estimation of biomass for roots with a diameter greater
    than or equal to 2 mm or 5 mm. For pine and spruce, more complex models
    are available that incorporate additional variables such as tree age,
    basal area, and soil conditions to improve accuracy.

    The primary method, `below_ground_biomass`, provides a unified interface
    to access the appropriate model based on the provided parameters.

    References:
        Petersson, H., & Ståhl, G. (2006). Functions for below-ground biomass of
        Pinus sylvestris, Picea abies, Betula pendula and Betula pubescens in Sweden.
        Scandinavian Journal of Forest Research, 21(sup7), 84-93.
        DOI: 10.1080/014004080500486864
    """

    # Birch functions
    @staticmethod
    def birch_root_5mm(diameter_mm):
        """Calculates ln(biomass) for birch roots >= 5 mm.

        Args:
            diameter_mm (float): Tree diameter at breast height (1.3 m) in millimeters.

        Returns:
            float: The natural logarithm of below-ground biomass in grams.
        """
        return 4.90864 + 9.91194 * (diameter_mm / (diameter_mm + 138))

    @staticmethod
    def birch_root_2mm(diameter_mm):
        """Calculates ln(biomass) for birch roots >= 2 mm.

        Args:
            diameter_mm (float): Tree diameter at breast height (1.3 m) in millimeters.

        Returns:
            float: The natural logarithm of below-ground biomass in grams.
        """
        return 6.17080 + 10.01111 * (diameter_mm / (diameter_mm + 225))

    # Pine functions
    @staticmethod
    def pine_root_5mm_1(diameter_mm):
        """Calculates ln(biomass) for pine roots >= 5 mm using only diameter.

        Args:
            diameter_mm (float): Tree diameter at breast height (1.3 m) in millimeters.

        Returns:
            float: The natural logarithm of below-ground biomass in grams.
        """
        return 3.39014 + 11.06822 * (diameter_mm / (diameter_mm + 113))

    @staticmethod
    def pine_root_5mm_2(diameter_mm, age_at_breast_height):
        """Calculates ln(biomass) for pine roots >= 5 mm using diameter and age.

        Args:
            diameter_mm (float): Tree diameter at breast height (1.3 m) in millimeters.
            age_at_breast_height (int): Tree age at breast height in years.

        Returns:
            float: The natural logarithm of below-ground biomass in grams.
        """
        return (
            3.57249
            + 11.07427 * (diameter_mm / (diameter_mm + 113))
            - 0.05119 * diameter_mm / age_at_breast_height
        )

    @staticmethod
    def pine_root_5mm_3(diameter_mm, age_basal_area_weighted, dry_soil):
        """Calculates ln(biomass) for pine roots >= 5 mm with detailed parameters.

        Args:
            diameter_mm (float): Tree diameter at breast height (1.3 m) in millimeters.
            age_basal_area_weighted (float): Basal area weighted mean age of the stand.
            dry_soil (int): Dummy variable for dry soil (1 if dry, 0 otherwise).

        Returns:
            float: The natural logarithm of below-ground biomass in grams.
        """
        return (
            3.50127
            + 10.96210 * (diameter_mm / (diameter_mm + 113))
            + 0.00250 * age_basal_area_weighted
            - 0.37595 * dry_soil
        )

    @staticmethod
    def pine_root_2mm_1(diameter_mm):
        """Calculates ln(biomass) for pine roots >= 2 mm using only diameter.

        Args:
            diameter_mm (float): Tree diameter at breast height (1.3 m) in millimeters.

        Returns:
            float: The natural logarithm of below-ground biomass in grams.
        """
        return 3.44275 + 11.06537 * (diameter_mm / (diameter_mm + 113))

    @staticmethod
    def pine_root_2mm_2(diameter_mm, age_at_breast_height):
        """Calculates ln(biomass) for pine roots >= 2 mm using diameter and age.

        Args:
            diameter_mm (float): Tree diameter at breast height (1.3 m) in millimeters.
            age_at_breast_height (int): Tree age at breast height in years.

        Returns:
            float: The natural logarithm of below-ground biomass in grams.
        """
        return (
            3.62193
            + 11.07117 * (diameter_mm / (diameter_mm + 113))
            - 0.05029 * diameter_mm / age_at_breast_height
        )

    @staticmethod
    def pine_root_2mm_3(diameter_mm, age_basal_area_weighted, dry_soil):
        """Calculates ln(biomass) for pine roots >= 2 mm with detailed parameters.

        Args:
            diameter_mm (float): Tree diameter at breast height (1.3 m) in millimeters.
            age_basal_area_weighted (float): Basal area weighted mean age of the stand.
            dry_soil (int): Dummy variable for dry soil (1 if dry, 0 otherwise).

        Returns:
            float: The natural logarithm of below-ground biomass in grams.
        """
        return (
            3.56553
            + 10.96370 * (diameter_mm / (diameter_mm + 113))
            + 0.00236 * age_basal_area_weighted
            - 0.38089 * dry_soil
        )

    # Spruce functions
    @staticmethod
    def spruce_root_5mm_1(diameter_mm):
        """Calculates ln(biomass) for spruce roots >= 5 mm using only diameter.

        Args:
            diameter_mm (float): Tree diameter at breast height (1.3 m) in millimeters.

        Returns:
            float: The natural logarithm of below-ground biomass in grams.
        """
        return 4.52965 + 10.57571 * (diameter_mm / (diameter_mm + 142))

    @staticmethod
    def spruce_root_5mm_2(diameter_mm, age_at_breast_height):
        """Calculates ln(biomass) for spruce roots >= 5 mm using diameter and age.

        Args:
            diameter_mm (float): Tree diameter at breast height (1.3 m) in millimeters.
            age_at_breast_height (int): Tree age at breast height in years.

        Returns:
            float: The natural logarithm of below-ground biomass in grams.
        """
        return (
            4.60559
            + 10.60542 * (diameter_mm / (diameter_mm + 142))
            - 0.02489 * diameter_mm / age_at_breast_height
        )

    @staticmethod
    def spruce_root_5mm_3(diameter_mm, age_at_breast_height, basal_area, crown_length, dry_soil):
        """Calculates ln(biomass) for spruce roots >= 5 mm with detailed parameters.

        Args:
            diameter_mm (float): Tree diameter at breast height (1.3 m) in millimeters.
            age_at_breast_height (int): Tree age at breast height in years.
            basal_area (float): Stand basal area in m^2/ha.
            crown_length (float): Length of the tree crown in meters.
            dry_soil (int): Dummy variable for dry soil (1 if dry, 0 otherwise).

        Returns:
            float: The natural logarithm of below-ground biomass in grams.
        """
        return (
            4.98414
            + 9.89245 * (diameter_mm / (diameter_mm + 142))
            - 0.03411 * diameter_mm / age_at_breast_height
            - 0.00769 * basal_area
            + 0.00317 * crown_length
            - 0.23375 * dry_soil
        )

    @staticmethod
    def spruce_root_2mm_1(diameter_mm):
        """Calculates ln(biomass) for spruce roots >= 2 mm using only diameter.

        Args:
            diameter_mm (float): Tree diameter at breast height (1.3 m) in millimeters.

        Returns:
            float: The natural logarithm of below-ground biomass in grams.
        """
        return 4.58761 + 10.44035 * (diameter_mm / (diameter_mm + 138))

    @staticmethod
    def spruce_root_2mm_2(diameter_mm, age_at_breast_height):
        """Calculates ln(biomass) for spruce roots >= 2 mm using diameter and age.

        Args:
            diameter_mm (float): Tree diameter at breast height (1.3 m) in millimeters.
            age_at_breast_height (int): Tree age at breast height in years.

        Returns:
            float: The natural logarithm of below-ground biomass in grams.
        """
        return (
            4.69287
            + 10.45700 * (diameter_mm / (diameter_mm + 138))
            - 0.03057 * diameter_mm / age_at_breast_height
        )

    @staticmethod
    def spruce_root_2mm_3(
        diameter_mm, age_basal_area_weighted, basal_area, crown_length, dry_soil
    ):
        """Calculates ln(biomass) for spruce roots >= 2 mm with detailed parameters.

        Args:
            diameter_mm (float): Tree diameter at breast height (1.3 m) in millimeters.
            age_basal_area_weighted (float): Basal area weighted mean age of the stand.
            basal_area (float): Stand basal area in m^2/ha.
            crown_length (float): Length of the tree crown in meters.
            dry_soil (int): Dummy variable for dry soil (1 if dry, 0 otherwise).

        Returns:
            float: The natural logarithm of below-ground biomass in grams.
        """
        return (
            5.00171
            + 9.89713 * (diameter_mm / (diameter_mm + 138))
            - 0.03653 * age_basal_area_weighted
            - 0.00636 * basal_area
            + 0.00261 * crown_length
            - 0.21705 * dry_soil
        )

    @staticmethod
    def below_ground_biomass(species, root_detail, **kwargs):
        """Selects and evaluates the appropriate below-ground biomass function.

        This method dynamically selects the correct biomass function based on the
        species and the desired root size detail. It attempts to find the most
        complex model that can be satisfied by the provided keyword arguments.

        For instance, if all arguments for a `_3` model (e.g., `pine_root_5mm_3`)
        are supplied, that model will be used. If not, it will fall back to the
        simpler `_2` or `_1` models.

        Note:
            Diameter must be provided as `diameter_cm` in centimeters. It will be
            automatically converted to millimeters for the calculations.

        Args:
            species (str): The tree species. Must be one of 'birch', 'pine', or 'spruce'.
            root_detail (int): The minimum root diameter to include. Must be 2 or 5 (mm).
            **kwargs: Keyword arguments required by the specific biomass functions.
                Common arguments include:
                - diameter_cm (float): Tree diameter at breast height in cm. (Required)
                - age_at_breast_height (int): Age at breast height.
                - age_basal_area_weighted (float): Basal area weighted stand age.
                - basal_area (float): Stand basal area in m^2/ha.
                - crown_length (float): Crown length in meters.
                - dry_soil (int): 1 if soil is dry, 0 otherwise.

        Returns:
            float: The calculated below-ground biomass in kilograms (kg).

        Raises:
            ValueError: If an invalid `species` or `root_detail` is given, or if
                the provided arguments do not match any available function for
                the selected species and root detail.
        """
        species_map = {
            "birch": {
                5: [PeterssonStahl2006.birch_root_5mm],
                2: [PeterssonStahl2006.birch_root_2mm],
            },
            "pine": {
                5: [
                    PeterssonStahl2006.pine_root_5mm_1,
                    PeterssonStahl2006.pine_root_5mm_2,
                    PeterssonStahl2006.pine_root_5mm_3,
                ],
                2: [
                    PeterssonStahl2006.pine_root_2mm_1,
                    PeterssonStahl2006.pine_root_2mm_2,
                    PeterssonStahl2006.pine_root_2mm_3,
                ],
            },
            "spruce": {
                5: [
                    PeterssonStahl2006.spruce_root_5mm_1,
                    PeterssonStahl2006.spruce_root_5mm_2,
                    PeterssonStahl2006.spruce_root_5mm_3,
                ],
                2: [
                    PeterssonStahl2006.spruce_root_2mm_1,
                    PeterssonStahl2006.spruce_root_2mm_2,
                    PeterssonStahl2006.spruce_root_2mm_3,
                ],
            },
        }

        if species not in species_map:
            raise ValueError(
                f"Invalid species '{species}'. Must be one of 'birch', 'pine', 'spruce'."
            )
        if root_detail not in species_map[species]:
            raise ValueError(f"Invalid root_detail '{root_detail}'. Must be 2 or 5.")

        functions = species_map[species][root_detail]
        diameter_mm = kwargs.get("diameter_cm", 0) * 10  # Convert cm to mm
        kwargs["diameter_mm"] = diameter_mm

        for func in functions:
            try:
                # Match arguments dynamically and evaluate the function
                func_args = func.__code__.co_varnames[: func.__code__.co_argcount]
                args = {key: value for key, value in kwargs.items() if key in func_args}
                return np.exp(func(**args)) / 1000  # return kg
            except TypeError:
                continue

        raise ValueError("No suitable function matched the provided arguments.")
