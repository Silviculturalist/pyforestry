import math

# --- Helper class for taper methods ---
class TaperMethods:
    def __init__(self, parent):
        self._parent = parent # Reference to the main Schmidt2001 instance

    # Define species-specific methods dynamically later or explicitly here
    # Explicit definition is clearer:
    def picea_abies(self, requested_height_m, diameter_cm, height_m):
        return self._parent._call_taper('picea_abies', requested_height_m, diameter_cm, height_m)

    def pseudotsuga_menziesii(self, requested_height_m, diameter_cm, height_m):
         return self._parent._call_taper('pseudotsuga_menziesii', requested_height_m, diameter_cm, height_m)

    def pinus_sylvestris(self, requested_height_m, diameter_cm, height_m):
         return self._parent._call_taper('pinus_sylvestris', requested_height_m, diameter_cm, height_m)

    def fagus_sylvatica(self, requested_height_m, diameter_cm, height_m):
         return self._parent._call_taper('fagus_sylvatica', requested_height_m, diameter_cm, height_m)

    def quercus_robur(self, requested_height_m, diameter_cm, height_m):
         # Use same parameters for both Quercus species based on provided data
         return self._parent._call_taper('quercus_robur', requested_height_m, diameter_cm, height_m)

    def quercus_petraea(self, requested_height_m, diameter_cm, height_m):
         # Use same parameters for both Quercus species based on provided data
         return self._parent._call_taper('quercus_petraea', requested_height_m, diameter_cm, height_m)

