# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Funnels for combining sequences."""

from __future__ import annotations

import itertools
from types import GeneratorType
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from tibbar.core.resource import Reserver

from tibbar.core.resource import ReservationError


class FunnelBase:
    def __init__(self, tibbar: object) -> None:
        self._seqs: list = []
        self.tibbar = tibbar

    def add_sequence(self, seq: object) -> FunnelBase:
        self._seqs.append(seq)
        return self

    def add_funnel(self, funnel: FunnelBase) -> FunnelBase:
        self._seqs.append(funnel)
        return self

    def gen(self) -> Iterator[Any]:
        raise NotImplementedError


def _is_funnel(producer: object) -> bool:
    """True if producer is a funnel (has _seqs), else treat as sequence."""
    return hasattr(producer, "_seqs") and hasattr(producer, "gen")


class SimpleFunnel(FunnelBase):
    def gen(self) -> Iterator[Any]:
        for producer in self._seqs:
            yield from producer.gen()


class RoundRobinFunnel(FunnelBase):
    """
    Round-robin: yield one item from each producer per round.
    Supports optional reserver: sequences reserve on start, release on exhaustion.
    Producers may be sequences or nested funnels; only sequences get reserve/release.
    """

    def __init__(self, tibbar: object, reserver: "Reserver | None" = None) -> None:
        super().__init__(tibbar)
        self._reserver = reserver
        self._sequence_id_counter = itertools.count()

    def gen(self) -> Iterator[Any]:
        # (producer, iterator, sequence_id or None)
        active: list[tuple[Any, GeneratorType | None, int | None]] = [
            (p, None, None) for p in self._seqs
        ]
        idx = 0
        while active:
            progressed = False
            rounds = len(active)
            for _ in range(rounds):
                if not active:
                    break
                pos = idx % len(active)
                producer, it, sequence_id = active[pos]
                if it is None:
                    # Start this producer
                    if _is_funnel(producer):
                        it = producer.gen()
                        active[pos] = (producer, it, None)
                    else:
                        # Sequence: reserve then gen
                        requests = getattr(producer, "get_resource_requests", lambda: {})()
                        if self._reserver and requests:
                            sid = next(self._sequence_id_counter)
                            try:
                                claim = self._reserver.request(sid, requests)
                            except ReservationError as e:
                                msg = (
                                    f"Invalid resource request from "
                                    f"{producer.__class__.__name__}: {e}"
                                )
                                raise RuntimeError(msg) from e
                            if claim is None:
                                idx += 1
                                continue
                            producer.reservation_claim = claim

                            def _gen_with_release(
                                _producer: Any, _reserver: Any, _sid: int
                            ) -> Iterator[Any]:
                                try:
                                    yield from _producer.gen()
                                finally:
                                    _reserver.release(_sid)

                            it = _gen_with_release(producer, self._reserver, sid)
                        else:
                            producer.reservation_claim = None
                            it = producer.gen()
                        active[pos] = (producer, it, None)

                try:
                    item = next(it)
                    yield item
                    progressed = True
                    idx += 1
                except StopIteration:
                    active.pop(pos)
                    progressed = True
                    if active:
                        idx %= len(active)
                    else:
                        idx = 0

            if not progressed:
                raise RuntimeError(
                    "RoundRobinFunnel cannot make progress: all producers are blocked on"
                    " reservations."
                )
