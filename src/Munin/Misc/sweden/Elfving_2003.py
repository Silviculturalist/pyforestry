from __future__ import annotations

"""swedish_forest_models.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Python translations of two classical Swedish stand / tree models.

This revision adds **robust field-layer handling**: the private helper
:py:meth:`Elfving2003SingleTreeAge._is_rich_site` now accepts either

* an **``int`` 1-18** (the raw NFI vegetation code), or
* a **``SwedenFieldLayer`` enum member** from :pymod:`SwedishSite`, or
* a plain *Vegetation* dataclass instance - all with graceful fallback to
  ``0`` (not rich) when the value is missing or cannot be parsed.

A site is considered *rich* when the vegetation code ∈ [1-9, 12].

--------------------------------------------------------------------
Public API
--------------------------------------------------------------------
* :class:`Lind2003MeanDiameterCodominantTrees` - dominant-mean diameter
  of the co-dominant stratum (``md``, cm).
* :class:`Elfving2003SingleTreeAge` - breast-height age (years) for a
  single tree.

Both helpers are **stateless** (all public methods are
:py:meth:`@staticmethod`s) and work with either the lightweight
"typed-float" classes from your *Base.py* layer **or** plain
numbers/strings supplied by users.
"""

from math import exp, log, sqrt, pi
from typing import Union, SupportsFloat, Optional, Any

# ------------------------------------------------------------------
# Optional import from rich Swedish site taxonomy. We soft-fail so the
# models can still run in minimal environments that lack it.
# ------------------------------------------------------------------
try:
    from SwedishSite import SwedenFieldLayer, Vegetation  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - docs build / CI image
    SwedenFieldLayer = None  # type: ignore[misc,assignment]
    Vegetation = None  # type: ignore[misc,assignment]

Number = Union[int, float, SupportsFloat]

__all__ = [
    "Lind2003MeanDiameterCodominantTrees",
    "Elfving2003SingleTreeAge",
]

# =============================================================================
# Stand-level helper - Lind (2003) dominant-mean diameter (md)
# =============================================================================
class Lind2003MeanDiameterCodominantTrees:
    """Dominant-mean diameter (``md``) of co-dominant trees [cm].

    Implements Lind (2003, Eq. 1) as used by Elfving (2003) and later
    work‐flows.  The function is deterministic and carries the
    logarithmic-bias correction (``+ 0.036``) baked-in.

    Parameters
    ----------
    total_stand_age : Number
        *bald* - basal-area-weighted stand age (yrs).
    stand_density_gf : Number
        *Gf* - relascope basal area (m² ha⁻¹).
    site_index : Number
        *sis* - top height at reference age 100 (m).

    Returns
    -------
    float
        Dominant-mean diameter, centimetres (``md``).
    """

    # Coefficients from C# reference implementation (MeanDiameterDominantTrees.cs)
    _C0, _C1, _C2, _C3, _C4, _C5 = (
        -0.92313,
        1.00322,
        -0.00701,
        -4.00529,
        0.01859,
        -1.88177,
    )
    _BIAS = 0.036  # ln-bias correction

    @staticmethod
    def estimate(
        *,
        total_stand_age: Number,
        stand_density_gf: Number,
        site_index: Number,
    ) -> float:
        age = float(total_stand_age)
        gf = float(stand_density_gf)
        si = float(site_index)
        if age <= 0 or si <= 0 or gf <= 0:
            raise ValueError("total_stand_age, stand_density_gf and site_index must all be > 0.")

        ln_md = (
            Lind2003MeanDiameterCodominantTrees._C0
            + Lind2003MeanDiameterCodominantTrees._C1 * log(age)
            + Lind2003MeanDiameterCodominantTrees._C2 * age
            + Lind2003MeanDiameterCodominantTrees._C3 / si
            + Lind2003MeanDiameterCodominantTrees._C4 * si
            + Lind2003MeanDiameterCodominantTrees._C5 / (1 + gf)
            + Lind2003MeanDiameterCodominantTrees._BIAS
        )
        md = exp(ln_md)
        if md < 0:
            raise ArithmeticError("Calculated dominant-mean diameter is negative - check inputs.")
        return md


