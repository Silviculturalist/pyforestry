import numpy as np

class PeterssonStahl2006:
    """
    Functions for below-ground biomass calculation for Birch, Pine, and Spruce based on
    Petersson, H., & Ståhl, G. (2006). Scandinavian Journal of Forest Research.
    """

    # Birch functions
    @staticmethod
    def birch_root_5mm(diameter_mm):
        return 4.90864 + 9.91194 * (diameter_mm / (diameter_mm + 138))

    @staticmethod
    def birch_root_2mm(diameter_mm):
        return 6.17080 + 10.01111 * (diameter_mm / (diameter_mm + 225))

    # Pine functions
    @staticmethod
    def pine_root_5mm_1(diameter_mm):
        return 3.39014 + 11.06822 * (diameter_mm / (diameter_mm + 113))

    @staticmethod
    def pine_root_5mm_2(diameter_mm, age_at_breast_height):
        return 3.57249 + 11.07427 * (diameter_mm / (diameter_mm + 113)) - 0.05119 * diameter_mm / age_at_breast_height

    @staticmethod
    def pine_root_5mm_3(diameter_mm, age_basal_area_weighted, dry_soil):
        return 3.50127 + 10.96210 * (diameter_mm / (diameter_mm + 113)) + 0.00250 * age_basal_area_weighted - 0.37595 * dry_soil

    @staticmethod
    def pine_root_2mm_1(diameter_mm):
        return 3.44275 + 11.06537 * (diameter_mm / (diameter_mm + 113))

    @staticmethod
    def pine_root_2mm_2(diameter_mm, age_at_breast_height):
        return 3.62193 + 11.07117 * (diameter_mm / (diameter_mm + 113)) - 0.05029 * diameter_mm / age_at_breast_height

    @staticmethod
    def pine_root_2mm_3(diameter_mm, age_basal_area_weighted, dry_soil):
        return 3.56553 + 10.96370 * (diameter_mm / (diameter_mm + 113)) + 0.00236 * age_basal_area_weighted - 0.38089 * dry_soil

    # Spruce functions
    @staticmethod
    def spruce_root_5mm_1(diameter_mm):
        return 4.52965 + 10.57571 * (diameter_mm / (diameter_mm + 142))

    @staticmethod
    def spruce_root_5mm_2(diameter_mm, age_at_breast_height):
        return 4.60559 + 10.60542 * (diameter_mm / (diameter_mm + 142)) - 0.02489 * diameter_mm / age_at_breast_height

    @staticmethod
    def spruce_root_5mm_3(diameter_mm, age_at_breast_height, basal_area, crown_length, dry_soil):
        return (
            4.98414 + 9.89245 * (diameter_mm / (diameter_mm + 142))
            - 0.03411 * diameter_mm / age_at_breast_height
            - 0.00769 * basal_area
            + 0.00317 * crown_length
            - 0.23375 * dry_soil
        )

    @staticmethod
    def spruce_root_2mm_1(diameter_mm):
        return 4.58761 + 10.44035 * (diameter_mm / (diameter_mm + 138))

    @staticmethod
    def spruce_root_2mm_2(diameter_mm, age_at_breast_height):
        return 4.69287 + 10.45700 * (diameter_mm / (diameter_mm + 138)) - 0.03057 * diameter_mm / age_at_breast_height

    @staticmethod
    def spruce_root_2mm_3(diameter_mm, age_basal_area_weighted, basal_area, crown_length, dry_soil):
        return (
            5.00171 + 9.89713 * (diameter_mm / (diameter_mm + 138))
            - 0.03653 * age_basal_area_weighted
            - 0.00636 * basal_area
            + 0.00261 * crown_length
            - 0.21705 * dry_soil
        )

    @staticmethod
    def below_ground_biomass(species, root_detail, **kwargs):
        """
        Dynamically selects and evaluates the appropriate below-ground biomass function.

        :param species: 'birch', 'pine', or 'spruce'.
        :param root_detail: Resolution of smallest included roots (2 or 5 mm).
        :param kwargs: Additional arguments required by specific functions.
        :return: Below-ground biomass (g).
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
            raise ValueError(f"Invalid species '{species}'. Must be one of 'birch', 'pine', 'spruce'.")
        if root_detail not in species_map[species]:
            raise ValueError(f"Invalid root_detail '{root_detail}'. Must be 2 or 5.")

        functions = species_map[species][root_detail]
        diameter_mm = kwargs.get("diameter_cm", 0) * 10  # Convert cm to mm
        kwargs["diameter_mm"] = diameter_mm

        for func in functions:
            try:
                # Match arguments dynamically and evaluate the function
                func_args = func.__code__.co_varnames[:func.__code__.co_argcount]
                args = {key: value for key, value in kwargs.items() if key in func_args}
                return np.exp(func(**args))/1000 # return kg
            except TypeError:
                continue

        raise ValueError("No suitable function matched the provided arguments.")

# Inputs
#diameter_cm = 30
#height_m = 15
#crown_base_height_m = 5
#age_at_breast_height = 50
#height_basal_area_weighted = 12
#age_basal_area_weighted = 60
#basal_area = 25
#altitude = 200
#dry_soil = 1
#root_detail = 5
#
## Birch example
#birch_biomass = PeterssonStahl2006.below_ground_biomass(
#    species="birch", root_detail=5, diameter_cm=diameter_cm
#)
#print(f"Birch below-ground biomass: {birch_biomass:.2f} g")
#
## Pine example
#pine_biomass = PeterssonStahl2006.below_ground_biomass(
#    species="pine",
#    root_detail=5,
#    diameter_cm=diameter_cm,
#    age_at_breast_height=age_at_breast_height,
#    age_basal_area_weighted=age_basal_area_weighted,
#    dry_soil=dry_soil,
#)
#print(f"Pine below-ground biomass: {pine_biomass:.2f} g")
#
## Spruce example
#spruce_biomass = PeterssonStahl2006.below_ground_biomass(
#    species="spruce",
#    root_detail=5,
#    diameter_cm=diameter_cm,
#    age_at_breast_height=age_at_breast_height,
#    basal_area=basal_area,
#    crown_length=(height_m * 10 - crown_base_height_m * 10),
#    dry_soil=dry_soil,
#)
#print(f"Spruce below-ground biomass: {spruce_biomass:.2f} kg")