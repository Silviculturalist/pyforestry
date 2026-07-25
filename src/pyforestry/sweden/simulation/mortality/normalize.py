"""Normalization helpers for unified mortality context."""

from __future__ import annotations

from dataclasses import replace

from .context import MortalityContext, MortalityHistoryConditions


def normalize_mortality_context(context: MortalityContext) -> MortalityContext:
    """Return normalized context with copied mutable fields and non-null history."""
    history = context.history if context.history is not None else MortalityHistoryConditions()
    return replace(
        context,
        trees=[replace(tree, metadata=dict(tree.metadata)) for tree in context.trees],
        stand=replace(
            context.stand,
            species_basal_area_m2_ha=(
                dict(context.stand.species_basal_area_m2_ha)
                if context.stand.species_basal_area_m2_ha is not None
                else None
            ),
        ),
        history=history,
    )


__all__ = ["normalize_mortality_context"]
