"""Reusable tree-list metrics that operate on ordered collections of trees.

Currently this module exposes :func:`basal_area_larger`, the "basal area of
larger trees" (BAL) competition index used by many individual-tree growth
models.
"""

from typing import List, Sequence

__all__ = ["basal_area_larger"]


def basal_area_larger(
    sizes: Sequence[float],
    basal_areas: Sequence[float],
) -> List[float]:
    """Basal area of all trees larger than each tree (the BAL competition index).

    For every element ``i`` the returned value is the sum of ``basal_areas`` over
    all elements whose ``sizes`` value is strictly greater than ``sizes[i]``.
    Trees that tie on ``sizes`` therefore all receive the same BAL -- the sum of
    the strictly larger trees only -- which is the conventional definition.

    The result is aligned to the input order (``result[i]`` corresponds to
    ``sizes[i]``). The computation is ``O(n log n)`` (one sort plus a single
    linear cumulative pass), so it stays efficient for large tree lists.

    Parameters
    ----------
    sizes:
        The ordering key for each tree, typically diameter at breast height in
        centimetres. Larger means "more dominant".
    basal_areas:
        The basal area contributed by each tree, in whatever unit the caller
        wants BAL expressed in (e.g. m²/ha after applying per-hectare expansion
        factors). Must be the same length as ``sizes``.

    Returns
    -------
    list[float]
        BAL for each input tree, in the original input order.

    Raises
    ------
    ValueError
        If ``sizes`` and ``basal_areas`` have different lengths.

    Examples
    --------
    >>> basal_area_larger([30.0, 20.0, 20.0, 10.0], [3.0, 2.0, 2.0, 1.0])
    [0.0, 3.0, 3.0, 7.0]
    """
    n = len(sizes)
    if len(basal_areas) != n:
        raise ValueError("sizes and basal_areas must have the same length.")

    # Indices sorted from largest to smallest tree.
    order = sorted(range(n), key=lambda i: sizes[i], reverse=True)

    result = [0.0] * n
    cumulative = 0.0  # basal area of all strictly-larger trees seen so far
    i = 0
    while i < n:
        # Group together the run of equal-sized trees starting at position i so
        # that ties share the BAL of the strictly-larger trees.
        current_size = sizes[order[i]]
        group_sum = 0.0
        j = i
        while j < n and sizes[order[j]] == current_size:
            group_sum += basal_areas[order[j]]
            j += 1
        for k in range(i, j):
            result[order[k]] = cumulative
        cumulative += group_sum
        i = j

    return result
