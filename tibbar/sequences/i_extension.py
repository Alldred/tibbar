# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Directed RV I-extension stress sequences."""

from __future__ import annotations

from tibbar.testobj import GenData

from .sequences import LoadGPR
from .utils import MASK_64_BIT, encode_instr, get_min_max_values


class _IExtensionBase:
    """Shared helpers for directed integer sequences."""

    def __init__(self, tibbar: object, name: str) -> None:
        self.tibbar = tibbar
        self.name = name

    def _has(self, mnemonic: str) -> bool:
        return mnemonic in self.tibbar.instrs

    def _emit(self, mnemonic: str, comment: str | None = None, **ops: int) -> GenData | None:
        if not self._has(mnemonic):
            return None
        try:
            opc = encode_instr(self.tibbar, mnemonic, **ops)
        except Exception:
            return None
        return GenData(
            data=opc,
            comment=comment or mnemonic,
            seq=self.name,
        )

    def _u64(self, value: int) -> int:
        return value & MASK_64_BIT

    def _load_gpr(self, reg_idx: int, value: int) -> object:
        yield from LoadGPR(
            self.tibbar, reg_idx=reg_idx, value=self._u64(value), name=self.name
        ).gen()

    def _current_pc(self) -> int:
        if hasattr(self.tibbar, "_pc"):
            return int(self.tibbar.get_current_pc())
        return int(getattr(self.tibbar, "load_addr", 0))


class DirectedALUEdges(_IExtensionBase):
    """ALU-focused edge values for register and immediate arithmetic/logic ops."""

    def __init__(self, tibbar: object) -> None:
        super().__init__(tibbar, "DirectedALUEdges")

    def gen(self) -> object:
        reg_ops = ["add", "sub", "xor", "or", "and"]
        imm_ops = ["addi", "xori", "ori", "andi"]
        vectors = [
            (0, 0),
            (1, -1),
            (0x7FFF_FFFF_FFFF_FFFF, 1),
            (0x8000_0000_0000_0000, -1),
            (0xFFFF_FFFF_FFFF_FFFF, 1),
        ]
        for idx, (a, b) in enumerate(vectors):
            yield from self._load_gpr(1, a)
            yield from self._load_gpr(2, b)
            for mnemonic in reg_ops:
                item = self._emit(
                    mnemonic,
                    comment=f"{mnemonic} edge[{idx}]",
                    dest=3,
                    src1=1,
                    src2=2,
                )
                if item is not None:
                    yield item

            imm = [-2048, -1, 0, 1, 2047][idx % 5]
            for mnemonic in imm_ops:
                item = self._emit(
                    mnemonic,
                    comment=f"{mnemonic} imm={imm}",
                    dest=4,
                    src1=1,
                    imm=imm,
                )
                if item is not None:
                    yield item


class DirectedShiftEdges(_IExtensionBase):
    """Shift operations at boundary shift amounts and sign-sensitive values."""

    def __init__(self, tibbar: object) -> None:
        super().__init__(tibbar, "DirectedShiftEdges")

    def gen(self) -> object:
        reg_ops = ["sll", "srl", "sra"]
        imm_ops = ["slli", "srli", "srai"]
        shift_values = [0, 1, 7, 15, 31, 63]
        base_values = [
            0x0000_0000_0000_0001,
            0x8000_0000_0000_0000,
            0xFFFF_FFFF_FFFF_FFFF,
        ]
        for base in base_values:
            yield from self._load_gpr(1, base)
            for shamt in shift_values:
                yield from self._load_gpr(2, shamt)
                for mnemonic in reg_ops:
                    item = self._emit(
                        mnemonic,
                        comment=f"{mnemonic} shamt={shamt}",
                        dest=3,
                        src1=1,
                        src2=2,
                    )
                    if item is not None:
                        yield item
                for mnemonic in imm_ops:
                    item = self._emit(
                        mnemonic,
                        comment=f"{mnemonic} shamt={shamt}",
                        dest=4,
                        src1=1,
                        shamt=shamt,
                    )
                    if item is not None:
                        yield item


