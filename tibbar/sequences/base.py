# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Base class for sequences; provides reservation stub and claim slot."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tibbar.core.resource import AllocatedClaim, ResourceId, ResourceSlot


class SequenceBase:
    """
    Minimal base for sequences: tibbar, get_resource_requests(), reservation_claim.

    The funnel sets reservation_claim (AllocatedClaim) on the sequence before
    calling gen() so the sequence can use the allocated resources. Override
    get_resource_requests() to declare EXCLUSIVE/SHARED resource needs.
    """

    def __init__(self, tibbar: object) -> None:
        self.tibbar = tibbar
        self.reservation_claim: AllocatedClaim | None = None

    def get_resource_requests(
        self,
    ) -> dict[str, list[ResourceId | ResourceSlot]]:
        """
        Override to declare resource reservations. Default: empty dict.

        Returns a dict keyed by ReservationKind.EXCLUSIVE and/or
        ReservationKind.SHARED, with lists of ResourceId or ResourceSlot.
        """
        return {}
