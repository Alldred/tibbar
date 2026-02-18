# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Stuart Alldred.

"""Funnels for combining sequences."""


class FunnelBase:
    def __init__(self, tibbar: object) -> None:
        self._seqs: list = []
        self.tibbar = tibbar

    def add_sequence(self, seq: object) -> None:
        self._seqs.append(seq)

    def gen(self):
        raise NotImplementedError


class SimpleFunnel(FunnelBase):
    def gen(self):
        for seq in self._seqs:
            yield from seq.gen()


class RoundRobinFunnel(FunnelBase):
    def gen(self):
        active_seqs = list(self._seqs)
        idx = 0
        while active_seqs:
            seq = active_seqs[idx]
            try:
                yield from seq.gen()
            except StopIteration:
                active_seqs.pop(idx)
                if not active_seqs:
                    break
                idx = idx % len(active_seqs)
            else:
                idx = (idx + 1) % len(active_seqs)
