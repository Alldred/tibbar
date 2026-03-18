# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Smoke tests for directed RV I-extension sequences."""

from __future__ import annotations

from tibbar.core.tibbar import Tibbar
from tibbar.sequences.i_extension import (
    BranchOutcomeControlled,
    DirectedALUEdges,
    DirectedComparePairs,
    DirectedShiftEdges,
    ImmBoundarySweep,
    JalJalrLinkCheck,
    LoadSignZeroExtend,
    LongDependencyChains,
    StoreLoadRoundTrip,
    X0InvariantStress,
)


class _EmptyGenerator:
    relocate_sequence = None

    def __init__(self, tibbar: Tibbar) -> None:
        self.tibbar = tibbar

    def gen(self):
        if False:
            yield None


def _make_tibbar(seed: int = 123) -> Tibbar:
    return Tibbar(
        generator_factory=lambda t: _EmptyGenerator(t),
        seed=seed,
        verbosity="error",
    )


def _assert_sequence_emits_decodable_instructions(seq: object, tibbar: Tibbar) -> None:
    out = list(seq.gen())
    emitted = [g for g in out if getattr(g, "seq", None) == seq.name]
    assert emitted, f"{seq.name} should emit at least one instruction"
    for g in emitted:
        assert isinstance(g.data, int)
        inst = tibbar.decoder.from_opc(int(g.data) & 0xFFFF_FFFF, pc=0)
        assert inst is not None


def test_directed_alu_edges_smoke() -> None:
    tibbar = _make_tibbar()
    _assert_sequence_emits_decodable_instructions(DirectedALUEdges(tibbar), tibbar)


def test_directed_shift_edges_smoke() -> None:
    tibbar = _make_tibbar()
    _assert_sequence_emits_decodable_instructions(DirectedShiftEdges(tibbar), tibbar)


def test_directed_compare_pairs_smoke() -> None:
    tibbar = _make_tibbar()
    _assert_sequence_emits_decodable_instructions(DirectedComparePairs(tibbar), tibbar)


def test_branch_outcome_controlled_smoke() -> None:
    tibbar = _make_tibbar()
    _assert_sequence_emits_decodable_instructions(BranchOutcomeControlled(tibbar), tibbar)


def test_jal_jalr_link_check_smoke() -> None:
    tibbar = _make_tibbar()
    _assert_sequence_emits_decodable_instructions(JalJalrLinkCheck(tibbar), tibbar)


def test_load_sign_zero_extend_smoke() -> None:
    tibbar = _make_tibbar()
    out = list(LoadSignZeroExtend(tibbar).gen())
    emitted = [g for g in out if getattr(g, "seq", None) == "LoadSignZeroExtend"]
    assert emitted
    assert any(getattr(g, "ldst_data", None) is not None for g in emitted)


def test_store_load_roundtrip_smoke() -> None:
    tibbar = _make_tibbar()
    _assert_sequence_emits_decodable_instructions(StoreLoadRoundTrip(tibbar), tibbar)


def test_imm_boundary_sweep_smoke() -> None:
    tibbar = _make_tibbar()
    _assert_sequence_emits_decodable_instructions(ImmBoundarySweep(tibbar), tibbar)


def test_x0_invariant_stress_smoke() -> None:
    tibbar = _make_tibbar()
    out = list(X0InvariantStress(tibbar).gen())
    emitted = [g for g in out if getattr(g, "seq", None) == "X0InvariantStress"]
    assert emitted
    ldst_addrs = [g.ldst_addr for g in emitted if getattr(g, "ldst_data", None) is not None]
    assert len(ldst_addrs) == len(set(ldst_addrs))
    hits_x0 = []
    for g in emitted:
        inst = tibbar.decoder.from_opc(int(g.data) & 0xFFFF_FFFF, pc=0)
        assert inst is not None
        if "rd" in getattr(inst, "operand_values", {}):
            hits_x0.append(inst.operand_values["rd"] == 0)
    assert any(hits_x0)


def test_long_dependency_chains_smoke() -> None:
    tibbar = _make_tibbar()
    seq = LongDependencyChains(tibbar, length=40)
    _assert_sequence_emits_decodable_instructions(seq, tibbar)
