# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Tibbar main generator loop with trap handling."""

from __future__ import annotations

import logging
import random
import sys
import time
from pathlib import Path

from eumos import Eumos
from eumos.decoder import Decoder

from tibbar.core.memory_store import MemoryStore
from tibbar.core.model import create_model


class Tibbar:
    """Instruction Stream Generator main class."""

    def __init__(
        self,
        generator: object | None = None,
        generator_factory: object | None = None,
        seed: int = 42,
        output: Path | None = None,
        verbosity: str = "info",
    ) -> None:
        if generator is None and generator_factory is None:
            raise ValueError("Provide generator or generator_factory")
        self._generator_factory = generator_factory
        self.generator = generator
        self.seed = seed
        self.output = output or Path("test.S")

        self.log = logging.getLogger("tibbar")
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)-20s - %(levelname)s - %(message)s")
        )
        self.log.addHandler(handler)
        self.log.setLevel(getattr(logging, verbosity.upper()))
        self.debug = self.log.debug
        self.info = self.log.info
        self.warning = self.log.warning
        self.error = self.log.error

        self.free_space_required_to_relocate = 13 * 4  # 13 instructions

        self.boot_address: int | None = None
        self.exception_address: int | None = None
        self.exit_address: int | None = None

        self.random = random.Random()
        self.random.seed(self.seed)

        memory_max_size = 2**20
        self.mem_store = MemoryStore(
            self.log.getChild("memstore"),
            self.random,
            self.seed,
            memory_max_size,
        )
        self.mem_store.reserve_data_region(256 * 1024)

        self.eumos = Eumos()
        self.instrs = self.eumos.instructions
        self.decoder = Decoder(instructions=self.eumos.instructions)
        causes = getattr(self.eumos, "exception_causes", None)
        self.exception_ids = {c.code: c.identifier for c in causes.values()} if causes else {}
        self.csr_addresses = {name: csr.address for name, csr in self.eumos.csrs.items()}

        self.model = create_model(self.mem_store, self.eumos)

        if self.generator is None and self._generator_factory is not None:
            self.generator = self._generator_factory(self)

    def get_current_pc(self) -> int:
        return self._pc

    def create_test(self) -> None:
        self.info("Creating test")

        max_boot = self.mem_store.get_memory_size() - self.free_space_required_to_relocate
        data_base = self.mem_store.get_data_region_base()
        if data_base is not None:
            max_boot = min(max_boot, data_base - 1)
        self.boot_address = self.random.randint(0, max(0, max_boot - 1))
        self.boot_address = self.boot_address & ~7

        self._pc = self.boot_address
        self.info(f"Created boot: 0x{self._pc:x}")

        exit_region = self.mem_store.allocate_region(100)
        assert exit_region is not None, "No space for exit region"
        self.exit_address = exit_region
        self._exit_ptr = self.exit_address
        self.info(f"Created exit_ptr: 0x{self._exit_ptr:x}")

        gen = self.generator.gen()
        relocate_gen = None
        model_hung_counter = 0
        gen_hung_counter = 0
        relocating = False
        instr_count = 0
        start = time.time()
        last_gen_pc = "0x0"

        while True:
            if self.mem_store.is_memory_populated(self._pc):
                mem_data = self.mem_store.read_from_mem_store(self._pc, 4)
                try:
                    instr = self.decoder.from_opc(mem_data, pc=self._pc)
                    instr_asm = instr.to_asm().upper() if instr else "UNDECODABLE_INSTRUCTION"
                except Exception:
                    instr = None
                    instr_asm = "UNDECODABLE_INSTRUCTION"
                    self.error(f"Undecodable instruction: ({mem_data:#010x})")

                self.debug(f"Modelling: [0x{self._pc:x}]: {mem_data:#010x} -> {instr_asm}")

                self.model.poke_pc(self._pc)
                changes = self.model.execute(mem_data)

                exc_code = getattr(changes, "exception_code", None)
                if exc_code is None and changes is not None and getattr(changes, "exception", None):
                    exc_code = 2  # illegal_instruction
                if changes is not None and exc_code is not None:
                    self.debug(
                        f"INSTRUCTION EXCEPTED: {hex(exc_code)}: "
                        f"{self.exception_ids.get(exc_code, f'UNKNOWN_{exc_code}')}"
                    )
                    self._apply_trap(exc_code, changes)
                elif changes is not None:
                    self._pc = self.model.get_pc()
                else:
                    self._pc = self.model.get_pc()

                gen_hung_counter = 0
                model_hung_counter += 1
            else:
                free_space_remaining = self.mem_store.get_free_space(self._pc)
                if free_space_remaining <= self.free_space_required_to_relocate or relocating:
                    if relocate_gen is None:
                        relocate_gen = self.generator.relocate_sequence.gen()
                        relocating = True
                    try:
                        test_data = next(relocate_gen)
                    except StopIteration:
                        relocating = False

                if not relocating:
                    test_data = next(gen)

                if test_data.addr is None:
                    test_data.addr = self._pc

                self.mem_store.add_to_mem_store(test_data)
                instr_count += 1

                if self._pc == self._exit_ptr:
                    break

                gen_hung_counter += 1
                model_hung_counter = 0
                last_gen_pc = f"0x{self._pc:x}"

            if gen_hung_counter > 100:
                raise AssertionError("Potentially hung - not modelling new instrs")
            if model_hung_counter > 1000:
                raise AssertionError(
                    f"Potentially hung - not generating new instrs: " f"Last gen at {last_gen_pc}"
                )

        end = time.time()
        self.info("Generated testcase")
        self.info(
            f"Generated {instr_count} instructions in "
            f"{(end - start):.1f} seconds. "
            f"({instr_count / max(0.001, end - start):.02f} ips)"
        )

    def _apply_trap(
        self,
        exception_code: int,
        changes: object,
    ) -> None:
        """Apply trap: set mepc, mcause, mtval, then PC = mtvec."""
        mepc_addr = self.csr_addresses.get("mepc")
        mcause_addr = self.csr_addresses.get("mcause")
        mtval_addr = self.csr_addresses.get("mtval")
        mtvec_addr = self.csr_addresses.get("mtvec")

        if mepc_addr is not None:
            self.model.poke_csr(mepc_addr, self._pc)
        if mcause_addr is not None:
            self.model.poke_csr(mcause_addr, exception_code)

        mtval = 0
        if hasattr(changes, "memory_accesses") and changes.memory_accesses:
            ma = changes.memory_accesses[0]
            mtval = ma.address
        if mtval_addr is not None:
            self.model.poke_csr(mtval_addr, mtval)

        if mtvec_addr is not None:
            mtvec_val = self.model.peek_csr(mtvec_addr)
            if mtvec_val is not None:
                self.model.poke_pc(mtvec_val & ~3)
            else:
                self.model.poke_pc(0)
        else:
            self.model.poke_pc(0)

        self._pc = self.model.get_pc()

    def run(self) -> None:
        """Create test and write output."""
        self.create_test()
        self.write_asm()

    def write_asm(self) -> None:
        """Write .asm output: .text for code, .data for loadable data (no mixing)."""
        data = self.mem_store.compact_and_return()
        code_items: list[tuple[int, object]] = []
        data_items: list[tuple[int, object]] = []
        for addr in sorted(data.keys()):
            item = data[addr]
            if not hasattr(item, "data") or not hasattr(item, "byte_size"):
                continue
            if getattr(item, "is_data", False):
                data_items.append((addr, item))
            else:
                code_items.append((addr, item))

        lines: list[str] = []
        lines.append("# Tibbar - RISC-V instruction stream")
        lines.append("# Assemble with: riscv64-unknown-elf-as -march=rv64gc -o test.o test.S")
        lines.append("")
        lines.append(f"# Boot: 0x{self.boot_address:x}")
        lines.append(f"# Exit: 0x{self.exit_address:x}")
        lines.append("")

        # .text: code only
        lines.append("  .section .text")
        lines.append("  .align 2")
        lines.append("  .globl _start")
        lines.append("")
        location = 0
        for addr, item in code_items:
            val = getattr(item, "data", 0) or 0
            byte_size = item.byte_size
            if addr > location:
                lines.append(f"  .org 0x{addr:08x}")
            location = addr + byte_size
            if addr == self.boot_address:
                lines.append("_start:")
            if byte_size == 4:
                try:
                    inst = self.decoder.from_opc(val & 0xFFFFFFFF, pc=addr)
                    asm = inst.to_asm() if inst else f".word 0x{val:08x}"
                except Exception:
                    asm = f".word 0x{val:08x}"
                lines.append(f"  {asm}  # 0x{addr:08x}")
            elif byte_size == 8:
                lines.append(f"  .dword 0x{val:016x}  # 0x{addr:08x}")
            else:
                lines.append(f"  .word 0x{val & 0xFFFFFFFF:08x}  # 0x{addr:08x}")

        # .data: loadable data only
        if data_items:
            lines.append("")
            lines.append("  .section .data")
            lines.append("  .align 8")
            lines.append("")
            location = 0
            for addr, item in data_items:
                val = getattr(item, "data", 0) or 0
                byte_size = item.byte_size
                if addr > location:
                    lines.append(f"  .org 0x{addr:08x}")
                location = addr + byte_size
                if byte_size == 8:
                    lines.append(f"  .dword 0x{val:016x}  # 0x{addr:08x}")
                else:
                    lines.append(f"  .word 0x{val & 0xFFFFFFFF:08x}  # 0x{addr:08x}")

        with open(self.output, "w") as f:
            f.write("\n".join(lines))

    def write_debug_yaml(self, path: Path) -> None:
        """Write debug YAML with internal representation (addresses, metadata)."""
        from dataclasses import asdict

        import yaml

        data = self.mem_store.compact_and_return()
        out: dict = {
            "boot_address": (hex(self.boot_address) if self.boot_address is not None else None),
            "exit_address": (hex(self.exit_address) if self.exit_address is not None else None),
            "exception_address": (
                hex(self.exception_address) if self.exception_address is not None else None
            ),
            "memory": {},
        }
        for addr in sorted(data.keys()):
            item = data[addr]
            if hasattr(item, "__dataclass_fields__"):
                d = asdict(item)
                for k in ("data", "ldst_data", "ldst_addr"):
                    if k in d and isinstance(d[k], int):
                        d[k] = hex(d[k])
                out["memory"][hex(addr)] = d
            else:
                out["memory"][hex(addr)] = str(item)
        with open(path, "w") as f:
            yaml.dump(out, f, default_flow_style=False, sort_keys=False)
