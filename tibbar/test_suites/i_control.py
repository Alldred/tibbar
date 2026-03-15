# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""RV-I control-flow suite: directed branch and jump/link behavior."""

from tibbar.core.funnels import SimpleFunnel
from tibbar.core.generator_base import GeneratorBase
from tibbar.sequences.branch_and_jump import RelativeBranching
from tibbar.sequences.i_extension import BranchOutcomeControlled, JalJalrLinkCheck
from tibbar.sequences.random_instrs import RandomSafeInstrs
from tibbar.sequences.sequences import DefaultProgramEnd, DefaultProgramStart, DefaultRelocate


class Generator(GeneratorBase):
    """Directed branch outcome and JAL/JALR link patterns with background noise."""

    def __init__(self, tibbar: object, **kwargs: object) -> None:
        super().__init__(tibbar, length=0)
        self.main_funnel = SimpleFunnel(tibbar)
        self.main_funnel.add_sequence(RandomSafeInstrs(tibbar, length=64))
        for _ in range(6):
            self.main_funnel.add_sequence(BranchOutcomeControlled(tibbar))
            self.main_funnel.add_sequence(JalJalrLinkCheck(tibbar))
            self.main_funnel.add_sequence(RelativeBranching(tibbar))
            self.main_funnel.add_sequence(RandomSafeInstrs(tibbar, length=8))
        self.start_sequence = DefaultProgramStart(tibbar)
        self.end_sequence = DefaultProgramEnd(tibbar)
        self.relocate_sequence = DefaultRelocate(tibbar)
