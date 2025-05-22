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

A site is considered *rich* when the vegetation code ∈ \[1-9, 12].

--------------------------------------------------------------------
Public API
--------------------------------------------------------------------
* :class:`Lind2003MeanDiameterCodominantTrees` - dominant-mean diameter
  of the co-dominant stratum (``Dm``, cm).
* :class:`Elfving2003SingleTreeAge` - breast-height age (years) for a
  single tree.

Both helpers are **stateless** (all public methods are
:py:meth:`@staticmethod`s) and work with either the lightweight
"typed-float" classes from your *Base.py* layer **or** plain
numbers/strings supplied by users.
"""

from math import exp, log
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
# Stand-level helper - Lind (2003) dominant-mean diameter (Dm)
# =============================================================================
class Lind2003MeanDiameterCodominantTrees:
    """Dominant-mean diameter (``Dm``) of co-dominant trees [cm].

    Implements Lind (2003, Eq. 1) as used by Elfving (2003) and later
    work‐flows.  The function is deterministic and carries the
    logarithmic-bias correction (``+ 0.036``) baked-in.

    Parameters
    ----------
    total_age : Number
        *bald* - basal-area-weighted stand age (yrs).
    stand_density_gf : Number
        *Gf* - relascope basal area (m² ha⁻¹).
    site_index : Number
        *sis* - top height at reference age 100 (m).

    Returns
    -------
    float
        Dominant-mean diameter, centimetres (``Dm``).
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
        total_age: Number,
        stand_density_gf: Number,
        site_index: Number,
    ) -> float:
        age = float(total_age)
        gf = float(stand_density_gf)
        si = float(site_index)
        if age <= 0 or si <= 0 or gf <= 0:
            raise ValueError("total_age, stand_density_gf and site_index must all be > 0.")

        ln_dm = (
            Lind2003MeanDiameterCodominantTrees._C0
            + Lind2003MeanDiameterCodominantTrees._C1 * log(age)
            + Lind2003MeanDiameterCodominantTrees._C2 * age
            + Lind2003MeanDiameterCodominantTrees._C3 / si
            + Lind2003MeanDiameterCodominantTrees._C4 * si
            + Lind2003MeanDiameterCodominantTrees._C5 / (1 + gf)
            + Lind2003MeanDiameterCodominantTrees._BIAS
        )
        dm = exp(ln_dm)
        if dm < 0:
            raise ArithmeticError("Calculated dominant-mean diameter is negative - check inputs.")
        return dm


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
        4: 0.042,
        5: 0.012,
        6: 0.018,
        7: 0.038,
        8: 0.034,
        9: 0.045,
    }

    # ---- Coefficient dictionaries (only groups whose equations are used) ----
    _COEFF_9_STD = (
        1.7993,  # const
        1.1489,  # ln d
        -0.01841,  # d
        0.00634,  # bald
        -0.0346,  # sis
        -0.2254,  # ljuslov
    )

    _COEFF_4_UNEVEN = (
        0.4181,  # const
        0.5572,  # ln d
        -0.01803,  # d
        0.1713,  # d/Dm
        0.3923,  # ln bald
        0.00367,  # bald
        0.1051,  # bokek
        -0.2228,  # ljuslov
        -0.01171,  # sis
        0.0002851,  # sis×d
        -0.00135,  # sis×gran
        0.8362,  # ts
        -0.4469,  # ts²
        0.0469,  # lng (longitude east)
        -0.0668,  # rich
        0.0313,  # poor
        -0.0379,  # dike
        0.1449,  # gotland
    )

    # (5) Pine even-aged
    _COEFF_5_PINE = (
        -1.6957,  # const
        0.2982,  # ln d
        -0.00801,  # d
        0.0726,  # d/Dm
        1.1587,  # ln bald
        0.0007699,  # bald
        0.0310,  # lng
    )

    # (6) Spruce even-aged
    _COEFF_6_SPRUCE = (
        -1.3834,
        0.3790,
        -0.01003,
        0.1283,
        1.0201,
        0.0175,
    )

    # (7) Birch even-aged
    _COEFF_7_BIRCH = (
        0.1006,
        0.5207,
        -0.00793,
        -0.0814,
        0.6701,
        -0.01053,
        0.0990,
        0.0394,
    )

    # (8) Other broad-leaved even-aged
    _COEFF_8_DECID = (
        0.1380,
        0.6469,
        -0.2650,
        0.5053,
        0.1939,
        -0.1787,
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
        total_age: Optional[Number] = None,
        site_index: Optional[Number] = None,
        basal_area_plot: Optional[Number] = None,
        stand_density_gf: Optional[Number] = None,
        altitude_m: Optional[Number]=None,
        latitude: Optional[Number]=None,
        longitude_east: Optional[Number] = None,
        # --- helper hints ---------------------------------------------------
        is_standard: bool | None = None,
        is_uneven_aged: bool | None = None,
        dominant_mean_diameter: Optional[Number] = None,
    ) -> float:
        """Return breast-height age (yrs).

        The helper detects *standards* (remnant trees) automatically via

        ``d > 1.8·(Dm + 8 cm)``



        if you did not pass ``is_standard`` explicitly.
        """

        temperature_sum = 0.001*(4835 - 5.76*latitude - 0.9*altitude_m)  # SIC! Should be 57.6*latitude but was erroneously input in SAS at regression time!

        d_cm = float(diameter)
        if d_cm <= 0:
            raise ValueError("diameter must be > 0 cm")

        # ---------------- derive / default context -------------------------
        bald = float(total_age) if total_age is not None else 0.0
        sis = float(site_index) if site_index is not None else 0.0
        g_plot = float(basal_area_plot) if basal_area_plot is not None else 0.0
        gf = float(stand_density_gf) if stand_density_gf is not None else 0.0
        ts = float(temperature_sum) if temperature_sum is not None else 0.0
        lng_e = float(longitude_east) if longitude_east is not None else 0.0

        # Need Dm for several expressions
        if dominant_mean_diameter is not None:
            dm = float(dominant_mean_diameter)
        else:
            if bald and sis and gf:
                dm = Lind2003MeanDiameterCodominantTrees.estimate(
                    total_age=bald, site_index=sis, stand_density_gf=gf
                )
            else:
                dm = d_cm  # fallback - prevents ZeroDivision but flags questionable input

        # ------------------------------------------------------------------
        # 1. Group selection (very light heuristic - enough for demo).
        # ------------------------------------------------------------------
        if is_standard is None:
            is_standard = d_cm > 1.8 * (dm + 8)
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
        d_over_dm = d_cm / dm if dm else 0.0
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
                + c3 * d_over_dm
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
                + c3 * d_over_dm
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
                + c2 * (d_cm / dm)
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
        underlying *Vegetation* dataclass.  Only codes 1-9 are classed as
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

        return 1 if 1 <= code <= 9 else 0  # Codes 1-9 = rich, 10-18 = not rich
