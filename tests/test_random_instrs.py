# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Regression tests for RandomInstrs sampling path."""

from __future__ import annotations

import pytest
from eumos import Eumos
from eumos.instance import InstructionInstance
from lome import Lome

from tibbar.core.tibbar import Tibbar
from tibbar.sequences.random_instrs import RandomFloatInstrs, RandomSafeInstrs


class _EmptyGenerator:
    relocate_sequence = None

    def __init__(self, tibbar: Tibbar) -> None:
        self.tibbar = tibbar

    def gen(self):
        if False:
            yield None


def _make_tibbar() -> Tibbar:
    return Tibbar(
        generator_factory=lambda t: _EmptyGenerator(t),
        seed=1,
        verbosity="error",
    )


def test_random_safe_instrs_emits_requested_count_without_decode_rejection(monkeypatch) -> None:
    tibbar = _make_tibbar()
    original_from_opc = tibbar.decoder.from_opc
    decode_calls = 0

    def counting_from_opc(*args, **kwargs):
        nonlocal decode_calls
        decode_calls += 1
        return original_from_opc(*args, **kwargs)

    monkeypatch.setattr(tibbar.decoder, "from_opc", counting_from_opc)

    seq = RandomSafeInstrs(tibbar, length=40)
    out = list(seq.gen())
    emitted = [g for g in out if getattr(g, "seq", None) == seq.name]
    assert len(emitted) == 40
    # Sampling/round-trip should be near O(length), not O(length * 100).
    assert decode_calls < 2000

    for g in emitted:
        inst = original_from_opc(int(g.data) & 0xFFFF_FFFF)
        assert inst is not None
        assert inst.instruction.mnemonic in seq._i_only


def test_random_safe_instrs_can_emit_czero(monkeypatch) -> None:
    tibbar = _make_tibbar()
    seq = RandomSafeInstrs(tibbar, length=2)
    assert {"czero.eqz", "czero.nez"}.issubset(set(seq._i_only))

    original_choice = seq.random.choice
    forced = iter(["czero.eqz", "czero.nez"])

    def forced_choice(population):
        if population is seq._i_only:
            try:
                return next(forced)
            except StopIteration:
                return original_choice(population)
        return original_choice(population)

    monkeypatch.setattr(seq.random, "choice", forced_choice)

    out = list(seq.gen())
    emitted = [g for g in out if getattr(g, "seq", None) == seq.name]
    assert len(emitted) == 2

    decoded = [tibbar.decoder.from_opc(int(g.data) & 0xFFFF_FFFF) for g in emitted]
    assert all(inst is not None for inst in decoded)
    assert [inst.instruction.mnemonic for inst in decoded] == ["czero.eqz", "czero.nez"]


@pytest.mark.parametrize(
    ("mnemonic", "rs2", "expected"),
    [
        ("czero.eqz", 0, 0),
        ("czero.eqz", 7, 0x1234),
        ("czero.nez", 0, 0x1234),
        ("czero.nez", 7, 0),
    ],
)
def test_lome_executes_czero_semantics(mnemonic: str, rs2: int, expected: int) -> None:
    eumos = Eumos()
    model = Lome(eumos)
    model.reset()
    model.set_gpr(1, 0x1234)
    model.set_gpr(2, rs2)
    model.set_gpr(3, 0xDEAD)

    opc = InstructionInstance(
        instruction=eumos.instructions[mnemonic],
        operand_values={"rd": 3, "rs1": 1, "rs2": 2},
    ).to_opc()
    model.execute(opc)

    assert model.get_gpr(3) == expected
    assert model.get_pc() == 4


def test_random_float_instrs_emits_requested_count(monkeypatch) -> None:
    tibbar = _make_tibbar()
    original_from_opc = tibbar.decoder.from_opc
    decode_calls = 0

    def counting_from_opc(*args, **kwargs):
        nonlocal decode_calls
        decode_calls += 1
        return original_from_opc(*args, **kwargs)

    monkeypatch.setattr(tibbar.decoder, "from_opc", counting_from_opc)

    seq = RandomFloatInstrs(tibbar, length=30)
    out = list(seq.gen())
    emitted = [g for g in out if getattr(g, "seq", None) == seq.name]
    assert len(emitted) == 30
    assert decode_calls < 2000

    for g in emitted:
        inst = original_from_opc(int(g.data) & 0xFFFF_FFFF)
        assert inst is not None
        assert inst.instruction.mnemonic in seq._i_only
