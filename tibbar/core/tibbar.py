# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Tibbar main generator loop with trap handling."""

from __future__ import annotations

import logging
import random
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any

from eumos import Eumos
from eumos.decoder import Decoder

from tibbar.core.address_mapper import AddressMapper
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
        *,
        record_execution_trace: bool = False,
    ) -> None:
        if generator is None and generator_factory is None:
            raise ValueError("Provide generator or generator_factory")
        self._generator_factory = generator_factory
        self.generator = generator
        self.seed = seed
        self.output = output or Path("test.S")

        self.log = logging.getLogger("tibbar")
        if not any(getattr(h, "_tibbar_handler", False) for h in self.log.handlers):
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)-20s - %(levelname)s - %(message)s")
            )
            handler._tibbar_handler = True  # type: ignore[attr-defined]
            self.log.addHandler(handler)
        self.log.setLevel(getattr(logging, verbosity.upper()))
        self.log.propagate = False
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
        code_regions = [
            (int(bank["base"]), int(bank["base"]) + int(bank["size"]))
            for bank in self._memory_banks
            if bank.get("code")
        ]
        data_regions = [
            (int(bank["base"]), int(bank["base"]) + int(bank["size"]))
            for bank in self._memory_banks
            if bank.get("data") and not bank.get("code")
        ]
        self.ram_size = code_region_size
        data_reserve = separate_data_size if separate_data_size is not None else config_data_reserve

        self.mem_store = MemoryStore(
            self.log.getChild("memstore"),
            self.random,
            self.seed,
            code_region_size,
            code_regions=code_regions,
            data_regions=data_regions,
        )
        self.mem_store.reserve_data_region(data_reserve)

        self.eumos = Eumos()
        self.instrs = self.eumos.instructions
        self.decoder = Decoder(instructions=self.eumos.instructions)
        causes = getattr(self.eumos, "exception_causes", None)
        self.exception_ids = {c.code: c.identifier for c in causes.values()} if causes else {}
        self.csr_addresses = {name: csr.address for name, csr in self.eumos.csrs.items()}

        self._addr = AddressMapper.from_memory_banks(
            self.mem_store,
            self._memory_banks,
        )
        self.model = create_model(
            self.mem_store,
            self.eumos,
            address_mapper=self._addr,
        )
        self._record_execution_trace = record_execution_trace
        self._executed_instructions: list[dict[str, Any]] = []
        self._execution_summary: dict[str, Any] = {}

        if self.generator is None and self._generator_factory is not None:
            self.generator = self._generator_factory(self)

    def get_current_pc(self) -> int:
        """Current absolute PC for sequence generation."""
        return int(self._pc)

    def allocate_code(
        self,
        min_size: int,
        *,
        align: int = 8,
        pc: int | None = None,
        min_start: int | None = None,
        within: tuple[int, int] | None = None,
    ) -> int | None:
        """Allocate code and return absolute address."""
        return self.mem_store.allocate(
            min_size=min_size,
            align=align,
            purpose="code",
            pc=pc,
            min_start=min_start,
            within=within,
        )

    def allocate_data(self, size: int, *, align: int = 8) -> int | None:
        """Allocate data and return absolute address."""
        return self.mem_store.allocate_data_region(size, align=align)

    def create_test(self) -> None:
        self.info("Creating test")
        self._executed_instructions = []
        self._execution_summary = {}
        self.boot_address = None
        self.exception_address = None
        self.exit_address = None

        # No pre-defined exit address; test ends by jump-to-self, placed when end_sequence runs.
        code_segments = self._addr.code_segments
        if not code_segments:
            raise ValueError("No code banks configured")

        def _range_is_free(addr: int, size: int) -> bool:
            return self.mem_store.check_region_empty(addr, size)

        def _pick_random_boot() -> int:
            eligible = [
                seg for seg in code_segments if seg.size >= self.free_space_required_to_relocate
            ]
            if not eligible:
                raise ValueError("No code bank has enough space for boot/relocate window")
            for _ in range(256):
                seg = self.random.choice(eligible)
                lo = (seg.base + 7) & ~7
                hi = (seg.hi - self.free_space_required_to_relocate) & ~7
                if hi < lo:
                    continue
                cand = self.random.randint(lo, hi) & ~7
                if _range_is_free(cand, self.free_space_required_to_relocate):
                    return cand
            raise ValueError("Unable to choose a valid boot address in configured code banks")

        if self._config_boot is not None:
            boot_val = int(self._config_boot) & ~7
            if not self._addr.is_runtime_code(boot_val, self.free_space_required_to_relocate):
                raise ValueError(
                    f"Configured boot 0x{boot_val:x} is outside configured code banks."
                )
            boot_addr = boot_val
            if not _range_is_free(boot_addr, self.free_space_required_to_relocate):
                raise ValueError(
                    f"Configured boot 0x{boot_addr:x} overlaps pre-reserved memory ranges."
                )
        else:
            boot_addr = _pick_random_boot()

        self.boot_address = boot_addr
        self._pc = boot_addr
        self.info(f"Created boot: 0x{self.boot_address:x}")

        gen = self.generator.gen()
        relocate_gen = None
        model_hung_counter = 0
        gen_hung_counter = 0
        cycle_repeat_count = 0  # only raise after many repeats (allow intentional loops)
        relocating = False
        instr_count = 0
        start = time.time()
        last_gen_pc = "0x0"
        recent_pcs: deque[int] = deque(maxlen=128)
        debug_enabled = self.log.isEnabledFor(logging.DEBUG)
        decode_for_asm = self._record_execution_trace or debug_enabled

        def _raise_hung_in_loop(last_gen: str) -> None:
            raise RuntimeError(
                "Generated code entered an infinite loop (did not reach exit). "
                f"Last instruction placed at {last_gen}. "
                "Try a different --seed (e.g. --seed 43 or --seed 0)."
            )

        while True:
            if self.mem_store.is_memory_populated(self._pc):
                mem_data = self.mem_store.read_from_mem_store(self._pc, 4)
                instr_asm = f".word 0x{mem_data:08x}"
                if decode_for_asm:
                    try:
                        inst = self.decoder.from_opc(mem_data, pc=self._pc)
                        instr_asm = inst.to_asm().upper() if inst else "UNDECODABLE_INSTRUCTION"
                    except Exception:
                        instr_asm = "UNDECODABLE_INSTRUCTION"
                        self.error(f"Undecodable instruction: ({mem_data:#010x})")

                if debug_enabled:
                    self.debug("Modelling: [0x%x]: %#010x -> %s", self._pc, mem_data, instr_asm)

                pc_before = self._pc
                abs_pc_before = self._pc
                self.model.poke_pc(abs_pc_before)
                changes = self.model.execute(mem_data)

                exc_code = getattr(changes, "exception_code", None)
                if exc_code is None and changes is not None and getattr(changes, "exception", None):
                    exc_code = 2  # illegal_instruction
                if changes is not None and exc_code is not None:
                    self.debug(
                        f"INSTRUCTION EXCEPTED: {hex(exc_code)}: "
                        f"{self.exception_ids.get(exc_code, f'UNKNOWN_{exc_code}')}"
                    )
                    self._apply_trap(exc_code, changes, pc_before_abs=abs_pc_before)
                elif changes is not None:
                    self._pc = self._validate_model_pc_in_code_banks(
                        self.model.get_pc(),
                        instr_asm=instr_asm,
                        pc_before_abs=abs_pc_before,
                    )
                else:
                    self._pc = self._validate_model_pc_in_code_banks(
                        self.model.get_pc(),
                        instr_asm=instr_asm,
                        pc_before_abs=abs_pc_before,
                    )

                if self._record_execution_trace:
                    self._record_execution_step(
                        pc_before=pc_before,
                        pc_after=self._pc,
                        instr=mem_data,
                        instr_asm=instr_asm,
                        changes=changes,
                        exception_code=exc_code,
                    )

                # Exit loop: branch/jal to self (infinite loop at exit sequence) → test complete
                if self._pc == pc_before:
                    if self.exit_address is None:
                        self.exit_address = pc_before
                    self._execution_summary = {
                        "termination_reason": "self_loop_exit",
                        "termination_pc": hex(pc_before),
                        "termination_abs_pc": hex(pc_before),
                        "steps_recorded": len(self._executed_instructions),
                    }
                    break

                # Accidental loop: raise only after many repeats (intentional loops allowed)
                if self._pc in recent_pcs:
                    cycle_repeat_count += 1
                    if cycle_repeat_count > 100:
                        _raise_hung_in_loop(last_gen_pc)
                else:
                    cycle_repeat_count = 0
                recent_pcs.append(self._pc)

                gen_hung_counter = 0
                model_hung_counter += 1
            else:
                recent_pcs.clear()
                cycle_repeat_count = 0
                free_space_remaining = self.mem_store.get_free_space(self._pc)
                test_data = None
                if free_space_remaining <= self.free_space_required_to_relocate or relocating:
                    if relocate_gen is None:
                        relocate_gen = self.generator.relocate_sequence.gen()
                        relocating = True
                    try:
                        test_data = next(relocate_gen)
                    except StopIteration:
                        relocating = False
                        relocate_gen = None
                if test_data is None:
                    try:
                        test_data = next(gen)
                    except StopIteration:
                        self._execution_summary = {
                            "termination_reason": "generator_exhausted",
                            "steps_recorded": len(self._executed_instructions),
                        }
                        break

                if test_data.addr is None:
                    test_data.addr = self._pc
                else:
                    test_data.addr = self._runtime_addr_to_mem_store_addr(
                        int(test_data.addr), int(test_data.byte_size)
                    )
                if getattr(test_data, "ldst_addr", None) is not None:
                    ldst_size = int(getattr(test_data, "ldst_size", 8))
                    test_data.ldst_addr = self._runtime_addr_to_mem_store_addr(
                        int(test_data.ldst_addr),
                        ldst_size,
                    )

                self.mem_store.add_to_mem_store(test_data)
                if getattr(test_data, "seq", None) == "DefaultProgramEnd":
                    self.exit_address = test_data.addr
                instr_count += 1

                gen_hung_counter += 1
                model_hung_counter = 0
                last_gen_pc = f"0x{self._pc:x}"

            if gen_hung_counter > 100:
                raise RuntimeError(
                    "Potentially hung - generator produced many instructions without modelling; "
                    "internal consistency error."
                )
            if model_hung_counter > 1000:
                _raise_hung_in_loop(last_gen_pc)

        end = time.time()
        self.info("Generated testcase")
        self.info(
            f"Generated {instr_count} instructions in "
            f"{(end - start):.1f} seconds. "
            f"({instr_count / max(0.001, end - start):.02f} ips)"
        )
        if not self._execution_summary:
            self._execution_summary = {
                "termination_reason": "complete",
                "steps_recorded": len(self._executed_instructions),
            }

    def _fmt_u64(self, value: Any) -> str | None:
        if value is None:
            return None
        return hex(int(value) & 0xFFFF_FFFF_FFFF_FFFF)

    def _fmt_code_addr(self, value: Any) -> tuple[str, str]:
        return self._addr.format_code_addr(int(value))

    def _runtime_addr_to_mem_store_addr(self, addr: int, size: int) -> int:
        """Validate runtime address for MemoryStore access."""
        return self._addr.require_store_addr(addr, size)

    def _record_execution_step(
        self,
        *,
        pc_before: int,
        pc_after: int,
        instr: int,
        instr_asm: str,
        changes: object | None,
        exception_code: int | None,
    ) -> None:
        rel_pc, abs_pc = self._fmt_code_addr(pc_before)
        rel_next_pc, abs_next_pc = self._fmt_code_addr(pc_after)
        step: dict[str, Any] = {
            "step": len(self._executed_instructions),
            "pc": rel_pc,
            "abs_pc": abs_pc,
            "instr": hex(instr & 0xFFFF_FFFF),
            "asm": instr_asm,
            "next_pc": rel_next_pc,
            "abs_next_pc": abs_next_pc,
            "gpr_writes": [],
            "csr_writes": [],
            "fpr_writes": [],
            "memory_reads": [],
            "memory_writes": [],
        }
        if exception_code is not None:
            step["exception_code"] = hex(exception_code)
            step["exception_name"] = self.exception_ids.get(
                exception_code, f"UNKNOWN_{exception_code}"
            )
        if changes is None:
            step["changes_available"] = False
            self._executed_instructions.append(step)
            return

        detail = changes.to_detailed_dict() if hasattr(changes, "to_detailed_dict") else {}
        step["changes_available"] = True
        if detail.get("exception") is not None:
            step["exception"] = detail["exception"]
        if detail.get("pc_change") is not None:
            new_pc, old_pc = detail["pc_change"]
            rel_from, abs_from = self._fmt_code_addr(old_pc)
            rel_to, abs_to = self._fmt_code_addr(new_pc)
            step["pc_change"] = {
                "from": rel_from,
                "abs_from": abs_from,
                "to": rel_to,
                "abs_to": abs_to,
            }
        if detail.get("branch_info") is not None:
            branch = detail["branch_info"]
            target_rel, target_abs = self._fmt_code_addr(branch["target"])
            step["branch_info"] = {
                "taken": bool(branch["taken"]),
                "condition": branch["condition"],
                "target": target_rel,
                "abs_target": target_abs,
            }

        for wr in detail.get("gpr_writes", []):
            step["gpr_writes"].append(
                {
                    "register": int(wr["register"]),
                    "value": self._fmt_u64(wr["value"]),
                    "old_value": self._fmt_u64(wr["old_value"]),
                }
            )
        for wr in detail.get("csr_writes", []):
            step["csr_writes"].append(
                {
                    "address": hex(int(wr["address"])),
                    "name": wr["name"],
                    "value": self._fmt_u64(wr["value"]),
                    "old_value": self._fmt_u64(wr["old_value"]),
                }
            )
        for wr in detail.get("fpr_writes", []):
            step["fpr_writes"].append(
                {
                    "register": int(wr["register"]),
                    "value": self._fmt_u64(wr["value"]),
                    "old_value": self._fmt_u64(wr["old_value"]),
                }
            )
        for access in detail.get("memory_accesses", []):
            addr = int(access["address"])
            size = int(access["size"])
            is_write = bool(access["is_write"])
            value = access["value"]
            if value is None and not is_write:
                try:
                    mem_addr = self._runtime_addr_to_mem_store_addr(addr, size)
                    value = self.mem_store.read_from_mem_store(mem_addr, size)
                except (ValueError, AssertionError):
                    value = None
            mem_item = {
                "address": hex(addr),
                "size": size,
                "value": self._fmt_u64(value),
            }
            if is_write:
                step["memory_writes"].append(mem_item)
            else:
                step["memory_reads"].append(mem_item)

        self._executed_instructions.append(step)

    def _apply_trap(
        self,
        exception_code: int,
        changes: object,
        *,
        pc_before_abs: int,
    ) -> None:
        """Apply trap: set mepc, mcause, mtval, then PC = mtvec."""
        mepc_addr = self.csr_addresses.get("mepc")
        mcause_addr = self.csr_addresses.get("mcause")
        mtval_addr = self.csr_addresses.get("mtval")
        mtvec_addr = self.csr_addresses.get("mtvec")

        if mepc_addr is not None:
            self.model.poke_csr(mepc_addr, pc_before_abs)
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

        self._pc = self._validate_model_pc_in_code_banks(
            self.model.get_pc(),
            instr_asm="trap_handler_redirect",
            pc_before_abs=pc_before_abs,
        )

    def _code_banks_str(self) -> str:
        banks = [
            (
                int(bank["base"]),
                int(bank["base"]) + int(bank["size"]),
            )
            for bank in self._memory_banks
            if bank.get("code")
        ]
        return ", ".join(f"[0x{lo:x}, 0x{hi:x})" for lo, hi in banks)

    def _validate_model_pc_in_code_banks(
        self,
        model_pc: int,
        *,
        instr_asm: str,
        pc_before_abs: int,
    ) -> int:
        try:
            # Lome PC is already absolute. This function only validates that
            # control flow stays inside configured executable banks.
            return self._addr.require_code_addr(model_pc, 1)
        except ValueError:
            pass
        raise RuntimeError(
            "Generated control flow escaped configured code banks: "
            f"pc_before=0x{pc_before_abs:x}, next_pc=0x{model_pc:x}, instr={instr_asm}. "
            f"Allowed code ranges: {self._code_banks_str()}"
        )

    def run(self) -> None:
        """Create test and write output."""
        self.create_test()
        self.write_asm()

    def _find_code_segment_index(self, addr: int) -> int | None:
        return self._addr.find_code_segment_index(addr)

    def _find_data_segment_index(self, addr: int) -> int | None:
        return self._addr.find_data_segment_index(addr)

    def _write_linker_script(self) -> None:
        """Write linker script aligned to configured memory banks next to ASM output."""
        ld_path = self.output.with_suffix(".ld")
        code_banks = [b for b in self._memory_banks if b.get("code")]
        data_banks = [b for b in self._memory_banks if b.get("data") and not b.get("code")]
        valid_access_chars = set("rwxail!")

        def _ld_access(bank: dict[str, object], default: str) -> str:
            access = str(bank.get("access", default)).strip().lower()
            filtered = "".join(ch for ch in access if ch in valid_access_chars)
            return filtered or default

        lines: list[str] = []
        lines.append("/* Auto-generated by Tibbar. */")
        lines.append("OUTPUT_ARCH(riscv)")
        lines.append("ENTRY(_start)")
        lines.append("")
        lines.append("MEMORY")
        lines.append("{")
        for i, bank in enumerate(code_banks):
            attrs = _ld_access(bank, "rwx")
            base = int(bank["base"])
            size = int(bank["size"])
            lines.append(f"    CODE{i} ({attrs}) : ORIGIN = 0x{base:x}, LENGTH = 0x{size:x}")
        if data_banks:
            for i, bank in enumerate(data_banks):
                attrs = _ld_access(bank, "rw")
                base = int(bank["base"])
                size = int(bank["size"])
                lines.append(f"    DATA{i} ({attrs}) : ORIGIN = 0x{base:x}, LENGTH = 0x{size:x}")
        lines.append("}")
        lines.append("")
        lines.append("PHDRS")
        lines.append("{")
        lines.append("    text PT_LOAD FLAGS(5);")
        lines.append("    data PT_LOAD FLAGS(6);")
        lines.append("}")
        lines.append("")
        lines.append("SECTIONS")
        lines.append("{")
        for i, _bank in enumerate(code_banks):
            lines.append(f"    .text.bank{i} : {{ *(.text.bank{i}) }} > CODE{i} :text")
        # Compatibility section in first code bank.
        lines.append("    .text : { *(.text .text.*) } > CODE0 :text")
        lines.append("    .rodata : { *(.rodata .rodata.*) } > CODE0 :text")
        if data_banks:
            for i, _bank in enumerate(data_banks):
                lines.append(f"    .data.bank{i} : {{ *(.data.bank{i}) }} > DATA{i} :data")
            lines.append("    .data : { *(.data .data.*) } > DATA0 :data")
            lines.append("    .bss : { *(.bss .bss.*) *(COMMON) } > DATA0 :data")
            lines.append("    __stack_top = ORIGIN(DATA0) + LENGTH(DATA0);")
        else:
            # Unified mode: data is at end of the last code bank. With multiple code
            # banks that is the last bank; with one bank it is CODE0.
            last_code = len(code_banks) - 1
            lines.append(f"    .data : {{ *(.data .data.*) }} > CODE{last_code} :data")
            lines.append(f"    .bss : {{ *(.bss .bss.*) *(COMMON) }} > CODE{last_code} :data")
            lines.append(f"    __stack_top = ORIGIN(CODE{last_code}) + LENGTH(CODE{last_code});")
        lines.append("}")
        lines.append("")

        with open(ld_path, "w") as f:
            f.write("\n".join(lines))

    def write_asm(self) -> None:
        """Write .asm output using bank-aware sections and runtime address comments."""
        data = self.mem_store.export_and_return()
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
        if self.exit_address is not None:
            lines.append(f"# Exit: 0x{self.exit_address:x}")
        lines.append("")

        # Ensure every branch/jal target has an instruction (insert nop if missing, e.g. from
        # random allocator choosing a target that was never filled).
        code_addrs = {addr for addr, _ in code_items}
        _BRANCH_JAL = ("jal", "beq", "bne", "blt", "bge", "bltu", "bgeu")
        _NOP_ENC = 0x00000013  # addi x0, x0, 0
        placeholder = type("_Placeholder", (), {"data": _NOP_ENC, "byte_size": 4})()
        for addr, item in list(code_items):
            if getattr(item, "byte_size", 0) != 4:
                continue
            val = getattr(item, "data", 0) or 0
            try:
                inst = self.decoder.from_opc(val & 0xFFFFFFFF, pc=addr)
                if not inst or inst.instruction.mnemonic not in _BRANCH_JAL:
                    continue
                imm = inst.operand_values.get("imm")
                if imm is not None:
                    target_runtime = addr + imm
                    try:
                        target = self._addr.require_code_addr(target_runtime, 1)
                    except ValueError:
                        # Unmappable targets are outside configured code banks.
                        continue
                    if target not in code_addrs:
                        code_items.append((target, placeholder))
                        code_addrs.add(target)
            except Exception:
                pass
        code_items.sort(key=lambda x: x[0])
        branch_targets_with_code = {addr: f".L_tgt_{addr:x}" for addr in code_addrs}

        # .text.bankN: code only, emitted at per-bank section offsets.
        code_by_bank: dict[int, list[tuple[int, object]]] = {}
        for addr, item in code_items:
            bank_idx = self._find_code_segment_index(addr)
            if bank_idx is None:
                continue
            code_by_bank.setdefault(bank_idx, []).append((addr, item))

        lines.append("  .globl _start")
        lines.append("")
        for bank_idx in sorted(code_by_bank.keys()):
            seg = self._addr.code_segments[bank_idx]
            lines.append(f"  .section .text.bank{bank_idx}")
            lines.append("  .align 2")
            lines.append("")
            location = 0
            for addr, item in sorted(code_by_bank[bank_idx], key=lambda x: x[0]):
                val = getattr(item, "data", 0) or 0
                byte_size = item.byte_size
                section_addr = addr - seg.base
                runtime_addr = addr
                if section_addr > location:
                    lines.append(f"  .org 0x{section_addr:08x}")
                location = section_addr + byte_size
                if self.boot_address is not None and addr == self.boot_address:
                    lines.append("_start:")
                if self.exit_address is not None and addr == self.exit_address:
                    lines.append("  .globl _exit")
                    lines.append("_exit:")
                if addr in branch_targets_with_code:
                    lines.append(f"{branch_targets_with_code[addr]}:")
                if byte_size == 4:
                    try:
                        inst = self.decoder.from_opc(val & 0xFFFFFFFF, pc=runtime_addr)
                        asm = inst.to_asm() if inst else f".word 0x{val:08x}"
                        if inst and inst.instruction.mnemonic in _BRANCH_JAL:
                            imm = inst.operand_values.get("imm")
                            if imm is not None:
                                target_runtime = runtime_addr + imm
                                try:
                                    target = self._addr.require_code_addr(target_runtime, 1)
                                except ValueError:
                                    target = None
                                label = (
                                    branch_targets_with_code.get(target)
                                    if target is not None
                                    else None
                                )
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
                    lines.append(f"  {asm}  # 0x{runtime_addr:016x}")
                elif byte_size == 8:
                    lines.append(f"  .dword 0x{val:016x}  # 0x{runtime_addr:016x}")
                else:
                    lines.append(f"  .word 0x{val & 0xFFFFFFFF:08x}  # 0x{runtime_addr:016x}")
            lines.append("")

        # .data.bankN: loadable data only.
        if data_items:
            data_by_bank: dict[int, list[tuple[int, object]]] = {}
            for addr, item in data_items:
                bank_idx = self._find_data_segment_index(addr)
                if bank_idx is None:
                    continue
                data_by_bank.setdefault(bank_idx, []).append((addr, item))
            if data_by_bank:
                for bank_idx in sorted(data_by_bank.keys()):
                    seg = self._addr.data_segments[bank_idx]
                    lines.append(f"  .section .data.bank{bank_idx}")
                    lines.append("  .align 8")
                    lines.append("")
                    location = 0
                    for addr, item in sorted(data_by_bank[bank_idx], key=lambda x: x[0]):
                        val = getattr(item, "data", 0) or 0
                        byte_size = item.byte_size
                        section_addr = addr - seg.base
                        runtime_addr = addr
                        if section_addr > location:
                            lines.append(f"  .org 0x{section_addr:08x}")
                        location = section_addr + byte_size
                        if byte_size == 8:
                            lines.append(f"  .dword 0x{val:016x}  # 0x{runtime_addr:016x}")
                        else:
                            lines.append(
                                f"  .word 0x{val & 0xFFFFFFFF:08x}  # 0x{runtime_addr:016x}"
                            )
                    lines.append("")
            else:
                # Unified mode: data is at end of the last code bank. With multiple
                # code banks, .data is placed in the last code bank so section
                # offsets must be relative to that segment.
                last_seg = self._addr.code_segments[-1]
                section_base = last_seg.base
                lines.append("  .section .data")
                lines.append("  .align 8")
                lines.append("")
                location = 0
                for addr, item in sorted(data_items, key=lambda x: x[0]):
                    val = getattr(item, "data", 0) or 0
                    byte_size = item.byte_size
                    section_addr = addr - section_base
                    runtime_addr = addr
                    if section_addr > location:
                        lines.append(f"  .org 0x{section_addr:08x}")
                    location = section_addr + byte_size
                    if byte_size == 8:
                        lines.append(f"  .dword 0x{val:016x}  # 0x{runtime_addr:016x}")
                    else:
                        lines.append(f"  .word 0x{val & 0xFFFFFFFF:08x}  # 0x{runtime_addr:016x}")
                lines.append("")

        with open(self.output, "w") as f:
            f.write("\n".join(lines) + "\n")
        self._write_linker_script()

    def write_debug_yaml(self, path: Path) -> None:
        """Write debug YAML with internal representation (addresses, metadata)."""
        from dataclasses import asdict

        import yaml

        data = self.mem_store.export_and_return()
        out: dict = {
            "load_addr": hex(self.load_addr),
            "ram_size": hex(self.ram_size),
            "boot_address": (hex(self.boot_address) if self.boot_address is not None else None),
            "exit_address": (hex(self.exit_address) if self.exit_address is not None else None),
            "exception_address": (
                hex(self.exception_address) if self.exception_address is not None else None
            ),
            "memory": {},
            "executed_instructions": self._executed_instructions,
            "execution_summary": self._execution_summary,
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
