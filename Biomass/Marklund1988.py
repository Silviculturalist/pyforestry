import numpy as np

def Marklund_1988_T1(DBH):
    return np.exp(-2.3388 + 11.3264 * (DBH / (DBH + 13)))

def Marklund_1988_T2(DBH, height_m):
    return np.exp(-2.6768 + 7.5939 * (DBH / (DBH + 13)) + 0.0151 * height_m + 0.8799 * np.log(height_m))

def Marklund_1988_T3(DBH, height_m, double_bark_mm, ageBH):
    return np.exp(-2.6232 + 7.7318 * (DBH / (DBH + 13)) + 0.0139 * height_m + 0.8625 * np.log(height_m) - 0.0704 * np.log(double_bark_mm) + 0.00185 * ageBH)

def Marklund_1988_T4(DBH, height_m, double_bark_mm, ageBH, form_quotient5=None, form_quotient3=None, altitude=None):
    if form_quotient5 is not None and form_quotient3 is not None:
        print('Either form_quotient5 or form_quotient3 can be supplied. Not both.')
        print('form_quotient5 taking precedence.')
        form_quotient3 = None
    return np.exp(-2.4826 + 7.9039 * (DBH / (DBH + 13)) + 0.0184 * height_m + 0.6939 * np.log(height_m) - 0.0731 * np.log(double_bark_mm) + 0.00182 * ageBH + 0.2382 * (form_quotient5 or 0) + 0.2217 * (form_quotient3 or 0) - 0.1596 * (altitude or 0))

MarklundPineStem = [Marklund_1988_T1, Marklund_1988_T2, Marklund_1988_T3, Marklund_1988_T4]
MarklundPineStem = sorted(MarklundPineStem, key=lambda f: f.__code__.co_argcount, reverse=True)

# Stem wood functions
def Marklund_1988_T5(DBH):
    return np.exp(-2.2184 + 11.4219 * (DBH / (DBH + 14)))

def Marklund_1988_T6(DBH, height_m):
    return np.exp(-2.6864 + 7.6066 * (DBH / (DBH + 14)) + 0.0200 * height_m + 0.8658 * np.log(height_m))

def Marklund_1988_T7(DBH, height_m, double_bark_mm, ageBH):
    return np.exp(-2.5325 + 7.8936 * (DBH / (DBH + 14)) + 0.0231 * height_m + 0.7887 * np.log(height_m) - 0.1065 * np.log(double_bark_mm) + 0.00201 * ageBH)

def Marklund_1988_T8(DBH, height_m, double_bark_mm, ageBH, form_quotient5=None, form_quotient3=None, altitude=None):
    if form_quotient5 is not None and form_quotient3 is not None:
        print('Either form_quotient5 or form_quotient3 can be supplied. Not both.')
        print('form_quotient5 taking precedence.')
        form_quotient3 = None
    return np.exp(-2.0028 + 7.9455 * (DBH / (DBH + 14)) + 0.0439 * height_m + 0.2437 * np.log(height_m) - 0.0875 * np.log(double_bark_mm) + 0.00172 * ageBH + 0.7778 * (form_quotient5 or 0) + 0.4855 * (form_quotient3 or 0) - 0.1557 * (altitude or 0))

MarklundPineStemWood = [Marklund_1988_T5, Marklund_1988_T6, Marklund_1988_T7, Marklund_1988_T8]
MarklundPineStemWood = sorted(MarklundPineStemWood, key=lambda f: f.__code__.co_argcount, reverse=True)

# Stem bark functions
def Marklund_1988_T9(DBH):
    return np.exp(-2.9748 + 8.8489 * (DBH / (DBH + 16)))

def Marklund_1988_T10(DBH, height_m):
    return np.exp(-3.2765 + 7.2482 * (DBH / (DBH + 16)) + 0.4487 * np.log(height_m))

def Marklund_1988_T11(DBH, height_m, relative_bark_thickness):
    return np.exp(-3.6065 + 7.0834 * (DBH / (DBH + 16)) + 0.5086 * np.log(height_m) + 0.0255 * relative_bark_thickness)

