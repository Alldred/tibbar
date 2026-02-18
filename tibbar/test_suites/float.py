# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Float test suite: RandomFloatInstrs + branching."""

from tibbar.core.funnels import SimpleFunnel
from tibbar.core.generator_base import GeneratorBase
from tibbar.sequences.branch_and_jump import RelativeBranching
from tibbar.sequences.random_instrs import RandomFloatInstrs
from tibbar.sequences.sequences import DefaultProgramEnd, DefaultProgramStart, DefaultRelocate


class Generator(GeneratorBase):
    """RandomFloatInstrs + branching."""

    def __init__(self, tibbar: object, **kwargs: object) -> None:
        super().__init__(tibbar, length=0)
        self.main_funnel = SimpleFunnel(tibbar)
        for _ in range(25):
            self.main_funnel.add_sequence(
                RandomFloatInstrs(tibbar, length=tibbar.random.randint(50, 200))
            )
            self.main_funnel.add_sequence(RelativeBranching(tibbar))
        self.start_sequence = DefaultProgramStart(tibbar)
        self.end_sequence = DefaultProgramEnd(tibbar)
        self.relocate_sequence = DefaultRelocate(tibbar)
