# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Ld/st-heavy test suite: repeated Load and Store sequences."""

from tibbar.core.funnels import SimpleFunnel
from tibbar.core.generator_base import GeneratorBase
from tibbar.sequences.ldst import Load, Store
from tibbar.sequences.sequences import DefaultProgramEnd, DefaultProgramStart, DefaultRelocate


class Generator(GeneratorBase):
    """Generator that stresses load/store with many Load/Store sequence pairs."""

    def __init__(self, tibbar: object, **kwargs: object) -> None:
        super().__init__(tibbar, length=0)
        self.main_funnel = SimpleFunnel(tibbar)
        for _ in range(25):
            for _ in range(20):
                self.main_funnel.add_sequence(Load(tibbar))
                self.main_funnel.add_sequence(Store(tibbar))
        self.start_sequence = DefaultProgramStart(tibbar)
        self.end_sequence = DefaultProgramEnd(tibbar)
        self.relocate_sequence = DefaultRelocate(tibbar)
