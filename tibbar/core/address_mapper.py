# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Absolute-address bank mapping shared by Tibbar and Lome."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tibbar.core.memory_store import MemoryStore


@dataclass(frozen=True)
class AddressSegment:
    """One absolute-address bank segment."""

    base: int
    size: int

    @property
    def hi(self) -> int:
        return self.base + self.size

    def contains(self, addr: int, size: int = 1) -> bool:
        return self.base <= addr and addr + size <= self.hi

    def offset_of(self, addr: int) -> int:
        if not self.contains(addr):
            raise ValueError(f"Address 0x{addr:x} outside segment [0x{self.base:x}, 0x{self.hi:x})")
        return addr - self.base


@dataclass(frozen=True)
class AddressMapper:
    """Absolute-address validator/locator for code and data banks."""

    code_segments: tuple[AddressSegment, ...]
    data_segments: tuple[AddressSegment, ...] = ()

    @classmethod
    def from_mem_store(
        cls,
        mem_store: "MemoryStore",
    ) -> "AddressMapper":
        code_regions = mem_store.get_code_regions()
        code_segments = tuple(
            AddressSegment(base=int(lo), size=int(hi) - int(lo)) for lo, hi in code_regions
        )

        data_regions = mem_store.get_data_regions()
        data_segments = tuple(
            AddressSegment(base=int(lo), size=int(hi) - int(lo)) for lo, hi in data_regions
        )
        if not code_segments:
            raise ValueError("MemoryStore has no configured code regions")
        return cls(code_segments=code_segments, data_segments=data_segments)

    @classmethod
    def from_memory_banks(
        cls,
        _mem_store: "MemoryStore",
        banks: list[dict[str, object]],
    ) -> "AddressMapper":
        code_segments: list[AddressSegment] = []
        data_segments: list[AddressSegment] = []
        for bank in banks:
            size = int(bank["size"])
            base = int(bank["base"])
            if bool(bank.get("code")):
                code_segments.append(AddressSegment(base=base, size=size))
            if bool(bank.get("data")) and not bool(bank.get("code")):
                data_segments.append(AddressSegment(base=base, size=size))
        if not code_segments:
            raise ValueError("No code banks provided")
        return cls(code_segments=tuple(code_segments), data_segments=tuple(data_segments))

    @property
    def code_base(self) -> int:
        return self.code_segments[0].base

    @property
    def code_size(self) -> int:
        return sum(seg.size for seg in self.code_segments)

    @property
    def has_data(self) -> bool:
        return len(self.data_segments) > 0

    def find_code_segment(self, addr: int, size: int = 1) -> AddressSegment | None:
        for seg in self.code_segments:
            if seg.contains(addr, size):
                return seg
        return None

    def find_data_segment(self, addr: int, size: int = 1) -> AddressSegment | None:
        for seg in self.data_segments:
            if seg.contains(addr, size):
                return seg
        return None

    def find_code_segment_index(self, addr: int, size: int = 1) -> int | None:
        for idx, seg in enumerate(self.code_segments):
            if seg.contains(addr, size):
                return idx
        return None

    def find_data_segment_index(self, addr: int, size: int = 1) -> int | None:
        for idx, seg in enumerate(self.data_segments):
            if seg.contains(addr, size):
                return idx
        return None

    def is_runtime_code(self, addr: int, size: int = 1) -> bool:
        return self.find_code_segment(addr, size) is not None

    def is_runtime_data(self, addr: int, size: int = 1) -> bool:
        return self.find_data_segment(addr, size) is not None

    def require_code_addr(self, addr: int, size: int = 1) -> int:
        if self.find_code_segment(addr, size) is None:
            raise ValueError(f"Code address out of range: 0x{addr:x} (size={size})")
        return addr

    def require_store_addr(self, addr: int, size: int = 1) -> int:
        if self.find_code_segment(addr, size) is not None:
            return addr
        if self.find_data_segment(addr, size) is not None:
            return addr
        code_ranges = ", ".join(f"[0x{s.base:x}, 0x{s.hi:x})" for s in self.code_segments)
        data_ranges = ", ".join(f"[0x{s.base:x}, 0x{s.hi:x})" for s in self.data_segments)
        raise ValueError(
            f"Address 0x{addr:x} (size={size}) outside mapped banks. "
            f"Code: {code_ranges}; Data: {data_ranges or '(none)'}"
        )

    def format_code_addr(self, addr: int) -> tuple[str, str]:
        """Return ``(display_pc, abs_pc)``; both absolute in this model."""
        return hex(addr), hex(addr)
