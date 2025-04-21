#https://treegross.sourceforge.net/treegross.pdf


class Gaffrey1988:
    """
    Provides methods for height imputation based on Gaffrey (1988) 
    referencing the uniform height curve developed by Sloboda.
    
    Uses parameters fitted to the NFV data as documented in TreeGrOSS.
    """

    class height_impute_NFV:
        """
        Implements the uniform height curve using NFV-specific parameters.
        
        Formula (Sloboda, via Gaffrey 1988, TreeGrOSS pdf p. 17):
        h_i = 1.3 + (HG - 1.3) * exp(-(a0 * QMD + a1) * (1/d_i - 1/QMD))
        
        Where:
         h_i:  Height of the individual tree (m)
         HG:   Height corresponding to QMD (m)
         QMD:  Quadratic Mean Diameter of the stand (cm)
         d_i:  Diameter of the individual tree (cm)
         a0, a1: Species-specific parameters
        """
        
        # Parameter dictionary structure:
        # species_code: {'name': 'Latin name', 'params': [a0, a1]}
        _params = {
            # Eiche (Quercus)
            110: {'name': 'quercus', 'params': [0.14657227, 3.78686023]},
            # Roteiche (Quercus rubra)
            113: {'name': 'quercus_rubra', 'params': [0.26932445, 4.32123002]},
            # Buche (Fagus silvatica)
            211: {'name': 'fagus_silvatica', 'params': [0.20213328, 5.64023296]},
            # Fichte (Picea abies)
            511: {'name': 'picea_abies', 'params': [0.18290951, 5.68789430]},
            # Douglasie (Pseudotsuga menziesii)
            611: {'name': 'pseudotsuga_menziesii', 'params': [0.19965100, 4.63277655]},
            # Kiefer (Pinus silvestris)
            711: {'name': 'pinus_silvestris', 'params': [0.25963741, 1.30645374]},
            # Europäische Lärche (Larix decidua)
            811: {'name': 'larix_decidua', 'params': [0.12931522, 4.44234560]},
             # Japanische Lärche (Larix kaempferi)
            812: {'name': 'larix_kaempferi', 'params': [0.53934489, 4.16512685]},
        }

        @staticmethod
        def _calculate_height(species_code, QMD, HG, diameter):
            """Calculates the height for a single tree."""
            if species_code not in Gaffrey1988.height_impute_NFV._params:
                raise ValueError(f"Parameters for species code {species_code} not available.")

            if QMD <= 0 or diameter <= 0:
                raise ValueError("QMD and diameter must be positive.")
            
            if QMD == diameter:
                 # Avoid division by zero or indeterminate form; by definition h_i = HG
                 return HG

            # Ensure inputs are floats
            QMD = float(QMD)
            HG = float(HG)
            diameter = float(diameter)

            a0, a1 = Gaffrey1988.height_impute_NFV._params[species_code]['params']

            try:
                exponent_term = -(a0 * QMD + a1) * (1.0 / diameter - 1.0 / QMD)
                # Prevent potential overflow with very large exponents
                if exponent_term > 700: # exp(700) is roughly 1e304
                     exponent_term = 700
                elif exponent_term < -700: # Avoid underflow issues if needed, though less critical
                     exponent_term = -700
                     
                height = 1.3 + (HG - 1.3) * math.exp(exponent_term)
            except OverflowError:
                 print(f"OverflowError calculating height for species {species_code} with QMD={QMD}, HG={HG}, diameter={diameter}")
                 # Handle overflow - perhaps return HG or raise a specific error?
                 # Returning NaN might be appropriate here
                 return float('nan')
            except Exception as e:
                 print(f"An error occurred during height calculation: {e}")
                 raise e

            # Height should generally be positive. Could add a check: max(0, height)
            return height

        @staticmethod
        def calculate_heights(species_code, QMD, HG, diameters):
            """
            Calculates heights for a list of tree diameters using the uniform height curve.

            Args:
                species_code (int): The species code according to the NFV list.
                QMD (float): Quadratic Mean Diameter (Dg) of the stand in cm.
                HG (float): Height corresponding to QMD (Hg) in m.
                diameters (list[float]): A list of individual tree diameters in cm.

            Returns:
                list[float]: A list containing the calculated heights in m.
            
            Raises:
                ValueError: If species_code is not found or calculation errors occur.
            """
            if not isinstance(diameters, list):
                 raise TypeError("diameters must be a list.")
                 
            heights = []
            for d_i in diameters:
                try:
                    h_i = Gaffrey1988.height_impute_NFV._calculate_height(species_code, QMD, HG, d_i)
                    heights.append(h_i)
                except ValueError as e:
                     # Propagate the error if a single height calculation fails
                     raise ValueError(f"Failed to calculate height for species {species_code}, diameter {d_i}: {e}")
            return heights

        # --- Static methods for specific species ---
        
        @staticmethod
        def quercus(QMD, HG, diameters):
            """Calculates heights for Eiche (Quercus), code 110."""
            if isinstance(diameters, (int, float)): diameters = [diameters] # Allow single diameter input
            return Gaffrey1988.height_impute_NFV.calculate_heights(110, QMD, HG, diameters)

        @staticmethod
        def quercus_rubra(QMD, HG, diameters):
            """Calculates heights for Roteiche (Quercus rubra), code 113."""
            if isinstance(diameters, (int, float)): diameters = [diameters]
            return Gaffrey1988.height_impute_NFV.calculate_heights(113, QMD, HG, diameters)

        @staticmethod
        def fagus_silvatica(QMD, HG, diameters):
            """Calculates heights for Buche (Fagus silvatica), code 211."""
            if isinstance(diameters, (int, float)): diameters = [diameters]
            return Gaffrey1988.height_impute_NFV.calculate_heights(211, QMD, HG, diameters)
            
        @staticmethod
        def picea_abies(QMD, HG, diameters):
            """Calculates heights for Fichte (Picea abies), code 511."""
            if isinstance(diameters, (int, float)): diameters = [diameters]
            return Gaffrey1988.height_impute_NFV.calculate_heights(511, QMD, HG, diameters)

        @staticmethod
        def pseudotsuga_menziesii(QMD, HG, diameters):
            """Calculates heights for Douglasie (Pseudotsuga menziesii), code 611."""
            if isinstance(diameters, (int, float)): diameters = [diameters]
            return Gaffrey1988.height_impute_NFV.calculate_heights(611, QMD, HG, diameters)
            
        @staticmethod
        def pinus_silvestris(QMD, HG, diameters):
            """Calculates heights for Kiefer (Pinus silvestris), code 711."""
            if isinstance(diameters, (int, float)): diameters = [diameters]
            return Gaffrey1988.height_impute_NFV.calculate_heights(711, QMD, HG, diameters)

        @staticmethod
        def larix_decidua(QMD, HG, diameters):
            """Calculates heights for Europäische Lärche (Larix decidua), code 811."""
            if isinstance(diameters, (int, float)): diameters = [diameters]
            return Gaffrey1988.height_impute_NFV.calculate_heights(811, QMD, HG, diameters)

        @staticmethod
        def larix_kaempferi(QMD, HG, diameters):
            """Calculates heights for Japanische Lärche (Larix kaempferi), code 812."""
            if isinstance(diameters, (int, float)): diameters = [diameters]
            return Gaffrey1988.height_impute_NFV.calculate_heights(812, QMD, HG, diameters)


