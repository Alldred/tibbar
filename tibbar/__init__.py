# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Tibbar - RISC-V Instruction Stream Generator."""

TEST_SUITE_NAMES = (
    "ldst",
    "rel_branching",
    "simple",
    "float",
    "stress_float",
    "hazard",
    "ldst_exception",
    "i_alu",
    "i_control",
    "i_memory",
    "i_invariants",
    "i_mixed",
)


def get_suite_names() -> tuple[str, ...]:
    """Return the supported generator suite names."""
    return TEST_SUITE_NAMES