class DirectedComparePairs(_IExtensionBase):
    """Comparison ops with signed/unsigned-divergent operand pairs."""

    def __init__(self, tibbar: object) -> None:
        super().__init__(tibbar, "DirectedComparePairs")

    def gen(self) -> object:
        pairs = [
            (0, -1),
            (-1, 1),
            (0x7FFF_FFFF_FFFF_FFFF, 0x8000_0000_0000_0000),
            (5, 5),
        ]
        for a, b in pairs:
            yield from self._load_gpr(1, a)
            yield from self._load_gpr(2, b)
            for mnemonic in ("slt", "sltu"):
                item = self._emit(
                    mnemonic,
                    comment=f"{mnemonic} pair",
                    dest=3,
                    src1=1,
                    src2=2,
                )
                if item is not None:
                    yield item

        for imm in (-2048, -1, 0, 1, 2047):
            for mnemonic in ("slti", "sltiu"):
                item = self._emit(
                    mnemonic,
                    comment=f"{mnemonic} imm={imm}",
                    dest=4,
                    src1=1,
                    imm=imm,
                )
                if item is not None:
                    yield item


class BranchOutcomeControlled(_IExtensionBase):
    """Emit branches with controlled taken/not-taken operand construction."""

    def __init__(self, tibbar: object) -> None:
        super().__init__(tibbar, "BranchOutcomeControlled")

    def _branch_values(self, mnemonic: str, taken: bool) -> tuple[int, int]:
        if mnemonic == "beq":
            return (0x1234, 0x1234) if taken else (0x1234, 0x1235)
        if mnemonic == "bne":
            return (0x5678, 0x5679) if taken else (0x5678, 0x5678)
        if mnemonic == "blt":
            return (-1, 1) if taken else (2, -2)
        if mnemonic == "bge":
            return (2, -2) if taken else (-1, 1)
        if mnemonic == "bltu":
            return (1, 2) if taken else (3, 2)
        if mnemonic == "bgeu":
            return (3, 2) if taken else (1, 2)
        return (0, 1)

    def gen(self) -> object:
        for mnemonic in ("beq", "bne", "blt", "bge", "bltu", "bgeu"):
            if not self._has(mnemonic):
                continue
            instr = self.tibbar.instrs[mnemonic]
            min_off, max_off = get_min_max_values(instr)
            for taken in (True, False):
                a, b = self._branch_values(mnemonic, taken)
                yield from self._load_gpr(1, a)
                yield from self._load_gpr(2, b)
                pc = self._current_pc()
                target = self.tibbar.allocate_code(
                    64,
                    align=4,
                    pc=pc,
                    within=(min_off, max_off),
                )
                if target is None:
                    continue
                item = self._emit(
                    mnemonic,
                    comment=f"{mnemonic} taken={taken}",
                    rs1=1,
                    rs2=2,
                    imm=(target - pc),
                )
                if item is not None:
                    yield item


class JalJalrLinkCheck(_IExtensionBase):
    """Emit JAL/JALR patterns that exercise link-register writes and control transfers."""

    def __init__(self, tibbar: object) -> None:
        super().__init__(tibbar, "JalJalrLinkCheck")

    def gen(self) -> object:
        if self._has("jal"):
            instr = self.tibbar.instrs["jal"]
            min_off, max_off = get_min_max_values(instr)
            pc = self._current_pc()
            target = self.tibbar.allocate_code(
                64,
                align=4,
                pc=pc,
                within=(min_off, max_off),
            )
            if target is not None:
                item = self._emit(
                    "jal",
                    comment="jal link x1",
                    rd=1,
                    imm=(target - pc),
                )
                if item is not None:
                    yield item

        if self._has("jalr"):
            target = self.tibbar.allocate_code(
                64,
                align=4,
                pc=self._current_pc(),
            )
            if target is not None:
                yield from self._load_gpr(2, target & ~1)
                item = self._emit(
                    "jalr",
                    comment="jalr link x5",
                    rd=5,
                    rs1=2,
                    imm=0,
                )
                if item is not None:
                    yield item


