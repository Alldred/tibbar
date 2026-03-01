# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Tests for resource reservation and RoundRobinFunnel with reserver."""

import pytest

from tibbar.core.funnels import RoundRobinFunnel
from tibbar.core.resource import (
    DictResourceSpace,
    ReservationError,
    ReservationKind,
    Reserver,
    ResourceId,
    ResourceSlot,
)
from tibbar.sequences.base import SequenceBase
from tibbar.sequences.reserving_examples import ExampleGPRSequence, ExampleSlotSequence
from tibbar.testobj import GenData

# --- DictResourceSpace / eumos-style dict ---


def test_dict_resource_space_all_resources():
    """DictResourceSpace builds ResourceIds from namespace -> list of ids."""
    space = DictResourceSpace(
        {
            "GPR": list(range(4)),
            "CSR": ["mstatus", "mie"],
        }
    )
    all_res = space.all_resources()
    assert ResourceId("GPR", 0) in all_res
    assert ResourceId("GPR", 3) in all_res
    assert ResourceId("CSR", "mstatus") in all_res
    assert ResourceId("CSR", "mie") in all_res
    assert len(all_res) == 6


def test_dict_resource_space_allocatable_from_namespace():
    """allocatable_from_namespace returns available minus exclude."""
    space = DictResourceSpace({"GPR": list(range(4))})
    exclude = frozenset({ResourceId("GPR", 0)})
    available = space.allocatable_from_namespace("GPR", 2, exclude)
    assert ResourceId("GPR", 1) in available
    assert ResourceId("GPR", 2) in available
    assert ResourceId("GPR", 3) in available
    assert ResourceId("GPR", 0) not in available


# --- Reserver ---


def test_reserver_exclusive_allocation():
    """Reserver allocates EXCLUSIVE from UNASSIGNED."""
    space = DictResourceSpace({"GPR": list(range(1, 5))})  # x1..x4
    reserver = Reserver(space)
    claim = reserver.request(
        1,
        {ReservationKind.EXCLUSIVE: [ResourceId("GPR", 1), ResourceId("GPR", 2)]},
    )
    assert claim is not None
    assert claim.exclusive == frozenset({ResourceId("GPR", 1), ResourceId("GPR", 2)})
    reserver.release(1)
    claim2 = reserver.request(2, {ReservationKind.EXCLUSIVE: [ResourceId("GPR", 1)]})
    assert claim2 is not None


def test_reserver_exclusive_conflict_returns_none():
    """Reserver returns None when EXCLUSIVE request conflicts."""
    space = DictResourceSpace({"GPR": list(range(1, 5))})
    reserver = Reserver(space)
    reserver.request(1, {ReservationKind.EXCLUSIVE: [ResourceId("GPR", 1)]})
    claim = reserver.request(2, {ReservationKind.EXCLUSIVE: [ResourceId("GPR", 1)]})
    assert claim is None


def test_reserver_resource_slot_allocation():
    """Reserver allocates ResourceSlot to concrete ResourceIds."""
    space = DictResourceSpace({"GPR": list(range(4))})
    reserver = Reserver(space)
    claim = reserver.request(1, {ReservationKind.EXCLUSIVE: [ResourceSlot("GPR", count=2)]})
    assert claim is not None
    assert len(claim.exclusive) == 2
    assert all(r.namespace == "GPR" for r in claim.exclusive)


def test_reserver_gpr0_raises_reservation_error():
    """Requesting GPR 0 (x0, zero register) raises ReservationError."""
    space = DictResourceSpace({"GPR": list(range(1, 8))})  # x1..x7
    reserver = Reserver(space)
    with pytest.raises(ReservationError, match="zero register"):
        reserver.request(1, {ReservationKind.EXCLUSIVE: [ResourceId("GPR", 0)]})
    with pytest.raises(ReservationError, match="zero register"):
        reserver.request(1, {ReservationKind.SHARED: [ResourceId("GPR", 0)]})