import math

class Bergel1974:
    """
    Implements volume form factor functions based on Bergel (1971, 1973, 1974)
    as documented in the TreeGrOSS pdf (pages 17-18).
    Uses nested classes for species access: Bergel1974.SpeciesName.method(d, h)
    
    Methods within species classes calculate form factors ('fs' or 'fd').
    Helper methods calculate volume from form factors.
    """

    @staticmethod
    def _check_inputs(d, h):
        if d <= 0:
            raise ValueError("Diameter (d) must be positive.")
        if h <= 0:
            raise ValueError("Height (h) must be positive.")

    @staticmethod
    def calculate_volume_fs(d, h, fs):
        """Calculates Schaftholz volume (m^3) from d(cm), h(m), and fs."""
        if fs is None or fs < 0: 
             return 0.0 
        return (math.pi / 40000.0) * d**2 * h * fs
        
    @staticmethod
    def calculate_volume_fd(d, h, fd):
        """Calculates Derbholz volume (m^3) from d(cm), h(m), and fd."""
        if d <= 7: 
            return 0.0
        if fd is None or fd < 0: 
             return 0.0 
        return (math.pi / 40000.0) * d**2 * h * fd

    # --- Nested Species Classes for Bergel ---
    
    class quercus:
        @staticmethod
        def derbholz_fd_1974(d, h):
            """Function 1: Eiche (Quercus) Derbholz fd (Bergel, 1974)"""
            Bergel1974._check_inputs(d, h)
            try:
                fd = 0.4786 - (1.011176 / d) + (2.10428 / h) - (203.1997 / (d * h**2))
                return fd
            except ZeroDivisionError:
                raise ValueError("Inputs d and h must be non-zero.")

    class fagus_silvatica:
        @staticmethod
        def derbholz_fd_1973(d, h):
            """Function 2: Buche (Fagus silvatica) Derbholz fd (Bergel, 1973)"""
            Bergel1974._check_inputs(d, h)
            try:
                 fd = 0.4039 + 0.0017335 * h + 1.1267 / h \
                      - 18.188 / (d**3) + 0.0000042 * d**2
                 return fd
            except ZeroDivisionError:
                raise ValueError("Inputs d and h must be non-zero.")

    class picea_abies:
        @staticmethod
        def schaftholz_fs_1973(d, h):
            """Function 3: Fichte (Picea abies) Schaftholz fs (Bergel, 1973)"""
            Bergel1974._check_inputs(d, h)
            try:
                fs = 0.5848 + 3.34262 / (h**2) - 1.73375 / (h * d) \
                     - 0.26215 * math.log10(d) + 0.18736 * math.log10(h) \
                     + 11.34436 / (d * h**2)
                return fs
            except (ZeroDivisionError, ValueError): 
                raise ValueError("Inputs d and h must be positive.")

        @staticmethod
        def derbholz_fd_1974(d, h):
            """Function 13: Fichte (Picea abies) Derbholz fd (Bergel, 1974)"""
            Bergel1974._check_inputs(d, h)
            try:
                if d == 1: 
                     raise ValueError("Diameter (d) cannot be 1 for this function.")
                fd = 0.04016 - 27.56211 / (d**2) + 1.36195 / math.log(d) \
                     + 0.057654 * h / d
                return fd
            except (ZeroDivisionError, ValueError): 
                 raise ValueError("Inputs d (>0, !=1) and h (>0) required.")

    class pinus_silvestris:
        @staticmethod
        def schaftholz_fs_1974(d, h):
            """Function 4: Kiefer (Pinus silvestris) Schaftholz fs (Bergel, 1974)"""
            Bergel1974._check_inputs(d, h)
            try:
                fs = 0.35096 + 0.93964 / d + 1.5464 / h - 2.0482 / (d**2) \
                     - 5.7305 / (d * h) + 17.444 / (h * d**2) \
                     - 335.8731 / (h**2 * d**2) 
                return fs
            except ZeroDivisionError:
                raise ValueError("Inputs d and h must be non-zero.")

        @staticmethod
        def derbholz_fd_1974(d, h):
            """Function 14: Kiefer (Pinus silvestris) Derbholz fd (Bergel, 1974)"""
            Bergel1974._check_inputs(d, h)
            try:
                 fd = 0.40804 - 318.3342 / (h * d**2) + 36.90522 / (h * d) \
                      - 4.05292 / (d**2)
                 return fd
            except ZeroDivisionError:
                raise ValueError("Inputs d and h must be non-zero.")

    class quercus_rubra:
        @staticmethod
        def schaftholz_fs_1974(d, h): 
            """Function 5: Roteiche (Quercus rubra) 'Derbholz' fs (Bergel, 1974) - NOTE: uses 'fs' """
            Bergel1974._check_inputs(d, h)
            try:
                fs = 0.10798 + 0.71858 / math.log10(d * 10.0) + 0.04065 * (h / d)
                return fs
            except (ZeroDivisionError, ValueError): 
                 raise ValueError("Inputs d and h must be positive.")

    class pseudotsuga_menziesii:
        @staticmethod
        def schaftholz_fs_1971(d, h):
            """Function 7: Douglasie (Pseudotsuga menziesii) Schaftholz fs (Bergel, 1971)"""
            Bergel1974._check_inputs(d, h)
            try:
                fs = 0.583 + 4.52132 / (h**2) - 5.59827 / (h * d) \
                     - 0.2101 * math.log10(d) + 0.12363 * math.log10(h) \
                     + 21.92938 / (d * h**2)
                return fs
            except (ZeroDivisionError, ValueError): 
                raise ValueError("Inputs d and h must be positive.")

        @staticmethod
        def derbholz_fd_1974(d, h):
            """Function 12: Douglasie (Pseudotsuga menziesii) Derbholz fd (Bergel, 1974)"""
            Bergel1974._check_inputs(d, h)
            try:
                # Coefficient before log assumed +0.0052 based on PDF layout
                fd = -200.31914 / (h * d**2) + 0.8734 / d \
                     + 0.0052 * math.log10(d**2) + 7.3594 / (h * d) \
                     + 0.46155
                return fd
            except (ZeroDivisionError, ValueError): 
                 raise ValueError("Inputs d and h must be positive.")

    class larix_decidua:
        @staticmethod
        def schaftholz_fs_1974(d, h): # Assumed species for Fn 19
             """Function 19 (Implied Eur. Lärche): Schaftholz fs (Bergel, 1974) - Uses Fn 10 formula per PDF"""
             # Using Fn 10 as indicated in PDF for Fn 19
             return Bergel1974.Larix_kaempferi.schaftholz_fs_1973(d, h)

        @staticmethod
        def derbholz_fd_1974(d, h):
            """Function 15: Europäische Lärche (Larix decidua) Derbholz fd (Bergel, 1974)"""
            Bergel1974._check_inputs(d, h)
            try:
                fd = 0.69196 + 38.64556 / (h * d**2) - 0.01724 * math.log2(d) \
                     - 20.77608 / (d**2) - 0.41727 / h
                return fd
            except (ZeroDivisionError, ValueError): 
                 raise ValueError("Inputs d (>0) and h (>0) required.")
                 
    class larix_kaempferi:
        @staticmethod
        def schaftholz_fs_1973(d, h):
            """Function 10: Japanische Lärche (Larix kaempferi) Schaftholz fs (Bergel, 1973)"""
            Bergel1974._check_inputs(d, h)
            try:
                fs = 0.5073 + 7.41736 / (h**2) - 7.57701 / (h * d) \
                     - 0.32268 * math.log10(d) + 0.30583 * math.log10(h) \
                     + 20.75427 / (d * h**2)
                return fs
            except (ZeroDivisionError, ValueError): 
                raise ValueError("Inputs d and h must be positive.")


