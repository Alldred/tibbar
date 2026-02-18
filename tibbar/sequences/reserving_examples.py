# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Example sequences that use get_resource_requests() and reservation_claim."""

from __future__ import annotations

from tibbar.core.resource import ReservationKind, ResourceId, ResourceSlot
from tibbar.testobj import GenData

from .base import SequenceBase
from .utils import encode_instr


class ExampleGPRSequence(SequenceBase):
    """
    Example sequence that reserves one GPR (concrete ResourceId) and uses it.
    Yields a single addi instruction writing the reserved GPR.
    """

    def __init__(self, tibbar: object, gpr_index: int = 5) -> None:
        super().__init__(tibbar)
        self._gpr_index = gpr_index
        self.name = "ExampleGPRSequence"

    def get_resource_requests(self) -> dict:
        return {
            ReservationKind.EXCLUSIVE: [ResourceId("GPR", self._gpr_index)],
        }

    def gen(self) -> object:
        # Use reserved GPR from claim if set (when run under RoundRobinFunnel with reserver)
        if self.reservation_claim and self.reservation_claim.exclusive:
            rid = next(iter(self.reservation_claim.exclusive))
            reg_idx = rid.identifier if isinstance(rid.identifier, int) else self._gpr_index
        else:
            reg_idx = self._gpr_index
        yield GenData(
            data=encode_instr(self.tibbar, "addi", dest=reg_idx, src1=0, imm=42),
            comment=f"addi x{reg_idx}, x0, 42",
            seq=self.name,
        )


class ExampleSlotSequence(SequenceBase):
    """
    Example sequence that reserves one GPR via ResourceSlot (any GPR).
    Uses reservation_claim to get the allocated register and yields one instruction.
    """

    def __init__(self, tibbar: object) -> None:
        super().__init__(tibbar)
        self.name = "ExampleSlotSequence"

    def get_resource_requests(self) -> dict:
        return {
            ReservationKind.EXCLUSIVE: [ResourceSlot("GPR", count=1)],
        }

    def gen(self) -> object:
        if self.reservation_claim and self.reservation_claim.exclusive:
            rid = next(iter(self.reservation_claim.exclusive))
            reg_idx = rid.identifier if isinstance(rid.identifier, int) else 1
        else:
            reg_idx = 1
        yield GenData(
            data=encode_instr(self.tibbar, "addi", dest=reg_idx, src1=0, imm=1),
            comment=f"addi x{reg_idx}, x0, 1",
            seq=self.name,
        )