class LoadSignZeroExtend(_IExtensionBase):
    """Load-width and sign/zero-extension patterns using directed memory values."""

    def __init__(self, tibbar: object) -> None:
        super().__init__(tibbar, "LoadSignZeroExtend")

    def gen(self) -> object:
        base_addr = self.tibbar.allocate_data(64, align=8)
        if base_addr is None:
            return
        yield from self._load_gpr(1, base_addr)
        cases = [
            ("lb", 0x80, 1),
            ("lbu", 0x80, 1),
            ("lh", 0x8001, 2),
            ("lhu", 0x8001, 2),
            ("lw", 0x8000_0001, 4),
            ("lwu", 0x8000_0001, 4),
            ("ld", 0x8000_0000_0000_0001, 8),
        ]
        offset = 0
        for mnemonic, mem_value, mem_size in cases:
            if not self._has(mnemonic):
                continue
            item = self._emit(
                mnemonic,
                comment=f"{mnemonic} sign/zero-ext pattern",
                rd=2 + ((offset // 8) % 28),
                rs1=1,
                imm=offset,
            )
            if item is None:
                continue
            item.ldst_addr = base_addr + offset
            item.ldst_data = mem_value
            item.ldst_size = mem_size
            yield item
            offset += 8


class StoreLoadRoundTrip(_IExtensionBase):
    """Store then load back values at the same address across width variants."""

    def __init__(self, tibbar: object) -> None:
        super().__init__(tibbar, "StoreLoadRoundTrip")

    def gen(self) -> object:
        base_addr = self.tibbar.allocate_data(64, align=8)
        if base_addr is None:
            return
        yield from self._load_gpr(1, base_addr)
        cases = [
            ("sb", "lbu", "lb", 0xA5),
            ("sh", "lhu", "lh", 0xA55A),
            ("sw", "lwu", "lw", 0xA55A_A55A),
            ("sd", "ld", None, 0xA55A_A55A_A55A_A55A),
        ]
        offset = 0
        for store_mnemonic, load_u, load_s, pattern in cases:
            if not self._has(store_mnemonic):
                continue
            yield from self._load_gpr(2, pattern)
            store_item = self._emit(
                store_mnemonic,
                comment=f"{store_mnemonic} roundtrip",
                rs1=1,
                rs2=2,
                imm=offset,
            )
            if store_item is not None:
                yield store_item

            for mnemonic, dest in ((load_u, 3), (load_s, 4)):
                if mnemonic is None or not self._has(mnemonic):
                    continue
                load_item = self._emit(
                    mnemonic,
                    comment=f"{mnemonic} after {store_mnemonic}",
                    rd=dest,
                    rs1=1,
                    imm=offset,
                )
                if load_item is not None:
                    yield load_item
            offset += 8


class ImmBoundarySweep(_IExtensionBase):
    """Immediate boundary values over I/U-immediate instruction families."""

    def __init__(self, tibbar: object) -> None:
        super().__init__(tibbar, "ImmBoundarySweep")

    def gen(self) -> object:
        yield from self._load_gpr(1, 0x1234_5678_9ABC_DEF0)
        i_immediates = [-2048, -2047, -1, 0, 1, 2046, 2047]
        for imm in i_immediates:
            for mnemonic in ("addi", "xori", "ori", "andi", "slti", "sltiu", "addiw"):
                item = self._emit(
                    mnemonic,
                    comment=f"{mnemonic} imm={imm}",
                    dest=2,
                    src1=1,
                    imm=imm,
                )
                if item is not None:
                    yield item

        for imm20 in (0x0, 0x1, 0x7FFFF, 0x80000, 0xFFFFF):
            for mnemonic in ("lui", "auipc"):
                item = self._emit(
                    mnemonic,
                    comment=f"{mnemonic} imm20=0x{imm20:x}",
                    rd=3,
                    imm=imm20,
                )
                if item is not None:
                    yield item


class X0InvariantStress(_IExtensionBase):
    """Attempt many x0 writes via ALU/load paths; architectural zero must remain constant."""

    def __init__(self, tibbar: object) -> None:
        super().__init__(tibbar, "X0InvariantStress")

    def gen(self) -> object:
        yield from self._load_gpr(1, 0xDEAD_BEEF)
        yield from self._load_gpr(2, 0x1234_5678)

        for imm in (-2048, -1, 0, 1, 2047):
            for mnemonic in ("addi", "xori", "ori", "andi", "slti", "sltiu"):
                item = self._emit(
                    mnemonic,
                    comment=f"{mnemonic} -> x0",
                    dest=0,
                    src1=1,
                    imm=imm,
                )
                if item is not None:
                    yield item

        for mnemonic in ("add", "sub", "xor", "or", "and", "sll", "srl", "sra", "slt", "sltu"):
            item = self._emit(
                mnemonic,
                comment=f"{mnemonic} -> x0",
                dest=0,
                src1=1,
                src2=2,
            )
            if item is not None:
                yield item

        for mnemonic in ("lui", "auipc"):
            item = self._emit(
                mnemonic,
                comment=f"{mnemonic} -> x0",
                rd=0,
                imm=0x12345,
            )
            if item is not None:
                yield item

        base_addr = self.tibbar.allocate_data(8, align=8)
        if base_addr is None:
            return
        yield from self._load_gpr(3, base_addr)
        for mnemonic in ("lb", "lh", "lw", "ld"):
            item = self._emit(
                mnemonic,
                comment=f"{mnemonic} -> x0",
                rd=0,
                rs1=3,
                imm=0,
            )
            if item is not None:
                item.ldst_addr = base_addr
                item.ldst_data = 0xFFFF_FFFF_FFFF_FFFF
                item.ldst_size = 8
                yield item


class LongDependencyChains(_IExtensionBase):
    """Long RAW-heavy integer dependency chains."""

    def __init__(self, tibbar: object, length: int = 64) -> None:
        super().__init__(tibbar, "LongDependencyChains")
        self.length = max(8, int(length))

    def gen(self) -> object:
        regs = [1, 2, 3, 4, 5]
        yield from self._load_gpr(regs[0], 0x1020_3040_5060_7080)
        yield from self._load_gpr(regs[1], 0x0101_0101_0101_0101)
        yield from self._load_gpr(regs[2], 0x7)

        reg_ops = [
            m for m in ("add", "sub", "xor", "or", "and", "sll", "srl", "sra") if self._has(m)
        ]
        imm_ops = [
            m for m in ("addi", "xori", "ori", "andi", "slli", "srli", "srai") if self._has(m)
        ]
        if not reg_ops and not imm_ops:
            return

        for idx in range(self.length):
            src1 = regs[idx % len(regs)]
            src2 = regs[(idx + 1) % len(regs)]
            dest = regs[(idx + 2) % len(regs)]
            if idx % 7 == 0:
                yield from self._load_gpr(src2, self.tibbar.random.getrandbits(64))

            if reg_ops and (idx % 2 == 0 or not imm_ops):
                mnemonic = reg_ops[idx % len(reg_ops)]
                item = self._emit(
                    mnemonic,
                    comment=f"{mnemonic} dep[{idx}]",
                    dest=dest,
                    src1=src1,
                    src2=src2,
                )
            else:
                mnemonic = imm_ops[idx % len(imm_ops)]
                imm = [-2048, -1, 0, 1, 2047][idx % 5]
                kwargs = {"dest": dest, "src1": src1, "imm": imm}
                if mnemonic in ("slli", "srli", "srai"):
                    kwargs = {"dest": dest, "src1": src1, "shamt": [0, 1, 7, 31, 63][idx % 5]}
                item = self._emit(
                    mnemonic,
                    comment=f"{mnemonic} dep[{idx}]",
                    **kwargs,
                )
            if item is not None:
                yield item
