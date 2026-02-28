# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Regression tests for LoadGPR immediate expansion."""

from tibbar.sequences.sequences import LoadGPR


def test_loadgpr_uses_signed_i_type_immediates(monkeypatch):
    """I-type immediates emitted by LoadGPR must be signed 12-bit values."""

    calls: list[tuple[str, dict[str, int]]] = []

    def fake_encode_instr(tibbar: object, mnemonic: str, **operand_values: int) -> int:
        calls.append((mnemonic, dict(operand_values)))
        return 0x13

    monkeypatch.setattr("tibbar.sequences.sequences.encode_instr", fake_encode_instr)

    # Seed-42 regression reproducer from rheon_run simple suite.
    problematic = 18446744073709550737
    seq = LoadGPR(tibbar=object(), reg_idx=1, value=problematic, name="regression")
    list(seq.gen())

    i_type_imms = [
        operand_values["imm"]
        for mnemonic, operand_values in calls
        if mnemonic in {"addi", "addiw"} and "imm" in operand_values
    ]
    assert i_type_imms, "Expected LoadGPR to emit at least one I-type immediate"
    assert all(-2048 <= imm <= 2047 for imm in i_type_imms)
