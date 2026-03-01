# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Load and Store sequences (linear memory only)."""

from __future__ import annotations

from tibbar.testobj import GenData

from .sequences import LoadGPR
from .utils import encode_instr


class Load:
    """Generate a random load instruction with pre-populated data at a linear address."""

    def __init__(self, tibbar: object) -> None:
        self.tibbar = tibbar
        self.name = "Load"
        load_instrs = tibbar.eumos.instructions_by_group("memory/load")
        self._load_instrs = list(load_instrs)
        if not self._load_instrs:
            self._load_instrs = ["lw"]  # fallback

    def gen(
        self,
        base_reg: int | list[int] | None = None,
        dest_reg: int | list[int] | None = None,
    ) -> object:
        if not self._load_instrs:
            return
        mnemonic = self.tibbar.random.choice(self._load_instrs)
        instr = self.tibbar.instrs[mnemonic]

        valid_regs = list(range(1, 32))
        selected_base = (
            (
                base_reg
                if isinstance(base_reg, int)
                else self.tibbar.random.choice(base_reg or valid_regs)
            )
            if base_reg is not None
            else self.tibbar.random.choice(valid_regs)
        )
        selected_dest = (
            (
                dest_reg
                if isinstance(dest_reg, int)
                else self.tibbar.random.choice(dest_reg or valid_regs)
            )
            if dest_reg is not None
            else self.tibbar.random.choice(valid_regs)
        )

        data_size_bits = getattr(instr, "memory_access_width", None) or getattr(
            instr, "access_width", 32
        )
        data_size_bytes = data_size_bits // 8
        size = max(8, data_size_bytes)

        base_addr = self.tibbar.allocate_data(size)
        if base_addr is None:
            return

        yield from LoadGPR(
            self.tibbar,
            reg_idx=selected_base,
            value=base_addr,
            name=self.name,
        ).gen()

        load_data = self.tibbar.random.getrandbits(data_size_bits) & ((1 << data_size_bits) - 1)

        instr_enc = encode_instr(
            self.tibbar,
            mnemonic,
            rd=selected_dest,
            rs1=selected_base,
            imm=0,
        )
        load_instr = GenData(
            data=instr_enc,
            comment=f"{mnemonic}",
            seq=self.name,
            ldst_addr=base_addr,
            ldst_data=load_data,
            ldst_size=data_size_bytes,
        )
        yield load_instr


class LoadException:
    """Generate a load with base=x0 so the load address is 0 and triggers a fault."""

    def __init__(self, tibbar: object) -> None:
        self.tibbar = tibbar
        self.name = "LoadException"
        load_instrs = tibbar.eumos.instructions_by_group("memory/load")
        self._load_instrs = list(load_instrs)
        if not self._load_instrs:
            self._load_instrs = ["lw"]

    def gen(self) -> object:
        if not self._load_instrs:
            return
        mnemonic = self.tibbar.random.choice(self._load_instrs)
        selected_dest = self.tibbar.random.randint(1, 31)
        instr_enc = encode_instr(
            self.tibbar,
            mnemonic,
            rd=selected_dest,
            rs1=0,
            imm=0,
        )
        yield GenData(
            data=instr_enc,
            comment=f"{mnemonic} (base=x0 -> fault)",
            seq=self.name,
        )


class Store:
    """Generate a random store instruction."""

    def __init__(self, tibbar: object) -> None:
        self.tibbar = tibbar
        self.name = "Store"
        store_instrs = tibbar.eumos.instructions_by_group("memory/store")
        self._store_instrs = list(store_instrs)
        if not self._store_instrs:
            self._store_instrs = ["sw"]

    def gen(
        self,
        base_reg: int | list[int] | None = None,
        data_reg: int | list[int] | None = None,
    ) -> object:
        if not self._store_instrs:
            return
        mnemonic = self.tibbar.random.choice(self._store_instrs)
        instr = self.tibbar.instrs[mnemonic]

        valid_regs = list(range(1, 32))
        selected_base = (
            (
                base_reg
                if isinstance(base_reg, int)
                else self.tibbar.random.choice(base_reg or valid_regs)
            )
            if base_reg is not None
            else self.tibbar.random.choice(valid_regs)
        )
        selected_data = (
            (
                data_reg
                if isinstance(data_reg, int)
                else self.tibbar.random.choice(data_reg or valid_regs)
            )
            if data_reg is not None
            else self.tibbar.random.choice(valid_regs)
        )

        if selected_base == selected_data:
            selected_data = (selected_data % 31) + 1

        data_size_bits = getattr(instr, "memory_access_width", None) or getattr(
            instr, "access_width", 32
        )
        data_size_bytes = data_size_bits // 8
        size = max(8, data_size_bytes)

        base_addr = self.tibbar.allocate_data(size)
        if base_addr is None:
            return

        yield from LoadGPR(
            self.tibbar,
            reg_idx=selected_base,
            value=base_addr,
            name=self.name,
        ).gen()

        store_data = self.tibbar.random.getrandbits(data_size_bits) & ((1 << data_size_bits) - 1)
        yield from LoadGPR(
            self.tibbar, reg_idx=selected_data, value=store_data, name=self.name
        ).gen()

        instr_enc = encode_instr(
            self.tibbar,
            mnemonic,
            rs2=selected_data,
            rs1=selected_base,
            imm=0,
        )
        store_instr = GenData(
            data=instr_enc,
            comment=f"{mnemonic}",
            seq=self.name,
        )
        yield store_instr
