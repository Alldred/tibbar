# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Tests for absolute-address bank mapping shared by Tibbar and Lome adapter."""

from __future__ import annotations

import logging
import random

import pytest

from tibbar.core.address_mapper import AddressMapper, AddressSegment
from tibbar.core.memory_store import MemoryStore
from tibbar.core.model import TibbarMemoryAdapter


def _mapper() -> AddressMapper:
    return AddressMapper(
        code_segments=(AddressSegment(base=0x8000_0000, size=0x40_000),),
        data_segments=(AddressSegment(base=0x8004_0000, size=0x40_000),),
    )


def test_require_code_addr_accepts_code_address() -> None:
    mapper = _mapper()
    assert mapper.require_code_addr(0x8000_0120, 4) == 0x8000_0120


def test_require_store_addr_accepts_code_and_data() -> None:
    mapper = _mapper()
    assert mapper.require_store_addr(0x8000_0018, 8) == 0x8000_0018
    assert mapper.require_store_addr(0x8004_0018, 8) == 0x8004_0018


def test_rejects_out_of_range() -> None:
    mapper = _mapper()
    with pytest.raises(ValueError, match="outside mapped banks"):
        mapper.require_store_addr(0x9000_0000, 4)


def test_multi_code_banks_absolute_validation() -> None:
    mapper = AddressMapper(
        code_segments=(
            AddressSegment(base=0x8000_0000, size=0x100),
            AddressSegment(base=0x9000_0000, size=0x100),
        )
    )
    assert mapper.require_code_addr(0x8000_0040, 4) == 0x8000_0040
    assert mapper.require_code_addr(0x9000_0040, 4) == 0x9000_0040
    with pytest.raises(ValueError, match="Code address out of range"):
        mapper.require_code_addr(0x8800_0000, 4)


def test_segment_index_lookup() -> None:
    mapper = AddressMapper(
        code_segments=(
            AddressSegment(base=0x8000_0000, size=0x100),
            AddressSegment(base=0x9000_0000, size=0x100),
        ),
        data_segments=(AddressSegment(base=0xA000_0000, size=0x80),),
    )
    assert mapper.find_code_segment_index(0x8000_0010) == 0
    assert mapper.find_code_segment_index(0x9000_0010) == 1
    assert mapper.find_data_segment_index(0xA000_0010) == 0
    assert mapper.find_data_segment_index(0xA100_0010) is None


def test_tibbar_memory_adapter_uses_absolute_mapper() -> None:
    mem_store = MemoryStore(
        log=logging.getLogger("test-address-map"),
        rng=random.Random(1),
        seed=1,
        max_size=0x200,
        code_regions=[(0x8000_0000, 0x8000_0100)],
        data_regions=[(0x8001_0000, 0x8001_0100)],
    )
    mem_store.reserve_data_region(0x100)
    mapper = AddressMapper.from_mem_store(mem_store)
    adapter = TibbarMemoryAdapter(mem_store, address_mapper=mapper)

    mem_store.write_to_mem_store(0x8000_0020, 0xAB, 0xFF)
    mem_store.write_to_mem_store(0x8001_0010, 0xCD, 0xFF)

    assert adapter.load(0x8000_0020, 1) == 0xAB
    assert adapter.load(0x8001_0010, 1) == 0xCD
