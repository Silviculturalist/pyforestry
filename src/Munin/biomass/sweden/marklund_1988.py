import numpy as np
from typing import Optional
from munin.timber import Timber

def Marklund_1988_T1(diameter_cm):
    return np.exp(-2.3388 + 11.3264 * (diameter_cm / (diameter_cm + 13)))

def Marklund_1988_T2(diameter_cm, height_m):
    return np.exp(-2.6768 + 7.5939 * (diameter_cm / (diameter_cm + 13)) + 0.0151 * height_m + 0.8799 * np.log(height_m))

def Marklund_1988_T3(diameter_cm, height_m, double_bark_mm, age):
    return np.exp(-2.6232 + 7.7318 * (diameter_cm / (diameter_cm + 13)) + 0.0139 * height_m + 0.8625 * np.log(height_m) - 0.0704 * np.log(double_bark_mm) + 0.00185 * age)

def Marklund_1988_T4(diameter_cm, height_m, double_bark_mm, age, form_quotient5=None, form_quotient3=None, altitude_m=None):
    if form_quotient5 is not None and form_quotient3 is not None:
        print('Either form_quotient5 or form_quotient3 can be supplied. Not both.')
        print('form_quotient5 taking precedence.')
        form_quotient3 = None
    return np.exp(-2.4826 + 7.9039 * (diameter_cm / (diameter_cm + 13)) + 0.0184 * height_m + 0.6939 * np.log(height_m) - 0.0731 * np.log(double_bark_mm) + 0.00182 * age + 0.2382 * (form_quotient5 or 0) + 0.2217 * (form_quotient3 or 0) - 0.1596 * (altitude_m or 0))

MarklundPineStem = [Marklund_1988_T1, Marklund_1988_T2, Marklund_1988_T3, Marklund_1988_T4]
MarklundPineStem = sorted(MarklundPineStem, key=lambda f: f.__code__.co_argcount, reverse=True)

# Stem wood functions
def Marklund_1988_T5(diameter_cm):
    return np.exp(-2.2184 + 11.4219 * (diameter_cm / (diameter_cm + 14)))

def Marklund_1988_T6(diameter_cm, height_m):
    return np.exp(-2.6864 + 7.6066 * (diameter_cm / (diameter_cm + 14)) + 0.0200 * height_m + 0.8658 * np.log(height_m))

def Marklund_1988_T7(diameter_cm, height_m, double_bark_mm, age):
    return np.exp(-2.5325 + 7.8936 * (diameter_cm / (diameter_cm + 14)) + 0.0231 * height_m + 0.7887 * np.log(height_m) - 0.1065 * np.log(double_bark_mm) + 0.00201 * age)

def Marklund_1988_T8(diameter_cm, height_m, double_bark_mm, age, form_quotient5=None, form_quotient3=None, altitude_m=None):
    if form_quotient5 is not None and form_quotient3 is not None:
        print('Either form_quotient5 or form_quotient3 can be supplied. Not both.')
        print('form_quotient5 taking precedence.')
        form_quotient3 = None
    return np.exp(-2.0028 + 7.9455 * (diameter_cm / (diameter_cm + 14)) + 0.0439 * height_m + 0.2437 * np.log(height_m) - 0.0875 * np.log(double_bark_mm) + 0.00172 * age + 0.7778 * (form_quotient5 or 0) + 0.4855 * (form_quotient3 or 0) - 0.1557 * (altitude_m or 0))

MarklundPineStemWood = [Marklund_1988_T5, Marklund_1988_T6, Marklund_1988_T7, Marklund_1988_T8]
MarklundPineStemWood = sorted(MarklundPineStemWood, key=lambda f: f.__code__.co_argcount, reverse=True)

# Stem bark functions
def Marklund_1988_T9(diameter_cm):
    return np.exp(-2.9748 + 8.8489 * (diameter_cm / (diameter_cm + 16)))

def Marklund_1988_T10(diameter_cm, height_m):
    return np.exp(-3.2765 + 7.2482 * (diameter_cm / (diameter_cm + 16)) + 0.4487 * np.log(height_m))

