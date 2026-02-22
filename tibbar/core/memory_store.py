# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Linear byte-addressed memory store for the ISG."""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from tibbar.utils import MASK_64_BIT

if TYPE_CHECKING:
    from tibbar.testobj import GenData


# When using a separate data bank, data addresses live above this offset
# so they don't collide with code; ASM emit subtracts this for the .data section VMA.
DATA_VMA_OFFSET = 0x1_0000_0000


class MemoryStore:
    """Linear byte-addressed memory for instruction/data placement."""

    def __init__(
        self,
        log: logging.Logger,
        rng: random.Random,
        seed: int,
        max_size: int,
        *,
        separate_data_region_size: int | None = None,
    ) -> None:
        self.random = rng
        self.seed = seed
        self._max_size = max_size
        self._gen_store: dict[int, GenData] = {}
        self._live_memory: dict[int, int] = {}
        self._used_ranges: list[tuple[int, int]] = []
        self._data_region_base: int | None = None
        self._data_region_size: int = 0
        self._data_next: int = 0
        self._separate_data_region = separate_data_region_size is not None
        self._data_vma_offset = DATA_VMA_OFFSET if separate_data_region_size else 0
        self.debug = log.debug
        self.info = log.info
        self.warning = log.warning
        self.error = log.error

    def get_memory_size(self) -> int:
        return self._max_size

    def _normalize_pc(self, pc: int | object) -> int:
        if isinstance(pc, int):
            return pc
        return getattr(pc, "address", pc)

    def _insert_used_range(self, start: int, end: int) -> None:
        if start >= end:
            return
        self._used_ranges.append((start, end))
        self._used_ranges.sort(key=lambda r: r[0])
        merged: list[tuple[int, int]] = []
        for s, e in self._used_ranges:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))
        self._used_ranges = merged

    def check_region_empty(self, addr: int, byte_size: int) -> bool:
        """True iff [addr, addr+byte_size) does not overlap any existing _gen_store item."""
        if addr < 0 or byte_size <= 0 or addr + byte_size > self._max_size:
            return False
        end = addr + byte_size
        for s, item in self._gen_store.items():
            item_size = getattr(item, "byte_size", 4)
            e = s + item_size
            if not (end <= s or addr >= e):
                return False
        return True

    def _code_region_end(self) -> int:
        """End of code region: for single bank, data base; for multi-bank, max_size."""
        if self._data_region_base is not None and not self._separate_data_region:
            return self._data_region_base
        return self._max_size

    def _find_gap_in_region(
        self,
        min_size: int,
        align: int,
        pc_addr: int,
        min_start: int | None,
        within: tuple[int, int] | None,
        region_end: int | None,
    ) -> int | None:
        """Find one gap in [0, region_end) (or [0, _max_size) if region_end is None).

        Returns a block with at least min_size bytes, or None.
        """
        gaps: list[tuple[int, int]] = []
        prev_end = 0
        effective_max = self._max_size if region_end is None else min(self._max_size, region_end)
        for s, e in self._used_ranges:
            if s > prev_end:
                gap_end = min(s, effective_max)
                if gap_end > prev_end:
                    gaps.append((prev_end, gap_end))
            prev_end = max(prev_end, e)
        if prev_end < effective_max:
            gaps.append((prev_end, effective_max))

        candidates: list[int] = []
        for gap_start, gap_end in gaps:
            if gap_end - gap_start < min_size:
                continue
            aligned_start = (gap_start + align - 1) & -align
            if within is not None:
                if aligned_start + min_size <= gap_end:
                    min_off, max_off = within
                    lo = max(aligned_start, pc_addr + min_off)
                    hi = min(gap_end - min_size, pc_addr + max_off)
                    if lo <= hi:
                        cand = (lo + align - 1) & -align
                        if cand + min_size <= gap_end and cand <= hi:
                            candidates.append(cand)
            else:
                start_cand = aligned_start
                if min_start is not None and aligned_start < min_start:
                    start_cand = (min_start + align - 1) & -align
                if start_cand + min_size <= gap_end:
                    candidates.append(start_cand)
                    hi = gap_end - min_size
                    if hi > start_cand:
                        near = max(start_cand, min(hi, pc_addr))
                        near = (near + align - 1) & -align
                        if start_cand <= near <= hi and near not in candidates:
                            candidates.append(near)
        if min_start is not None:
            candidates = [c for c in candidates if c >= min_start]
        if not candidates:
            return None
        return self.random.choice(candidates)

    def allocate(
        self,
        min_size: int,
        align: int = 8,
        purpose: str = "code",
        pc: int | object | None = None,
        min_start: int | None = None,
        within: tuple[int, int] | None = None,
    ) -> int | None:
        """Allocate a block: code in code region, data in data region.

        Returns base address or None. When within= is set, pc is the current PC
        used to compute the valid target range [pc+min_off, pc+max_off].
        """
        if purpose == "data":
            if self._data_region_base is None:
                self.reserve_data_region(256 * 1024, align=align)
            assert self._data_region_base is not None
            addr = (self._data_next + align - 1) & -align
            end = addr + min_size
            if end > self._data_region_base + self._data_region_size:
                return None
            self._data_next = end
            return addr

        # purpose == "code"
        region_end = self._code_region_end()
        pc_addr = self._normalize_pc(pc) if pc is not None else 0
        base = self._find_gap_in_region(min_size, align, pc_addr, min_start, within, region_end)
        if base is None and pc_addr != 0:
            base = self._find_gap_in_region(min_size, align, 0, min_start, within, region_end)
        if base is None:
            return None
        self._insert_used_range(base, base + min_size)
        return base

    def get_free_space(self, pc: int | object) -> int:
        pc_addr = self._normalize_pc(pc)
        if pc_addr >= self._max_size:
            return 0
        region_end = self._code_region_end()
        if pc_addr >= region_end:
            return 0
        for s, e in self._used_ranges:
            if s > pc_addr:
                free = s - pc_addr
                return min(free, region_end - pc_addr)
            if e > pc_addr:
                return 0
        return min(self._max_size - pc_addr, region_end - pc_addr)

    def compact_and_return(self) -> dict[int, object]:
        output: dict[int, object] = {}
        for addr, item in self._gen_store.items():
            output[addr] = item.export_to_tibbar_item()
        return output

    def read_from_mem_store(self, addr: int, size: int = 8) -> int:
        assert 0 <= addr < self._max_size, f"Address out of range: {addr=}"
        assert addr + size <= self._max_size, f"Access past end: {addr}+{size}"
        assert size <= 8, f"Not expecting size over 8 bytes: {size=}"
        dword = 0
        for byte in range(size):
            byte_data = self._live_memory.get(addr + byte, 0)
            dword |= byte_data << (8 * byte)
        return dword

    def is_memory_populated(self, addr: int | object) -> bool:
        a = self._normalize_pc(addr) if not isinstance(addr, int) else addr
        return a in self._live_memory

    def write_to_mem_store(
        self,
        addr: int,
        data: int,
        strobe: int = MASK_64_BIT,
    ) -> None:
        assert 0 <= addr < self._max_size, f"Address out of range: {addr=}"
        for i in range(8):
            if (strobe >> (i * 8)) & 0xFF:
                self._live_memory[addr + i] = (data >> (8 * i)) & 0xFF

    def add_to_mem_store(self, test_obj: GenData) -> None:
        from tibbar.testobj import GenData

        addr = test_obj.addr
        if addr is None:
            raise ValueError("GenData.addr must be set before add_to_mem_store")
        if not isinstance(addr, int):
            addr = getattr(addr, "address", addr)

        free = self.get_free_space(addr)
        self.debug(f"Adding to mem_store: 0x{addr:x}: {test_obj} (free until next: {free} bytes)")

        if test_obj.ldst_data is not None:
            ldst_addr = test_obj.ldst_addr
            if ldst_addr is None:
                raise ValueError("ldst_addr required when ldst_data is set")
            if not isinstance(ldst_addr, int):
                ldst_addr = getattr(ldst_addr, "address", ldst_addr)
            self.add_to_mem_store(
                GenData(
                    seq=test_obj.seq,
                    addr=ldst_addr,
                    data=test_obj.ldst_data,
                    byte_size=test_obj.ldst_size,
                    comment=(
                        f"Load data for instruction at 0x{addr:x} "
                        f"(data=0x{test_obj.ldst_data:_x}, size={test_obj.ldst_size})"
                    ),
                    is_data=True,
                )
            )

        memory_empty = self.check_region_empty(addr, test_obj.byte_size)
        assert memory_empty, f"0x{addr:x} is already in use"

        self._gen_store[addr] = test_obj
        self._insert_used_range(addr, addr + test_obj.byte_size)

        match test_obj.byte_size:
            case 1:
                strobe = 0xFF
            case 2:
                strobe = 0xFFFF
            case 4:
                strobe = 0xFFFF_FFFF
            case 8:
                strobe = MASK_64_BIT
            case _:
                raise ValueError(f"Unsupported datasize: {test_obj.byte_size}")
        self.write_to_mem_store(addr, test_obj.data or 0, strobe)

    def allocate_region(
        self,
        size: int,
        align: int = 8,
        min_start: int | None = None,
        pc: int | object | None = None,
    ) -> int | None:
        """Find a free block in code region, mark it used, return base.

        Thin wrapper around allocate(..., purpose="code").
        """
        return self.allocate(
            min_size=size,
            align=align,
            purpose="code",
            pc=pc,
            min_start=min_start,
        )

    def reserve_data_region(self, size: int, align: int = 8) -> None:
        """Reserve a contiguous region for loadable data. Call once at init.
        If separate_data_region_size was set, data lives at DATA_VMA_OFFSET and does not
        consume code space; otherwise data is at the end of the code space.
        """
        if self._data_region_base is not None:
            return
        if self._separate_data_region:
            self._data_region_base = DATA_VMA_OFFSET
            self._data_region_size = size
            self._data_next = DATA_VMA_OFFSET
        else:
            base = (self._max_size - size) & -align
            if base < 0:
                raise AssertionError("No space for data region")
            self._data_region_base = base
            self._data_region_size = size
            self._data_next = base
            self._insert_used_range(base, base + size)

    def get_data_region_base(self) -> int | None:
        """Return the start of the reserved data region, or None if not reserved."""
        return self._data_region_base

    def get_data_region_size(self) -> int:
        """Return the size of the reserved data region (0 if not reserved)."""
        return self._data_region_size

    def allocate_data_region(self, size: int, align: int = 8) -> int | None:
        """Allocate from the reserved data region.

        Thin wrapper around allocate(..., purpose="data").
        """
        return self.allocate(min_size=size, align=align, purpose="data")

    def get_data_vma_offset(self) -> int:
        """Offset to subtract from data addresses when emitting .data.

        Returns 0 or DATA_VMA_OFFSET.
        """
        return self._data_vma_offset if self._separate_data_region else 0
