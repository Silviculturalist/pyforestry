"""Brandel (1990) stem-volume equations and coefficient selection helpers.

Coefficients are transcribed from Brandel, G. (1990) "Volymfunktioner för enskilda
träd", Report 26, Dept. of Forest Yield Research, SLU. The default sets come from
Appendix B (pp. 104-115) and are all of the V1 series -- volume above stump -- using
function type 01, whose independent variables are D, (D+20.0), H and (H-1.3)::

    lg V1 = a + b*lg(D) + c*lg(D+20.0) + d*lg(H) + e*lg(H-1.3)

The 10-logarithm is used, the constant (a) already carries Brandel's correction for
logarithmic bias, and the additive constant 20.0 was fixed for every species and both
regions (Report 26, p. 69).

Appendix B tables are numbered with four digits (Report 26, p. 103): volume above
stump (1) or above ground (2); South (1) or North (2) Sweden; pine (1), spruce (2) or
birch (3); then the function group. Each coefficient set below is tagged with its
table, e.g. ``T1211`` is Appendix B Table 1211, function 100-01.

Function groups differ in which bark convention the volume and the D.B.H. are
expressed in (Report 26, p. 103)::

    group 100   volume o.b.   D.B.H. o.b.
    group 200   volume u.b.   D.B.H. u.b.
    group 300   volume u.b.   D.B.H. o.b.

Group 400 (volume u.b., D.B.H. u.b., upper diameter o.b.) has no function 01 and so is
unreachable without an upper diameter. Since volume o.b. is never published against a
D.B.H. u.b., that combination is rejected rather than approximated.
"""

import math
from copy import deepcopy
from typing import Dict, List, Optional, Protocol, Union, runtime_checkable

from pyforestry.base.contracts import SourceReference


@runtime_checkable
class _HasCode(Protocol):
    """Protocol for enum-like objects exposing an integer ``code`` attribute."""

    code: int


