import math
from copy import deepcopy
from typing import Union, Dict, List, Optional

class BrandelVolume:
    # --- Default Over-Bark Coefficients ---
    NorthBirchCoeff: List[float]    = [-0.44224, 2.47580, -1.40854, 5.16863, -3.77147]
    SouthBirchCoeff: List[float]    = [-0.89359, 2.27954, -1.18672, 7.07362, -5.45175]

    NorthPineCoeff: List[float]     = [-1.20914, 1.94740, -0.05947, 1.40958, -0.45810]
    SouthPineCoeff: List[float]     = [-1.38903, 1.84493, 0.06563, 2.02122, -1.01095]

    NorthSpruceCoeff: List[float]   = [-0.79783, 2.07157, -0.73882, 3.16332, -1.82622]
    SouthSpruceCoeff: List[float]   = [-1.02039, 2.00128, -0.47473, 2.87138, -1.61803]

    # --- Default Under-Bark Coefficients ---
    NorthBirchUbCoeff: List[float]  = [-0.72541, 2.36594, -1.10578, 4.76151, -3.40177]
    SouthBirchUbCoeff: List[float]  = [-1.09667, 2.20855, -0.85821, 5.81764, -4.34685]

    NorthPineUbCoeff: List[float]   = [-1.23242, 1.95242, -0.05839, 1.13440, -0.13476]
    SouthPineUbCoeff: List[float]   = [-1.23602, 1.94126, -0.11924, 1.80842, -0.74261]

    NorthSpruceUbCoeff: List[float] = [-0.77561, 2.06126, -0.77313, 3.27580, -1.90707]
    SouthSpruceUbCoeff: List[float] = [-1.07676, 1.97159, -0.42776, 2.84877, -1.58630]

    # --- Detailed Adjustment Coefficients for Southern Sites ---
    BirchSouthWithLatitudeCoeff: List[float]   = [0.0, 2.23818, -1.06930, 6.02015, -4.51472]
    BirchSouthWithLatitudeConstant: List[float] = [-0.89363, -0.85480, -0.84627]

    PineSouthWithLatitudeCoeff: List[float]      = [0.0, 1.83182,  0.07275, 2.12777, -1.09439]
    PineSouthWithLatitudeConstant: List[float]   = [-1.40718, -1.41955, -1.41472]

    SpruceSouthWithfieldlayerTypeCoeff: List[float]   = [0.0, 1.99515, -0.46351, 2.84571, -1.59871]
    SpruceSouthWithfieldlayerTypeConstant: List[float]= [-1.01862, -1.02745, -1.02651, -1.03775, -1.03775, -1.03775]

    # --- Detailed Adjustment Coefficients for Northern Sites ---
    PineNorthWithLatitudeCoeff: List[float]    = [0.0, 1.93867, -0.04966, 1.81528, -0.80910]
    PineNorthWithLatitudeConstant: List[float] = [-1.30052, -1.29068, -1.28297, -1.28213]

    SpruceNorthWithLatitudeAndAltitudeCoeff: List[float] = [0.0, 2.11123, -0.76342, 3.07608, -1.78237]
    SpruceNorthWithLatitudeAndAltitudeConstant: List[List[float]] = [
        [-0.74910, -0.75384, -0.75549, -0.76640],
        [-0.75208, -0.75682, -0.75847, -0.76938],
        [-0.76488, -0.76962, -0.77127, -0.78218]
    ]

    # --- fieldlayer Mapping Array ---
    # Remaps 1-indexed fieldlayer codes to indices used for selecting spruce constants.
    fieldlayerTypeToIndex: List[int] = [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 3, 3, 3, 4, 5]

    @staticmethod
    def get_volume_log(coeff: List[float], diameter_cm: float, height_m: float) -> float:
        c0, c1, c2, c3, c4 = coeff
        if height_m <= 1.3:
            raise ValueError("height_m must be greater than 1.3")
        exponent = (c0 +
                    c1 * math.log10(diameter_cm) +
                    c2 * math.log10(diameter_cm + 20) +
                    c3 * math.log10(height_m) +
                    c4 * math.log10(height_m - 1.3))
        return 10 ** exponent

    @staticmethod
    def get_coefficients(part_of_sweden: str, latitude: float, 
                         altitude: Optional[float],
                         fieldlayer_type: Optional[Union[int, object]], 
                         over_bark: bool = True) -> Dict[str, List[float]]:
        """
        If both altitude and fieldlayer_type are provided, the most detailed remapping is used.
        Otherwise, fallback to a simpler default based solely on latitude:
          - if latitude > 60: use North coefficients;
          - else: use South coefficients.
        """
        # If detailed site data are missing, use fallback defaults.
        if altitude is None or fieldlayer_type is None:
            if latitude > 60:
                pine_coeff = BrandelVolume.NorthPineCoeff if over_bark else BrandelVolume.NorthPineUbCoeff
                spruce_coeff = BrandelVolume.NorthSpruceCoeff if over_bark else BrandelVolume.NorthSpruceUbCoeff
                birch_coeff = BrandelVolume.NorthBirchCoeff if over_bark else BrandelVolume.NorthBirchUbCoeff
            else:
                pine_coeff = BrandelVolume.SouthPineCoeff if over_bark else BrandelVolume.SouthPineUbCoeff
                spruce_coeff = BrandelVolume.SouthSpruceCoeff if over_bark else BrandelVolume.SouthSpruceUbCoeff
                birch_coeff = BrandelVolume.SouthBirchCoeff if over_bark else BrandelVolume.SouthBirchUbCoeff
            return {"Pine": pine_coeff, "Spruce": spruce_coeff, "Birch": birch_coeff}

        # Detailed mode.
        if part_of_sweden.lower() in ["south"] or (part_of_sweden.lower() == "middle" and latitude < 60):
            if latitude < 57:
                lat_index = 0
            elif latitude < 59:
                lat_index = 1
            else:
                lat_index = 2
            birch_coeff = deepcopy(BrandelVolume.BirchSouthWithLatitudeCoeff)
            birch_coeff[0] = BrandelVolume.BirchSouthWithLatitudeConstant[lat_index]
            pine_coeff = deepcopy(BrandelVolume.PineSouthWithLatitudeCoeff)
            pine_coeff[0] = BrandelVolume.PineSouthWithLatitudeConstant[lat_index]
            if isinstance(fieldlayer_type, int):
                veg_code = fieldlayer_type
            elif hasattr(fieldlayer_type, "code"):
                veg_code = fieldlayer_type.code
            else:
                veg_code = 1
            if veg_code < 1 or veg_code > len(BrandelVolume.fieldlayerTypeToIndex):
                mapped_index = 0
            else:
                mapped_index = BrandelVolume.fieldlayerTypeToIndex[veg_code - 1]
            spruce_coeff = deepcopy(BrandelVolume.SpruceSouthWithfieldlayerTypeCoeff)
            spruce_coeff[0] = BrandelVolume.SpruceSouthWithfieldlayerTypeConstant[mapped_index]
        else:
            if altitude < 200:
                alt_index = 0
            elif altitude < 500:
                alt_index = 1
            else:
                alt_index = 2
            if latitude < 63:
                lat_index = 0
            elif latitude < 65:
                lat_index = 1
            elif latitude < 67:
                lat_index = 2
            else:
                lat_index = 3
            pine_coeff = deepcopy(BrandelVolume.PineNorthWithLatitudeCoeff)
            pine_coeff[0] = BrandelVolume.PineNorthWithLatitudeConstant[lat_index]
            spruce_coeff = deepcopy(BrandelVolume.SpruceNorthWithLatitudeAndAltitudeCoeff)
            spruce_coeff[0] = BrandelVolume.SpruceNorthWithLatitudeAndAltitudeConstant[alt_index][lat_index]
            birch_coeff = deepcopy(BrandelVolume.NorthBirchCoeff)
        if not over_bark:
            pine_coeff = BrandelVolume.NorthPineUbCoeff if pine_coeff == BrandelVolume.NorthPineCoeff else BrandelVolume.SouthPineUbCoeff
            spruce_coeff = BrandelVolume.NorthSpruceUbCoeff if spruce_coeff == BrandelVolume.NorthSpruceCoeff else BrandelVolume.SouthSpruceUbCoeff
            birch_coeff = BrandelVolume.NorthBirchUbCoeff if birch_coeff == BrandelVolume.NorthBirchCoeff else BrandelVolume.SouthBirchUbCoeff
        return {"Pine": pine_coeff, "Spruce": spruce_coeff, "Birch": birch_coeff}

    @staticmethod
    def _internal_get_tree_volume(height_m: float, diameter_cm: float, species: str,
                        coeff_dict: Dict[str, List[float]]) -> float:
        """
        Dispatches the volume calculation based on the species string.
        If diameter is less than 5 cm, a ValueError is raised.
        """
        if diameter_cm < 5:
            raise ValueError("Diameter must be at least 5 cm.")
        sp: str = species.lower()
        # Here we check for keywords in species to select the appropriate coefficient group.
        if "pinus sylvestris" in sp or "pine" in sp:
            return BrandelVolume.get_volume_log(coeff_dict["Pine"], diameter_cm, height_m)/1000 #dm3 to m3
        elif "picea abies" in sp or "spruce" in sp:
            return BrandelVolume.get_volume_log(coeff_dict["Spruce"], diameter_cm, height_m)/1000 #dm3 to m3
        elif sp.startswith("betula") or "birch" in sp:
            return BrandelVolume.get_volume_log(coeff_dict["Birch"], diameter_cm, height_m)/1000 #dm3 to m3
        else:
            raise ValueError(f"Species '{species}' not supported.")

    @staticmethod
    def get_volume(species: str, diameter_cm: float, height_m: float, latitude: float,
                   altitude: Optional[float], field_layer: Optional[Union[int, object]], 
                   over_bark: bool = True) -> float:
        """
        Main entry point.
        Computes the tree volume (in dm³) for a given species based on:
          - diameter_cm: tree diameter in centimeters,
          - height_m: tree height in meters,
          - latitude: site latitude,
          - altitude: site altitude,
          - fieldlayer: fieldlayer type (as int or an object with a 'code' attribute),
          - over_bark: over bark flag.
        The part_of_sweden is determined from latitude:
          'south' if lat < 57, 'middle' if lat < 59, else 'north'.
        """
        if latitude < 57:
            part_of_sweden: str = "south"
        elif latitude < 59:
            part_of_sweden = "middle"
        else:
            part_of_sweden = "north"
        
        coeffs: Dict[str, List[float]] = BrandelVolume.get_coefficients(part_of_sweden, latitude, altitude, field_layer, over_bark)
        return BrandelVolume._internal_get_tree_volume(height_m, diameter_cm, species, coeffs)
