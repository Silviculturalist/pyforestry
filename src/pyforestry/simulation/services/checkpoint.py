"""Capture a running simulation's state, and put it back.

A checkpoint is what a run would need to be resumed somewhere else: in another
process, after a crash, or at the head of a branching scenario that explores two
managements from one common history. It is not a copy of the object -- a pipeline
holds its model, its price list and its steps, all of which are rebuilt from
configuration and none of which change while the run advances.

That distinction is the whole design. The evolving state is named by the object
that owns it, through :class:`Checkpointable`, rather than discovered here by
walking ``__dict__``. A composite pipeline's phases are frozen dataclasses each
holding a back-reference to the pipeline, so a blanket ``deepcopy`` of its
attributes would drag the model, the mortality engine and every step into the
snapshot, and restore a pipeline whose steps point at the *previous* one. Asking
the object what its state is keeps the answer where the answer is known.

This module stays region-neutral for the same reason the rest of
``simulation/services`` does: it is imported by the Sweden and Norway runtimes,
and must not import either.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class Checkpointable(Protocol):
    """Something that can name its evolving state and take it back.

    Two methods, and a contract between them: whatever ``checkpoint_state``
    returns, ``restore_checkpoint_state`` must accept, and a subject restored from
    a checkpoint must advance exactly as the subject it was captured from would
    have. Derived values -- caches, anything rebuilt from configuration -- belong
    outside the mapping, and anything rebuilt *from* restored state (a mortality
    engine drawing on the run's generator) should be rebuilt by
    ``restore_checkpoint_state`` itself.
    """

    def checkpoint_state(self) -> Mapping[str, Any]:
        """Return the evolving state of this object, by name."""
        ...

    def restore_checkpoint_state(self, state: Mapping[str, Any]) -> None:
        """Adopt a state mapping previously returned by :meth:`checkpoint_state`."""
        ...


@dataclass(frozen=True)
class Checkpoint:
    """One subject's evolving state, detached from the subject.

    Attributes:
        component_id: What the checkpoint was taken from. :meth:`
            CheckpointSerializer.restore` refuses a checkpoint whose id does not
            match its target, because the failure it prevents is silent: two
            pipelines expose the same state names, so restoring a Sweden
            checkpoint into a Norway run would succeed and mean nothing.
        state: The state mapping, deep-copied away from the live objects so that
            advancing the run does not edit the checkpoint underneath it.
    """

    component_id: str
    state: Mapping[str, Any]


class CheckpointSerializer:
    """Move state between a live subject and a :class:`Checkpoint`."""

    def capture(self, subject: Checkpointable) -> Checkpoint:
        """Return a checkpoint of ``subject`` as it stands now.

        Args:
            subject: Any :class:`Checkpointable` -- in practice a composite
                pipeline part-way through a projection.

        Returns:
            A :class:`Checkpoint` holding a deep copy of the subject's state.

        Raises:
            TypeError: If ``subject`` does not implement :class:`Checkpointable`.
        """
        self._require_checkpointable(subject, "capture")
        return Checkpoint(
            component_id=self._component_id(subject),
            state=deepcopy(dict(subject.checkpoint_state())),
        )

    def restore(self, subject: Checkpointable, checkpoint: Checkpoint) -> None:
        """Put ``checkpoint`` back into ``subject``, in place.

        The state is deep-copied on the way in as well as on the way out, so one
        checkpoint can seed any number of runs -- which is the point of taking one
        before a branching decision -- without those runs sharing tree objects.

        Args:
            subject: The object to restore into.
            checkpoint: A checkpoint taken from a subject with the same
                ``component_id``.

        Raises:
            TypeError: If ``subject`` does not implement :class:`Checkpointable`.
            ValueError: If the checkpoint was taken from a different component.
        """
        self._require_checkpointable(subject, "restore")
        target = self._component_id(subject)
        if checkpoint.component_id != target:
            raise ValueError(
                f"Checkpoint was taken from {checkpoint.component_id!r} and cannot be "
                f"restored into {target!r}. The two expose the same state names, so "
                f"this would otherwise succeed and produce a run that means nothing."
            )
        subject.restore_checkpoint_state(deepcopy(dict(checkpoint.state)))

    @staticmethod
    def _require_checkpointable(subject: object, action: str) -> None:
        """Raise unless ``subject`` implements both halves of the protocol."""
        missing = [
            name
            for name in ("checkpoint_state", "restore_checkpoint_state")
            if not callable(getattr(subject, name, None))
        ]
        if missing:
            raise TypeError(
                f"Cannot {action} {type(subject).__name__}: it does not implement "
                f"Checkpointable ({', '.join(missing)} missing)."
            )

    @staticmethod
    def _component_id(subject: object) -> str:
        """Name the subject, preferring its declared component id."""
        declared = getattr(subject, "component_id", None)
        return str(declared) if isinstance(declared, str) else type(subject).__name__
