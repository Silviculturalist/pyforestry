"""Reproduce published Petterson (1955) yield tables and report the deviation.

Petterson, H. (1955). *Barrskogens volymproduktion*. Meddelanden från Statens
skogsforskningsinstitut, Band 45:1.  Part XIV of that volume tabulates a large
family of production tables ("P-tables").  This script regenerates a
representative table for each of the four species/region variants with
:mod:`pyforestry.sweden.systems.petterson_1955` and compares the result, cell by
cell, against the published numbers.

Run::

    python examples/reproduce_petterson_1955.py

Each table prints as the classic 16-column yield table; a summary line reports
the mean/max absolute deviation of the post-thinning stem number, basal area
and volume against the published values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

from pyforestry.sweden.systems.petterson_1955 import (
    PettersonStandInit,
    PettersonThinningProgram,
    petterson_simulate,
)


@dataclass(frozen=True)
class PublishedTable:
    """A published P-table used as a reproduction target."""

    label: str
    init: PettersonStandInit
    program: PettersonThinningProgram
    # published rows: (age, stems_after, ba_after_m2, volume_after_m3sk)
    rows: Sequence[Tuple[int, int, float, int]]


# ── Reproduction targets (one clean H100=20/24 table per variant) ────────────
TARGETS: List[PublishedTable] = [
    PublishedTable(
        "P.9  Tall, Norra Sverige, icke planterad.  H100=20.  L 5 G 6, 10",
        PettersonStandInit("pine", "north", 20.0, max_total_age=148),
        PettersonThinningProgram(low=5.0, through=6.0, interval=10.0),
        [
            (38, 5954, 18.6, 53),
            (48, 3936, 18.3, 67),
            (58, 2661, 18.2, 81),
            (68, 1843, 17.9, 95),
            (78, 1304, 17.5, 105),
            (88, 937, 16.7, 114),
            (98, 690, 16.0, 118),
            (108, 513, 15.0, 120),
            (118, 387, 14.0, 120),
            (128, 294, 12.9, 116),
            (138, 225, 11.8, 112),
            (148, 173, 10.7, 106),
        ],
    ),
    PublishedTable(
        "P.58 Tall, Södra Sverige, icke planterad.  H100=20.  L 5 G 10, 10",
        PettersonStandInit("pine", "south", 20.0, start_total_age=31, max_total_age=111),
        PettersonThinningProgram(low=5.0, through=10.0, interval=10.0),
        [
            (31, 4461, 17.6, 47),
            (41, 2703, 18.3, 64),
            (51, 1675, 17.8, 76),
            (61, 1063, 16.9, 84),
            (71, 690, 15.8, 88),
            (81, 455, 14.6, 89),
            (91, 307, 13.4, 87),
            (101, 209, 12.0, 83),
            (111, 145, 10.7, 77),
        ],
    ),
    PublishedTable(
        "P.83 Gran, Södra Sverige, icke planterad.  H100=24.  L 5 G 10, 5",
        PettersonStandInit("spruce", "south", 24.0, start_total_age=29, max_total_age=109),
        PettersonThinningProgram(low=5.0, through=10.0, interval=5.0),
        [
            (29, 5327, 17.7, 53),
            (34, 4157, 20.6, 73),
            (39, 3266, 22.0, 90),
            (44, 2580, 22.7, 105),
            (49, 2050, 22.9, 119),
            (54, 1636, 22.9, 131),
            (59, 1315, 22.7, 141),
            (64, 1061, 22.4, 150),
            (69, 860, 22.0, 157),
            (74, 700, 21.6, 163),
            (79, 572, 21.1, 166),
            (84, 468, 20.5, 168),
            (89, 386, 19.9, 169),
            (94, 317, 19.2, 167),
            (99, 263, 18.4, 165),
            (104, 218, 17.6, 162),
            (109, 181, 16.7, 156),
        ],
    ),
    PublishedTable(
        "P.72 Gran, Norra Sverige, icke planterad.  H100=20.  L 5 G 4, 10  (provisional)",
        PettersonStandInit("spruce", "north", 20.0, start_total_age=48, max_total_age=148),
        PettersonThinningProgram(low=5.0, through=4.0, interval=10.0),
        [
            (48, 2785, 7.6, 22),
            (58, 1920, 13.8, 53),
            (68, 1354, 16.4, 79),
            (78, 978, 18.0, 104),
            (88, 722, 18.2, 122),
            (98, 541, 17.5, 133),
            (108, 416, 16.5, 139),
            (118, 322, 15.2, 141),
            (128, 254, 13.8, 138),
            (138, 201, 12.4, 134),
            (148, 161, 11.2, 128),
        ],
    ),
    PublishedTable(
        "P.21 Tall, Norra Sverige, icke planterad.  H100=20.  H 3 G 10, 10  (high thinning)",
        PettersonStandInit("pine", "north", 20.0, max_total_age=168),
        PettersonThinningProgram(low=0.0, high=3.0, through=10.0, interval=10.0),
        [
            (38, 6764, 17.3, 48),
            (48, 5129, 16.1, 56),
            (58, 3889, 15.2, 63),
            (68, 2948, 14.3, 68),
            (78, 2237, 13.3, 71),
            (88, 1696, 12.3, 72),
            (98, 1287, 11.2, 72),
            (108, 975, 10.2, 70),
            (118, 740, 9.3, 68),
            (128, 562, 8.4, 65),
            (138, 426, 7.5, 61),
            (148, 323, 6.7, 56),
            (158, 245, 5.8, 52),
            (168, 186, 5.1, 47),
        ],
    ),
]

_HEADER = (
    "  Age  Hdom   Dg  Hgt |  N_bef  N_aft |  G_bef  G_aft |"
    " V_bef V_gal V_aft |  CAI  MAI | %N   %G   %V"
)


def _print_table(target: PublishedTable) -> Tuple[float, float, float, float, float, float]:
    result = petterson_simulate(target.init, target.program)
    published = {row[0]: row for row in target.rows}
    print(f"\n### {target.label}")
    print(_HEADER)
    n_err = ba_err = v_err = 0.0
    n_max = ba_max = v_max = 0.0
    count = 0
    for row in result.rows:
        cai = f"{row.cai_m3sk:4.1f}" if row.cai_m3sk is not None else "  - "
        print(
            f"  {row.total_age:3d} {row.dominant_height_m:5.1f}"
            f"{row.qmd_after_cm:5.1f}{row.mean_height_after_m:5.1f} |"
            f"{row.stems_before:7.0f}{row.stems_after:7.0f} |"
            f"{row.ba_before_m2:6.1f}{row.ba_after_m2:6.1f} |"
            f"{row.volume_before_m3sk:5.0f}{row.volume_removed_m3sk:5.0f}"
            f"{row.volume_after_m3sk:5.0f} | {cai}{row.mai_m3sk:5.1f} |"
            f"{row.thin_pct_stems:5.1f}{row.thin_pct_ba:5.1f}{row.thin_pct_volume:5.1f}"
        )
        ref = published.get(row.total_age)
        if ref is None:
            continue
        _, n_ref, ba_ref, v_ref = ref
        dn = abs(row.stems_after - n_ref) / n_ref * 100.0
        dba = abs(row.ba_after_m2 - ba_ref)
        dv = abs(row.volume_after_m3sk - v_ref) / v_ref * 100.0
        n_err += dn
        ba_err += dba
        v_err += dv
        n_max = max(n_max, dn)
        ba_max = max(ba_max, dba)
        v_max = max(v_max, dv)
        count += 1
    count = max(count, 1)
    return (
        n_err / count,
        ba_err / count,
        v_err / count,
        n_max,
        ba_max,
        v_max,
    )


def main() -> None:
    print("Reproducing Petterson (1955) yield tables (simulated vs published)")
    print("=" * 78)
    for target in TARGETS:
        n_mean, ba_mean, v_mean, n_max, ba_max, v_max = _print_table(target)
        print(
            f"  deviation vs published:  stems mean {n_mean:.2f}% (max {n_max:.1f}%)"
            f" | basal area mean {ba_mean:.2f} m2 (max {ba_max:.2f})"
            f" | volume mean {v_mean:.1f}% (max {v_max:.1f}%)"
        )
    print("\nColumns: Hdom=dominant height, Dg=basal-area mean-stem diameter (o.b.),")
    print("Hgt=its height, N=stems/ha, G=basal area o.b. m2/ha, V=volume u.b. m3sk/ha,")
    print("CAI/MAI=current/mean annual increment, %=thinning percentages. Values are")
    print("post-thinning where a before/after split applies.")


if __name__ == "__main__":
    main()
