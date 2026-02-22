# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Branch and jump sequences (simplified, linear memory only)."""

from __future__ import annotations

from tibbar.testobj import GenData

from .sequences import LoadGPR
from .utils import encode_instr, get_min_max_values

BRANCH_MNEMONICS = ["beq", "bne", "blt", "bge", "bltu", "bgeu"]


class RelativeBranching:
    """Generate random relative branches. Uses plain ints for operands."""

    def __init__(self, tibbar: object) -> None:
        self.tibbar = tibbar
        self.name = "RelativeBranching"
        self._branch_instrs = [m for m in BRANCH_MNEMONICS if m in tibbar.instrs]
        if not self._branch_instrs:
            self._branch_instrs = ["beq"]

    def gen(self) -> object:
        if not self._branch_instrs:
            return
        mnemonic = self.tibbar.random.choice(self._branch_instrs)
        instr = self.tibbar.instrs[mnemonic]

        rs1_idx = self.tibbar.random.randint(1, 31)
        rs2_idx = self.tibbar.random.randint(1, 31)
        if rs1_idx == rs2_idx:
            rs2_idx = (rs2_idx % 31) + 1

        branch_taken = self.tibbar.random.choice([True, False])
        if branch_taken:
            val1 = self.tibbar.random.getrandbits(64)
            val2 = val1 if mnemonic in ("beq", "bge", "bgeu") else val1 + 1
        else:
            val1 = self.tibbar.random.getrandbits(64)
            val2 = val1 + self.tibbar.random.randint(1, 100)

        yield from LoadGPR(self.tibbar, reg_idx=rs1_idx, value=val1, name=self.name).gen()
        yield from LoadGPR(self.tibbar, reg_idx=rs2_idx, value=val2, name=self.name).gen()

        pc = self.tibbar.get_current_pc()
        min_off, max_off = get_min_max_values(instr)
        # Target must be in an empty block with enough space (min 64 bytes).
        target = self.tibbar.mem_store.allocate(
            64, align=4, purpose="code", pc=pc, within=(min_off, max_off)
        )

        if target is not None:
            offset = target - pc
            instr_enc = encode_instr(
                self.tibbar,
                mnemonic,
                rs1=rs1_idx,
                rs2=rs2_idx,
                imm=offset,
            )
            yield GenData(
                data=instr_enc,
                comment=f"{mnemonic}",
                seq=self.name,
            )
        else:
            self.tibbar.debug(f"Cannot generate {mnemonic}: no valid target in range")


class AbsoluteBranching:
    """Generate JALR (or similar indirect jump) to a suitable code address in linear memory."""

    def __init__(self, tibbar: object) -> None:
        self.tibbar = tibbar
        self.name = "AbsoluteBranching"
        self._jump_instrs = [
            m
            for m, instr in tibbar.instrs.items()
            if instr.in_group("branch/jump") and "rs1" in getattr(instr, "operands", {})
        ]
        if not self._jump_instrs:
            self._jump_instrs = ["jalr"] if "jalr" in tibbar.instrs else []

    def gen(self) -> object:
        if not self._jump_instrs:
            return
        mnemonic = self.tibbar.random.choice(self._jump_instrs)
        base_reg = self.tibbar.random.randint(1, 31)
        pc = self.tibbar.get_current_pc()
        # Target must be empty and have enough space (64 bytes).
        target = self.tibbar.mem_store.allocate(64, align=4, purpose="code", pc=pc)
        if target is None:
            self.tibbar.debug("AbsoluteBranching: no space for jump target")
            return
        target = target & ~3
        yield from LoadGPR(self.tibbar, reg_idx=base_reg, value=target, name=self.name).gen()
        rd = self.tibbar.random.choice([0, 1])
        instr_enc = encode_instr(self.tibbar, mnemonic, rd=rd, rs1=base_reg, imm=0)
        yield GenData(data=instr_enc, comment=f"{mnemonic}", seq=self.name)
