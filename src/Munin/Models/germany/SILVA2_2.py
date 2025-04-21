import numpy as np
from enum import Enum
from Munin.Site.SiteBase import SiteBase
from Munin.Helpers.Primitives import Diameter_cm, QuadraticMeanDiameter, SingleTree
from Munin.Helpers.Base import *
from typing import List
# German site classification
# Relative soil water retention capacity
# Soil Nutrient supply

class SilvaSite:
    temp_difference_warmest_coldest_month_kelvin : float
    growth_season_length_gt_10_C : float
    mean_temperature_growth_season_C : float
    precipitation_sum_growth_season_mm : float
    soil_nutrient_supply : int # German site classification
    soil_water_retention : int # German site classification 
    NOx_concentration_ppm : float
    CO2_atm_concentration_ppm : float

    trees : List[SingleTree]

# Initialise by ecoregion Kahn 1994

# Enum members store the associated float value directly.
# Frozen.
class EllenbergTM1963(Enum):
    """
    Represents species-specific transmission coefficients (TM) 
    based on Ellenberg (1963), used in competition indices.
    Access the float value using .value, e.g., EllenbergTM1963.fagus_sylvatica.value
    """
    fagus_sylvatica = 1.0
    abies_alba = 1.0
    picea_abies = 0.8
    quercus_petraea = 0.5
    pinus_sylvestris = 0.2



class silva_tree_crown_form:
    #a b, c, d
    params = {
        'picea_abies' : {
            'a',
            'b',
            'c',
            'd'
        }
    }

    @staticmethod
    def height_to_crown_base_m(diameter_cm, height_m, a0, a1, a2):

        return height_m * (1 - np.exp(-(a0 + a1 * (height_m / diameter_cm) + a2 * diameter_cm)))
        
    @staticmethod 
    def crown_diameter_m(diameter_cm, height_m, b0, b1, b2, b3):

        return np.exp(b0 + b1 * np.log(diameter_cm) + b2*height_m + b3*np.log(diameter_cm/height_m))
    
    @staticmethod
    def radius_illuminated_crown(distance_from_top_m, a, b):
        return a * distance_from_top_m ** b
        
    @staticmethod 
    def radius_shadowed_crown(distance_from_top_m, c, d):
        return c + distance_from_top_m * d
    
    @staticmethod
    def height_illuminated_crown():
        pass
        
    @staticmethod
    def height_shadowed_crown():
        pass



def get_pretzsch_beta_angle(focal_x, focal_y, focal_height,
                           competitor_x, competitor_y, competitor_height):
    """
    Calculates the competition angle beta_ij for a potential competitor tree i 
    relative to a focal tree j, according to the Pretzsch KKL index definition.

    This function checks if the competitor is within the search cone and 
    calculates the angle beta_ij (in radians) if it is. It does *not* calculate the full KKL index term, only the angle component.

    Args:
        focal_x (float): X-coordinate of the focal tree j.
        focal_y (float): Y-coordinate of the focal tree j.
        focal_height (float): Height of the focal tree j (h_j).
        competitor_x (float): X-coordinate of the competitor tree i.
        competitor_y (float): Y-coordinate of the competitor tree i.
        competitor_height (float): Height of the competitor tree i (h_i).

    Returns:
        float: The angle beta_ij in radians if the competitor's top is within 
               the search cone, otherwise 0.0. Returns 0.0 if heights are
               non-positive.
    """
    # Basic validation for heights
    if focal_height <= 0 or competitor_height <= 0:
        return 0.0

    # 1. Calculate cone apex height on the focal tree
    h_apex_j = 0.6 * focal_height

    # 2. Check if competitor's top is above the cone apex height
    delta_h = competitor_height - h_apex_j
    if delta_h <= 0:
        # Competitor is too short to reach into the cone's volume
        return 0.0 

    # 3. Calculate horizontal distance between trees
    dist = np.sqrt((focal_x - competitor_x)**2 + (focal_y - competitor_y)**2)

    # 4. Check if inside the reverse cone (Suchraum)
    # Cone opening angle = 60 degrees, so angle from vertical = 30 degrees.
    # Radius of the cone at the competitor's height: r = delta_h * tan(30 degrees)
    # tan(30 degrees) = 1 / sqrt(3) approx 0.57735
    tan_30_deg = np.tan(np.radians(30))
    cone_radius_at_competitor_height = delta_h * tan_30_deg

    # Competitor is inside if its horizontal distance is less than the cone radius at its height.
    # Handle the case where dist = 0 (competitor directly overhead) - it should be considered inside.
    is_competitor = False
    if dist == 0 and delta_h > 0:
        is_competitor = True
    elif dist > 0 and dist < cone_radius_at_competitor_height:
         is_competitor = True
    # If dist >= cone_radius_at_competitor_height (and dist > 0), it's outside.
    
    # 5. Calculate angle beta_ij if it is a competitor
    beta_ij = 0.0
    if is_competitor:
        # beta_ij is the angle (in radians) between the horizontal plane at h_apex_j 
        # and the line connecting the cone apex (h_apex_j) to the competitor's top (competitor_height).
        # Use atan2(y, x) where y=delta_h and x=dist for robustness.
        beta_ij = np.arctan2(delta_h, dist) 
        # atan2 handles dist=0 correctly, returning pi/2 (90 degrees) if delta_h > 0.
        
    return beta_ij

