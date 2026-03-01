# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Model wrapper: Lome model + MemoryInterface binding to MemoryStore."""

from __future__ import annotations

from typing import TYPE_CHECKING

from eumos import Eumos
from lome import Lome
from lome.memory import MemoryInterface

from tibbar.core.address_mapper import AddressMapper
from tibbar.utils import MASK_64_BIT

if TYPE_CHECKING:
    from tibbar.core.memory_store import MemoryStore


class TibbarMemoryAdapter(MemoryInterface):
    """Adapts MemoryStore to Lome's MemoryInterface."""

    def __init__(
        self,
        mem_store: "MemoryStore",
        *,
        address_mapper: AddressMapper | None = None,
    ) -> None:
        self._mem = mem_store
        self._addr = (
            address_mapper
            if address_mapper is not None
            else AddressMapper.from_mem_store(mem_store)
        )

    def _to_mem_addr(self, addr: int, size: int) -> int:
        return self._addr.require_store_addr(addr, size)

    def load(self, addr: int, size: int) -> int:
        return self._mem.read_from_mem_store(self._to_mem_addr(addr, size), size)

    def store(self, addr: int, value: int, size: int) -> None:
        strobe = {1: 0xFF, 2: 0xFFFF, 4: 0xFFFF_FFFF, 8: MASK_64_BIT}[size]
        self._mem.write_to_mem_store(self._to_mem_addr(addr, size), value, strobe)


def create_model(
    mem_store: "MemoryStore",
    eumos: Eumos | None = None,
    *,
    address_mapper: AddressMapper | None = None,
) -> Lome:
    """Create Lome (RISCV model) with memory bound to the given MemoryStore."""
    if eumos is None:
        eumos = Eumos()
    memory = TibbarMemoryAdapter(
        mem_store,
        address_mapper=address_mapper,
    )
    return Lome(eumos, memory=memory)
