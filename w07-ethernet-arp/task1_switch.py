#!/usr/bin/env python3
"""Week 7 · Task 1 — Build a learning switch."""
import argparse


class Switch:
    """A self-learning switch with ports numbered from zero."""

    BROADCAST = "ff:ff:ff:ff:ff:ff"
    AGE_SECONDS = 300

    def __init__(self, ports):
        if not isinstance(ports, int) or ports <= 0:
            raise ValueError("ports must be a positive integer")
        self.ports = ports
        self._entries = {}
        self._now = None

    def _expire(self, now):
        expired = [
            mac for mac, (_, last_seen) in self._entries.items()
            if now - last_seen >= self.AGE_SECONDS
        ]
        for mac in expired:
            del self._entries[mac]

    def handle(self, frame, in_port):
        if not isinstance(in_port, int) or not 0 <= in_port < self.ports:
            raise ValueError(f"invalid input port: {in_port!r}")
        try:
            src, dst, now = frame
        except (TypeError, ValueError):
            raise ValueError("frame must be (src_mac, dst_mac, time)") from None
        if not isinstance(src, str) or not src or not isinstance(dst, str) or not dst:
            raise ValueError("frame MAC addresses must be non-empty strings")
        if self._now is not None and now < self._now:
            raise ValueError("frame timestamps must not move backwards")

        self._now = now
        self._expire(now)
        self._entries[src] = (in_port, now)

        if dst.lower() == self.BROADCAST:
            return [port for port in range(self.ports) if port != in_port]

        destination = self._entries.get(dst)
        if destination is None:
            return [port for port in range(self.ports) if port != in_port]
        out_port = destination[0]
        return [] if out_port == in_port else [out_port]

    def table(self):
        if self._now is not None:
            self._expire(self._now)
        return {mac: port for mac, (port, _) in self._entries.items()}


A, B, C = "00:00:00:00:00:0a", "00:00:00:00:00:0b", "00:00:00:00:00:0c"
BC = Switch.BROADCAST


def verify():
    fails = 0

    def check(label, got, want):
        nonlocal fails
        ok = got == want
        print(f"  {'ok  ' if ok else 'FAIL'}  {label:<46} {got}"
              + ("" if ok else f"   want {want}"))
        fails += not ok

    switch = Switch(4)
    check("unknown destination floods",
          switch.handle((A, B, 0.0), 0), [1, 2, 3])
    check("known destination is not flooded",
          switch.handle((B, A, 1.0), 2), [0])
    check("learned both", switch.table(), {A: 0, B: 2})
    check("broadcast floods",
          switch.handle((A, BC, 2.0), 0), [1, 2, 3])
    check("never back out the arrival port",
          switch.handle((C, A, 3.0), 0), [])
    check("station moved, table follows",
          (switch.handle((B, A, 4.0), 3), switch.table()[B]), ([0], 3))
    switch.handle((C, BC, 400.0), 1)
    check("aged-out entry is gone", A in switch.table(), False)

    print(f"\n  {'all ok' if not fails else str(fails) + ' failed'}")
    return 1 if fails else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    raise SystemExit(verify() if args.verify else parser.print_help())
