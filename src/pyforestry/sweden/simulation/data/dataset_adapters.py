"""Minimal dataset adapters for Sweden preset execution."""

from __future__ import annotations


def stand_id_series(n_stands: int) -> list[int]:
    """Return deterministic stand ids for MVP preset runs."""
    if n_stands <= 0:
        raise ValueError("n_stands must be > 0")
    return list(range(1, n_stands + 1))
