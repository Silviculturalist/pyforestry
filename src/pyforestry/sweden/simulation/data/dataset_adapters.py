"""Stand identifiers for the artifact-contract harness.

Not a dataset adapter in any real sense; the module name is left over from a plan
for one. The harness in
:mod:`pyforestry.sweden.simulation.orchestration.runbook` runs no forest model --
it needs a deterministic set of stand ids to key its synthetic rows by, and this
is that.
"""

from __future__ import annotations


def stand_id_series(n_stands: int) -> list[int]:
    """Return ``n_stands`` consecutive stand ids, starting at 1.

    Args:
        n_stands: How many stands the artifact fixture covers.

    Returns:
        ``[1, 2, ..., n_stands]``.

    Raises:
        ValueError: If ``n_stands`` is not positive. A fixture over no stands
            would emit an empty summary that reads like a stand-free scenario
            rather than a caller mistake.
    """
    if n_stands <= 0:
        raise ValueError(f"n_stands must be > 0, got {n_stands!r}.")
    return list(range(1, n_stands + 1))
