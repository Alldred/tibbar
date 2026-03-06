# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Simple test suite: random safe instructions and relative branching."""

from tibbar.core.funnels import SimpleFunnel
from tibbar.core.generator_base import GeneratorBase
from tibbar.sequences.branch_and_jump import RelativeBranching
from tibbar.sequences.random_instrs import RandomSafeInstrs
from tibbar.sequences.sequences import DefaultProgramEnd, DefaultProgramStart, DefaultRelocate

_SIMPLE_WARMUP_SAFE_LENGTH = 6000
_SIMPLE_BLOCK_COUNT = 25
_SIMPLE_BLOCK_MIN_LEN = 1
_SIMPLE_BLOCK_MAX_LEN = 100


class Generator(GeneratorBase):
    """Generator with variable-length RandomSafeInstrs and RelativeBranching."""

    def __init__(self, tibbar: object, **kwargs: object) -> None:
        super().__init__(tibbar, length=0)
        self.main_funnel = SimpleFunnel(tibbar)
        self.main_funnel.add_sequence(RandomSafeInstrs(tibbar, length=_SIMPLE_WARMUP_SAFE_LENGTH))
        for _ in range(_SIMPLE_BLOCK_COUNT):
            self.main_funnel.add_sequence(
                RandomSafeInstrs(
                    tibbar,
                    length=tibbar.random.randint(_SIMPLE_BLOCK_MIN_LEN, _SIMPLE_BLOCK_MAX_LEN),
                )
            )
            self.main_funnel.add_sequence(RelativeBranching(tibbar))
        self.start_sequence = DefaultProgramStart(tibbar)
        self.end_sequence = DefaultProgramEnd(tibbar)
        self.relocate_sequence = DefaultRelocate(tibbar)