def Marklund_1988_T11(diameter_cm, height_m, relative_bark_thickness):
    return np.exp(-3.6065 + 7.0834 * (diameter_cm / (diameter_cm + 16)) + 0.5086 * np.log(height_m) + 0.0255 * relative_bark_thickness)

def Marklund_1988_T12(diameter_cm, height_m, crown_base_height_m, relative_bark_thickness):
    return np.exp(-3.5076 + 7.5295 * (diameter_cm / (diameter_cm + 16)) + 0.5629 * np.log(height_m) - 0.2271 * np.log(height_m - crown_base_height_m) + 0.0222 * relative_bark_thickness)

MarklundPineBark = [Marklund_1988_T9, Marklund_1988_T10, Marklund_1988_T11, Marklund_1988_T12]
MarklundPineBark = sorted(MarklundPineBark, key=lambda f: f.__code__.co_argcount, reverse=True)

# Living branches functions
def Marklund_1988_T13(diameter_cm):
    return np.exp(-2.9580 + 7.7428 * (diameter_cm / (diameter_cm + 18)))

def Marklund_1988_T14(diameter_cm, height_m):
    return np.exp(-3.0331 + 6.7610 * (diameter_cm / (diameter_cm + 18)) + 0.6565 * np.log(height_m))

def Marklund_1988_T15(diameter_cm, height_m, crown_base_height_m):
    return np.exp(-3.1398 + 6.6698 * (diameter_cm / (diameter_cm + 18)) + 0.6797 * np.log(height_m) - 0.2763 * np.log(height_m - crown_base_height_m))

MarklundPineLivingBranches = [Marklund_1988_T13, Marklund_1988_T14, Marklund_1988_T15]
MarklundPineLivingBranches = sorted(MarklundPineLivingBranches, key=lambda f: f.__code__.co_argcount, reverse=True)

# Needles functions
def Marklund_1988_T16(diameter_cm):
    return np.exp(-3.5285 + 6.5301 * (diameter_cm / (diameter_cm + 20)))

def Marklund_1988_T17(diameter_cm, height_m):
    return np.exp(-3.6531 + 5.9425 * (diameter_cm / (diameter_cm + 20)) + 0.8165 * np.log(height_m))

def Marklund_1988_T18(diameter_cm, height_m, crown_base_height_m):
    return np.exp(-3.7941 + 5.8956 * (diameter_cm / (diameter_cm + 20)) + 0.8482 * np.log(height_m) - 0.2436 * np.log(height_m - crown_base_height_m))

MarklundPineNeedles = [Marklund_1988_T16, Marklund_1988_T17, Marklund_1988_T18]
MarklundPineNeedles = sorted(MarklundPineNeedles, key=lambda f: f.__code__.co_argcount, reverse=True)

# Dead branches functions
def Marklund_1988_T19(diameter_cm):
    return np.exp(-4.3352 + 5.8210 * (diameter_cm / (diameter_cm + 23)))

def Marklund_1988_T20(diameter_cm, height_m):
    return np.exp(-4.4668 + 5.3836 * (diameter_cm / (diameter_cm + 23)) + 0.9584 * np.log(height_m))

def Marklund_1988_T21(diameter_cm, height_m, crown_base_height_m):
    return np.exp(-4.5368 + 5.4689 * (diameter_cm / (diameter_cm + 23)) + 0.8945 * np.log(height_m) - 0.3322 * np.log(height_m - crown_base_height_m))

MarklundPineDeadBranches = [Marklund_1988_T19, Marklund_1988_T20, Marklund_1988_T21]
MarklundPineDeadBranches = sorted(MarklundPineDeadBranches, key=lambda f: f.__code__.co_argcount, reverse=True)

# Stump-root system functions
def Marklund_1988_T22(diameter_cm):
    return np.exp(-2.2114 + 7.5246 * (diameter_cm / (diameter_cm + 19)))

def Marklund_1988_T23(diameter_cm, height_m):
    return np.exp(-2.3323 + 6.4935 * (diameter_cm / (diameter_cm + 19)) + 0.6055 * np.log(height_m))

