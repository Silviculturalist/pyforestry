"""Deterministic seeding utilities for Monte Carlo simulations."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Tuple

import numpy as np

__all__ = [
    "SeedPolicy",
    "FixedSeedPolicy",
    "PerModuleOffsetPolicy",
    "RollingSeedPolicy",
]


def _stable_hash(*parts: str) -> int:
    """Return a deterministic 64-bit hash for the provided parts."""

    digest = hashlib.sha256("::".join(parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _key_to_str(key: Tuple[str, str]) -> str:
    return f"{key[0]}::{key[1]}"


def _str_to_key(value: str) -> Tuple[str, str]:
    stand_id, module_name = value.split("::", 1)
    return stand_id, module_name


def _capture_state(generator: np.random.Generator) -> Mapping[str, Any]:
    return generator.bit_generator.state


def _restore_state(state: Mapping[str, Any]) -> np.random.Generator:
    bit_name = state.get("bit_generator", "PCG64")
    bit_cls = getattr(np.random, bit_name)
    bit_gen = bit_cls()
    bit_gen.state = state
    return np.random.Generator(bit_gen)


class SeedPolicy:
    """Base class describing an RNG seeding strategy."""

    def start_run(self) -> None:
        """Initialise internal state before a simulation run begins."""

    def generator(self, stand_id: str, module_name: str) -> np.random.Generator:
        """Return a :class:`numpy.random.Generator` for the given module."""

        raise NotImplementedError

    def snapshot(self) -> Mapping[str, Any]:
        """Return a serialisable description of the RNG state."""

        raise NotImplementedError

    def restore(self, payload: Mapping[str, Any]) -> None:
        """Restore the policy state from :meth:`snapshot` output."""

        raise NotImplementedError


@dataclass
class FixedSeedPolicy(SeedPolicy):
    """Use a single seed for all modules and stands."""

    seed: int
    _generators: Dict[Tuple[str, str], np.random.Generator] = field(
        default_factory=dict, init=False, repr=False
    )

    def start_run(self) -> None:  # noqa: D401 - see base class docstring
        self._generators.clear()

    def generator(self, stand_id: str, module_name: str) -> np.random.Generator:
        key = (stand_id, module_name)
        if key not in self._generators:
            value = (self.seed + _stable_hash(stand_id, module_name)) % (2**32)
            self._generators[key] = np.random.default_rng(value)
        return self._generators[key]

    def snapshot(self) -> Mapping[str, Any]:
        return {
            "seed": self.seed,
            "streams": {_key_to_str(k): _capture_state(g) for k, g in self._generators.items()},
        }

    def restore(self, payload: Mapping[str, Any]) -> None:
        self.seed = int(payload.get("seed", self.seed))
        self.start_run()
        for key_str, state in payload.get("streams", {}).items():
            key = _str_to_key(key_str)
            self._generators[key] = _restore_state(state)


@dataclass
class PerModuleOffsetPolicy(SeedPolicy):
    """Base seed plus deterministic offsets for each module identifier."""

    base_seed: int
    offsets: Mapping[str, int]
    _generators: Dict[Tuple[str, str], np.random.Generator] = field(
        default_factory=dict, init=False, repr=False
    )

    def start_run(self) -> None:  # noqa: D401 - see base class docstring
        self._generators.clear()

    def generator(self, stand_id: str, module_name: str) -> np.random.Generator:
        key = (stand_id, module_name)
        if key not in self._generators:
            offset = int(self.offsets.get(module_name, 0))
            value = (self.base_seed + offset + _stable_hash(stand_id)) % (2**32)
            self._generators[key] = np.random.default_rng(value)
        return self._generators[key]

    def snapshot(self) -> Mapping[str, Any]:
        return {
            "base_seed": self.base_seed,
            "offsets": dict(self.offsets),
            "streams": {_key_to_str(k): _capture_state(g) for k, g in self._generators.items()},
        }

    def restore(self, payload: Mapping[str, Any]) -> None:
        self.base_seed = int(payload.get("base_seed", self.base_seed))
        self.offsets = dict(payload.get("offsets", self.offsets))
        self.start_run()
        for key_str, state in payload.get("streams", {}).items():
            key = _str_to_key(key_str)
            self._generators[key] = _restore_state(state)


@dataclass
class RollingSeedPolicy(SeedPolicy):
    """Assign sequential seeds to each module request while recording them."""

    base_seed: int
    _streams: Dict[Tuple[str, str], int] = field(default_factory=dict, init=False, repr=False)
    _next_offset: int = field(default=0, init=False, repr=False)
    _generators: Dict[Tuple[str, str], np.random.Generator] = field(
        default_factory=dict, init=False, repr=False
    )

    def start_run(self) -> None:  # noqa: D401 - see base class docstring
        self._streams.clear()
        self._generators.clear()
        self._next_offset = 0

    def generator(self, stand_id: str, module_name: str) -> np.random.Generator:
        key = (stand_id, module_name)
        if key not in self._generators:
            seed = (self.base_seed + self._next_offset) % (2**32)
            self._streams[key] = seed
            self._generators[key] = np.random.default_rng(seed)
            self._next_offset += 1
        return self._generators[key]

    def snapshot(self) -> Mapping[str, Any]:
        return {
            "base_seed": self.base_seed,
            "streams": {
                _key_to_str(k): {"seed": seed, "state": _capture_state(self._generators[k])}
                for k, seed in self._streams.items()
            },
            "next_offset": self._next_offset,
        }

    def restore(self, payload: Mapping[str, Any]) -> None:
        self.base_seed = int(payload.get("base_seed", self.base_seed))
        self._streams = {}
        self._generators = {}
        for key_str, data in payload.get("streams", {}).items():
            key = _str_to_key(key_str)
            seed = int(data.get("seed", self.base_seed))
            state = data.get("state")
            self._streams[key] = seed
            if state is not None:
                self._generators[key] = _restore_state(state)
            else:
                self._generators[key] = np.random.default_rng(seed)
        self._next_offset = int(payload.get("next_offset", len(self._streams)))