class Nagel1988:
    """
    Implements volume functions based on Nagel (1988)
    as documented in the TreeGrOSS pdf (pages 17-18).
    Uses nested classes for species access: Nagel1988.SpeciesName.method(d, h)
    
    Methods calculate volume ('Vs' or 'vd') directly in m^3.
    """
    
    @staticmethod
    def _check_inputs(d, h):
        if d <= 0:
            raise ValueError("Diameter (d) must be positive.")
        if h <= 1.3:
            raise ValueError("Height (h) must be > 1.3 m.")

    @staticmethod
    def _check_inputs_vd(d, h):
        Nagel1988._check_inputs(d, h)
        if d <= 7:
            raise ValueError("Diameter (d) must be > 7 cm for Derbholz ")

    # --- Nested Species Classes for Nagel ---

    class abies_grandis:
        @staticmethod
        def derbholz_vd_1988(d, h):
            """Function 16: Gr.Küstentanne (Abies grandis) Derbholz (Nagel, 1988)"""
            Nagel1988._check_inputs_vd(d, h)
            try:
                log_vd = 1.64134 * math.log(d) + 0.84522 * math.log(h - 1.3) \
                         + 0.45253 * math.log(1.0 - (7.0 / d)) - 8.45379
                return math.exp(log_vd)
            except ValueError: 
                 raise ValueError("Inputs d (>7) and h (>1.3) required.")
            except OverflowError:
                 return float('inf') 

        @staticmethod
        def schaftholz_vs_1988(d, h):
            """Function 17: Gr.Küstentanne (Abies grandis) Schaftholz Vs (Nagel, 1988)"""
            Nagel1988._check_inputs(d, h)
            try:
                log_vs = 1.86089 * math.log(d) + 0.85685 * math.log(h - 1.3) - 9.31895
                return math.exp(log_vs)
            except ValueError: 
                 raise ValueError("Inputs d (>0) and h (>1.3) required.")
            except OverflowError:
                 return float('inf') 

    class thuja_plicata:
        @staticmethod
        def derbholz_vd_1988(d, h):
            """Function 18: Lebensbaum (Thuja plicata) Derbholz vd (Nagel, 1988)"""
            Nagel1988._check_inputs_vd(d, h)
            try:
                log_vd = 1.35860 * math.log(d) + 1.10900 * math.log(h - 1.3) \
                        + 0.50829 * math.log(1.0 - (7.0 / d)) - 8.32778
                return math.exp(log_vd)
            except ValueError: 
                 raise ValueError("Inputs d (>7) and h (>1.3) required.")
            except OverflowError:
                 return float('inf')

        @staticmethod
        def schaftholz_vs_1988(d, h):
            """Function 19: Lebensbaum (Thuja plicata) Schaftholz Vs (Nagel, 1988)"""
            Nagel1988._check_inputs(d, h)
            try:
                log_vs = 1.67590 * math.log(d) + 1.05313 * math.log(h - 1.3) - 9.32861
                return math.exp(log_vs)
            except ValueError: 
                 raise ValueError("Inputs d (>0) and h (>1.3) required.")
            except OverflowError:
                 return float('inf')

    class tsuga_heterophylla:
        @staticmethod
        def derbholz_vd_1988(d, h):
            """Function 20: Hemlock (Tsuga heterophylla) Derbholz vd (Nagel, 1988)"""
            Nagel1988._check_inputs_vd(d, h)
            try:
                 log_vd = 1.78913 * math.log(d) + 1.03195 * math.log(h - 1.3) \
                         + 0.29581 * math.log(1.0 - (7.0 / d)) - 9.41554
                 return math.exp(log_vd)
            except ValueError: 
                 raise ValueError("Inputs d (>7) and h (>1.3) required.")
            except OverflowError:
                 return float('inf')
                 
        @staticmethod
        def schaftholz_vs_1988(d, h):
            """Function 21: Hemlock (Tsuga heterophylla) Schaftholz Vs (Nagel, 1988)"""
            Nagel1988._check_inputs(d, h)
            try:
                log_vs = 1.83933 * math.log(d) + 1.07109 * math.log(h - 1.3) - 9.78039
                return math.exp(log_vs)
            except ValueError: 
                 raise ValueError("Inputs d (>0) and h (>1.3) required.")
            except OverflowError:
                 return float('inf')
                 
    class chamaecyparis: # Assuming Chamaecyparis lawsoniana based on context
        @staticmethod
        def derbholz_vd_1988(d, h):
            """Function 22: Scheinzypresse (Chamaecyparis) Derbholz vd (Nagel, 1988)"""
            Nagel1988._check_inputs_vd(d, h)
            try:
                 log_vd = 1.69307 * math.log(d) + 0.96994 * math.log(h - 1.3) \
                         + 0.39987 * math.log(1.0 - (7.0 / d)) - 8.82697
                 return math.exp(log_vd)
            except ValueError: 
                 raise ValueError("Inputs d (>7) and h (>1.3) required.")
            except OverflowError:
                 return float('inf')

        @staticmethod
        def schaftholz_vs_1988(d, h):
            """Function 23: Scheinzypresse (Chamaecyparis) Schaftholz Vs (Nagel, 1988)"""
            Nagel1988._check_inputs(d, h)
            try:
                log_vs = 1.83305 * math.log(d) + 0.96514 * math.log(h - 1.3) - 9.41531
                return math.exp(log_vs)
            except ValueError: 
                 raise ValueError("Inputs d (>0) and h (>1.3) required.")
            except OverflowError:
                 return float('inf')

        
