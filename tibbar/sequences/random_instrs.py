# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Random instruction sequences (I extension and float)."""

from eumos.instance import InstructionInstance

from tibbar.testobj import GenData

from .base_constraint import BaseConstraint
from .sequences import SetFPRs, SetGPRs


class RandomInstrs(BaseConstraint):
    """Generate random instructions by sampling valid fields for a chosen mnemonic."""

    def __init__(self, tibbar: object, length: int = 100) -> None:
        super().__init__(tibbar)
        self.length = length
        self.name = self.__class__.__name__
        self._i_only = [
            n for n, instr in tibbar.instrs.items() if getattr(instr, "extension", "") == "I"
        ]
        if not self._i_only:
            self._i_only = list(tibbar.instrs.keys())

    def _sample_operand(self, operand_type: str, size_bits: int) -> int:
        if size_bits <= 0:
            return 0
        if operand_type == "register":
            return self.random.getrandbits(size_bits)
        # Immediate: sample raw bits, then represent as signed N-bit value.
        raw = self.random.getrandbits(size_bits)
        sign_bit = 1 << (size_bits - 1)
        return raw - (1 << size_bits) if (raw & sign_bit) else raw

    def _normalize_immediate(self, instr_name: str, imm: int) -> int:
        # Shift-immediate forms reserve high immediate bits in RV64 encodings.
        if instr_name in {"slliw", "srliw"}:
            return imm & 0x1F
        if instr_name == "sraiw":
            return 0x400 | (imm & 0x1F)
        if instr_name in {"slli", "srli"}:
            return imm & 0x3F
        if instr_name == "srai":
            return 0x400 | (imm & 0x3F)
        return imm

    def _sample_valid_instance(self, instr_name: str) -> InstructionInstance:
        instr = self.tibbar.instrs[instr_name]
        for _ in range(128):
            operand_values: dict[str, int] = {}
            for operand_name in instr.inputs:
                operand = instr.operands.get(operand_name)
                if operand is None:
                    continue
                value = self._sample_operand(
                    operand.type,
                    int(operand.size),
                )
                if operand_name == "imm":
                    value = self._normalize_immediate(instr_name, value)
                operand_values[operand_name] = value

            try:
                instance = InstructionInstance(
                    instruction=instr,
                    operand_values=operand_values,
                )
                opcode = instance.to_opc()
                decoded = self.tibbar.decoder.from_opc(opcode)
                if decoded is not None and decoded.instruction.mnemonic == instr_name:
                    return decoded
            except Exception:
                continue
        raise RuntimeError(f"Unable to sample valid encoding for mnemonic: {instr_name}")

    def gen(self) -> object:
        for _ in range(self.length):
            if _ % 100 == 0:
                yield from SetFPRs(self.tibbar).gen()
                yield from SetGPRs(self.tibbar).gen()

            mnemonic = self.random.choice(self._i_only)
            instance = self._sample_valid_instance(mnemonic)
            yield GenData(
                data=instance.to_opc(),
                comment=instance.to_asm(),
                seq=self.name,
            )


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