class BrandelVolume:
    """Coefficient tables and helper methods for Brandel (1990) volume equations."""

    # Brandel's dividing line between the regions is the 60th parallel: North Sweden is
    # Norrland, Dalarna and northern Värmland "med 60:de breddgraden som gräns", South
    # Sweden is everything south of it (Report 26, p. 100).
    NORTH_SOUTH_LATITUDE_LIMIT: float = 60.0

    # The functions are not valid below this D.B.H. o.b.; trees under it were dropped
    # from the source material (Report 26, pp. 67 and 103).
    MIN_DIAMETER_CM: float = 4.5

    # --- Function group 100: volume o.b. from D.B.H. o.b. (Appendix B, function 01) ---
    NorthBirchCoeff: List[float] = [-0.44224, 2.47580, -1.40854, 5.16863, -3.77147]  # T1231
    SouthBirchCoeff: List[float] = [-0.89359, 2.27954, -1.18672, 7.07362, -5.45175]  # T1131

    NorthPineCoeff: List[float] = [-1.20914, 1.94740, -0.05947, 1.40958, -0.45810]  # T1211
    SouthPineCoeff: List[float] = [-1.38903, 1.84493, 0.06563, 2.02122, -1.01095]  # T1111

    NorthSpruceCoeff: List[float] = [-0.79783, 2.07157, -0.73882, 3.16332, -1.82622]  # T1221
    SouthSpruceCoeff: List[float] = [-1.02039, 2.00128, -0.47473, 2.87138, -1.61803]  # T1121

    # --- Function group 200: volume u.b. from D.B.H. u.b. (Appendix B, function 01) ---
    # These expect a diameter measured *under* bark; see get_coefficients.
    NorthBirchUbCoeff: List[float] = [-0.72541, 2.36594, -1.10578, 4.76151, -3.40177]  # T1232
    SouthBirchUbCoeff: List[float] = [-1.09667, 2.20855, -0.85821, 5.81764, -4.34685]  # T1132

    NorthPineUbCoeff: List[float] = [-1.23242, 1.95242, -0.05839, 1.13440, -0.13476]  # T1212
    SouthPineUbCoeff: List[float] = [-1.23602, 1.94126, -0.11924, 1.80842, -0.74261]  # T1112

    NorthSpruceUbCoeff: List[float] = [-0.77561, 2.06126, -0.77713, 3.27580, -1.90707]  # T1222
    SouthSpruceUbCoeff: List[float] = [-1.07676, 1.97159, -0.42776, 2.84877, -1.58630]  # T1122

    # --- Function group 300: volume u.b. from D.B.H. o.b. (Appendix B, function 01) ---
    # Brandel added this group so that volume under bark can be estimated without having
    # to record bark thickness (Report 26, p. 70).
    NorthBirchUbFromObCoeff: List[float] = [
        -0.35394,
        2.52141,
        -1.54257,
        4.88165,
        -3.47422,
    ]  # T1233
    SouthBirchUbFromObCoeff: List[float] = [
        -0.93631,
        2.30212,
        -1.40378,
        8.01817,
        -6.18825,
    ]  # T1133

    NorthPineUbFromObCoeff: List[float] = [
        -1.25246,
        1.98244,
        -0.13118,
        1.03781,
        -0.03482,
    ]  # T1213
    SouthPineUbFromObCoeff: List[float] = [
        -1.52761,
        1.82928,
        0.07454,
        1.43792,
        -0.35559,
    ]  # T1113

    NorthSpruceUbFromObCoeff: List[float] = [
        -0.82249,
        2.11094,
        -0.89626,
        3.51812,
        -2.05567,
    ]  # T1223
    SouthSpruceUbFromObCoeff: List[float] = [
        -1.06019,
        2.04239,
        -0.54292,
        2.80843,
        -1.52110,
    ]  # T1123

    # --- Indicator-variable functions (Appendix C) ---
    # Brandel's alternative functions, which enter altitude (HH), latitude (BG) or forest
    # vegetation type (ST, the Tamm-Holmen 1961 scheme) as indicator (dummy) variables.
    # They share the group-100 b..e coefficients and swap only the constant (a) between
    # classes of the indicator (Report 26, Appendix C, p. 133). Published for volume over
    # bark, above stump; used here only when over_bark is True.
    #
    # Appendix C offers several indicators per species/region; the set used for each
    # below is the one selected here, tagged with its Appendix C table. Birch North has
    # no indicator function in the report, so it keeps the plain NorthBirch set.

    # --- Detailed Adjustment Coefficients for Southern Sites ---
    # Table 1.5, Birch South, latitude (BG) intervals <57 / 57-58.9 / >=59.
    BirchSouthWithLatitudeCoeff: List[float] = [0.0, 2.23818, -1.06930, 6.02015, -4.51472]
    BirchSouthWithLatitudeConstant: List[float] = [-0.89363, -0.85480, -0.84627]

    # Table 1.3, Pine South, latitude (BG) intervals <57 / 57-58.9 / >=59.
    PineSouthWithLatitudeCoeff: List[float] = [0.0, 1.83182, 0.07275, 2.12777, -1.09439]
    PineSouthWithLatitudeConstant: List[float] = [-1.40718, -1.41955, -1.41472]

    # Table 1.9, Spruce South, vegetation type (ST). The report gives four classes
    # (Hoegoert, Laagoert, Myr/Mager, Vaccinium-myrtillus); FIELDLAYER_TYPE_TO_INDEX maps
    # the finer field-layer codes onto them, with the poorest codes held at the last
    # (Vm) constant.
    SpruceSouthWithfieldlayerTypeCoeff: List[float] = [0.0, 1.99915, -0.46351, 2.84571, -1.59871]
    SpruceSouthWithfieldlayerTypeConstant: List[float] = [
        -1.01862,
        -1.02745,
        -1.02651,
        -1.03775,
        -1.03775,
        -1.03775,
    ]

    # --- Detailed Adjustment Coefficients for Northern Sites ---
    # Table 1.6, Pine North, latitude (BG) intervals <63 / 63-64.9 / 65-66.9 / >=67.
    PineNorthWithLatitudeCoeff: List[float] = [0.0, 1.93867, -0.04966, 1.81528, -0.80910]
    PineNorthWithLatitudeConstant: List[float] = [-1.30052, -1.29068, -1.28297, -1.28213]

    # Table 1.11, Spruce North, latitude x altitude combined. Rows are altitude (HH)
    # intervals <200 / 200-499 / >=500; columns are the four BG intervals above. The
    # last value is an extrapolated corner in the report.
    SpruceNorthWithLatitudeAndAltitudeCoeff: List[float] = [
        0.0,
        2.11123,
        -0.76342,
        3.07608,
        -1.78237,
    ]
    SpruceNorthWithLatitudeAndAltitudeConstant: List[List[float]] = [
        [-0.74910, -0.75384, -0.75549, -0.76640],
        [-0.75208, -0.75682, -0.75847, -0.76938],
        [-0.76488, -0.76962, -0.77127, -0.78218],
    ]

    # --- fieldlayer Mapping Array ---
    # Remaps 1-indexed fieldlayer codes to indices used for selecting spruce constants.
    FIELDLAYER_TYPE_TO_INDEX: List[int] = [
        0,
        0,
        0,
        0,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        2,
        3,
        3,
        3,
        4,
        5,
    ]
    # Backward-compatible alias for existing consumers.
    fieldlayerTypeToIndex: List[int] = FIELDLAYER_TYPE_TO_INDEX

    @staticmethod
    def get_volume_log(coeff: List[float], diameter_cm: float, height_m: float) -> float:
        """Evaluate a Brandel log-volume equation and return volume in dm3."""
        c0, c1, c2, c3, c4 = coeff
        if height_m <= 1.3:
            raise ValueError("height_m must be greater than 1.3")
        exponent = (
            c0
            + c1 * math.log10(diameter_cm)
            + c2 * math.log10(diameter_cm + 20)
            + c3 * math.log10(height_m)
            + c4 * math.log10(height_m - 1.3)
        )
        return 10**exponent

    @staticmethod
    def is_north(part_of_sweden: Optional[str], latitude: float) -> bool:
        """Return True when the site belongs to Brandel's northern region.

        Brandel's boundary follows administrative borders -- Norrland, Dalarna and
        northern Värmland -- with the 60th parallel as its stated proxy, so an explicit
        ``part_of_sweden`` of "north" or "south" wins over the latitude test. Any other
        value (including None or "middle") defers to latitude.
        """
        if part_of_sweden is not None:
            normalised = part_of_sweden.strip().lower()
            if normalised == "north":
                return True
            if normalised == "south":
                return False
        return latitude >= BrandelVolume.NORTH_SOUTH_LATITUDE_LIMIT

    @staticmethod
    def get_default_coefficients(
        is_north: bool,
        over_bark: bool = True,
        diameter_over_bark: bool = True,
    ) -> Dict[str, List[float]]:
        """Select an Appendix B function-01 set for the requested bark conventions.

        Raises:
            ValueError: for volume o.b. from a D.B.H. u.b., which Brandel does not
                publish.
        """
        if over_bark and not diameter_over_bark:
            raise ValueError(
                "Brandel (1990) publishes no function for volume over bark from a "
                "diameter under bark; pass diameter_over_bark=True or over_bark=False."
            )
        if over_bark:  # group 100
            if is_north:
                return {
                    "Pine": BrandelVolume.NorthPineCoeff,
                    "Spruce": BrandelVolume.NorthSpruceCoeff,
                    "Birch": BrandelVolume.NorthBirchCoeff,
                }
            return {
                "Pine": BrandelVolume.SouthPineCoeff,
                "Spruce": BrandelVolume.SouthSpruceCoeff,
                "Birch": BrandelVolume.SouthBirchCoeff,
            }
        if diameter_over_bark:  # group 300
            if is_north:
                return {
                    "Pine": BrandelVolume.NorthPineUbFromObCoeff,
                    "Spruce": BrandelVolume.NorthSpruceUbFromObCoeff,
                    "Birch": BrandelVolume.NorthBirchUbFromObCoeff,
                }
            return {
                "Pine": BrandelVolume.SouthPineUbFromObCoeff,
                "Spruce": BrandelVolume.SouthSpruceUbFromObCoeff,
                "Birch": BrandelVolume.SouthBirchUbFromObCoeff,
            }
        if is_north:  # group 200
            return {
                "Pine": BrandelVolume.NorthPineUbCoeff,
                "Spruce": BrandelVolume.NorthSpruceUbCoeff,
                "Birch": BrandelVolume.NorthBirchUbCoeff,
            }
        return {
            "Pine": BrandelVolume.SouthPineUbCoeff,
            "Spruce": BrandelVolume.SouthSpruceUbCoeff,
            "Birch": BrandelVolume.SouthBirchUbCoeff,
        }

    @staticmethod
    def get_coefficients(
        part_of_sweden: Optional[str],
        latitude: float,
        altitude: Optional[float],
        fieldlayer_type: Optional[Union[int, object]],
        over_bark: bool = True,
        diameter_over_bark: bool = True,
    ) -> Dict[str, List[float]]:
        """Pick the coefficient set for a site.

        The indicator-variable functions (Appendix C) are used when altitude and
        fieldlayer_type are both given and volume over bark is wanted; they are not
        published under bark, so any under-bark request falls back to Appendix B.

        Args:
            part_of_sweden: "north"/"south" to force the region; otherwise latitude
                decides on the 60th parallel.
            latitude: Site latitude in degrees.
            altitude: Site altitude in metres, or None to skip the detailed functions.
            fieldlayer_type: Vegetation type code, or None to skip the detailed
                functions.
            over_bark: Whether the returned volume is over bark.
            diameter_over_bark: Whether the diameter fed to the equation is measured
                over bark. Selects between Brandel's function groups 200 and 300.
        """
        north = BrandelVolume.is_north(part_of_sweden, latitude)

        if altitude is None or fieldlayer_type is None or not over_bark:
            return BrandelVolume.get_default_coefficients(north, over_bark, diameter_over_bark)

        # Detailed mode.
        if not north:
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
                field_layer_code = fieldlayer_type
            elif isinstance(fieldlayer_type, _HasCode):
                field_layer_code = int(fieldlayer_type.code)
            else:
                field_layer_code = 1
            if field_layer_code < 1 or field_layer_code > len(
                BrandelVolume.FIELDLAYER_TYPE_TO_INDEX
            ):
                mapped_index = 0
            else:
                mapped_index = BrandelVolume.FIELDLAYER_TYPE_TO_INDEX[field_layer_code - 1]
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
            spruce_coeff[0] = BrandelVolume.SpruceNorthWithLatitudeAndAltitudeConstant[alt_index][
                lat_index
            ]
            # No indicator-variable function is published for birch in the north.
            birch_coeff = deepcopy(BrandelVolume.NorthBirchCoeff)
        return {"Pine": pine_coeff, "Spruce": spruce_coeff, "Birch": birch_coeff}

    @staticmethod
    def _internal_get_tree_volume(
        height_m: float, diameter_cm: float, species: str, coeff_dict: Dict[str, List[float]]
    ) -> float:
        """
        Dispatches the volume calculation based on the species string.
        If diameter is below Brandel's validity limit, a ValueError is raised.
        """
        if diameter_cm < BrandelVolume.MIN_DIAMETER_CM:
            raise ValueError(f"Diameter must be at least {BrandelVolume.MIN_DIAMETER_CM} cm.")
        species_name = species.lower()
        # Here we check for keywords in species to select the appropriate coefficient group.
        if "pinus sylvestris" in species_name or "pine" in species_name:
            return (
                BrandelVolume.get_volume_log(coeff_dict["Pine"], diameter_cm, height_m) / 1000
            )  # dm3 to m3
        elif "picea abies" in species_name or "spruce" in species_name:
            return (
                BrandelVolume.get_volume_log(coeff_dict["Spruce"], diameter_cm, height_m) / 1000
            )  # dm3 to m3
        elif species_name.startswith("betula") or "birch" in species_name:
            return (
                BrandelVolume.get_volume_log(coeff_dict["Birch"], diameter_cm, height_m) / 1000
            )  # dm3 to m3
        else:
            raise ValueError(f"Species '{species}' not supported.")

    @staticmethod
    def get_volume(
        species: str,
        diameter_cm: float,
        height_m: float,
        latitude: float,
        altitude: Optional[float],
        field_layer: Optional[Union[int, object]],
        over_bark: bool = True,
        diameter_over_bark: bool = True,
    ) -> float:
        """
        Main entry point.
        Computes the stem volume above stump (V1), in m³, for a given species.

        Brandel's material covers D.B.H. o.b. from 4.5 cm and heights from 4.0 m for
        pine and spruce, 6.0 m for birch; results outside that range are extrapolations.

        Args:
            species: Species name or Latin binomial.
            diameter_cm: Diameter at breast height, in centimetres.
            height_m: Tree height above ground, in metres.
            latitude: Site latitude in degrees; the region splits on the 60th parallel.
            altitude: Site altitude in metres, or None to skip the detailed functions.
            field_layer: Vegetation type, as an int or an object with a 'code'
                attribute, or None to skip the detailed functions.
            over_bark: Whether the returned volume is over bark.
            diameter_over_bark: Whether diameter_cm is measured over bark. Leave True
                for an ordinary field measurement; set False only when passing a
                diameter already reduced by bark thickness.

        Returns:
            Stem volume above stump in m³.
        """
        coefficients_by_species: Dict[str, List[float]] = BrandelVolume.get_coefficients(
            None, latitude, altitude, field_layer, over_bark, diameter_over_bark
        )
        return BrandelVolume._internal_get_tree_volume(
            height_m,
            diameter_cm,
            species,
            coefficients_by_species,
        )


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


class _Descriptor:
    """FormulaModuleDescriptor for Brandel (1990) volume functions."""

    @property
    def component_id(self):
        return "brandel_1990_volume"

    @property
    def source(self):
        return SourceReference(
            author="Brandel, G.",
            year=1990,
            title="Volymfunktioner för enskilda träd: tall, gran och björk",
            note=(
                "Sveriges lantbruksuniversitet, institutionen för skogsproduktion, "
                "Rapport nr 26, Garpenberg, 72 s. ISBN 91-576-4030-0."
            ),
        )

    @property
    def species_groups(self):
        return {}

    @property
    def units(self):
        return {"diameter_cm": "cm", "height_m": "m", "return": "m³"}

    @property
    def kernel_names(self):
        return ["BrandelVolume"]


DESCRIPTOR = _Descriptor()
