# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Random instruction sequences (I extension and float)."""

from tibbar.testobj import GenData

from .base_constraint import BaseConstraint


class RandomInstrs(BaseConstraint):
    """Generate random I-extension instructions."""

    def __init__(self, tibbar: object, length: int = 100) -> None:
        super().__init__(tibbar)
        self.length = length
        self.name = "RandomInstrs"
        self._i_only = [
            n for n, instr in tibbar.instrs.items() if getattr(instr, "extension", "") == "I"
        ]
        if not self._i_only:
            self._i_only = list(tibbar.instrs.keys())

    def gen(self) -> object:
        for _ in range(self.length):
            mnemonic = self.random.choice(self._i_only)
            for _ in range(100):
                rand_val = self.random.getrandbits(32)
                try:
                    instance = self.tibbar.decoder.from_opc(rand_val)
                    if instance is not None and instance.instruction.mnemonic == mnemonic:
                        yield GenData(
                            data=instance.to_opc(),
                            comment=instance.to_asm(),
                            seq=self.name,
                        )
                        break
                except Exception:
                    pass


class RandomSafeInstrs(RandomInstrs):
    """Random I instructions avoiding loads, stores, branches, CSRs."""

    def __init__(self, tibbar: object, length: int = 100) -> None:
        super().__init__(tibbar, length)
        self._i_only = [
            n
            for n in self._i_only
            if not tibbar.instrs[n].in_group("memory")
            and not tibbar.instrs[n].in_group("branch")
            and not tibbar.instrs[n].in_group("system")
        ]
        if not self._i_only:
            self._i_only = ["addi", "add", "nop"]


class RandomFloatInstrs(RandomInstrs):
    """Generate random F-extension (float) instructions."""

    def __init__(self, tibbar: object, length: int = 100) -> None:
        super().__init__(tibbar, length)
        self.name = "RandomFloatInstrs"
        self._i_only = [n for n, instr in tibbar.instrs.items() if instr.in_group("float")]
        if not self._i_only:
            self._i_only = list(tibbar.instrs.keys())