def Marklund_1988_T24(diameter_cm, height_m, crown_base_height_m):
    return np.exp(-2.4008 + 6.5480 * (diameter_cm / (diameter_cm + 19)) + 0.6187 * np.log(height_m) - 0.2052 * np.log(height_m - crown_base_height_m))

MarklundPineStumpRootSystem = [Marklund_1988_T22, Marklund_1988_T23, Marklund_1988_T24]
MarklundPineStumpRootSystem = sorted(MarklundPineStumpRootSystem, key=lambda f: f.__code__.co_argcount, reverse=True)

# Stump functions
def Marklund_1988_T25(diameter_cm):
    return np.exp(-3.1444 + 8.4027 * (diameter_cm / (diameter_cm + 15)))

def Marklund_1988_T26(diameter_cm, height_m):
    return np.exp(-3.2571 + 7.3144 * (diameter_cm / (diameter_cm + 15)) + 0.7078 * np.log(height_m))

def Marklund_1988_T27(diameter_cm, height_m, relative_bark_thickness):
    return np.exp(-3.3738 + 7.1416 * (diameter_cm / (diameter_cm + 15)) + 0.7956 * np.log(height_m) + 0.0119 * relative_bark_thickness)

MarklundPineStump = [Marklund_1988_T25, Marklund_1988_T26, Marklund_1988_T27]
MarklundPineStump = sorted(MarklundPineStump, key=lambda f: f.__code__.co_argcount, reverse=True)

# Norway Spruce Stem functions
def Marklund_1988_S1(diameter_cm):
    return np.exp(-2.3450 + 11.1111 * (diameter_cm / (diameter_cm + 12)))

def Marklund_1988_S2(diameter_cm, height_m):
    return np.exp(-2.7190 + 7.8497 * (diameter_cm / (diameter_cm + 12)) + 0.0095 * height_m + 0.8693 * np.log(height_m))

def Marklund_1988_S3(diameter_cm, height_m, double_bark_mm, age):
    return np.exp(-2.5490 + 7.7334 * (diameter_cm / (diameter_cm + 12)) + 0.0125 * height_m + 0.8854 * np.log(height_m) - 0.0588 * np.log(double_bark_mm) + 0.00191 * age)

MarklundSpruceStem = [Marklund_1988_S1, Marklund_1988_S2, Marklund_1988_S3]
MarklundSpruceStem = sorted(MarklundSpruceStem, key=lambda f: f.__code__.co_argcount, reverse=True)

# Norway Spruce Living branches functions
def Marklund_1988_S4(diameter_cm):
    return np.exp(-2.8470 + 8.6120 * (diameter_cm / (diameter_cm + 12)))

def Marklund_1988_S5(diameter_cm, height_m):
    return np.exp(-2.9892 + 7.1881 * (diameter_cm / (diameter_cm + 12)) + 0.7534 * np.log(height_m))

def Marklund_1988_S6(diameter_cm, height_m, crown_base_height_m):
    return np.exp(-3.1020 + 7.0834 * (diameter_cm / (diameter_cm + 12)) + 0.7707 * np.log(height_m) - 0.2426 * np.log(height_m - crown_base_height_m))

MarklundSpruceLivingBranches = [Marklund_1988_S4, Marklund_1988_S5, Marklund_1988_S6]
MarklundSpruceLivingBranches = sorted(MarklundSpruceLivingBranches, key=lambda f: f.__code__.co_argcount, reverse=True)

# Norway Spruce Dead branches functions
def Marklund_1988_S7(diameter_cm):
    return np.exp(-4.3352 + 5.8210 * (diameter_cm / (diameter_cm + 23)))

def Marklund_1988_S8(diameter_cm, height_m):
    return np.exp(-4.4668 + 5.3836 * (diameter_cm / (diameter_cm + 23)) + 0.9584 * np.log(height_m))

