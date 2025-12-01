"""RNG bundle providing keyed deterministic streams for simulations."""

from __future__ import annotations

import hashlib
from typing import Dict, Iterable, Tuple

from .keyed_rng import KeyedRNG


class RandomBundle:
    """Manage keyed random number generators derived from a root seed."""

    def __init__(self, seed: int) -> None:
        self.seed = int(seed)
        self._streams: Dict[Tuple[str, ...], KeyedRNG] = {}
        # Initialise the root generator so snapshotting always includes it.
        self._get_rng(())

    def _derive_seed(self, path: Tuple[str, ...]) -> int:
        if not path:
            return self.seed
        joined = "::".join(path).encode("utf8")
        seed_bytes = (self.seed & ((1 << 64) - 1)).to_bytes(8, "big")
        digest = hashlib.blake2b(joined, key=seed_bytes, digest_size=16)
        return int.from_bytes(digest.digest(), "big")

    def _normalize_path(self, keys: Iterable[object]) -> Tuple[str, ...]:
        return tuple(str(key) for key in keys)

    def _get_rng(self, path: Tuple[str, ...]) -> KeyedRNG:
        rng = self._streams.get(path)
        if rng is None:
            rng = KeyedRNG(self, path, self._derive_seed(path))
            self._streams[path] = rng
        return rng

    def rng_for(self, *keys: object) -> KeyedRNG:
        """Return a generator scoped by ``keys`` relative to the root seed."""

        return self._get_rng(self._normalize_path(keys))

    def snapshot(self) -> Dict[Tuple[str, ...], object]:
        """Return the states for all instantiated generators."""

        return {path: rng.state for path, rng in self._streams.items()}

    def restore(self, states: Dict[Tuple[str, ...], object]) -> None:
        """Restore generator states from ``states`` returned by :meth:`snapshot`."""

        self._streams.clear()
        self._get_rng(())
        for path, state in states.items():
            rng = self._get_rng(path)
            rng.state = state
