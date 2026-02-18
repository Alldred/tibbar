# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Hazard test suite: Hazards + safe instrs + load/store (SetFPRs/SetGPRs optional)."""

from tibbar.core.funnels import SimpleFunnel
from tibbar.core.generator_base import GeneratorBase
from tibbar.sequences.hazard import Hazards
from tibbar.sequences.ldst import Load, Store
from tibbar.sequences.random_instrs import RandomSafeInstrs
from tibbar.sequences.sequences import (
    DefaultProgramEnd,
    DefaultProgramStart,
    DefaultRelocate,
    SetGPRs,
)


class Generator(GeneratorBase):
    """Hazards + safe instrs + load/store."""

    def __init__(self, tibbar: object, **kwargs: object) -> None:
        super().__init__(tibbar, length=0)
        self.main_funnel = SimpleFunnel(tibbar)
        for _ in range(25):
            self.main_funnel.add_sequence(SetGPRs(tibbar))
            self.main_funnel.add_sequence(RandomSafeInstrs(tibbar, length=10))
            self.main_funnel.add_sequence(Hazards(tibbar))
            for _ in range(10):
                self.main_funnel.add_sequence(Load(tibbar))
                self.main_funnel.add_sequence(Store(tibbar))
        self.start_sequence = DefaultProgramStart(tibbar)
        self.end_sequence = DefaultProgramEnd(tibbar)
        self.relocate_sequence = DefaultRelocate(tibbar)
