# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Stress-float test suite. Full suite pending StressMultiFPRSourceFloatInstrs."""

from tibbar.core.funnels import SimpleFunnel
from tibbar.core.generator_base import GeneratorBase
from tibbar.sequences.random_instrs import RandomSafeInstrs
from tibbar.sequences.sequences import DefaultProgramEnd, DefaultProgramStart, DefaultRelocate


class Generator(GeneratorBase):
    """Placeholder: RandomSafeInstrs until StressMultiFPRSourceFloatInstrs is ported."""

    def __init__(self, tibbar: object, **kwargs: object) -> None:
        super().__init__(tibbar, length=0)
        self.main_funnel = SimpleFunnel(tibbar)
        for _ in range(100):
            self.main_funnel.add_sequence(RandomSafeInstrs(tibbar, length=20))
        self.start_sequence = DefaultProgramStart(tibbar)
        self.end_sequence = DefaultProgramEnd(tibbar)
        self.relocate_sequence = DefaultRelocate(tibbar)