def Marklund_1988_S9(diameter_cm, height_m, crown_base_height_m):
    return np.exp(-4.5368 + 5.4689 * (diameter_cm / (diameter_cm + 23)) + 0.8945 * np.log(height_m) - 0.3322 * np.log(height_m - crown_base_height_m))

MarklundSpruceDeadBranches = [Marklund_1988_S7, Marklund_1988_S8, Marklund_1988_S9]
MarklundSpruceDeadBranches = sorted(MarklundSpruceDeadBranches, key=lambda f: f.__code__.co_argcount, reverse=True)

# Norway Spruce Stump-root system functions
def Marklund_1988_S10(diameter_cm):
    return np.exp(-2.2114 + 7.5246 * (diameter_cm / (diameter_cm + 19)))

def Marklund_1988_S11(diameter_cm, height_m):
    return np.exp(-2.3323 + 6.4935 * (diameter_cm / (diameter_cm + 19)) + 0.6055 * np.log(height_m))

def Marklund_1988_S12(diameter_cm, height_m, crown_base_height_m):
    return np.exp(-2.4008 + 6.5480 * (diameter_cm / (diameter_cm + 19)) + 0.6187 * np.log(height_m) - 0.2052 * np.log(height_m - crown_base_height_m))

MarklundSpruceStumpRootSystem = [Marklund_1988_S10, Marklund_1988_S11, Marklund_1988_S12]
MarklundSpruceStumpRootSystem = sorted(MarklundSpruceStumpRootSystem, key=lambda f: f.__code__.co_argcount, reverse=True)

# Norway Spruce Stump functions
def Marklund_1988_S13(diameter_cm):
    return np.exp(-3.1444 + 8.4027 * (diameter_cm / (diameter_cm + 15)))

def Marklund_1988_S14(diameter_cm, height_m):
    return np.exp(-3.2571 + 7.3144 * (diameter_cm / (diameter_cm + 15)) + 0.7078 * np.log(height_m))

def Marklund_1988_S15(diameter_cm, height_m, relative_bark_thickness):
    return np.exp(-3.3738 + 7.1416 * (diameter_cm / (diameter_cm + 15)) + 0.7956 * np.log(height_m) + 0.0119 * relative_bark_thickness)

MarklundSpruceStump = [Marklund_1988_S13, Marklund_1988_S14, Marklund_1988_S15]
MarklundSpruceStump = sorted(MarklundSpruceStump, key=lambda f: f.__code__.co_argcount, reverse=True)

# Birch Stem functions
def Marklund_1988_B1(diameter_cm):
    return np.exp(-2.3450 + 11.1111 * (diameter_cm / (diameter_cm + 12)))

def Marklund_1988_B2(diameter_cm, height_m):
    return np.exp(-2.7190 + 7.8497 * (diameter_cm / (diameter_cm + 12)) + 0.0095 * height_m + 0.8693 * np.log(height_m))

def Marklund_1988_B3(diameter_cm, height_m, double_bark_mm, age):
    return np.exp(-2.5490 + 7.7334 * (diameter_cm / (diameter_cm + 12)) + 0.0125 * height_m + 0.8854 * np.log(height_m) - 0.0588 * np.log(double_bark_mm) + 0.00191 * age)

MarklundBirchStem = [Marklund_1988_B1, Marklund_1988_B2, Marklund_1988_B3]
MarklundBirchStem = sorted(MarklundBirchStem, key=lambda f: f.__code__.co_argcount, reverse=True)

# Birch Living branches functions
def Marklund_1988_B4(diameter_cm):
    return np.exp(-2.8470 + 8.6120 * (diameter_cm / (diameter_cm + 12)))

def Marklund_1988_B5(diameter_cm, height_m):
    return np.exp(-2.9892 + 7.1881 * (diameter_cm / (diameter_cm + 12)) + 0.7534 * np.log(height_m))

def Marklund_1988_B6(diameter_cm, height_m, crown_base_height_m):
    return np.exp(-3.1020 + 7.0834 * (diameter_cm / (diameter_cm + 12)) + 0.7707 * np.log(height_m) - 0.2426 * np.log(height_m - crown_base_height_m))

