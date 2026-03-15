# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""RV-I ALU suite: directed arithmetic/logic/shift/compare/immediate edges."""

from tibbar.core.funnels import SimpleFunnel
from tibbar.core.generator_base import GeneratorBase
from tibbar.sequences.i_extension import (
    DirectedALUEdges,
    DirectedComparePairs,
    DirectedShiftEdges,
    ImmBoundarySweep,
)
from tibbar.sequences.random_instrs import RandomSafeInstrs
from tibbar.sequences.sequences import DefaultProgramEnd, DefaultProgramStart, DefaultRelocate


class Generator(GeneratorBase):
    """Directed RV-I ALU/shift/compare/immediate boundary coverage."""

    def __init__(self, tibbar: object, **kwargs: object) -> None:
        super().__init__(tibbar, length=0)
        self.main_funnel = SimpleFunnel(tibbar)
        self.main_funnel.add_sequence(RandomSafeInstrs(tibbar, length=128))
        self.main_funnel.add_sequence(DirectedALUEdges(tibbar))
        self.main_funnel.add_sequence(DirectedShiftEdges(tibbar))
        self.main_funnel.add_sequence(DirectedComparePairs(tibbar))
        self.main_funnel.add_sequence(ImmBoundarySweep(tibbar))
        self.start_sequence = DefaultProgramStart(tibbar)
        self.end_sequence = DefaultProgramEnd(tibbar)
        self.relocate_sequence = DefaultRelocate(tibbar)
