# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Core sequences: LoadGPR, DefaultProgramStart, DefaultProgramEnd, DefaultRelocate,
Set*, Stress*, FloatDivSqrt."""

from __future__ import annotations

import itertools

from eumos.instance import InstructionInstance

from tibbar.testobj import GenData

from .utils import MASK_64_BIT, FloatGen, encode_instr, get_min_max_values


class LoadGPR:
    """Load a scalar value into a GPR using LUI+ADDIW (or LUI+ADDIW+SLLI+ADDI) expansion."""

    def __init__(
        self,
        tibbar: object,
        reg_idx: int,
        value: int,
        name: str | None = None,
    ) -> None:
        self.tibbar = tibbar
        self.value = value & MASK_64_BIT
        self.reg_idx = reg_idx
        self.name = f"{name} [LoadGPR]" if name else "LoadGPR"

    def _sign_extend_to_64(self, val: int, chosen_bit: int) -> int:
        if chosen_bit < 0 or chosen_bit > 63:
            raise ValueError("Chosen bit must be 0..63")
        sign_bit = (val >> chosen_bit) & 1
        if sign_bit:
            return (val | (MASK_64_BIT << (chosen_bit + 1))) & MASK_64_BIT
        return val & ((1 << (chosen_bit + 1)) - 1)

    def _find_first_set(self, x: int) -> int:
        if x == 0:
            return -1
        return (x & -x).bit_length() - 1

    def _li_gen(self) -> object:
        val = self.value
        if val == self._sign_extend_to_64(val, 31):
            src_reg = 0
            u20 = ((val + 0x800) >> 12) & 0xFFFFF
            l12 = self._sign_extend_to_64(val, 11)
            if u20:
                yield GenData(
                    data=encode_instr(self.tibbar, "lui", dest=self.reg_idx, imm=u20),
                    comment=f"lui x{self.reg_idx}, 0x{u20:x}",
                    seq=self.name,
                )
                src_reg = self.reg_idx
            if l12 or u20 == 0:
                yield GenData(
                    data=encode_instr(
                        self.tibbar, "addiw", dest=self.reg_idx, src1=src_reg, imm=l12
                    ),
                    comment=f"addiw x{self.reg_idx}, x{src_reg}, {l12}",
                    seq=self.name,
                )
        else:
            l12 = self._sign_extend_to_64(val, 11)
            u52 = (val + 0x800) >> 12
            shamt = 12 + self._find_first_set(u52)
            u52 = self._sign_extend_to_64(u52 >> (shamt - 12), 64 - shamt)
            yield from LoadGPR(self.tibbar, self.reg_idx, u52, self.name).gen()
            yield GenData(
                data=encode_instr(
                    self.tibbar,
                    "slli",
                    dest=self.reg_idx,
                    src1=self.reg_idx,
                    shamt=shamt,
                ),
                comment=f"slli x{self.reg_idx}, x{self.reg_idx}, {shamt}",
                seq=self.name,
            )
            if l12:
                yield GenData(
                    data=encode_instr(
                        self.tibbar,
                        "addi",
                        dest=self.reg_idx,
                        src1=self.reg_idx,
                        imm=l12,
                    ),
                    comment=f"addi x{self.reg_idx}, x{self.reg_idx}, {l12}",
                    seq=self.name,
                )

    def gen(self) -> object:
        if self.reg_idx == 0:
            return
        yield from self._li_gen()


class SetGPRs:
    """Set GPRs 1–31 to random values, null (0), or a fixed sentinel."""

    def __init__(
        self,
        tibbar: object,
        num_of_gprs: int = 32,
        random_values: bool = True,
    ) -> None:
        self.tibbar = tibbar
        self.num_of_gprs = num_of_gprs
        self.random_values = random_values
        self.name = "SetGPRs"

    def gen(self) -> object:
        for i in range(1, self.num_of_gprs):
            if self.random_values:
                choice = self.tibbar.random.randint(0, 2)
                if choice == 0:
                    val = self.tibbar.random.getrandbits(64) & 0xFFFF_FFFF_FFFF_FFFF
                elif choice == 1:
                    val = 0
                else:
                    val = 0xDEAD_BEEF
            else:
                val = 0xDEAD_BEEF
            yield from LoadGPR(self.tibbar, reg_idx=i, value=val, name=self.name).gen()


class SetFPRs:
    """Set FPRs 0–31 with float values from a data region (FloatGen)."""

    def __init__(self, tibbar: object, p_f64: float = 0.5) -> None:
        self.tibbar = tibbar
        self.name = "SetFPRs"
        self.p_f64 = p_f64
        self.base_idx = 1
        self.float_gen = FloatGen(tibbar)

    def gen(self) -> object:
        size = 32 * 8
        base_addr = self.tibbar.mem_store.allocate_data_region(size)
        if base_addr is None:
            return
        yield from LoadGPR(
            self.tibbar, reg_idx=self.base_idx, value=base_addr, name=self.name
        ).gen()
        if "fld" not in self.tibbar.instrs:
            return
        for i in range(32):
            float_data = self.float_gen.gen_any(p_f64=self.p_f64)
            if isinstance(float_data, int) and float_data > 0xFFFF_FFFF:
                float_data = float_data & 0xFFFF_FFFF_FFFF_FFFF
            offset = i * 8
            instr_enc = encode_instr(
                self.tibbar,
                "fld",
                rd=i,
                rs1=self.base_idx,
                imm=offset,
            )
            yield GenData(
                data=instr_enc,
                comment=f"fld f{i}, {offset}(x{self.base_idx})",
                seq=self.name,
                ldst_addr=base_addr + offset,
                ldst_data=float_data,
                ldst_size=8,
            )


class DefaultProgramStart:
    """Set up exception handler (MEPC+4, MRET) and set MTVEC."""

    def __init__(self, tibbar: object) -> None:
        self.tibbar = tibbar
        self.name = "DefaultProgramStart"

    def gen(self) -> object:
        mepc_addr = self.tibbar.csr_addresses.get("mepc")
        mtvec_addr = self.tibbar.csr_addresses.get("mtvec")
        if mepc_addr is None or mtvec_addr is None:
            raise RuntimeError("Eumos/Lome missing mepc or mtvec CSR")

        # Avoid 0 so boot can be at 0 (exit region already uses min_start=0x100).
        exception_base = self.tibbar.mem_store.allocate(40, purpose="code", min_start=0x100)
        assert exception_base is not None, "No space for exception handler"
        self.tibbar.exception_address = exception_base

        yield from LoadGPR(self.tibbar, reg_idx=1, value=exception_base, name=self.name).gen()

        yield GenData(
            seq=self.name,
            data=encode_instr(self.tibbar, "csrrw", dest=0, rs1=1, imm=mtvec_addr),
            comment="csrrw x0, mtvec, x1",
        )

        exception_addr = self.tibbar.exception_address

        yield GenData(
            seq="Exception handler",
            data=encode_instr(self.tibbar, "csrrs", dest=1, rs1=0, imm=mepc_addr),
            comment="csrrs x1, mepc, x0  (read mepc)",
            addr=exception_addr,
        )
        exception_addr += 4

        yield GenData(
            seq="Exception handler",
            data=encode_instr(self.tibbar, "addi", dest=1, src1=1, imm=4),
            comment="addi x1, x1, 4",
            addr=exception_addr,
        )
        exception_addr += 4

        yield GenData(
            seq="Exception handler",
            data=encode_instr(self.tibbar, "csrrw", dest=0, rs1=1, imm=mepc_addr),
            comment="csrrw x0, mepc, x1",
            addr=exception_addr,
        )
        exception_addr += 4

        yield GenData(
            seq="Exception handler",
            data=encode_instr(self.tibbar, "mret"),
            comment="mret",
            addr=exception_addr,
        )


class DefaultProgramEnd:
    """Jump to exit region and place infinite loop."""

    def __init__(self, tibbar: object) -> None:
        self.tibbar = tibbar
        self.name = "DefaultProgramEnd"

    def gen(self) -> object:
        yield from LoadGPR(
            self.tibbar,
            reg_idx=1,
            value=self.tibbar._exit_ptr,
            name=self.name,
        ).gen()
        yield GenData(
            seq=self.name,
            data=encode_instr(self.tibbar, "jalr", dest=0, rs1=1, imm=0),
            comment="jalr x0, x1, 0",
        )
        yield GenData(
            seq=self.name,
            data=0x0000006F,
            comment="jal x0, .  (END TEST)",
        )


class DefaultRelocate:
    """Relocate execution when free space is low."""

    def __init__(self, tibbar: object) -> None:
        self.tibbar = tibbar
        self.name = "Relocate"
        self.mscratch_addr = self.tibbar.csr_addresses.get("mscratch")

    def gen(self) -> object:
        min_off, max_off = get_min_max_values(self.tibbar.instrs["jal"])
        free_addr = self.tibbar.mem_store.allocate(
            100, purpose="code", pc_hint=self.tibbar.get_current_pc(), within=(min_off, max_off)
        )

        if free_addr is not None and self.tibbar.random.random() > 0.05:
            offset = free_addr - self.tibbar._pc
            yield GenData(
                seq=self.name,
                data=encode_instr(self.tibbar, "jal", dest=0, imm=offset),
                comment=f"jal x0, {offset}",
            )
        else:
            if self.mscratch_addr is None:
                free_addr = self.tibbar.mem_store.allocate(
                    100, purpose="code", pc_hint=self.tibbar._pc
                )
                if free_addr is None:
                    size = self.tibbar.random.randint(
                        2**6,
                        min(2**20, self.tibbar.mem_store.get_memory_size() - 64),
                    )
                    base = self.tibbar.mem_store.allocate(
                        size, purpose="code", pc_hint=self.tibbar._pc
                    )
                    assert base is not None, "No space for relocate"
                    if self.tibbar.random.random() < 0.9:
                        offset = self.tibbar.random.randint(0, max(0, size - 48))
                    elif self.tibbar.random.random() < 0.5:
                        offset = max(0, size - 48)
                    else:
                        offset = 0
                    offset &= -4
                    new_loc = base + offset
                else:
                    new_loc = free_addr
                yield from LoadGPR(self.tibbar, reg_idx=1, value=new_loc, name=self.name).gen()
                for _ in range(self.tibbar.random.randint(0, 4)):
                    yield GenData(
                        seq=self.name,
                        data=encode_instr(self.tibbar, "addi", dest=0, src1=0, imm=0),
                        comment="nop",
                    )
                yield GenData(
                    seq=self.name,
                    data=encode_instr(self.tibbar, "jalr", dest=0, rs1=1, imm=0),
                    comment="jalr x0, x1, 0",
                )
                return

            yield GenData(
                seq=self.name,
                data=encode_instr(
                    self.tibbar,
                    "csrrw",
                    dest=0,
                    rs1=1,
                    imm=self.mscratch_addr,
                ),
                comment="csrrw x0, mscratch, x1",
            )

            free_addr = self.tibbar.mem_store.allocate(100, purpose="code", pc_hint=self.tibbar._pc)
            if free_addr is not None:
                new_loc = free_addr
            else:
                size = self.tibbar.random.randint(
                    2**6,
                    min(2**20, self.tibbar.mem_store.get_memory_size() - 64),
                )
                base = self.tibbar.mem_store.allocate(size, purpose="code", pc_hint=self.tibbar._pc)
                assert base is not None, "No space for relocate"
                if self.tibbar.random.random() < 0.9:
                    offset = self.tibbar.random.randint(0, max(0, size - 48))
                elif self.tibbar.random.random() < 0.5:
                    offset = max(0, size - 48)
                else:
                    offset = 0
                offset &= -4
                new_loc = base + offset

            yield from LoadGPR(self.tibbar, reg_idx=1, value=new_loc, name=self.name).gen()

            for _ in range(self.tibbar.random.randint(0, 4)):
                yield GenData(
                    seq=self.name,
                    data=encode_instr(self.tibbar, "addi", dest=0, src1=0, imm=0),
                    comment="nop",
                )

            yield GenData(
                seq=self.name,
                data=encode_instr(self.tibbar, "jalr", dest=0, rs1=1, imm=0),
                comment="jalr x0, x1, 0",
            )

            yield GenData(
                seq=self.name,
                data=encode_instr(
                    self.tibbar,
                    "csrrw",
                    dest=1,
                    rs1=0,
                    imm=self.mscratch_addr,
                ),
                comment="csrrw x1, mscratch, x0",
            )


def _is_f64_mnemonic(mnemonic: str) -> bool:
    """True if instruction is double-precision (.d)."""
    return ".d" in mnemonic


def _valid_float_instr_opc(
    tibbar: object, mnemonic: str, max_tries: int = 200
) -> tuple[int, dict[str, int]] | None:
    """Decode a random opcode until we get a valid instruction for mnemonic with rm not 5,6.
    Return (opc, operand_values)."""
    instr = tibbar.instrs.get(mnemonic)
    if instr is None:
        return None
    for _ in range(max_tries):
        rand_opc = tibbar.random.getrandbits(32) & 0xFFFFFFFF
        try:
            inst = tibbar.decoder.from_opc(rand_opc, pc=0)
        except Exception:
            continue
        if inst is None or inst.instruction.mnemonic != mnemonic:
            continue
        op_vals = dict(inst.operand_values)
        if "rm" in op_vals and op_vals.get("rm", 0) in (5, 6):
            continue
        try:
            InstructionInstance(instruction=instr, operand_values=op_vals).to_opc()
        except Exception:
            continue
        return (inst.to_opc(), op_vals)
    return None


class StressSingleFPRSourceFloatInstrs:
    """Stress float instructions with exactly one FPR source (e.g. fcvt, fsqrt)."""

    POLARITY = [0.0, 1.0]
    EXP_MANT_RANGES = ["MAX", "NEAR_MAX", "LARGE", "MEDIUM", "SMALL", "NEAR_MIN", "MIN"]

    def __init__(self, tibbar: object) -> None:
        self.tibbar = tibbar
        self.name = "StressSingleFPRSourceFloatInstrs"
        self.base_idx = 1
        self.float_gen = FloatGen(tibbar)
        self._float_instrs = [
            m
            for m, instr in tibbar.instrs.items()
            if instr.in_group("float") and len(instr.fpr_source_operands()) == 1
        ]
        if not self._float_instrs:
            self._float_instrs = (
                ["fsqrt.d", "fsqrt.s"]
                if any(m in tibbar.instrs for m in ["fsqrt.d", "fsqrt.s"])
                else []
            )

    def gen(self) -> object:
        if not self._float_instrs or "fld" not in self.tibbar.instrs:
            return
        mnemonic = self.tibbar.random.choice(self._float_instrs)
        result = _valid_float_instr_opc(self.tibbar, mnemonic)
        if result is None:
            return
        instr_opc, op_vals = result
        instr = self.tibbar.instrs[mnemonic]
        src_names = instr.fpr_source_operands()
        if not src_names:
            return
        src_idx = op_vals.get(src_names[0], 0)
        size = 50 * 8
        base_addr = self.tibbar.mem_store.allocate_data_region(size)
        if base_addr is None:
            return
        yield from LoadGPR(
            self.tibbar, reg_idx=self.base_idx, value=base_addr, name=self.name
        ).gen()
        load_offset = 0
        f64 = _is_f64_mnemonic(mnemonic)
        for comb in itertools.product(self.POLARITY, self.EXP_MANT_RANGES, self.EXP_MANT_RANGES):
            p_neg, exp_r, mant_r = comb
            float_val = self.float_gen.gen_num(
                p_f64=float(f64),
                p_negative=p_neg,
                w_exponent={exp_r: 1},
                w_mantissa={mant_r: 1},
            )
            float_val = float_val & 0xFFFF_FFFF_FFFF_FFFF
            fld_enc = encode_instr(
                self.tibbar,
                "fld",
                rd=src_idx,
                rs1=self.base_idx,
                imm=load_offset,
            )
            yield GenData(
                data=fld_enc,
                comment=f"fld f{src_idx}, {load_offset}(x{self.base_idx})",
                seq=self.name,
                ldst_addr=base_addr + load_offset,
                ldst_data=float_val,
                ldst_size=8,
            )
            load_offset += 8
            yield GenData(data=instr_opc, comment=mnemonic, seq=self.name)


class StressMultiFPRSourceFloatInstrs:
    """Stress float instructions with >= 1 FPR source; one source stressed, others random."""

    POLARITY = [0.0, 1.0]
    EXP_MANT_RANGES = ["MAX", "NEAR_MAX", "LARGE", "MEDIUM", "SMALL", "NEAR_MIN", "MIN"]

    def __init__(self, tibbar: object) -> None:
        self.tibbar = tibbar
        self.name = "StressMultiFPRSourceFloatInstrs"
        self.base_idx = 1
        self.float_gen = FloatGen(tibbar)
        self._float_instrs = [
            m
            for m, instr in tibbar.instrs.items()
            if instr.in_group("float") and len(instr.fpr_source_operands()) >= 1
        ]
        if not self._float_instrs:
            self._float_instrs = (
                ["fadd.d", "fadd.s"]
                if any(m in tibbar.instrs for m in ["fadd.d", "fadd.s"])
                else []
            )

    def gen(self) -> object:
        if not self._float_instrs or "fld" not in self.tibbar.instrs:
            return
        mnemonic = self.tibbar.random.choice(self._float_instrs)
        result = _valid_float_instr_opc(self.tibbar, mnemonic)
        if result is None:
            return
        instr_opc, op_vals = result
        instr = self.tibbar.instrs[mnemonic]
        src_names = instr.fpr_source_operands()
        if not src_names:
            return
        num_srcs = len(src_names)
        selected_idx = self.tibbar.random.randint(0, num_srcs - 1) if num_srcs > 1 else 0
        other_idxs = [i for i in range(num_srcs) if i != selected_idx]
        base_addr = self.tibbar.mem_store.allocate_data_region(50 * 8)
        if base_addr is None:
            return
        yield from LoadGPR(
            self.tibbar, reg_idx=self.base_idx, value=base_addr, name=self.name
        ).gen()
        load_offset = 0
        f64 = _is_f64_mnemonic(mnemonic)
        for i in other_idxs:
            src_idx = op_vals.get(src_names[i], 0)
            float_val = self.float_gen.gen_any(p_f64=float(f64)) & 0xFFFF_FFFF_FFFF_FFFF
            yield GenData(
                data=encode_instr(
                    self.tibbar, "fld", rd=src_idx, rs1=self.base_idx, imm=load_offset
                ),
                comment=f"fld f{src_idx}, {load_offset}(x{self.base_idx})",
                seq=self.name,
                ldst_addr=base_addr + load_offset,
                ldst_data=float_val,
                ldst_size=8,
            )
            load_offset += 8
        stressed_name = src_names[selected_idx]
        stressed_idx = op_vals.get(stressed_name, 0)
        for comb in itertools.product(self.POLARITY, self.EXP_MANT_RANGES, self.EXP_MANT_RANGES):
            p_neg, exp_r, mant_r = comb
            float_val = self.float_gen.gen_num(
                p_f64=float(f64),
                p_negative=p_neg,
                w_exponent={exp_r: 1},
                w_mantissa={mant_r: 1},
            )
            float_val = float_val & 0xFFFF_FFFF_FFFF_FFFF
            yield GenData(
                data=encode_instr(
                    self.tibbar,
                    "fld",
                    rd=stressed_idx,
                    rs1=self.base_idx,
                    imm=load_offset,
                ),
                comment=f"fld f{stressed_idx}, {load_offset}(x{self.base_idx})",
                seq=self.name,
                ldst_addr=base_addr + load_offset,
                ldst_data=float_val,
                ldst_size=8,
            )
            load_offset += 8
            yield GenData(data=instr_opc, comment=mnemonic, seq=self.name)


class FloatDivSqrt:
    """Emit fdiv.s/d and fsqrt.s/d with SetFPRs-populated FPRs."""

    NUM_FPRS = 32
    VALID_MNEMONICS = ("fdiv.s", "fdiv.d", "fsqrt.s", "fsqrt.d")

    def __init__(self, tibbar: object) -> None:
        self.tibbar = tibbar
        self.name = "FloatDivSqrt"

    def gen(self) -> object:
        valid = [m for m in self.VALID_MNEMONICS if m in self.tibbar.instrs]
        if not valid:
            return
        instr_name = self.tibbar.random.choice(valid)
        p_f64 = 1.0 if _is_f64_mnemonic(instr_name) else 0.0
        yield from SetFPRs(self.tibbar, p_f64=p_f64).gen()
        dest_idx = self.tibbar.random.randint(0, self.NUM_FPRS - 1)
        all_fprs = [i for i in range(self.NUM_FPRS)]
        if instr_name.startswith("fsqrt"):
            for src1 in all_fprs:
                try:
                    enc = encode_instr(
                        self.tibbar,
                        instr_name,
                        rd=dest_idx,
                        rs1=src1,
                        rs2=0,
                        rm=0,
                    )
                except Exception:
                    continue
                yield GenData(
                    data=enc,
                    comment=f"{instr_name} f{dest_idx}, f{src1}",
                    seq=self.name,
                )
        else:
            for src1 in all_fprs:
                for src2 in all_fprs:
                    try:
                        enc = encode_instr(
                            self.tibbar,
                            instr_name,
                            rd=dest_idx,
                            rs1=src1,
                            rs2=src2,
                            rm=0,
                        )
                    except Exception:
                        continue
                    yield GenData(
                        data=enc,
                        comment=f"{instr_name} f{dest_idx}, f{src1}, f{src2}",
                        seq=self.name,
                    )
