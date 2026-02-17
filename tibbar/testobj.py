# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""GenData and TestData for instruction stream generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class GenData:
    """Generated instruction or data to place in memory."""

    def __init__(
        self,
        data: Optional[int] = None,
        byte_size: int = 4,
        addr: Optional[int] = None,
        ldst_data: Optional[int] = None,
        ldst_addr: Optional[int] = None,
        ldst_size: int = 8,
        seq: Optional[str] = None,
        with_next: bool = False,
        comment: Optional[str] = None,
        safe_to_jump_to: bool = True,
        is_data: bool = False,
    ) -> None:
        self.data = data
        self.byte_size = byte_size
        self.addr = addr
        self.ldst_data = ldst_data
        self.ldst_addr = ldst_addr
        self.ldst_size = ldst_size
        assert seq is not None, "seq needs to be specified"
        self.seq = seq
        self.comment = comment
        self.with_next = with_next
        self.safe_to_jump_to = safe_to_jump_to
        self.is_data = is_data

    def __str__(self) -> str:
        return f"GenData({self.seq}): {self.comment} || {self.data:#_x}"

    def export_to_tibbar_item(self) -> "TestData":
        return TestData(
            data=self.data or 0,
            byte_size=self.byte_size,
            ldst_data=self.ldst_data or 0,
            ldst_addr=self.ldst_addr or 0,
            seq=self.seq or "",
            comment=self.comment or "",
            is_data=self.is_data,
        )


@dataclass
class TestData:
    """Exported test item for output (debug YAML etc.)."""

    data: int
    byte_size: int
    ldst_data: int
    ldst_addr: int
    seq: str
    comment: str
    is_data: bool = False