def Marklund_1988_T12(DBH, height_m, crown_base_height_m, relative_bark_thickness):
    return np.exp(-3.5076 + 7.5295 * (DBH / (DBH + 16)) + 0.5629 * np.log(height_m) - 0.2271 * np.log(height_m - crown_base_height_m) + 0.0222 * relative_bark_thickness)

MarklundPineBark = [Marklund_1988_T9, Marklund_1988_T10, Marklund_1988_T11, Marklund_1988_T12]
MarklundPineBark = sorted(MarklundPineBark, key=lambda f: f.__code__.co_argcount, reverse=True)

# Living branches functions
def Marklund_1988_T13(DBH):
    return np.exp(-2.9580 + 7.7428 * (DBH / (DBH + 18)))

def Marklund_1988_T14(DBH, height_m):
    return np.exp(-3.0331 + 6.7610 * (DBH / (DBH + 18)) + 0.6565 * np.log(height_m))

def Marklund_1988_T15(DBH, height_m, crown_base_height_m):
    return np.exp(-3.1398 + 6.6698 * (DBH / (DBH + 18)) + 0.6797 * np.log(height_m) - 0.2763 * np.log(height_m - crown_base_height_m))

MarklundPineLivingBranches = [Marklund_1988_T13, Marklund_1988_T14, Marklund_1988_T15]
MarklundPineLivingBranches = sorted(MarklundPineLivingBranches, key=lambda f: f.__code__.co_argcount, reverse=True)

# Needles functions
def Marklund_1988_T16(DBH):
    return np.exp(-3.5285 + 6.5301 * (DBH / (DBH + 20)))

def Marklund_1988_T17(DBH, height_m):
    return np.exp(-3.6531 + 5.9425 * (DBH / (DBH + 20)) + 0.8165 * np.log(height_m))

def Marklund_1988_T18(DBH, height_m, crown_base_height_m):
    return np.exp(-3.7941 + 5.8956 * (DBH / (DBH + 20)) + 0.8482 * np.log(height_m) - 0.2436 * np.log(height_m - crown_base_height_m))

MarklundPineNeedles = [Marklund_1988_T16, Marklund_1988_T17, Marklund_1988_T18]
MarklundPineNeedles = sorted(MarklundPineNeedles, key=lambda f: f.__code__.co_argcount, reverse=True)

# Dead branches functions
def Marklund_1988_T19(DBH):
    return np.exp(-4.3352 + 5.8210 * (DBH / (DBH + 23)))

def Marklund_1988_T20(DBH, height_m):
    return np.exp(-4.4668 + 5.3836 * (DBH / (DBH + 23)) + 0.9584 * np.log(height_m))

def Marklund_1988_T21(DBH, height_m, crown_base_height_m):
    return np.exp(-4.5368 + 5.4689 * (DBH / (DBH + 23)) + 0.8945 * np.log(height_m) - 0.3322 * np.log(height_m - crown_base_height_m))

MarklundPineDeadBranches = [Marklund_1988_T19, Marklund_1988_T20, Marklund_1988_T21]
MarklundPineDeadBranches = sorted(MarklundPineDeadBranches, key=lambda f: f.__code__.co_argcount, reverse=True)

# Stump-root system functions
def Marklund_1988_T22(DBH):
    return np.exp(-2.2114 + 7.5246 * (DBH / (DBH + 19)))

def Marklund_1988_T23(DBH, height_m):
    return np.exp(-2.3323 + 6.4935 * (DBH / (DBH + 19)) + 0.6055 * np.log(height_m))

def Marklund_1988_T24(DBH, height_m, crown_base_height_m):
    return np.exp(-2.4008 + 6.5480 * (DBH / (DBH + 19)) + 0.6187 * np.log(height_m) - 0.2052 * np.log(height_m - crown_base_height_m))