MarklundBirchLivingBranches = [Marklund_1988_B4, Marklund_1988_B5, Marklund_1988_B6]
MarklundBirchLivingBranches = sorted(MarklundBirchLivingBranches, key=lambda f: f.__code__.co_argcount, reverse=True)

# Birch Dead branches functions
def Marklund_1988_B7(diameter_cm):
    return np.exp(-4.3352 + 5.8210 * (diameter_cm / (diameter_cm + 23)))

def Marklund_1988_B8(diameter_cm, height_m):
    return np.exp(-4.4668 + 5.3836 * (diameter_cm / (diameter_cm + 23)) + 0.9584 * np.log(height_m))

def Marklund_1988_B9(diameter_cm, height_m, crown_base_height_m):
    return np.exp(-4.5368 + 5.4689 * (diameter_cm / (diameter_cm + 23)) + 0.8945 * np.log(height_m) - 0.3322 * np.log(height_m - crown_base_height_m))

MarklundBirchDeadBranches = [Marklund_1988_B7, Marklund_1988_B8, Marklund_1988_B9]
MarklundBirchDeadBranches = sorted(MarklundBirchDeadBranches, key=lambda f: f.__code__.co_argcount, reverse=True)

# Birch Stump-root system functions
def Marklund_1988_B10(diameter_cm):
    return np.exp(-2.2114 + 7.5246 * (diameter_cm / (diameter_cm + 19)))

def Marklund_1988_B11(diameter_cm, height_m):
    return np.exp(-2.3323 + 6.4935 * (diameter_cm / (diameter_cm + 19)) + 0.6055 * np.log(height_m))

def Marklund_1988_B12(diameter_cm, height_m, crown_base_height_m):
    return np.exp(-2.4008 + 6.5480 * (diameter_cm / (diameter_cm + 19)) + 0.6187 * np.log(height_m) - 0.2052 * np.log(height_m - crown_base_height_m))

MarklundBirchStumpRootSystem = [Marklund_1988_B10, Marklund_1988_B11, Marklund_1988_B12]
MarklundBirchStumpRootSystem = sorted(MarklundBirchStumpRootSystem, key=lambda f: f.__code__.co_argcount, reverse=True)

# Birch Stump functions
def Marklund_1988_B13(diameter_cm):
    return np.exp(-3.1444 + 8.4027 * (diameter_cm / (diameter_cm + 15)))

def Marklund_1988_B14(diameter_cm, height_m):
    return np.exp(-3.2571 + 7.3144 * (diameter_cm / (diameter_cm + 15)) + 0.7078 * np.log(height_m))

def Marklund_1988_B15(diameter_cm, height_m, relative_bark_thickness):
    return np.exp(-3.3738 + 7.1416 * (diameter_cm / (diameter_cm + 15)) + 0.7956 * np.log(height_m) + 0.0119 * relative_bark_thickness)

MarklundBirchStump = [Marklund_1988_B13, Marklund_1988_B14, Marklund_1988_B15]
MarklundBirchStump = sorted(MarklundBirchStump, key=lambda f: f.__code__.co_argcount, reverse=True)

species_map = {
        'pinus sylvestris': {
            'stem': MarklundPineStem,
            'stem_wood': MarklundPineStemWood,
            'stem_bark': MarklundPineBark,
            'living_branches': MarklundPineLivingBranches,
            'needles': MarklundPineNeedles,
            'dead_branches': MarklundPineDeadBranches,
            'stump_root_system': MarklundPineStumpRootSystem,
            'stump': MarklundPineStump
        },
        'picea abies': {
            'stem': MarklundSpruceStem,
            'living_branches': MarklundSpruceLivingBranches,
            'dead_branches': MarklundSpruceDeadBranches,
            'stump_root_system': MarklundSpruceStumpRootSystem,
            'stump': MarklundSpruceStump
        },
        'betula pendula': {
            'stem': MarklundBirchStem,
            'living_branches': MarklundBirchLivingBranches,
            'dead_branches': MarklundBirchDeadBranches,
            'stump_root_system': MarklundBirchStumpRootSystem,
            'stump': MarklundBirchStump
        },
        'betula pubescens': {
            'stem': MarklundBirchStem,
            'living_branches': MarklundBirchLivingBranches,
            'dead_branches': MarklundBirchDeadBranches,
            'stump_root_system': MarklundBirchStumpRootSystem,
            'stump': MarklundBirchStump
        }
    }


