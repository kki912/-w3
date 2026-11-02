#!/usr/bin/env python3
"""Week 7 · Task 3 — A capacity-limited learning switch."""
from collections import OrderedDict
import zlib


class NaiveSwitch:
    """Baseline implementation: evict the oldest learned station."""

    BROADCAST = "ff:ff:ff:ff:ff:ff"

    def __init__(self, ports, capacity):
        self.ports = ports
        self.capacity = capacity
        self.table = OrderedDict()

    def handle(self, frame, in_port):
        src, dst, _ = frame
        if src not in self.table and len(self.table) >= self.capacity:
            self.table.popitem(last=False)
        self.table[src] = in_port
        if dst == self.BROADCAST or dst not in self.table:
            return [port for port in range(self.ports) if port != in_port]
        out_port = self.table[dst]
        return [] if out_port == in_port else [out_port]


class YourSwitch:
    """Bounded frequency-aware admission and eviction using a Count-Min Sketch."""

    BROADCAST = "ff:ff:ff:ff:ff:ff"
    _WIDTH = 4096
    _SEEDS = (0x13579BDF, 0x2468ACE0, 0x10203040, 0x55667788)

    def __init__(self, ports, capacity):
        if not isinstance(ports, int) or ports <= 0:
            raise ValueError("ports must be a positive integer")
        if not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        self.ports = ports
        self.capacity = capacity
        self.table = OrderedDict()
        self._frequency = [[0] * self._WIDTH for _ in self._SEEDS]

    def _record_source(self, mac):
        encoded = mac.encode("utf-8")
        estimates = []
        for row, seed in zip(self._frequency, self._SEEDS):
            index = zlib.crc32(encoded, seed) % self._WIDTH
            row[index] = min(row[index] + 1, 65535)
            estimates.append(row[index])
        return min(estimates)

    def _estimate(self, mac):
        encoded = mac.encode("utf-8")
        return min(
            row[zlib.crc32(encoded, seed) % self._WIDTH]
            for row, seed in zip(self._frequency, self._SEEDS)
        )

    def handle(self, frame, in_port):
        src, dst, _ = frame
        source_frequency = self._record_source(src)

        if src in self.table:
            self.table[src] = in_port
            self.table.move_to_end(src)
        elif len(self.table) < self.capacity:
            self.table[src] = in_port
        else:
            victim = min(
                self.table,
                key=self._estimate,
            )
            if source_frequency > self._estimate(victim):
                del self.table[victim]
                self.table[src] = in_port

        if dst == self.BROADCAST or dst not in self.table:
            return [port for port in range(self.ports) if port != in_port]
        out_port = self.table[dst]
        return [] if out_port == in_port else [out_port]
