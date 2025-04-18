import math
import numpy as np
from Munin.Taper import Taper
from Munin.Timber import Timber
from Munin.Helpers.TreeSpecies import TreeName
from Munin.Helpers.Primitives import Diameter_cm, Volume
import warnings
from scipy.optimize import minimize_scalar

class Hansen2023(Taper):
    """
    Implements the taper model for spruce, pine, and birch in Norway.

    Computes stem diameters (taper) along the bole based on the equations
    described in Hansen et al. (2023), which adapt Kozak's (1988)
    variable-exponent taper equation.

    Note: The original article by Hansen et al. (2023) contains minor errata
    (e.g., missing brackets, use of `Log` instead of `ln`, sign error for `b7`
    in pine model), which are corrected in this implementation based on the
    provided R code's logic.

    The calculation for diameter under bark (`with_bark=False`) relies on an
    external bark thickness function (`barkNOR` in the original R code) which
    is not provided here. Therefore, `get_diameter_at_height` currently only
    supports `with_bark=True`.

    References:
        Hansen, E., Rahlf, J., Astrup, R., & Gobakken, T. (2023).
        Taper, volume, and bark thickness models for spruce, pine, and birch
        in Norway. Scandinavian Journal of Forest Research,
        DOI: 10.1080/02827581.2023.2243821.

        Kozak, A. (1988). A variable-exponent taper equation.
        Canadian Journal of Forest Research, 18(11), 1363–1368.

    Attributes:
        timber (Timber): An object containing tree properties like species,
                         dbh, and height.
        taper (callable): Reference to the taper calculation methods within
                          this class. Passed to superclass.
    """

    def __init__(self, timber: Timber):
        """
        Initializes the Hansen2023 taper model for a specific Timber object.

        Args:
            timber (Timber): The timber object with species, dbh, height, etc.
        """
        # Pass the timber and the instance (self) as the taper argument to the superclass.
        # The Taper superclass __init__ should store the timber object and
        # call self.validate(timber)
        super().__init__(timber, self)

    @staticmethod
    def validate(timber: Timber):
        """
        Validate that the Timber object is compatible with this taper model.

        Checks for necessary attributes: species (as string), diameter_cm,
        height_m.

        Args:
            timber (Timber): The timber object to validate.

        Raises:
            ValueError: If required attributes are missing, have invalid types,
                        or species is not recognized.
            TypeError: If timber is not a Timber instance.
        """
        # Check if the dummy Timber class is being used due to import failure
        # Access Timber class safely using globals()
        timber_class = globals().get('Timber')
        is_dummy_timber = False
        if timber_class and hasattr(timber_class, '__module__') and timber_class.__module__ == __name__:
             is_dummy_timber = True
             print("Warning: Using dummy Timber class. Validation may be incomplete.")
             # Perform basic checks even with dummy class
             if not hasattr(timber, 'species') or not hasattr(timber, 'diameter_cm') or not hasattr(timber, 'height_m'):
                 raise ValueError("Dummy Timber object lacks required attributes (species, diameter_cm, height_m).")
        elif not isinstance(timber, timber_class): # Check against potentially real Timber type
            raise TypeError("Provided object is not an instance of Timber.")

        # Proceed with checks assuming timber is a valid (real or dummy) object
        if not hasattr(timber, 'species') or not isinstance(timber.species, str) or not timber.species:
             raise ValueError("Timber object must have a non-empty 'species' string attribute.")

        if not hasattr(timber, 'diameter_cm') or not isinstance(timber.diameter_cm, (int, float)) or timber.diameter_cm <= 0:
             raise ValueError("Timber object must have a positive numeric 'diameter_cm' attribute (DBH).")

        if not hasattr(timber, 'height_m') or not isinstance(timber.height_m, (int, float)) or timber.height_m <= 0:
             raise ValueError("Timber object must have a positive numeric 'height_m' attribute (total height).")

        # Check if species string is one of the recognized ones
        sp_lower = timber.species.lower()
        recognized_species = {
            "spruce", "s", "gran", "g", "1",
            "pine", "p", "furu", "f", "2",
            "birch", "b", "bjørk", "bjork", "bj", "lauv", "l", "3"
        }
        if sp_lower not in recognized_species:
            raise ValueError(f"Species '{timber.species}' is not recognized by the Hansen2023 model. "
                             f"Must be one of spruce, pine, or birch (or aliases).")

        # Optional: Check stump height if needed by base class or usage
        if not hasattr(timber, 'stump_height_m'):
             warnings.warn("Timber object 'stump_height_m' is missing. Assuming 0 if needed.")
             # Optionally add a default if missing
             # timber.stump_height_m = 0.0
        elif not isinstance(timber.stump_height_m, (int, float)) or timber.stump_height_m < 0:
             warnings.warn("Timber object 'stump_height_m' is invalid (must be non-negative).")


    @staticmethod
    def _get_params(species_str: str) -> tuple:
        """
        Internal helper to get model parameters b1-b8 based on species string.

        Args:
            species_str (str): The species identifier (case-insensitive).

        Returns:
            tuple: Coefficients (b1, b2, b3, b4, b5, b6, b7, b8).

        Raises:
            ValueError: If the species string is not recognized.
        """
        sp = species_str.lower()
        if sp in {"spruce", "s", "gran", "g", "1"}:
            # Spruce parameters from R code
            return (1.0625010, 0.9590684, 0.9982461, 2.2909135,
                    -0.5201230, 3.8808849, -2.1078922, 0.1695809)
        elif sp in {"pine", "p", "furu", "f", "2"}:
            # Pine parameters from R code (note correction to b7 if needed)
            # R comment mentions sign error at b7, but R code uses positive.
            # Assuming R code reflects the correct implementation intent.
            return (1.14798036, 0.90295964, 1.00118665, 0.24116857,
                    -0.09667025, -0.50359177, 0.32132441, 0.05546691)
        elif sp in {"birch", "b", "bjørk", "bjork", "bj", "lauv", "l", "3"}:
             # Birch parameters from R code
             return (0.9810885, 0.9936293, 0.9941538, 0.8526987,
                     -0.1819791, 0.4687623, -0.2198294, 0.1591102)
        else:
            # This should be caught by validate, but double-check
            raise ValueError(f"Species '{species_str}' not recognized for parameter lookup.")

    @staticmethod
    def get_diameter_at_height(timber: Timber, height_m: float, with_bark: bool = True) -> float:
        """
        Computes the stem diameter at a specific height above ground.

        Args:
            timber (Timber): The timber object containing tree properties.
            height_m (float): The height above ground (in meters) at which to
                              calculate the diameter.
            with_bark (bool): If True (default), returns diameter over bark.
                              If False, attempts to calculate diameter under bark.
                              Currently, `with_bark=False` is NOT IMPLEMENTED
                              due to the missing bark thickness function.

        Returns:
            float: The calculated diameter in centimeters (cm) at the specified
                   height. Returns 0.0 if height is outside the valid range
                   [0, total_height].

        Raises:
            NotImplementedError: If `with_bark` is False.
            ValueError: If height_m is invalid (e.g., negative, though typically
                        handled by range check), or if internal calculations fail.
        """
        # Use timber attributes directly
        dbh = timber.diameter_cm
        h_top = timber.height_m
        sp = timber.species # Assumes timber object has species string

        # Basic validation for height
        if not isinstance(height_m, (int, float)):
            raise ValueError("height_m must be numeric.")
        if height_m < 0:
             warnings.warn(f"Requested height {height_m}m is below ground. Returning 0 diameter.")
             return 0.0
        if height_m > h_top:
            # Return 0 for heights outside the tree limits (above top)
            return 0.0
        # Avoid division by zero or log(0) issues if height_m is exactly h_top
        if np.isclose(height_m, h_top):
             return 0.0
        # Handle h_top being zero or negative (should be caught by validate)
        if h_top <= 0:
             raise ValueError("Invalid timber height (h_top <= 0).")


        # Calculate relative height
        relative_h = height_m / h_top

        # Clamp relative_h slightly below 1 for the numerator sqrt term to avoid sqrt(negative) due to precision
        if np.isclose(relative_h, 1.0):
            relative_h_sqrt_arg = 1.0 - 1e-9 # Small offset from 1
        elif relative_h > 1.0: # Should not happen if height_m <= h_top check passed
            relative_h_sqrt_arg = 1.0 # Clamp to 1 if somehow > 1
        else:
            relative_h_sqrt_arg = relative_h # Use as is if clearly < 1

        # Denominator term (constant, assuming 0.2 is fixed like in R code)
        denom_term = (1 - math.sqrt(0.2))
        if np.isclose(denom_term, 0.0):
             raise ValueError("Internal calculation error: denominator term is zero.") # Should not happen

        # Numerator term - use clamped argument for sqrt
        num_term = (1 - math.sqrt(max(0.0, relative_h_sqrt_arg))) # Ensure non-negative argument

        # Base term
        if abs(denom_term) < 1e-15:
            # Should be caught by check above, but as fallback
             raise ValueError("Internal calculation error: denominator term is effectively zero.")
        else:
            base = num_term / denom_term
            # Handle case where base might become slightly negative due to precision near the top (num_term -> 0)
            if base < 0 and np.isclose(base, 0.0):
                 base = 0.0

        # Get species-specific parameters
        b1, b2, b3, b4, b5, b6, b7, b8 = Hansen2023._get_params(sp)

        # Exponent term components
        term_h_sq = b4 * (relative_h**2)
        # Add small constant to avoid log(0) or log(negative) if relative_h is 0
        log_arg = max(relative_h, 0) + 0.001
        if log_arg <= 0:
             raise ValueError(f"Invalid argument for logarithm: {log_arg}")
        term_log_h = b5 * math.log(log_arg)
        term_sqrt_h = b6 * math.sqrt(max(relative_h, 0)) # Ensure non-negative arg for sqrt
        term_exp_h = b7 * math.exp(relative_h)
        term_dbh_h = b8 * (dbh / h_top)

        # Full exponent
        exponent = term_h_sq + term_log_h + term_sqrt_h + term_exp_h + term_dbh_h

        # --- Main Calculation ---
        # Pre-factor term
        # Handle dbh <= 0 if not caught by validation
        if dbh <= 0:
             pre_factor = 0.0 # Diameter must be 0 if dbh is 0
        else:
             try:
                  # Protect against b3**dbh potential overflow/underflow if dbh is huge
                  b3_pow_dbh = b3**dbh
                  if not np.isfinite(b3_pow_dbh):
                      raise OverflowError(f"Calculation of b3**dbh ({b3=} ** {dbh=}) resulted in non-finite value.")
                  pre_factor = b1 * (dbh**b2) * b3_pow_dbh
             except (OverflowError, ValueError) as e:
                   warnings.warn(f"Error in pre-factor calculation: {e}. Setting pre-factor to 0.")
                   pre_factor = 0.0

        # Power term (base^exponent)
        if np.isclose(base, 0.0):
            term_power = 0.0
        elif base < 0:
             # This case indicates an issue, likely near the top where (1-sqrt(rel_h)) becomes slightly negative.
             # Treat as 0 diameter.
             warnings.warn(f"Taper equation base term became negative ({base:.2e}) at relative height {relative_h:.3f}. Setting diameter to 0.")
             term_power = 0.0
        else:
             try:
                 # Protect against extremely large positive/negative exponents
                 # Using numpy's power function for potentially better handling
                 term_power = np.power(base, exponent)
                 if not np.isfinite(term_power):
                      # Handle Inf or NaN resulting from power operation
                      raise ValueError(f"Result of base**exponent ({base=} ** {exponent=}) is not finite.")

             except (OverflowError, ValueError) as e:
                   warnings.warn(f"Error during power calculation (base={base:.2e}, exponent={exponent:.2e}): {e}. Clamping result.")
                   # Decide clamping: If base > 1, large positive exp -> inf, large negative exp -> 0
                   # If 0 < base < 1, large positive exp -> 0, large negative exp -> inf
                   if exponent > 0:
                        term_power = float('inf') if base > 1 else 0.0
                   else: # exponent <= 0
                        term_power = 0.0 if base >= 1 else float('inf') # Handle base=1 case -> 1.0 ? Let's use 0 for negative exp.
                   # Need more robust clamping based on context if this occurs often.
                   if np.isclose(base, 1.0): term_power = 1.0 # If base is 1, result is 1

        # Diameter over bark calculation
        d_ob = pre_factor * term_power

        # Final checks for NaN or Inf
        if not np.isfinite(d_ob):
             warnings.warn(f"Non-finite diameter ({d_ob}) calculated at height {height_m:.2f}m (pre={pre_factor:.2e}, power={term_power:.2e}). Clamping to 0.")
             d_ob = 0.0

        # Ensure diameter is non-negative
        d_ob = max(0.0, d_ob)

        if with_bark:
            return d_ob
        else:
            # --- Bark thickness calculation is missing ---
            raise NotImplementedError("Diameter under bark calculation requires the 'barkNOR' function, which is not implemented.")


    @staticmethod
    def get_height_at_diameter(timber: Timber, diameter_cm: float, with_bark: bool = True) -> float:
        """
        Finds the height (meters above ground) where the stem has a specific diameter.

        Uses numerical optimization (`minimize_scalar`) to find the height `h`
        such that `get_diameter_at_height(timber, h)` matches `diameter_cm`.

        Args:
            timber (Timber): The timber object.
            diameter_cm (float): The target diameter in centimeters.
            with_bark (bool): Whether the target diameter is over bark (True)
                              or under bark (False). Currently only True is
                              supported.

        Returns:
            float | None: The height (m) above ground corresponding to the target
                   diameter. Returns `None` if the diameter is not found within
                   the tree's height range or if optimization fails. Returns 0.0
                   if the target diameter is larger than or equal to the diameter
                   at height 0. Returns `timber.height_m` if the target diameter
                   is 0 or less.

        Raises:
            NotImplementedError: If `with_bark` is False.
            ValueError: If `diameter_cm` is negative.
        """
        if not with_bark:
             raise NotImplementedError("get_height_at_diameter for under bark diameter is not implemented.")
        if not isinstance(diameter_cm, (int, float)) or diameter_cm < 0:
             raise ValueError("Target diameter_cm must be non-negative.")

        h_top = timber.height_m
        if h_top <= 0: # Should be caught by validate
             raise ValueError("Invalid timber height (h_top <= 0).")

        # Handle edge case: target diameter is zero or negative
        if diameter_cm <= 1e-6: # Use tolerance for zero
             return h_top # Diameter is zero only at the very top

        # Get diameter at base (height = 0) to check bounds
        # Use a small epsilon above 0 to avoid potential issues exactly at 0 if the model behaves strangely there
        epsilon = 1e-6
        try:
            diam_base = Hansen2023.get_diameter_at_height(timber, epsilon, with_bark=True)
            if not np.isfinite(diam_base):
                 warnings.warn("Could not calculate valid diameter near base. Cannot solve for height.")
                 return None
        except Exception as e:
             warnings.warn(f"Error calculating diameter near base: {e}. Cannot solve for height.")
             return None


        # Handle edge case: target diameter is larger than base diameter
        if diameter_cm >= diam_base:
             return 0.0 # Target diameter is met or exceeded at the base (height 0)

        # Define the objective function to minimize: |calculated_diameter - target_diameter|
        def objective(h):
            # Ensure h is within bounds for the calculation inside get_diameter_at_height
            # Clamp h slightly away from h_top to avoid potential NaN/Inf from get_diameter_at_height edge case handling
            h_calc = max(epsilon, min(h, h_top - epsilon))
            try:
                calc_diam = Hansen2023.get_diameter_at_height(timber, h_calc, with_bark=True)
                if not np.isfinite(calc_diam):
                    # Return a large penalty if calculation fails
                    return 1e10 # Return large finite number instead of inf
                return abs(calc_diam - diameter_cm)
            except Exception:
                 # Catch any unexpected errors during diameter calculation
                 return 1e10 # Return large finite number

        # Search for the height within the bounds [epsilon, total_height - epsilon]
        try:
            result = minimize_scalar(
                objective,
                bounds=(epsilon, h_top - epsilon),
                method='bounded',
                options={'xatol': 1e-5, 'maxiter': 100} # Adjust tolerance/iterations if needed
            )

            # Check if optimization was successful and the difference is small enough
            # result.fun is the minimum value of the objective function found
            if result.success and result.fun < 1e-3: # Check if the minimum difference is close to zero
                # Additionally check if the calculated diameter at result.x is indeed close
                final_h = float(result.x)
                check_diam = Hansen2023.get_diameter_at_height(timber, final_h, with_bark=True)
                if abs(check_diam - diameter_cm) < 1e-2: # Stricter check on final result
                     return final_h # Return the height where the diameter is matched
                else:
                     warnings.warn(f"Optimization converged (fun={result.fun:.2e}), but diameter check failed ({check_diam:.2f} vs {diameter_cm:.2f}).")
                     return None
            else:
                # Optimization failed or minimum difference is too large
                warnings.warn(f"Optimization for diameter {diameter_cm} failed or did not converge well. Success: {result.success}, Min Diff: {result.fun:.2e}. Check if diameter is realistically achievable.")
                return None

        except Exception as e:
            warnings.warn(f"Error during optimization for diameter {diameter_cm}: {e}")
            return None