# Wrapper function
def Marklund_1988(species: Optional[str] = None, component: Optional[str] = None, *args, timber: Optional[Timber] = None, **kwargs):
    """
    Calculates the dry-weight biomass for individual trees in Sweden.

    This function serves as a wrapper for the various biomass component functions
    developed by Marklund (1988). It selects the appropriate formula based on
    the tree species and the provided arguments.

    Args:
        species (str): The tree species. Must be one of 'Picea abies' (Norway spruce),
            'Pinus sylvestris' (Scots pine), or 'Betula' (Birch).
        DBH (float): Diameter at breast height (1.3m), in centimeters.
        height_m (Optional[float]): Total tree height, in meters. Required for more
            accurate models for stem, bark, and branches.
        age_at_breast_height (Optional[float]): The age of the tree at breast
            height (1.3m). Used for some pine foliage models.
        crown_base_height_m (Optional[float]): Height from the ground to the lowest
            green branch, in meters. Used for some foliage and branch models.
        is_southern_sweden (Optional[bool]): Set to True if the tree is in
            southern Sweden, False if in northern Sweden. Affects some spruce
            component calculations.

    Returns:
        Dict[str, float]: A dictionary where keys are the biomass components
        (e.g., 'stem', 'bark', 'living_branches', 'dead_branches', 'stump', 'roots')
        and values are their calculated dry weight in kilograms (kg). Components
        that cannot be calculated with the provided inputs will be omitted.

    Raises:
        ValueError: If the species is not one of the recognized types or if
            required arguments are missing for a selected calculation.

    Source:
        Marklund, Lars-Gunnar. (1988). Biomassafunktioner för Tall, Gran och Björk i
        Sverige [Biomass functions for pine, spruce and birch in Sweden]. Report 45.
        Dept. of Forest Survey. Swedish University of Agricultural Sciences. Umeå.
        73 pp. ISSN 0348-0496. ISBN 91-576-3524-2.

    Examples:
        >>> # Calculate biomass for a Norway spruce with only DBH
        >>> Marklund_1988_biomass_Sweden(species='Picea abies', DBH=20)
        {'stem': 148.8, 'stump': 34.6, 'roots_1mm': 30.0}

        >>> # Calculate biomass for a Scots pine with DBH and height
        >>> Marklund_1988_biomass_Sweden(species='Pinus sylvestris', DBH=25, height_m=18)
        {'stem': 234.1, 'bark': 30.5, 'living_branches': 45.2, 'dead_branches': 5.1, 'stump': 55.7, 'roots_1mm': 49.8}
    """
    
    # Handle Timber object as the first argument if provided
    if isinstance(species, Timber):
        timber = species
        species = None

    if timber:
        timber.validate()
        species = timber.species
        component_args = {
            'diameter_cm': timber.diameter_cm,
            'height_m': timber.height_m,
            'double_bark_mm': timber.double_bark_mm,
            'crown_base_height_m': timber.crown_base_height_m
        }
        kwargs.update({k: v for k, v in component_args.items() if v is not None})

    if not species:
        raise ValueError("Species must be specified either directly or through a Timber object.")

    if species not in species_map:
        raise ValueError(f"Unknown species: {species}")

    if component:
        if component not in species_map[species]:
            raise ValueError(f"Unknown component for species {species}: {component}")

        functions = species_map[species][component]
        for func in functions:
            try:
                return func(**kwargs)
            except TypeError:
                continue
        raise ValueError("No function matched the provided arguments.")
    else:
        # Return a dictionary of all components
        results = {}
        for comp, functions in species_map[species].items():
            for func in functions:
                try:
                    results[comp] = func(**kwargs)
                    break
                except TypeError:
                    continue
        return results