MarklundPineStumpRootSystem = [Marklund_1988_T22, Marklund_1988_T23, Marklund_1988_T24]
MarklundPineStumpRootSystem = sorted(MarklundPineStumpRootSystem, key=lambda f: f.__code__.co_argcount, reverse=True)

# Stump functions
def Marklund_1988_T25(DBH):
    return np.exp(-3.1444 + 8.4027 * (DBH / (DBH + 15)))

def Marklund_1988_T26(DBH, height_m):
    return np.exp(-3.2571 + 7.3144 * (DBH / (DBH + 15)) + 0.7078 * np.log(height_m))

def Marklund_1988_T27(DBH, height_m, relative_bark_thickness):
    return np.exp(-3.3738 + 7.1416 * (DBH / (DBH + 15)) + 0.7956 * np.log(height_m) + 0.0119 * relative_bark_thickness)

MarklundPineStump = [Marklund_1988_T25, Marklund_1988_T26, Marklund_1988_T27]
MarklundPineStump = sorted(MarklundPineStump, key=lambda f: f.__code__.co_argcount, reverse=True)

# Norway Spruce Stem functions
def Marklund_1988_S1(DBH):
    return np.exp(-2.3450 + 11.1111 * (DBH / (DBH + 12)))

def Marklund_1988_S2(DBH, height_m):
    return np.exp(-2.7190 + 7.8497 * (DBH / (DBH + 12)) + 0.0095 * height_m + 0.8693 * np.log(height_m))

def Marklund_1988_S3(DBH, height_m, double_bark_mm, ageBH):
    return np.exp(-2.5490 + 7.7334 * (DBH / (DBH + 12)) + 0.0125 * height_m + 0.8854 * np.log(height_m) - 0.0588 * np.log(double_bark_mm) + 0.00191 * ageBH)

MarklundSpruceStem = [Marklund_1988_S1, Marklund_1988_S2, Marklund_1988_S3]
MarklundSpruceStem = sorted(MarklundSpruceStem, key=lambda f: f.__code__.co_argcount, reverse=True)

# Norway Spruce Living branches functions
def Marklund_1988_S4(DBH):
    return np.exp(-2.8470 + 8.6120 * (DBH / (DBH + 12)))

def Marklund_1988_S5(DBH, height_m):
    return np.exp(-2.9892 + 7.1881 * (DBH / (DBH + 12)) + 0.7534 * np.log(height_m))

def Marklund_1988_S6(DBH, height_m, crown_base_height_m):
    return np.exp(-3.1020 + 7.0834 * (DBH / (DBH + 12)) + 0.7707 * np.log(height_m) - 0.2426 * np.log(height_m - crown_base_height_m))

MarklundSpruceLivingBranches = [Marklund_1988_S4, Marklund_1988_S5, Marklund_1988_S6]
MarklundSpruceLivingBranches = sorted(MarklundSpruceLivingBranches, key=lambda f: f.__code__.co_argcount, reverse=True)

# Norway Spruce Dead branches functions
def Marklund_1988_S7(DBH):
    return np.exp(-4.3352 + 5.8210 * (DBH / (DBH + 23)))

def Marklund_1988_S8(DBH, height_m):
    return np.exp(-4.4668 + 5.3836 * (DBH / (DBH + 23)) + 0.9584 * np.log(height_m))

def Marklund_1988_S9(DBH, height_m, crown_base_height_m):
    return np.exp(-4.5368 + 5.4689 * (DBH / (DBH + 23)) + 0.8945 * np.log(height_m) - 0.3322 * np.log(height_m - crown_base_height_m))

MarklundSpruceDeadBranches = [Marklund_1988_S7, Marklund_1988_S8, Marklund_1988_S9]
MarklundSpruceDeadBranches = sorted(MarklundSpruceDeadBranches, key=lambda f: f.__code__.co_argcount, reverse=True)

# Norway Spruce Stump-root system functions
def Marklund_1988_S10(DBH):
    return np.exp(-2.2114 + 7.5246 * (DBH / (DBH + 19)))

def Marklund_1988_S11(DBH, height_m):
    return np.exp(-2.3323 + 6.4935 * (DBH / (DBH + 19)) + 0.6055 * np.log(height_m))

