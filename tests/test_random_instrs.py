# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Regression tests for RandomInstrs sampling path."""

from __future__ import annotations

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