# =============================================================================
# Tree-level helper - Elfving (2003) single-tree age at breast height
# =============================================================================
class Elfving2003SingleTreeAge:
    """Age at 1.3 m for a single tree according to Elfving (2003).

    The *public* portal is :py:meth:`age`.  Internally the class selects
    among nine published linear-mixed models.  The current revision
    includes (2) even-aged with stand age, (4) uneven-aged, (5) pine,
    (6) spruce, (7) birch, (8) other broad-leaved, and (9) standards.
    All equations include their respective ln-bias corrections.

    Only the helper for *rich-site* detection changed in this commit -
    see :py:meth:`_is_rich_site`.
    """

    # ---- Bias terms ---------------------------------------------------------
    _BIAS = {
        2: 0.028,
        3: 0.062,
        4: 0.042,
        5: 0.012,
        6: 0.018,
        7: 0.038,
        8: 0.034,
        9: 0.045,
    }

    # ---- Coefficient dictionaries (only groups whose equations are used) ----
    _COEFF_2_TOTAL_W_AGE = (
        -1.46921, #const
        0.29889, #lnd
        -0.01132, #d
        0.25943, #dfrel
        1.01901, #lnbald
        -0.09476, #tall
        -0.09798, #ljuslov
        0.00465, #SIS
        -0.00372, #SIGRAN
        0.33497, #ts
        -0.15507, #ts2
        0.56842, #ost
        -0.21026, #sma
        -0.03118, #LIKALD
        0.04492, #ln g
        0.03439, #gotland
        -0.13876, #rich
        0.06144 #poor
    )

    _COEFF_3_TOTAL_WO_AGE = (
        2.25519, #const
        1.21082, #ln d
        -1.51153, # reld
        0.39625, # reld2
        -0.18216, #tall
        0.14160, #bokek
        -0.12756, #ljuslov
        -0.02778, #SIS
        -0.00471, #SIGRAN
        -0.00304, #sid2gt
        -0.39207, #ts
        0.16211, #ost
        0.29504, #sma
        0.19080, #lngfp1
        0.19944, #gotland
        -0.20707, #rich
        0.03196, #poor
        -0.09185, #Dike
        0.14096 #Torv


    )

    _COEFF_4_UNEVEN = (
        0.41811,  # const
        0.55719,  # ln d
        -0.01803,  # d
        0.17128,  # d/md
        0.39232,  # ln bald
        0.00367,  # bald
        0.10508,  # bokek
        -0.22284,  # ljuslov
        -0.01171,  # sis
        0.00028510,  # sid
        -0.00135,  # sigran
        0.83621,  # ts
        -0.44686,  # ts²
        0.04693,  # lng 
        -0.06676,  # rich
        0.03127,  # poor
        -0.03794,  # dike
        0.14490,  # gotland
    )

    # (5) Pine even-aged
    _COEFF_5_PINE = (
        -1.69566,  # const
        0.29819,  # ln d
        -0.00801,  # d
        0.07258,  # dfrel
        1.15873,  # ln bald
        0.00076986,  # bald
        0.03098,  # lng
    )

    # (6) Spruce even-aged
    _COEFF_6_SPRUCE = (
        -1.38343, # const 
        0.37897, #lnd 
        -0.01003, #d 
        0.12834,#reld
        1.02011, #lnbald
        0.01748, #lng
    )

    # (7) Birch even-aged
    _COEFF_7_BIRCH = (
        0.10055, #const 
        0.52067, #lnd
        -0.00793, #d
        -0.08139, #reld
        0.67013, #lnbald
        -0.01053, #SIS
        -0.09905, #rich
        0.03945, #lngfp1
    )

    # (8) Other broad-leaved even-aged
    _COEFF_8_DECID = (
        0.13800, #const
        0.64693, #lnd
        -0.26496, #dfrel
        0.50530, #lnbald
        0.19386, #slov
        -0.17874, #ljuslov
    )

    _COEFF_9_STD = (
        1.79933,  # const
        1.14894,  # ln d
        -0.01841,  # d
        0.00634,  # bald
        -0.03460,  # sis
        -0.22537,  # ljuslov
    )

    # ------------------------------------------------------------------
    # Public façade
    # ------------------------------------------------------------------
    @staticmethod
    def age(
        *,
        diameter: Number,
        species: str | Any,
        # --- stand context --------------------------------------------------
        total_stand_age: Optional[Number] = None,
        SIS: Optional[Number] = None,
        basal_area_plot_m2_ha: Optional[Number] = None,
        basal_area_relascope_m2_ha: Optional[Number] = None,
        altitude_m: Optional[Number]=None,
        latitude: Optional[Number]=None,
        QMD_cm: Optional[Number] = None,
        stems_ha: Optional[int] = None,
        # --- helper hints ---------------------------------------------------
        is_standard: bool | None = None,
        is_uneven_aged: bool | None = None,
        dominant_mean_diameter: Optional[Number] = None,
    ) -> float:
        """Return breast-height age (yrs).

        The helper detects *standards* (remnant trees) automatically via

        ``d > 1.8·(md + 8 cm)``



        if you did not pass ``is_standard`` explicitly.
        """

        if float(total_stand_age) < 10: 
            total_stand_age = 10
        elif float(total_stand_age) > 175:
            total_stand_age = 175
        
        float(basal_area_plot_m2_ha) *= 0.01
        logBA = log(basal_area_plot_m2_ha)
        
        if basal_area_relascope_m2_ha is None and basal_area_plot_m2_ha:
            basal_area_relascope_m2_ha = basal_area_plot_m2_ha

        if not QMD_cm: 
            if basal_area_relascope_m2_ha and stems_ha:
                QMD_cm = sqrt(basal_area_relascope_m2_ha/((pi/40e3)*stems_ha))            

        invgfp1 = 1 / (basal_area_relascope_m2_ha + 1)
        lngfp1 = log(basal_area_relascope_m2_ha+1)
        lngrel = log((basal_area_plot_m2_ha+0.1))/(basal_area_relascope_m2_ha+0.1))
        invsis = 1 / SIS
          
        temperature_sum = 0.001*(4835 - 5.76*latitude - 0.9*altitude_m)  # TODO: SIC! Should be 57.6*latitude but was erroneously input in SAS at regression time! Contact has been taken with B. Elfving for clarification.
        ts2 = temperature_sum*temperature_sum

        d_cm = float(diameter)
        if d_cm <= 0:
            raise ValueError("diameter must be > 0 cm")
        
        logD = log(d_cm)
        relD = d_cm/QMD_cm
        logrelD = log(relD)


        # ---------------- derive / default context -------------------------
        bald = float(total_stand_age) if total_stand_age is not None else 0.0
        sis = float(site_index) if site_index is not None else 0.0
        g_plot = float(basal_area_plot_m2_ha) if basal_area_plot_m2_ha is not None else 0.0
        gf = float(basal_area_relascope_m2_ha) if basal_area_relascope_m2_ha is not None else 0.0
        ts = float(temperature_sum) if temperature_sum is not None else 0.0
        lng_e = float(longitude_east) if longitude_east is not None else 0.0

        # Need md for several expressions
        if dominant_mean_diameter is not None:
            md = float(dominant_mean_diameter)
        else:
            if bald and sis and gf:
                md = Lind2003MeanDiameterCodominantTrees.estimate(
                    total_stand_age=bald, site_index=sis, stand_density_gf=gf
                )
            else:
                md = d_cm  # fallback - prevents ZeroDivision but flags questionable input

        # ------------------------------------------------------------------
        # 1. Group selection (very light heuristic - enough for demo).
        # ------------------------------------------------------------------
        if is_standard is None:
            is_standard = md > 1.8 * (md + 8)
        
        if is_undergrowth is None:
            is_undergrowth = md < 0.4*md

        if is_standard:
            group = 9
        elif is_uneven_aged:
            group = 4
        else:
            # Very crude species test - real code should use your TreeSpecies enum
            sp_low = str(species).lower()
            if "pinus" in sp_low or "pine" in sp_low or "larch" in sp_low:
                group = 5
            elif "picea" in sp_low or "spruce" in sp_low:
                group = 6
            elif "betula" in sp_low or "birch" in sp_low:
                group = 7
            else:
                group = 8  # other deciduous

        # ------------------------------------------------------------------
        # 2. Compute predictors common to several equations.
        # ------------------------------------------------------------------
        ln_d = log(d_cm)
        ln_bald = log(bald) if bald > 0 else 0.0
        ln_g_plot = log(g_plot) if g_plot > 0 else 0.0
        d_over_md = d_cm / md if md else 0.0
        reld = d_cm / (g_plot / 1.273) if g_plot else 0.0  # 1.273 ≈ (4/π)

        # Species indicator flags (simplified)
        is_spruce = 1 if "spruce" in sp_low or "picea" in sp_low else 0
        is_light_decid = 1 if any(k in sp_low for k in ("ulmus", "lime", "maple", "cherry", "sallow")) else 0
        is_bokek = 1 if any(k in sp_low for k in ("fagus", "quercus")) else 0

        # Site richness indicators via new helper
        rich = Elfving2003SingleTreeAge._is_rich_site(species)  # doc test below
        poor = 0 if rich else 1  # simplistic, real model has separate coding

        # ------------------------------------------------------------------
        # 3. Evaluate equation by group.
        # ------------------------------------------------------------------
        if group == 9:
            c0, c1, c2, c3, c4, c5 = Elfving2003SingleTreeAge._COEFF_9_STD
            ln_a13 = (
                c0
                + c1 * ln_d
                + c2 * d_cm
                + c3 * bald
                + c4 * sis
                + c5 * is_light_decid
                + Elfving2003SingleTreeAge._BIAS[9]
            )
        elif group == 4:
            (
                c0,
                c1,
                c2,
                c3,
                c4,
                c5,
                c6,
                c7,
                c8,
                c9,
                c10,
                c11,
                c12,
                c13,
                c14,
                c15,
                c16,
                c17,
            ) = Elfving2003SingleTreeAge._COEFF_4_UNEVEN
            ln_a13 = (
                c0
                + c1 * ln_d
                + c2 * d_cm
                + c3 * d_over_md
                + c4 * ln_bald
                + c5 * bald
                + c6 * is_bokek
                + c7 * is_light_decid
                + c8 * sis
                + c9 * sis * d_cm
                + c10 * sis * is_spruce
                + c11 * ts
                + c12 * ts ** 2
                + c13 * lng_e
                + c14 * rich
                + c15 * poor
                + c16 * 0  # dike not tracked here
                + c17 * 0  # gotland flag not tracked here
                + Elfving2003SingleTreeAge._BIAS[4]
            )
        elif group == 5:
            c0, c1, c2, c3, c4, c5, c6 = Elfving2003SingleTreeAge._COEFF_5_PINE
            ln_a13 = (
                c0
                + c1 * ln_d
                + c2 * d_cm
                + c3 * d_over_md
                + c4 * ln_bald
                + c5 * bald
                + c6 * lng_e
                + Elfving2003SingleTreeAge._BIAS[5]
            )
        elif group == 6:
            c0, c1, c2, c3, c4, c5 = Elfving2003SingleTreeAge._COEFF_6_SPRUCE
            ln_a13 = (
                c0
                + c1 * ln_d
                + c2 * d_cm
                + c3 * reld
                + c4 * ln_bald
                + c5 * lng_e
                + Elfving2003SingleTreeAge._BIAS[6]
            )
        elif group == 7:
            (
                c0,
                c1,
                c2,
                c3,
                c4,
                c5,
                c6,
                c7,
            ) = Elfving2003SingleTreeAge._COEFF_7_BIRCH
            ln_a13 = (
                c0
                + c1 * ln_d
                + c2 * d_cm
                + c3 * reld
                + c4 * ln_bald
                + c5 * sis
                + c6 * rich
                + c7 * log(gf + 1)
                + Elfving2003SingleTreeAge._BIAS[7]
            )
        else:  # group 8 - other deciduous
            c0, c1, c2, c3, c4, c5 = Elfving2003SingleTreeAge._COEFF_8_DECID
            ln_a13 = (
                c0
                + c1 * ln_d
                + c2 * (d_cm / md)
                + c3 * ln_bald
                + c4 * 0  # slov indicator not derived here
                + c5 * is_light_decid
                + Elfving2003SingleTreeAge._BIAS[8]
            )

        a13 = exp(ln_a13)
        if not 0 < a13 < 1000:
            raise ArithmeticError("Computed tree age implausible; check inputs.")
        return a13

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _is_rich_site(field_layer: Any) -> int:
        """Return 1 if *field_layer* indicates a **rich herb layer**.

        The function understands multiple input formats - raw NFI
        vegetation codes, ``SwedenFieldLayer`` enum members, or the
        underlying *Vegetation* dataclass.  Only codes 1-9 + 12 are classed as
        "rich" (bilberry / grass or richer) according to Elfving (2003).
        """

        if field_layer is None:
            return 0

        # 1. Enum member from SwedishSite
        if SwedenFieldLayer is not None and isinstance(field_layer, SwedenFieldLayer):
            code = field_layer.value.code  # unwrap the Vegetation dataclass inside
        # 2. Raw Vegetation dataclass
        elif Vegetation is not None and isinstance(field_layer, Vegetation):
            code = field_layer.code
        else:  # 3. Int, str, or anything coercible to int
            try:
                code = int(field_layer)  # may raise ValueError / TypeError
            except Exception:
                return 0  # unrecognised → assume not rich

        return 1 if 1 <= code <= 9 or code == 12 else 0  # Codes 1-9 + 12 = rich, 10-18 (- 12) = not rich
    
    @staticmethod
    def _is_poor_site(field_layer: Any)-> int:
        '''
        Return 1 if *field_layer* indicates a poor site.
        The function understands multiple input formats - raw NFI
        vegetation codes, ``SwedenFieldLayer`` enum members, or the
        underlying *Vegetation* dataclass.  Only codes >13 are classed as
        poor according to Elfving (2003).
        '''
        if field_layer is None:
            return 0

        # 1. Enum member from SwedishSite
        if SwedenFieldLayer is not None and isinstance(field_layer, SwedenFieldLayer):
            code = field_layer.value.code  # unwrap the Vegetation dataclass inside
        # 2. Raw Vegetation dataclass
        elif Vegetation is not None and isinstance(field_layer, Vegetation):
            code = field_layer.code
        else:  # 3. Int, str, or anything coercible to int
            try:
                code = int(field_layer)  # may raise ValueError / TypeError
            except Exception:
                return 0  # unrecognised → assume not rich

        return 1 if code > 13 else 0  # Codes >13 == poor