# --- Schmidt2001 class with nested taper object ---
class Schmidt2001:
    """
    Implements taper functions based on Schmidt (2001), using functions and
    parameters specified in functiondefs.pdf and NWFA_schaftform_params.pdf.

    Access species-specific functions via the `.taper` attribute,
    e.g., Schmidt2001().taper.picea_abies(...)

    Uses:
    - Original Pain function for conifers (Picea abies, Pseudotsuga menziesii, Pinus sylvestris).
      Formulas 33, 34, 35 from functiondefs.pdf.
      Parameters from Tables 530, 61, 62 in NWFA_schaftform_params.pdf.
    - Modified Brink function for broadleaves (Fagus sylvatica, Quercus robur/petraea).
      Formula 37 from functiondefs.pdf.
      Parameters from Tables 58, 59 in NWFA_schaftform_params.pdf.
    """

    def __init__(self):
        # Parameters from NWFA_schaftform_params.pdf
        self._params_pain = {
            # Fichte - Table 530
            'picea_abies': {'a0': -0.223, 'a1': 1.595, 'a2': -3.155,
                            'b0': 0.512, 'b1': -0.158, 'b2': -0.502},
            # Douglasie - Table 61
            'pseudotsuga_menziesii': {'a0': -0.5828, 'a1': 1.4423, 'a2': -2.1807,
                                      'b0': 0.4369, 'b1': -0.2008, 'b2': -0.2836},
            # Kiefer - Table 62 (b0 not significant, treated as 0)
            'pinus_sylvestris': {'a0': -1.7258, 'a1': 1.3311, 'a2': -0.7016,
                                 'b0': 0.0, 'b1': -0.2142, 'b2': 0.1306}
        }
        self._params_brink = {
             # Buche - Table 58
            'fagus_sylvatica': {'k': 0.6946140, 'p': 0.0862735, 'q': 0.1359840},
             # Eiche - Table 59 (Same params for both Quercus)
            'quercus_robur': {'k': 0.5698770, 'p': 0.0450652, 'q': 0.2452940},
            'quercus_petraea': {'k': 0.5698770, 'p': 0.0450652, 'q': 0.2452940}
        }
        self._conifers = set(self._params_pain.keys())
        self._broadleaves = set(self._params_brink.keys())

        # Create the taper attribute containing species methods
        self.taper = TaperMethods(self)

    def _pain_function(self, requested_height, D, H, species_params):
        """[CORRECTED] Original Pain Function (Formulas 33, 34, 35)."""
        if H <= 0 or D <= 0:
             return None
        if H <= 0 or H == 1.0: # Check for log(H) denominator term
            return None

        try:
            log_H = math.log(H)
            term1_param_calc = D / log_H # Corrected term calculation
            term2_param_calc = (D / H)**2 if H != 0 else 0

            alpha = species_params['a0'] + species_params['a1'] * term1_param_calc + species_params['a2'] * term2_param_calc
            beta = species_params['b0'] + species_params['b1'] * term1_param_calc + species_params['b2'] * term2_param_calc
        except (ValueError, ZeroDivisionError, OverflowError) as e:
            return None

        hrel = requested_height / H
        if hrel <= 0 or hrel >= 1:
             if abs(hrel - 1.0) < 1e-9: return 0.0
             else: return None
        try:
            hrel_cubed = hrel**3
            log_hrel = math.log(hrel)
            radius_cm = alpha * (1.0 - hrel_cubed) + beta * log_hrel
            return max(0.0, radius_cm) # Ensure non-negative
        except (ValueError, OverflowError) as e:
            return None

    def _brink_function(self, requested_height, D, H, species_params):
        """Modified Brink Function (Formula 37)."""
        h = requested_height
        r13 = D / 2.0
        k = species_params['k']
        p = species_params['p']
        q = species_params['q']

        if abs(H - 1.3) < 1e-9:
            return r13 if abs(h - 1.3) < 1e-9 else 0.0

        try:
            i = k * r13
            den_q = 1.0 - math.exp(q * (1.3 - H))
            den_p = 1.0 - math.exp(p * (1.3 - H))

            if abs(den_q) < 1e-9 or abs(den_p) < 1e-9:
                 if abs(h - 1.3) < 1e-9: return r13
                 else: return 0.0 # Or handle differently

            u = i / den_q + (r13 - i) * (1.0 - (1.0 / den_p))
            v = ((r13 - i) * math.exp(p * 1.3)) / den_p
            w = (i * math.exp(-q * H)) / den_q

            radius_cm = u + v * math.exp(-p * h) - w * math.exp(q * h)
            return max(0.0, radius_cm) # Ensure non-negative
        except (ValueError, OverflowError, ZeroDivisionError) as e:
             return None

    def _call_taper(self, species, requested_height_m, diameter_cm, height_m):
        """Internal helper to call the correct taper function."""
        # --- Input Validation ---
        if not (isinstance(requested_height_m, (int, float)) and isinstance(diameter_cm, (int, float)) and isinstance(height_m, (int, float))):
             print("Error: requested_height_m, diameter_cm, and height_m must be numeric.")
             return None
        if diameter_cm <= 0 or height_m <= 0:
            print("Error: Diameter and total height must be positive.")
            return None
        if requested_height_m < 0 or requested_height_m > height_m:
             print(f"Error: Requested height ({requested_height_m}m) must be between 0 and total height ({height_m}m).")
             return None

        # --- Select Function and Parameters ---
        radius_cm = None
        if species in self._conifers:
             if requested_height_m <= 0: # Pain function needs h > 0
                 print("Warning: Pain function not defined for requested_height = 0. Returning None.")
                 return None
             species_params = self._params_pain.get(species)
             radius_cm = self._pain_function(requested_height_m, diameter_cm, height_m, species_params)
        elif species in self._broadleaves:
             species_params = self._params_brink.get(species)
             radius_cm = self._brink_function(requested_height_m, diameter_cm, height_m, species_params)
        else:
             # Should not happen if called from TaperMethods, but good practice
             print(f"Error: Species '{species}' is not defined as conifer or broadleaf internally.")
             return None

        # --- Return Diameter ---
        if radius_cm is not None:
             # Check for NaN or Inf before multiplying
            if math.isnan(radius_cm) or math.isinf(radius_cm):
                print(f"Warning: Calculation resulted in NaN or Inf for h={requested_height_m}")
                return None
            return radius_cm * 2.0
        else:
            # Calculation failed in the specific function
            return None