# KKL tree competition index
def pretzsch_KKL_CI(focal_x,focal_y,focal_height,competitor_height, competitor_x, competitor_y):

    CI = 0.0 
    
    dist = np.sqrt((focal_x-competitor_x)**2 + (focal_y - competitor_y)**2)

    #Check if inside reverse cone


    return CI 

    




import math
import random

class NagelBiging1995:
    """
    Implements the Weibull diameter distribution generation based on 
    Nagel and Biging (1995) as described in the TreeGrOSS documentation.

    Species parameters are taken from tables on page 9 of treegross.pdf.
    Formulas for parameters b and c:
    b = p0 + p1 * Dg 
    c = p0 + p1 * Dg + p2 * Dmax
    
    Formula for diameter generation (inverse transformation):
    DBH = b * ( (T/b)**c - log(1 - F_T(x)) )**(1/c)
    Where T is the lower limit (often 7cm, but assumed 0 here for simplicity 
    unless specified otherwise, as T is not explicitly defined in the 
    gendistribution section beyond the formula context [cite: 169, 172]) and F_T(x) is a random 
    number [0,1). 
    
    Note: The original method generates trees until a target basal area (gfl) 
    is reached[cite: 174]. This implementation provides a function to generate a 
    single diameter or a list of diameters, rather than managing the basal area target.
    """

    # Parameter dictionary structure:
    # species_code: {'name': 'Latin name', 'b_params': [p0, p1], 'c_params': [p0, p1, p2]}
    _params = {
        # Eiche (Quercus) [cite: 165, 167, 293]
        110: {'name': 'quercus', 'b_params': [-1.937, 1.082], 'c_params': [4.669, 0.366, -0.234]},
        # Roteiche (Quercus rubra) [cite: 165, 167, 293]
        113: {'name': 'quercus_rubra', 'b_params': [0.267, 1.031], 'c_params': [6.122, 0.374, -0.258]},
        # Buche (Fagus silvatica) [cite: 165, 167, 293]
        211: {'name': 'fagus_silvatica', 'b_params': [-4.282, 1.132], 'c_params': [4.518, 0.317, -0.200]},
        # Fichte (Picea abies) [cite: 165, 167, 296]
        511: {'name': 'picea_abies', 'b_params': [-2.492, 1.104], 'c_params': [3.418, 0.353, -0.192]},
        # Douglasie (Pseudotsuga menziesii) [cite: 165, 167, 296]
        611: {'name': 'pseudotsuga_menziesii', 'b_params': [-0.621, 1.060], 'c_params': [4.380, 0.236, -0.141]},
        # Kiefer (Pinus silvestris) [cite: 165, 167, 296]
        711: {'name': 'pinus_silvestris', 'b_params': [-0.047, 1.047], 'c_params': [3.640, 0.332, -0.180]},
    }
    
    @staticmethod
    def _generate_single_diameter(species_code, QMD, DMax, T=0.0):
        """Generates a single diameter using the Weibull distribution."""
        if species_code not in NagelBiging1995._params:
            raise ValueError(f"Parameters for species code {species_code} not available in NagelBiging1995.")
            
        species_params = NagelBiging1995._params[species_code]
        
        # Calculate Weibull parameters b and c [cite: 164, 166]
        b_p = species_params['b_params']
        c_p = species_params['c_params']
        
        # Ensure input is float for calculations
        QMD = float(QMD)
        DMax = float(DMax)
        
        b = b_p[0] + b_p[1] * QMD
        c = c_p[0] + c_p[1] * QMD + c_p[2] * DMax
        
        # Handle potential issues with parameters
        if b <= 0 or c <= 0:
            # This might indicate inputs are outside the typical range 
            # for the model or derived parameters are invalid.
            # Returning NaN or raising an error might be appropriate.
            # Based on the formula, b > T >= 0 and c > 0 are required.
            # Let's raise an error for now.
             raise ValueError(f"Calculated Weibull parameters are invalid (b={b}, c={c}). Check input QMD/DMax values.")

        # Inverse transformation to get diameter [cite: 172]
        # Generate a random number F_T(x) between 0 and 1 (exclusive of 1)
        fx = random.random() 
        # Avoid log(0) by ensuring fx is not exactly 1.0
        while fx == 1.0: 
             fx = random.random()

        try:
            # Component inside the outer exponentiation
            inner_term = (T / b)**c - math.log(1 - fx)
            
            # Handle potential domain errors for the power function
            if inner_term < 0 and (1/c) % 1 != 0 : # Negative base with fractional exponent
                 raise ValueError(f"Cannot calculate diameter due to invalid intermediate term ({inner_term}) with exponent (1/c={1/c}).")
                 
            dbh = b * (inner_term)**(1 / c)
            
            # Generated diameter should likely not exceed DMax, though the formula doesn't strictly enforce this.
            # Optionally, cap the value at DMax or handle as needed.
            # dbh = min(dbh, DMax) 

        except ValueError as e:
             # Catch math domain errors (e.g., log(<=0)) or negative base issues
             print(f"Error during diameter calculation: {e}")
             print(f"Inputs: QMD={QMD}, DMax={DMax}, T={T}")
             print(f"Calculated params: b={b}, c={c}, Fx={fx}")
             # Decide how to handle: return None, NaN, or re-raise
             raise e 
             
        return dbh

    @staticmethod
    def generate_diameters(species_code, QMD, DMax, count=1, diameter_limit=0.0):
        """
        Generates a list of tree diameters based on Weibull distribution.

        Args:
            species_code (int): The species code according to the NFV list.
            QMD (float): Quadratic Mean Diameter (Dg in the document) in cm.
            DMax (float): Maximum expected diameter in cm.
            count (int): The number of diameters to generate.
            diameter_limit (float): The lower diameter limit for the distribution (often 7cm). Defaults to 0.

        Returns:
            list[float]: A list containing the generated diameters in cm.
                         Returns an empty list if count is not positive.
            
        Raises:
            ValueError: If species_code is not found or calculation errors occur.
        """
        if count <= 0:
            return []
            
        diameters = []
        for _ in range(count):
             try:
                 dbh = NagelBiging1995._generate_single_diameter(species_code, QMD, DMax, diameter_limit)
                 diameters.append(dbh)
             except ValueError as e:
                  # Propagate the error if a single diameter generation fails
                  raise ValueError(f"Failed to generate diameter for species {species_code} with QMD={QMD}, DMax={DMax}: {e}")

        return diameters

    # --- Static methods for specific species ---
    
    @staticmethod
    def quercus(QMD, DMax, count=1, diameter_limit=0.0):
        """Generates diameters for Eiche (Quercus), code 110."""
        return NagelBiging1995.generate_diameters(110, QMD, DMax, count, diameter_limit)

    @staticmethod
    def quercus_rubra(QMD, DMax, count=1, diameter_limit=0.0):
        """Generates diameters for Roteiche (Quercus rubra), code 113."""
        return NagelBiging1995.generate_diameters(113, QMD, DMax, count, diameter_limit)

    @staticmethod
    def fagus_silvatica(QMD, DMax, count=1, diameter_limit=0.0):
        """Generates diameters for Buche (Fagus silvatica), code 211."""
        return NagelBiging1995.generate_diameters(211, QMD, DMax, count, diameter_limit)
        
    @staticmethod
    def picea_abies(QMD, DMax, count=1, diameter_limit=0.0):
        """Generates diameters for Fichte (Picea abies), code 511."""
        return NagelBiging1995.generate_diameters(511, QMD, DMax, count, diameter_limit)

    @staticmethod
    def pseudotsuga_menziesii(QMD, DMax, count=1, diameter_limit=0.0):
        """Generates diameters for Douglasie (Pseudotsuga menziesii), code 611."""
        return NagelBiging1995.generate_diameters(611, QMD, DMax, count, diameter_limit)
        
    @staticmethod
    def pinus_silvestris(QMD, DMax, count=1, diameter_limit=0.0):
        """Generates diameters for Kiefer (Pinus silvestris), code 711."""
        return NagelBiging1995.generate_diameters(711, QMD, DMax, count, diameter_limit)
