"""Deterministic random number generators keyed by hierarchical identifiers."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional, Tuple

import numpy as np

if False:  # pragma: no cover - typing aid
    from .rng_bundle import RandomBundle


@dataclass
class KeyedRNG:
    """One reproducible random stream, identified by its path from the root seed.

    Two generators live behind this: a :class:`random.Random` for the scalar draws
    most kernels make, and a :class:`numpy.random.Generator` for the vectorised
    ones, reachable as :attr:`numpy`. Both are seeded from the *same* derived
    seed, and both are captured by :attr:`state`, so a checkpoint restores either.

    Keying is what makes that safe. Two generators seeded from one scalar and
    drawn from in the same code -- which is what the Elfving composite carried --
    make the interleaving of draws across the two an unwritten part of every
    result: reorder two calls that touch different streams and the numbers move.
    Streams reached by different paths (``rng.child("mortality")`` versus
    ``rng.child("ingrowth")``) are independent, so the order in which their owners
    happen to run cannot change what either produces.
    """

    _bundle: "RandomBundle"
    path: Tuple[str, ...]
    seed: int
    _numpy: Optional[np.random.Generator] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Seed this stream's generator from its derived seed."""
        self._random = random.Random(self.seed)

    @property
    def numpy(self) -> np.random.Generator:
        """This stream's NumPy generator, for vectorised draws.

        Created on first use and seeded from the same derived seed as the scalar
        generator, so a stream that only ever draws scalars costs nothing.
        """
        if self._numpy is None:
            self._numpy = np.random.default_rng(self.seed)
        return self._numpy

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
        """Return the serialisable state of both underlying generators.

        The NumPy state is included only once its generator exists, so a stream
        that has never drawn a vector does not force one into being just to be
        snapshotted -- and a checkpoint written before the first vectorised draw
        restores correctly into a run that makes one.
        """
        payload: dict[str, Any] = {"random": self._random.getstate()}
        if self._numpy is not None:
            payload["numpy"] = self._numpy.bit_generator.state
        return payload

    @state.setter
    def state(self, value: object) -> None:
        """Restore the state of both underlying generators."""
        if not isinstance(value, dict) or "random" not in value:
            # A checkpoint written before this stream carried a NumPy generator.
            self._random.setstate(value)
            return
        self._random.setstate(value["random"])
        if "numpy" in value:
            self.numpy.bit_generator.state = value["numpy"]

    def jumpahead(self, steps: int) -> None:
        """Advance the generator ``steps`` positions without yielding values."""

        for _ in range(int(steps)):
            self._random.random()

    def __getattr__(self, name: str):
        """Forward anything else to the scalar generator, e.g. ``gauss``.

        ``_random`` is built in :meth:`__post_init__` rather than being a field,
        so it is missing on an instance Python has allocated but not initialised
        -- which is exactly what ``copy.deepcopy`` and ``pickle`` do before they
        ask for ``__deepcopy__`` or ``__reduce_ex__``. Forwarding those lookups
        blindly sent us to ``self._random``, which was itself missing, which came
        back here: deep-copying or pickling a generator, or anything holding one,
        was a ``RecursionError`` naming nothing. The dunder guard is the same one
        :class:`~pyforestry.base.helpers.primitives.AgeMeasurement` and
        :class:`~pyforestry.base.helpers.primitives.TopHeightMeasurement` carry.

        Raises:
            AttributeError: If the generator has no such attribute, or if this
                instance has not been initialised.
        """
        if name.startswith("__") or name == "_random":
            raise AttributeError(name)
        return getattr(self._random, name)
