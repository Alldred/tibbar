# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Base generator with start, main funnel, end, and relocate sequences."""

from tibbar.core.funnels import SimpleFunnel
from tibbar.sequences.branch_and_jump import RelativeBranching
from tibbar.sequences.ldst import Load, Store
from tibbar.sequences.random_instrs import RandomSafeInstrs
from tibbar.sequences.sequences import DefaultProgramEnd, DefaultProgramStart, DefaultRelocate


class GeneratorBase:
    def __init__(self, tibbar: object, length: int = 50) -> None:
        self.tibbar = tibbar
        self.main_funnel = SimpleFunnel(tibbar)
        self.main_funnel.add_sequence(RandomSafeInstrs(tibbar, length=length))
        self.main_funnel.add_sequence(Load(tibbar))
        self.main_funnel.add_sequence(Store(tibbar))
        self.main_funnel.add_sequence(RelativeBranching(tibbar))
        self.start_sequence = DefaultProgramStart(tibbar)
        self.end_sequence = DefaultProgramEnd(tibbar)
        self.relocate_sequence = DefaultRelocate(tibbar)

    def gen(self) -> object:
        yield from self.start_sequence.gen()
        yield from self.main_funnel.gen()
        yield from self.end_sequence.gen()
