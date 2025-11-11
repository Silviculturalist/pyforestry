"""Deterministic random number generators keyed by hierarchical identifiers."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, Tuple

if False:  # pragma: no cover - typing aid
    from .rng_bundle import RandomBundle


@dataclass
class KeyedRNG:
    """Wrap :class:`random.Random` instances with deterministic key derivation."""

    _bundle: "RandomBundle"
    path: Tuple[str, ...]
    seed: int

    def __post_init__(self) -> None:
        self._random = random.Random(self.seed)

    def random(self) -> float:
        """Return the next random floating point number in the range [0.0, 1.0)."""

        return self._random.random()

    def randint(self, a: int, b: int) -> int:
        """Return a random integer N such that ``a <= N <= b``."""

        return self._random.randint(a, b)

    def uniform(self, a: float, b: float) -> float:
        """Return a random floating point number ``N`` such that ``a <= N <= b``."""

        return self._random.uniform(a, b)

    def child(self, *keys: Iterable[str] | str) -> "KeyedRNG":
        """Return a derived generator scoped by ``keys`` relative to ``path``."""

        expanded: Tuple[str, ...] = self.path
        for key in keys:
            if isinstance(key, str):
                expanded += (key,)
            else:
                expanded += tuple(str(item) for item in key)
        return self._bundle.rng_for(*expanded)

    @property
    def state(self) -> object:
        """Return the serialisable state of the underlying generator."""

        return self._random.getstate()

    @state.setter
    def state(self, value: object) -> None:
        """Restore the state of the underlying generator."""

        self._random.setstate(value)

    def jumpahead(self, steps: int) -> None:
        """Advance the generator ``steps`` positions without yielding values."""

        for _ in range(int(steps)):
            self._random.random()

    def __getattr__(self, name: str):  # pragma: no cover - passthrough
        return getattr(self._random, name)