def Marklund_1988_S12(DBH, height_m, crown_base_height_m):
    return np.exp(-2.4008 + 6.5480 * (DBH / (DBH + 19)) + 0.6187 * np.log(height_m) - 0.2052 * np.log(height_m - crown_base_height_m))

MarklundSpruceStumpRootSystem = [Marklund_1988_S10, Marklund_1988_S11, Marklund_1988_S12]
MarklundSpruceStumpRootSystem = sorted(MarklundSpruceStumpRootSystem, key=lambda f: f.__code__.co_argcount, reverse=True)

# Norway Spruce Stump functions
def Marklund_1988_S13(DBH):
    return np.exp(-3.1444 + 8.4027 * (DBH / (DBH + 15)))

def Marklund_1988_S14(DBH, height_m):
    return np.exp(-3.2571 + 7.3144 * (DBH / (DBH + 15)) + 0.7078 * np.log(height_m))

def Marklund_1988_S15(DBH, height_m, relative_bark_thickness):
    return np.exp(-3.3738 + 7.1416 * (DBH / (DBH + 15)) + 0.7956 * np.log(height_m) + 0.0119 * relative_bark_thickness)

MarklundSpruceStump = [Marklund_1988_S13, Marklund_1988_S14, Marklund_1988_S15]
MarklundSpruceStump = sorted(MarklundSpruceStump, key=lambda f: f.__code__.co_argcount, reverse=True)

# Birch Stem functions
def Marklund_1988_B1(DBH):
    return np.exp(-2.3450 + 11.1111 * (DBH / (DBH + 12)))

def Marklund_1988_B2(DBH, height_m):
    return np.exp(-2.7190 + 7.8497 * (DBH / (DBH + 12)) + 0.0095 * height_m + 0.8693 * np.log(height_m))

def Marklund_1988_B3(DBH, height_m, double_bark_mm, ageBH):
    return np.exp(-2.5490 + 7.7334 * (DBH / (DBH + 12)) + 0.0125 * height_m + 0.8854 * np.log(height_m) - 0.0588 * np.log(double_bark_mm) + 0.00191 * ageBH)

MarklundBirchStem = [Marklund_1988_B1, Marklund_1988_B2, Marklund_1988_B3]
MarklundBirchStem = sorted(MarklundBirchStem, key=lambda f: f.__code__.co_argcount, reverse=True)

# Birch Living branches functions
def Marklund_1988_B4(DBH):
    return np.exp(-2.8470 + 8.6120 * (DBH / (DBH + 12)))

def Marklund_1988_B5(DBH, height_m):
    return np.exp(-2.9892 + 7.1881 * (DBH / (DBH + 12)) + 0.7534 * np.log(height_m))

def Marklund_1988_B6(DBH, height_m, crown_base_height_m):
    return np.exp(-3.1020 + 7.0834 * (DBH / (DBH + 12)) + 0.7707 * np.log(height_m) - 0.2426 * np.log(height_m - crown_base_height_m))

MarklundBirchLivingBranches = [Marklund_1988_B4, Marklund_1988_B5, Marklund_1988_B6]
MarklundBirchLivingBranches = sorted(MarklundBirchLivingBranches, key=lambda f: f.__code__.co_argcount, reverse=True)

# Birch Dead branches functions
def Marklund_1988_B7(DBH):
    return np.exp(-4.3352 + 5.8210 * (DBH / (DBH + 23)))

def Marklund_1988_B8(DBH, height_m):
    return np.exp(-4.4668 + 5.3836 * (DBH / (DBH + 23)) + 0.9584 * np.log(height_m))

def Marklund_1988_B9(DBH, height_m, crown_base_height_m):
    return np.exp(-4.5368 + 5.4689 * (DBH / (DBH + 23)) + 0.8945 * np.log(height_m) - 0.3322 * np.log(height_m - crown_base_height_m))

