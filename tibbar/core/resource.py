# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Resource reservation types for interleaving sequences safely."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceId:
    """Concrete reference to a specific resource (e.g. 'I want x5')."""

    namespace: str  # e.g. "GPR", "FPR", "CSR"
    identifier: str | int  # e.g. 5, "mstatus"


@dataclass(frozen=True)
class ResourceSlot:
    """Abstract request (e.g. 'I want a GPR', allocator picks)."""

    namespace: str
    count: int = 1


class ReservationKind:
    """Reservation kind constants. Use as dict keys for resource requests."""

    EXCLUSIVE = "exclusive"  # Only this sequence can write
    SHARED = "shared"  # May write; others may too


@dataclass
class AllocatedClaim:
    """Result of a successful reservation request. Maps slots to allocated ResourceIds."""

    exclusive: frozenset[ResourceId]
    shared: frozenset[ResourceId]


class ResourceSpace(ABC):
    """Defines the set of resources that can be reserved."""

    @abstractmethod
    def all_resources(self) -> frozenset[ResourceId]:
        """Return all reservable resources."""
        ...

    @abstractmethod
    def allocatable_from_namespace(
        self,
        namespace: str,
        count: int,
        exclude: frozenset[ResourceId],
    ) -> frozenset[ResourceId]:
        """
        Return resources that can be allocated from namespace.

        Args:
            namespace: Resource namespace (e.g. "GPR").
            count: Number of resources needed.
            exclude: Resources to exclude from the pool (e.g. EXCLUSIVE holds).

        Returns:
            Set of ResourceIds that could be allocated. Size may be >= count.
        """
        ...


SequenceId = int


class Reserver:
    """
    Centralised resource reservation. All sequences share this instance.

    Maintains three pools: UNASSIGNED (free), EXCLUSIVE (held per sequence),
    SHARED (available for overlapping use = all - EXCLUSIVE).
    """

    def __init__(self, resource_space: ResourceSpace) -> None:
        self._resource_space = resource_space
        self._all_resources = resource_space.all_resources()
        self._unassigned: set[ResourceId] = set(self._all_resources)
        self._exclusive: dict[SequenceId, frozenset[ResourceId]] = {}
        self._shared: dict[SequenceId, frozenset[ResourceId]] = {}
        self._shared_refcount: dict[ResourceId, int] = {}

    def request(
        self,
        sequence_id: SequenceId,
        requests: dict[str, list[ResourceId | ResourceSlot]],
    ) -> AllocatedClaim | None:
        """
        Allocate resources from requests. All-or-nothing: succeeds fully or fails.

        EXCLUSIVE from UNASSIGNED; SHARED from (all - EXCLUSIVE).
        Returns None if cannot satisfy full request.
        Raises ReservationError if the request is invalid (e.g. GPR 0 cannot be reserved).
        """
        if sequence_id in self._exclusive or sequence_id in self._shared:
            return None  # Already allocated; caller must release first

        exclusive_requests = requests.get(ReservationKind.EXCLUSIVE, [])
        shared_requests = requests.get(ReservationKind.SHARED, [])

        # GPR 0 (x0) is the zero register: not writable, always zero. Cannot be reserved.
        _ZERO_REG = ResourceId("GPR", 0)
        for req in exclusive_requests + shared_requests:
            if isinstance(req, ResourceId) and req == _ZERO_REG:
                raise ReservationError("GPR 0 (x0) is the zero register and cannot be reserved.")

        exclusive_holds = set()
        for holds in self._exclusive.values():
            exclusive_holds.update(holds)
        shared_holds = set()
        for holds in self._shared.values():
            shared_holds.update(holds)
        exclusive_exclude = frozenset(exclusive_holds | shared_holds)

        exclusive_available = self._unassigned - exclusive_exclude
        exclusive_needed: set[ResourceId] = set()
        for req in exclusive_requests:
            if isinstance(req, ResourceId):
                if req not in exclusive_available:
                    return None
                exclusive_needed.add(req)
            else:
                available = self._resource_space.allocatable_from_namespace(
                    req.namespace, req.count, exclusive_exclude
                )
                candidates = available & exclusive_available
                if len(candidates) < req.count:
                    return None
                picked = list(candidates)[: req.count]
                exclusive_needed.update(picked)

        shared_exclude = frozenset(exclusive_holds | exclusive_needed)

        shared_needed: set[ResourceId] = set()
        for req in shared_requests:
            if isinstance(req, ResourceId):
                if req in shared_exclude:
                    return None
                shared_needed.add(req)
            else:
                available = self._resource_space.allocatable_from_namespace(
                    req.namespace, req.count, shared_exclude
                )
                shared_pool = self._all_resources - shared_exclude
                candidates = available & shared_pool
                if len(candidates) < req.count:
                    return None
                picked = list(candidates)[: req.count]
                shared_needed.update(picked)

        if exclusive_needed & shared_needed:
            return None

        self._unassigned -= exclusive_needed
        if exclusive_needed:
            self._exclusive[sequence_id] = frozenset(exclusive_needed)
        if shared_needed:
            self._shared[sequence_id] = frozenset(shared_needed)
            for r in shared_needed:
                prev = self._shared_refcount.get(r, 0)
                self._shared_refcount[r] = prev + 1
                if prev == 0:
                    self._unassigned.discard(r)

        return AllocatedClaim(
            exclusive=frozenset(exclusive_needed),
            shared=frozenset(shared_needed),
        )

    def release(self, sequence_id: SequenceId) -> None:
        """Release all EXCLUSIVE and SHARED holds for this sequence."""
        if sequence_id in self._exclusive:
            self._unassigned.update(self._exclusive[sequence_id])
            del self._exclusive[sequence_id]
        if sequence_id in self._shared:
            for r in self._shared[sequence_id]:
                self._shared_refcount[r] -= 1
                if self._shared_refcount[r] == 0:
                    del self._shared_refcount[r]
                    self._unassigned.add(r)
            del self._shared[sequence_id]


class DictResourceSpace(ResourceSpace):
    """
    ResourceSpace built from a dict of namespace -> list of identifiers.

    Eumos.reservable_resources() returns such a dict. This class wraps it
    for use with Reserver.
    """

    def __init__(self, resource_sets: dict[str, list[int | str]]) -> None:
        self._resources: set[ResourceId] = set()
        self._by_namespace: dict[str, set[ResourceId]] = {}
        for namespace, ids in resource_sets.items():
            for id_ in ids:
                rid = ResourceId(namespace, id_)
                self._resources.add(rid)
                self._by_namespace.setdefault(namespace, set()).add(rid)

    def all_resources(self) -> frozenset[ResourceId]:
        return frozenset(self._resources)

    def allocatable_from_namespace(
        self,
        namespace: str,
        count: int,
        exclude: frozenset[ResourceId],
    ) -> frozenset[ResourceId]:
        available = self._by_namespace.get(namespace, set()) - exclude
        return frozenset(available)


class ReservationError(RuntimeError):
    """Raised when resource reservation fails (all-or-nothing)."""

    pass