def test_reserver_shared_blocks_exclusive():
    """Resources allocated as SHARED cannot be claimed EXCLUSIVE by another."""
    space = DictResourceSpace({"GPR": list(range(1, 5))})
    reserver = Reserver(space)
    claim_a = reserver.request(1, {ReservationKind.SHARED: [ResourceId("GPR", 1)]})
    assert claim_a is not None
    claim_b = reserver.request(2, {ReservationKind.EXCLUSIVE: [ResourceId("GPR", 1)]})
    assert claim_b is None
    reserver.release(1)
    claim_b = reserver.request(2, {ReservationKind.EXCLUSIVE: [ResourceId("GPR", 1)]})
    assert claim_b is not None


# --- SequenceBase ---


def test_sequence_base_get_resource_requests_default():
    """SequenceBase.get_resource_requests returns empty dict by default."""

    class EmptySeq(SequenceBase):
        def __init__(self, tibbar):
            super().__init__(tibbar)

        def gen(self):
            yield GenData(data=0, seq="x")

    tibbar = None  # not used for this test
    seq = EmptySeq(tibbar)
    assert seq.get_resource_requests() == {}
    assert seq.reservation_claim is None


# --- RoundRobinFunnel: true round-robin without reserver ---


def test_round_robin_funnel_one_item_per_producer():
    """RoundRobinFunnel yields one item per producer per round (no reserver)."""

    class SeqA(SequenceBase):
        def __init__(self, tibbar):
            super().__init__(tibbar)

        def gen(self):
            yield 1
            yield 2
            yield 3

    class SeqB(SequenceBase):
        def __init__(self, tibbar):
            super().__init__(tibbar)

        def gen(self):
            yield 10
            yield 20

    class FakeTibbar:
        pass

    tibbar = FakeTibbar()
    funnel = RoundRobinFunnel(tibbar, reserver=None)
    funnel.add_sequence(SeqA(tibbar)).add_sequence(SeqB(tibbar))
    result = list(funnel.gen())
    assert len(result) == 5
    assert set(result) == {1, 2, 3, 10, 20}
    # True round-robin: first from A, then from B, then from A, ...
    assert result[0] == 1
    assert result[1] == 10
    assert result[2] == 2
    assert result[3] == 20
    assert result[4] == 3


# --- RoundRobinFunnel with reserver ---


def test_round_robin_funnel_with_reserver_interleaves():
    """With reserver, two sequences with disjoint EXCLUSIVE requests interleave."""
    from eumos import Eumos

    space = DictResourceSpace({"GPR": list(range(8))})
    reserver = Reserver(space)
    eumos = Eumos()

    # Minimal tibbar-like object so encode_instr works in example sequences
    class FakeTibbar:
        instrs = eumos.instructions

    tibbar = FakeTibbar()
    funnel = RoundRobinFunnel(tibbar, reserver=reserver)
    funnel.add_sequence(ExampleGPRSequence(tibbar, gpr_index=1))
    funnel.add_sequence(ExampleSlotSequence(tibbar))
    out = list(funnel.gen())
    assert len(out) >= 1
    assert all(hasattr(g, "data") for g in out)


def test_round_robin_funnel_raises_for_invalid_reservation_request():
    """Invalid reservation requests fail fast instead of spinning forever."""
    from eumos import Eumos

    space = DictResourceSpace({"GPR": list(range(8))})
    reserver = Reserver(space)
    eumos = Eumos()

    class FakeTibbar:
        instrs = eumos.instructions

    tibbar = FakeTibbar()
    funnel = RoundRobinFunnel(tibbar, reserver=reserver)
    funnel.add_sequence(ExampleGPRSequence(tibbar, gpr_index=0))  # x0 is invalid
    with pytest.raises(RuntimeError, match="Invalid resource request"):
        list(funnel.gen())


def test_eumos_reservable_resources():
    """reservable_resources() returns namespace -> ids; GPR 0 and read-only CSRs excluded."""
    from eumos import Eumos

    eu = Eumos()
    d = eu.reservable_resources()
    assert "GPR" in d
    assert "FPR" in d
    assert "CSR" in d
    # x0 is not writable (zero register); only x1..x31 are reservable
    assert d["GPR"] == list(range(1, eu.gpr_count))
    assert d["FPR"] == list(range(eu.fpr_count))
    # CSRs: only writable; read-only (access "RO") are excluded
    assert set(d["CSR"]).issubset(set(eu.csrs.keys()))
    for name in d["CSR"]:
        access = getattr(eu.csrs[name], "access", None)
        assert access is None or access.strip().upper() != "RO"
