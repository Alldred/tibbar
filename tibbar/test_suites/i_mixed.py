# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""RV-I mixed suite: balanced blend of all directed integer sequences."""

from tibbar.core.funnels import SimpleFunnel
from tibbar.core.generator_base import GeneratorBase
from tibbar.sequences.branch_and_jump import RelativeBranching
from tibbar.sequences.i_extension import (
    BranchOutcomeControlled,
    DirectedALUEdges,
    DirectedComparePairs,
    DirectedShiftEdges,
    ImmBoundarySweep,
    JalJalrLinkCheck,
    LoadSignZeroExtend,
    LongDependencyChains,
    StoreLoadRoundTrip,
    X0InvariantStress,
)
from tibbar.sequences.ldst import Load, Store
from tibbar.sequences.random_instrs import RandomSafeInstrs
from tibbar.sequences.sequences import DefaultProgramEnd, DefaultProgramStart, DefaultRelocate


class Generator(GeneratorBase):
    """Balanced directed+random RV-I stress across ALU, control, memory, and invariants."""

    def __init__(self, tibbar: object, **kwargs: object) -> None:
        super().__init__(tibbar, length=0)
        self.main_funnel = SimpleFunnel(tibbar)
        self.main_funnel.add_sequence(RandomSafeInstrs(tibbar, length=256))
        for _ in range(4):
            self.main_funnel.add_sequence(DirectedALUEdges(tibbar))
            self.main_funnel.add_sequence(DirectedShiftEdges(tibbar))
            self.main_funnel.add_sequence(DirectedComparePairs(tibbar))
            self.main_funnel.add_sequence(ImmBoundarySweep(tibbar))
            self.main_funnel.add_sequence(BranchOutcomeControlled(tibbar))
            self.main_funnel.add_sequence(JalJalrLinkCheck(tibbar))
            self.main_funnel.add_sequence(LoadSignZeroExtend(tibbar))
            self.main_funnel.add_sequence(StoreLoadRoundTrip(tibbar))
            self.main_funnel.add_sequence(X0InvariantStress(tibbar))
            self.main_funnel.add_sequence(LongDependencyChains(tibbar, length=64))
            self.main_funnel.add_sequence(Load(tibbar))
            self.main_funnel.add_sequence(Store(tibbar))
            self.main_funnel.add_sequence(RelativeBranching(tibbar))
            self.main_funnel.add_sequence(RandomSafeInstrs(tibbar, length=16))
        self.start_sequence = DefaultProgramStart(tibbar)
        self.end_sequence = DefaultProgramEnd(tibbar)
        self.relocate_sequence = DefaultRelocate(tibbar)
