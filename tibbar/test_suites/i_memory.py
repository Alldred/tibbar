# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""RV-I memory suite: load extension behavior and store/load round trips."""

from tibbar.core.funnels import SimpleFunnel
from tibbar.core.generator_base import GeneratorBase
from tibbar.sequences.i_extension import LoadSignZeroExtend, StoreLoadRoundTrip
from tibbar.sequences.ldst import Load, Store
from tibbar.sequences.sequences import DefaultProgramEnd, DefaultProgramStart, DefaultRelocate


class Generator(GeneratorBase):
    """Directed and random load/store patterns."""

    def __init__(self, tibbar: object, **kwargs: object) -> None:
        super().__init__(tibbar, length=0)
        self.main_funnel = SimpleFunnel(tibbar)
        for _ in range(10):
            self.main_funnel.add_sequence(LoadSignZeroExtend(tibbar))
            self.main_funnel.add_sequence(StoreLoadRoundTrip(tibbar))
            self.main_funnel.add_sequence(Load(tibbar))
            self.main_funnel.add_sequence(Store(tibbar))
        self.start_sequence = DefaultProgramStart(tibbar)
        self.end_sequence = DefaultProgramEnd(tibbar)
        self.relocate_sequence = DefaultRelocate(tibbar)
