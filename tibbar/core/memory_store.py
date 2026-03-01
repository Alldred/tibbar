# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Absolute-address memory store for instruction/data placement."""

from __future__ import annotations

import bisect
import logging
import random
from typing import TYPE_CHECKING

from tibbar.utils import MASK_64_BIT

if TYPE_CHECKING:
    from tibbar.testobj import GenData


class MemoryStore:
    """Absolute-address memory for instruction/data placement."""

    def __init__(
        self,
        log: logging.Logger,
        rng: random.Random,
        seed: int,
        max_size: int,
        *,
        code_regions: list[tuple[int, int]] | None = None,
        data_regions: list[tuple[int, int]] | None = None,
    ) -> None:
        self.random = rng
        self.seed = seed
        self._max_size = max_size
        self._gen_store: dict[int, GenData] = {}
        self._live_memory: dict[int, int] = {}
        self._used_ranges: list[tuple[int, int]] = []
        self._used_starts: list[int] = []

        self._code_regions = self._normalize_regions(code_regions or [(0, max_size)])
        self._data_regions = self._normalize_regions(data_regions or [])

        self._data_next: list[int] = [lo for lo, _ in self._data_regions]
        self._data_region_base: int | None = (
            self._data_regions[0][0] if self._data_regions else None
        )
        self._data_region_size: int = sum(hi - lo for lo, hi in self._data_regions)
        self._log = log

        self.debug = log.debug
        self.info = log.info
        self.warning = log.warning
        self.error = log.error

    def _normalize_regions(self, regions: list[tuple[int, int]]) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        for lo, hi in regions:
            lo_i = int(lo)
            hi_i = int(hi)
            if hi_i <= lo_i:
                continue
            out.append((lo_i, hi_i))
        out.sort(key=lambda r: r[0])
        return out

    def get_memory_size(self) -> int:
        return self._max_size

    def get_code_regions(self) -> list[tuple[int, int]]:
        return list(self._code_regions)

    def get_data_regions(self) -> list[tuple[int, int]]:
        return list(self._data_regions)

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
        self._used_starts = [s for s, _ in self._used_ranges]

    def _range_overlaps_used(self, addr: int, size: int) -> bool:
        if not self._used_ranges:
            return False
        end = addr + size
        # Find first interval with start >= end; only previous interval can overlap.
        idx = bisect.bisect_left(self._used_starts, end)
        if idx == 0:
            return False
        _s, e = self._used_ranges[idx - 1]
        return e > addr

    def _in_regions(self, regions: list[tuple[int, int]], addr: int, size: int) -> bool:
        end = addr + size
        for lo, hi in regions:
            if lo <= addr and end <= hi:
                return True
        return False

    def _is_valid_range(self, addr: int, size: int) -> bool:
        if addr < 0 or size <= 0:
            return False
        if self._in_regions(self._code_regions, addr, size):
            return True
        if self._in_regions(self._data_regions, addr, size):
            return True
        return False

    def check_region_empty(self, addr: int, byte_size: int) -> bool:
        """True iff [addr, addr+byte_size) does not overlap any existing _gen_store item."""
        if not self._is_valid_range(addr, byte_size):
            return False
        return not self._range_overlaps_used(addr, byte_size)

    def _iter_code_candidates(
        self,
        *,
        min_size: int,
        align: int,
        pc_addr: int | None,
        min_start: int | None,
        within: tuple[int, int] | None,
    ) -> list[int]:
        candidates: list[int] = []
        seen: set[int] = set()

        def _add_candidate(cand: int) -> None:
            if cand not in seen:
                seen.add(cand)
                candidates.append(cand)

        used = self._used_ranges
        for lo_raw, hi_raw in self._code_regions:
            lo = lo_raw
            hi = hi_raw
            if min_start is not None:
                lo = max(lo, int(min_start))
            if within is not None and pc_addr is not None:
                min_off, max_off = within
                lo = max(lo, int(pc_addr) + int(min_off))
                hi = min(hi, int(pc_addr) + int(max_off) + 1)
            if hi - lo < min_size:
                continue
            last = hi - min_size
            if last < lo:
                continue

            # Build free gaps for [lo, last + min_size) from merged used ranges.
            gap_lo = lo
            window_end = last + min_size

            # Start near first potentially overlapping used range.
            idx = bisect.bisect_left(self._used_starts, lo)
            if idx > 0 and used[idx - 1][1] > lo:
                idx -= 1

            while idx < len(used):
                s, e = used[idx]
                if s >= window_end:
                    break
                if e <= gap_lo:
                    idx += 1
                    continue
                gap_hi = min(s, window_end)
                if gap_hi - gap_lo >= min_size:
                    cand_lo = (gap_lo + align - 1) & -align
                    cand_hi = gap_hi - min_size
                    if cand_lo <= cand_hi:
                        _add_candidate(cand_lo)
                        if pc_addr is not None:
                            near = (max(cand_lo, min(cand_hi, pc_addr)) + align - 1) & -align
                            if near > cand_hi:
                                near = ((cand_hi // align) * align) if align > 1 else cand_hi
                            if cand_lo <= near <= cand_hi:
                                _add_candidate(near)
                gap_lo = max(gap_lo, e)
                idx += 1

            if gap_lo < window_end:
                gap_hi = window_end
                if gap_hi - gap_lo >= min_size:
                    cand_lo = (gap_lo + align - 1) & -align
                    cand_hi = gap_hi - min_size
                    if cand_lo <= cand_hi:
                        _add_candidate(cand_lo)
                        if pc_addr is not None:
                            near = (max(cand_lo, min(cand_hi, pc_addr)) + align - 1) & -align
                            if near > cand_hi:
                                near = ((cand_hi // align) * align) if align > 1 else cand_hi
                            if cand_lo <= near <= cand_hi:
                                _add_candidate(near)
        return candidates

    def allocate(
        self,
        min_size: int,
        align: int = 8,
        purpose: str = "code",
        pc: int | object | None = None,
        min_start: int | None = None,
        within: tuple[int, int] | None = None,
    ) -> int | None:
        """Allocate a block in absolute space.

        Returns base address or None. When within= is set, pc is the current PC
        used to compute the valid target range [pc+min_off, pc+max_off].
        """
        if purpose == "data":
            if not self._data_regions:
                self.reserve_data_region(256 * 1024, align=align)
            if not self._data_regions:
                return None
            for idx, (lo, hi) in enumerate(self._data_regions):
                addr = (self._data_next[idx] + align - 1) & -align
                end = addr + min_size
                if end <= hi:
                    self._data_next[idx] = end
                    return addr
            return None

        # purpose == "code"
        pc_addr = self._normalize_pc(pc) if pc is not None else None
        candidates = self._iter_code_candidates(
            min_size=min_size,
            align=align,
            pc_addr=pc_addr,
            min_start=min_start,
            within=within,
        )
        if not candidates and pc_addr is not None:
            candidates = self._iter_code_candidates(
                min_size=min_size,
                align=align,
                pc_addr=None,
                min_start=min_start,
                within=within,
            )
        if not candidates:
            return None
        if pc_addr is None:
            base = self.random.choice(candidates)
        else:
            candidates.sort(key=lambda c: abs(c - pc_addr))
            near = candidates[: min(64, len(candidates))]
            base = self.random.choice(near)
        self._insert_used_range(base, base + min_size)
        return base

    def get_free_space(self, pc: int | object) -> int:
        pc_addr = self._normalize_pc(pc)
        seg: tuple[int, int] | None = None
        for lo, hi in self._code_regions:
            if lo <= pc_addr < hi:
                seg = (lo, hi)
                break
        if seg is None:
            return 0
        _seg_lo, seg_hi = seg

        nearest_next = seg_hi
        for s, item in self._gen_store.items():
            item_size = getattr(item, "byte_size", 4)
            e = s + item_size
            if s <= pc_addr < e:
                return 0
            if pc_addr < s < nearest_next:
                nearest_next = s
        return nearest_next - pc_addr

    def export_and_return(self) -> dict[int, object]:
        """Return placed memory items keyed by absolute address."""
        output: dict[int, object] = {}
        for addr, item in self._gen_store.items():
            output[addr] = item.export_to_tibbar_item()
        return output

    def read_from_mem_store(self, addr: int, size: int = 8) -> int:
        assert size <= 8, f"Not expecting size over 8 bytes: {size=}"
        assert self._is_valid_range(addr, size), f"Address out of range: {addr=}, {size=}"
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
        max_byte = 0
        for i in range(8):
            if (strobe >> (i * 8)) & 0xFF:
                max_byte = i + 1
        required = max(max_byte, 1)
        assert self._is_valid_range(addr, required), f"Address out of range: {addr=}"
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

        if self._log.isEnabledFor(logging.DEBUG):
            free = self.get_free_space(addr)
            self.debug(
                f"Adding to mem_store: 0x{addr:x}: {test_obj} (free until next: {free} bytes)"
            )

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

        # add_to_mem_store writes concrete objects; allow pre-reserved ranges and
        # only reject overlap with already populated objects.
        end = addr + test_obj.byte_size
        for s, item in self._gen_store.items():
            item_size = getattr(item, "byte_size", 4)
            e = s + item_size
            if not (end <= s or addr >= e):
                raise AssertionError(
                    f"0x{addr:x} is already in use "
                    f"(new={getattr(test_obj, 'seq', None)}:{getattr(test_obj, 'comment', None)} "
                    f"existing={getattr(item, 'seq', None)}:{getattr(item, 'comment', None)})"
                )

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
        """Find a free block in code region, mark it used, return base."""
        return self.allocate(
            min_size=size,
            align=align,
            purpose="code",
            pc=pc,
            min_start=min_start,
        )

    def reserve_data_region(self, size: int, align: int = 8) -> None:
        """Reserve data regions.

        Separate mode:
        - If explicit data regions exist, they are used as-is.
        Unified mode:
        - Reserve from the tail of the last code region.
        """
        if self._data_regions:
            self._data_region_base = self._data_regions[0][0]
            self._data_region_size = sum(hi - lo for lo, hi in self._data_regions)
            self._data_next = [lo for lo, _ in self._data_regions]
            if size > self._data_region_size:
                raise AssertionError("Configured data banks smaller than requested reserve")
            return

        if not self._code_regions:
            raise AssertionError("No code regions available for unified data reserve")
        lo, hi = self._code_regions[-1]
        base = (hi - size) & -align
        if base < lo:
            raise AssertionError("No space for data region")
        self._data_regions = [(base, base + size)]
        self._data_region_base = base
        self._data_region_size = size
        self._data_next = [base]
        self._insert_used_range(base, base + size)

    def get_data_region_base(self) -> int | None:
        """Return the first reserved data region base, or None if not reserved."""
        return self._data_region_base

    def get_data_region_size(self) -> int:
        """Return total size of reserved data regions (0 if not reserved)."""
        return self._data_region_size

    def allocate_data_region(self, size: int, align: int = 8) -> int | None:
        """Allocate from reserved data regions."""
        return self.allocate(min_size=size, align=align, purpose="data")
