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

from tibbar.core.memory_config import (
    get_default_config_path,
    load_memory_config,
    resolve_memory_from_config,
)
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
        memory_config: Path | None = None,
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

        # Config: default separate inst/data banks; --memory-config for single RAM.
        config_path = memory_config if memory_config is not None else get_default_config_path()
        banks, config_data_reserve, self._config_boot = load_memory_config(config_path)
        (
            code_region_size,
            self.load_addr,
            separate_data_size,
            self._data_region_base,
            self._memory_banks,
        ) = resolve_memory_from_config(banks)
        self.ram_size = code_region_size
        data_reserve = separate_data_size if separate_data_size is not None else config_data_reserve

        self.mem_store = MemoryStore(
            self.log.getChild("memstore"),
            self.random,
            self.seed,
            code_region_size,
            separate_data_region_size=separate_data_size,
        )
        self.mem_store.reserve_data_region(data_reserve)

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

        # Allocate exit region first (avoid 0; TB detects exit by known PC or branch-to-self).
        exit_min_start = 0x100
        mem_size = self.mem_store.get_memory_size()
        exit_region = self.mem_store.allocate_region(
            100,
            min_start=exit_min_start,
            pc_hint=self.random.randint(exit_min_start, max(exit_min_start, mem_size - 100 - 1)),
        )
        assert exit_region is not None, "No space for exit region"
        self.exit_address = exit_region
        self._exit_ptr = self.exit_address
        self.info(f"Created exit_ptr: 0x{self._exit_ptr:x}")

        # Boot: from config (if set) or random, not inside the exit region.
        max_boot = mem_size - self.free_space_required_to_relocate
        data_base = self.mem_store.get_data_region_base()
        if data_base is not None:
            max_boot = min(max_boot, data_base - 1)
        exit_end = exit_region + 100
        if self._config_boot is not None:
            self.boot_address = self._config_boot & ~7
            if exit_region <= self.boot_address < exit_end:
                raise ValueError(
                    f"Config boot 0x{self._config_boot:x} (aligned 0x{self.boot_address:x}) "
                    "inside exit region; choose another boot or omit for random."
                )
            if self.boot_address > max_boot:
                raise ValueError(
                    f"Config boot 0x{self._config_boot:x} exceeds range (max 0x{max_boot:x})."
                )
        else:
            candidates_lo = (0, exit_region) if exit_region > 0 else (0, 0)
            candidates_hi = (exit_end, max_boot + 1) if exit_end <= max_boot else (0, 0)
            ranges = [r for r in (candidates_lo, candidates_hi) if r[1] > r[0]]
            assert ranges, "No space for boot address"
            lo, hi = self.random.choice(ranges)
            self.boot_address = self.random.randint(lo, max(lo, hi - 1))
            self.boot_address = self.boot_address & ~7
            if exit_region <= self.boot_address < exit_end:
                self.boot_address = (exit_end + 7) & ~7
            assert self.boot_address <= max_boot, "No space for aligned boot address"

        self._pc = self.boot_address
        self.info(f"Created boot: 0x{self._pc:x}")

        gen = self.generator.gen()
        relocate_gen = None
        end_sequence_gen = None  # used only when _pc == _exit_ptr so we place full exit loop
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

                pc_before = self._pc
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

                # Exit loop: branch/jal to self (infinite loop at exit sequence) → test complete
                if self._pc == pc_before:
                    break

                gen_hung_counter = 0
                model_hung_counter += 1
            else:
                free_space_remaining = self.mem_store.get_free_space(self._pc)
                test_data = None
                # At exit pointer: place the full end sequence (LoadGPR + jalr + infinite jal)
                # so we never leave a branch target empty (avoids R_RISCV_JAL *UND*).
                if self._pc == self._exit_ptr:
                    if end_sequence_gen is None:
                        end_sequence_gen = self.generator.end_sequence.gen()
                    try:
                        test_data = next(end_sequence_gen)
                    except StopIteration:
                        break
                elif free_space_remaining <= self.free_space_required_to_relocate or relocating:
                    if relocate_gen is None:
                        relocate_gen = self.generator.relocate_sequence.gen()
                        relocating = True
                    try:
                        test_data = next(relocate_gen)
                    except StopIteration:
                        relocating = False
                if test_data is None:
                    try:
                        test_data = next(gen)
                    except StopIteration:
                        break

                if test_data.addr is None:
                    test_data.addr = self._pc

                self.mem_store.add_to_mem_store(test_data)
                instr_count += 1

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
        lines.append(f"# Load address: 0x{self.load_addr:x}")
        lines.append(f"# RAM size: 0x{self.ram_size:x}")
        if self._data_region_base is not None:
            data_size = self.mem_store.get_data_region_size()
            lines.append(f"# Data region: 0x{self._data_region_base:x}, size 0x{data_size:x}")
        lines.append(f"# Boot: 0x{self.boot_address:x}")
        lines.append(f"# Exit: 0x{self.exit_address:x}")
        lines.append("")

        # Fail if any branch/jal target has no instruction (generator bug).
        code_addrs = {addr for addr, _ in code_items}
        _BRANCH_JAL = ("jal", "beq", "bne", "blt", "bge", "bltu", "bgeu")
        branch_targets_with_code: dict[int, str] = {}  # addr -> label for linkability
        for addr, item in code_items:
            if getattr(item, "byte_size", 0) != 4:
                continue
            val = getattr(item, "data", 0) or 0
            try:
                inst = self.decoder.from_opc(val & 0xFFFFFFFF, pc=addr)
                if not inst or inst.instruction.mnemonic not in _BRANCH_JAL:
                    continue
                imm = inst.operand_values.get("imm")
                if imm is not None:
                    target = addr + imm
                    if target not in code_addrs:
                        raise AssertionError(
                            f"Branch/jal at 0x{addr:x} targets 0x{target:x} but there is no "
                            "instruction there; generator must place code at every target."
                        )
                    if target not in branch_targets_with_code:
                        branch_targets_with_code[target] = f".L_tgt_{target:x}"
            except AssertionError:
                raise
            except Exception:
                pass

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
            if addr == self.exit_address:
                lines.append("  .globl _exit")
                lines.append("_exit:")
            # Emit labels at branch/jal targets so linker can resolve R_RISCV_JAL (target has
            # an instruction; we already asserted that; labels are for linkability only).
            if addr in branch_targets_with_code:
                lines.append(f"{branch_targets_with_code[addr]}:")
            if byte_size == 4:
                try:
                    inst = self.decoder.from_opc(val & 0xFFFFFFFF, pc=addr)
                    asm = inst.to_asm() if inst else f".word 0x{val:08x}"
                    # Use label for jal/branch target so linker resolves R_RISCV_JAL
                    if inst and inst.instruction.mnemonic in _BRANCH_JAL:
                        imm = inst.operand_values.get("imm")
                        if imm is not None:
                            target = addr + imm
                            label = branch_targets_with_code.get(target)
                            if label is not None:
                                parts = asm.split(None, 1)
                                if len(parts) == 2:
                                    mnemonic, rest = parts
                                    rest_parts = [x.strip() for x in rest.split(",")]
                                    if rest_parts:
                                        rest_parts[-1] = label
                                        asm = f"{mnemonic} {', '.join(rest_parts)}"
                except Exception:
                    asm = f".word 0x{val:08x}"
                lines.append(f"  {asm}  # 0x{addr:08x}")
            elif byte_size == 8:
                lines.append(f"  .dword 0x{val:016x}  # 0x{addr:08x}")
            else:
                lines.append(f"  .word 0x{val & 0xFFFFFFFF:08x}  # 0x{addr:08x}")

        # .data: loadable data only (addresses 0-based in section when using separate data bank)
        data_vma_offset = self.mem_store.get_data_vma_offset()
        if data_items:
            lines.append("")
            lines.append("  .section .data")
            lines.append("  .align 8")
            lines.append("")
            location = 0
            for addr, item in data_items:
                val = getattr(item, "data", 0) or 0
                byte_size = item.byte_size
                section_addr = addr - data_vma_offset
                if section_addr > location:
                    lines.append(f"  .org 0x{section_addr:08x}")
                location = section_addr + byte_size
                if byte_size == 8:
                    lines.append(f"  .dword 0x{val:016x}  # 0x{addr:08x}")
                else:
                    lines.append(f"  .word 0x{val & 0xFFFFFFFF:08x}  # 0x{addr:08x}")

        with open(self.output, "w") as f:
            f.write("\n".join(lines) + "\n")

    def write_debug_yaml(self, path: Path) -> None:
        """Write debug YAML with internal representation (addresses, metadata)."""
        from dataclasses import asdict

        import yaml

        data = self.mem_store.compact_and_return()
        out: dict = {
            "load_addr": hex(self.load_addr),
            "ram_size": hex(self.ram_size),
            "boot_address": (hex(self.boot_address) if self.boot_address is not None else None),
            "exit_address": (hex(self.exit_address) if self.exit_address is not None else None),
            "exception_address": (
                hex(self.exception_address) if self.exception_address is not None else None
            ),
            "memory": {},
            "memory_banks": self._memory_banks,
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