MarklundBirchDeadBranches = [Marklund_1988_B7, Marklund_1988_B8, Marklund_1988_B9]
MarklundBirchDeadBranches = sorted(MarklundBirchDeadBranches, key=lambda f: f.__code__.co_argcount, reverse=True)

# Birch Stump-root system functions
def Marklund_1988_B10(DBH):
    return np.exp(-2.2114 + 7.5246 * (DBH / (DBH + 19)))

def Marklund_1988_B11(DBH, height_m):
    return np.exp(-2.3323 + 6.4935 * (DBH / (DBH + 19)) + 0.6055 * np.log(height_m))

def Marklund_1988_B12(DBH, height_m, crown_base_height_m):
    return np.exp(-2.4008 + 6.5480 * (DBH / (DBH + 19)) + 0.6187 * np.log(height_m) - 0.2052 * np.log(height_m - crown_base_height_m))

MarklundBirchStumpRootSystem = [Marklund_1988_B10, Marklund_1988_B11, Marklund_1988_B12]
MarklundBirchStumpRootSystem = sorted(MarklundBirchStumpRootSystem, key=lambda f: f.__code__.co_argcount, reverse=True)

# Birch Stump functions
def Marklund_1988_B13(DBH):
    return np.exp(-3.1444 + 8.4027 * (DBH / (DBH + 15)))

def Marklund_1988_B14(DBH, height_m):
    return np.exp(-3.2571 + 7.3144 * (DBH / (DBH + 15)) + 0.7078 * np.log(height_m))

def Marklund_1988_B15(DBH, height_m, relative_bark_thickness):
    return np.exp(-3.3738 + 7.1416 * (DBH / (DBH + 15)) + 0.7956 * np.log(height_m) + 0.0119 * relative_bark_thickness)

MarklundBirchStump = [Marklund_1988_B13, Marklund_1988_B14, Marklund_1988_B15]
MarklundBirchStump = sorted(MarklundBirchStump, key=lambda f: f.__code__.co_argcount, reverse=True)

# Wrapper function
def Marklund_1988(species, component, *args, **kwargs):
    species_map = {
        'pine': {
            'stem': MarklundPineStem,
            'stem_wood': MarklundPineStemWood,
            'stem_bark': MarklundPineBark,
            'living_branches': MarklundPineLivingBranches,
            'needles': MarklundPineNeedles,
            'dead_branches': MarklundPineDeadBranches,
            'stump_root_system': MarklundPineStumpRootSystem,
            'stump': MarklundPineStump
        },
        'spruce': {
            'stem': MarklundSpruceStem,
            'living_branches': MarklundSpruceLivingBranches,
            'dead_branches': MarklundSpruceDeadBranches,
            'stump_root_system': MarklundSpruceStumpRootSystem,
            'stump': MarklundSpruceStump
        },
        'birch': {
            'stem': MarklundBirchStem,
            'living_branches': MarklundBirchLivingBranches,
            'dead_branches': MarklundBirchDeadBranches,
            'stump_root_system': MarklundBirchStumpRootSystem,
            'stump': MarklundBirchStump
        }
    }

    if species not in species_map:
        raise ValueError(f"Unknown species: {species}")
    if component not in species_map[species]:
        raise ValueError(f"Unknown component for species {species}: {component}")

    functions = species_map[species][component]
    for func in functions:
        try:
            return func(*args, **kwargs)
        except TypeError as e:
            continue
    raise ValueError("No function matched the provided arguments.")

## Example usage
#dbh = 30  # Diameter at breast height in cm
#height_m = 15  # Height in meters
#crown_base_height_m = 5  # Crown base height in meters#

## Calculate stem biomass for pine
#pine_stem_biomass = Marklund_1988('pine', 'stem', dbh, height_m)
#print(f"Pine stem biomass: {pine_stem_biomass}")#

## Calculate living branches biomass for spruce
#spruce_living_branches_biomass = Marklund_1988('spruce', 'living_branches', dbh, height_m, crown_base_height_m)
#print(f"Spruce living branches biomass: {spruce_living_branches_biomass}")

