# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Ld/st exception test suite. LoadException + Load/Store + branching."""

from tibbar.core.funnels import SimpleFunnel
from tibbar.core.generator_base import GeneratorBase
from tibbar.sequences.branch_and_jump import RelativeBranching
from tibbar.sequences.ldst import LoadException, Store
from tibbar.sequences.sequences import DefaultProgramEnd, DefaultProgramStart, DefaultRelocate


class Generator(GeneratorBase):
    """LoadException (faulting loads) + Load/Store + branching."""

    def __init__(self, tibbar: object, **kwargs: object) -> None:
        super().__init__(tibbar, length=0)
        self.main_funnel = SimpleFunnel(tibbar)
        for _ in range(25):
            for _ in range(50):
                self.main_funnel.add_sequence(LoadException(tibbar))
                self.main_funnel.add_sequence(Store(tibbar))
            self.main_funnel.add_sequence(RelativeBranching(tibbar))
        self.start_sequence = DefaultProgramStart(tibbar)
        self.end_sequence = DefaultProgramEnd(tibbar)
        self.relocate_sequence = DefaultRelocate(tibbar)
