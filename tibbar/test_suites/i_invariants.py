# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""RV-I invariants suite: x0 stability and dependency-chain stress."""

from tibbar.core.funnels import SimpleFunnel
from tibbar.core.generator_base import GeneratorBase
from tibbar.sequences.i_extension import LongDependencyChains, X0InvariantStress
from tibbar.sequences.random_instrs import RandomSafeInstrs
from tibbar.sequences.sequences import DefaultProgramEnd, DefaultProgramStart, DefaultRelocate


class Generator(GeneratorBase):
    """Architectural invariant and dependency-focused integer suite."""

    def __init__(self, tibbar: object, **kwargs: object) -> None:
        super().__init__(tibbar, length=0)
        self.main_funnel = SimpleFunnel(tibbar)
        self.main_funnel.add_sequence(RandomSafeInstrs(tibbar, length=64))
        for _ in range(8):
            self.main_funnel.add_sequence(X0InvariantStress(tibbar))
            self.main_funnel.add_sequence(LongDependencyChains(tibbar, length=96))
            self.main_funnel.add_sequence(RandomSafeInstrs(tibbar, length=16))
        self.start_sequence = DefaultProgramStart(tibbar)
        self.end_sequence = DefaultProgramEnd(tibbar)
        self.relocate_sequence = DefaultRelocate(tibbar)
