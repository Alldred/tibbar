# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Hazard sequence: two instructions that share a GPR (dest of first, source of second)."""

from __future__ import annotations

from eumos.instance import InstructionInstance

from tibbar.testobj import GenData

from .base_constraint import BaseConstraint


def _blocked_groups() -> list[str]:
    """Group names to exclude from hazard pair selection (memory, control, system)."""
    return ["memory", "branch", "system"]


class Hazards(BaseConstraint):
    """Generate two instructions that share a GPR: first writes it, second reads it."""

    def __init__(self, tibbar: object, will_hazard: bool | None = None) -> None:
        super().__init__(tibbar)
        self.name = "Hazards"
        if will_hazard is None:
            self.will_hazard = self.random.choice([True, False])
        else:
            assert isinstance(will_hazard, bool), "Expecting will_hazard to be a bool"
            self.will_hazard = will_hazard

        blocked = _blocked_groups()
        self._instrs_with_dest = [
            m
            for m, instr in tibbar.instrs.items()
            if instr.gpr_dest_operands() and not any(instr.in_group(g) for g in blocked)
        ]
        self._instrs_with_src = [
            m
            for m, instr in tibbar.instrs.items()
            if instr.gpr_source_operands() and not any(instr.in_group(g) for g in blocked)
        ]
        if not self._instrs_with_dest:
            self._instrs_with_dest = ["addi"]
        if not self._instrs_with_src:
            self._instrs_with_src = ["add"]

    def gen(self) -> object:
        first_mnemonic = self.random.choice(self._instrs_with_dest)
        second_mnemonic = self.random.choice(self._instrs_with_src)
        first_instr = self.tibbar.instrs[first_mnemonic]
        second_instr = self.tibbar.instrs[second_mnemonic]

        first_dest_names = first_instr.gpr_dest_operands()
        second_src_names = second_instr.gpr_source_operands()
        valid_reg_idxs = list(range(0, 32))
        if self.will_hazard and first_dest_names and second_src_names:
            selected_hazard_reg = self.random.choice(valid_reg_idxs)
        else:
            selected_hazard_reg = self.random.choice(valid_reg_idxs)

        for _ in range(200):
            rand_opc = self.random.getrandbits(32) & 0xFFFFFFFF
            try:
                inst = self.tibbar.decoder.from_opc(rand_opc, pc=0)
            except Exception:
                continue
            if inst is None or inst.instruction.mnemonic != first_mnemonic:
                continue
            op_vals = dict(inst.operand_values)
            for name in first_dest_names:
                if name in op_vals:
                    op_vals[name] = selected_hazard_reg
            try:
                first_opc = InstructionInstance(
                    instruction=first_instr,
                    operand_values=op_vals,
                ).to_opc()
            except Exception:
                continue
            first_asm = InstructionInstance(
                instruction=first_instr,
                operand_values=op_vals,
            ).to_asm()
            break
        else:
            return

        for _ in range(200):
            rand_opc = self.random.getrandbits(32) & 0xFFFFFFFF
            try:
                inst = self.tibbar.decoder.from_opc(rand_opc, pc=0)
            except Exception:
                continue
            if inst is None or inst.instruction.mnemonic != second_mnemonic:
                continue
            op_vals = dict(inst.operand_values)
            for name in second_src_names:
                if name in op_vals:
                    op_vals[name] = selected_hazard_reg
            try:
                second_opc = InstructionInstance(
                    instruction=second_instr,
                    operand_values=op_vals,
                ).to_opc()
            except Exception:
                continue
            second_asm = InstructionInstance(
                instruction=second_instr,
                operand_values=op_vals,
            ).to_asm()
            break
        else:
            return

        yield GenData(data=first_opc, comment=first_asm, seq=self.name)
        yield GenData(data=second_opc, comment=second_asm, seq=self.name)
