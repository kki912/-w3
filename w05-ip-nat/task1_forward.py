#!/usr/bin/env python3
"""Week 5 · Task 1 — Subnets and longest-prefix match.

Textbook §4.3.2 (IPv4 addressing, CIDR) and §4.3.3 (forwarding).

Two things a router does with every packet: work out which prefixes the
destination falls inside, and pick the longest one. The second is the whole
of "longest prefix match", and it is the reason the internet's routing table
can hold a million entries and still be answerable.

You build both, from integers up. No `ipaddress` module - that library is
exactly the thing you are supposed to understand this week.

    python3 task1_forward.py --verify
"""
import argparse


def _parse_ipv4(address):
    """Parse a dotted-decimal IPv4 address into a 32-bit integer."""
    parts = address.split(".")
    if len(parts) != 4:
        raise ValueError(f"invalid IPv4 address: {address!r}")

    value = 0
    for part in parts:
        if not part or not part.isascii() or not part.isdecimal():
            raise ValueError(f"invalid IPv4 address: {address!r}")
        octet = int(part)
        if octet > 255:
            raise ValueError(f"invalid IPv4 address: {address!r}")
        value = (value << 8) | octet
    return value


def _format_ipv4(value):
    return ".".join(str((value >> shift) & 0xFF) for shift in (24, 16, 8, 0))


def parse_cidr(cidr):
    """'163.152.6.0/24' -> (network as int, prefix length).

    Requirements: reject a prefix length outside 0-32, and reject an address
    whose host bits are set when they should not be (163.152.6.5/24 is a
    common way to write a host, but it is not a network).
    """
    try:
        address, prefix_text = cidr.split("/")
        if not prefix_text or not prefix_text.isascii() or not prefix_text.isdecimal():
            raise ValueError
        prefix = int(prefix_text)
    except (AttributeError, ValueError):
        raise ValueError(f"invalid CIDR block: {cidr!r}") from None

    if not 0 <= prefix <= 32:
        raise ValueError(f"prefix length must be between 0 and 32: {prefix}")

    address_value = _parse_ipv4(address)
    mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    network = address_value & mask
    if address_value != network:
        raise ValueError(f"CIDR address has host bits set: {cidr!r}")
    return network, prefix


def network_range(cidr):
    """'163.152.6.0/24' -> (first usable, last usable, broadcast) as strings.

    Careful at the edges. /31 and /32 do not have a usable host range in the
    ordinary sense - decide what you return and say so in observation.md.
    """
    network, prefix = parse_cidr(cidr)
    host_mask = (1 << (32 - prefix)) - 1
    broadcast = network | host_mask

    if prefix <= 30:
        first = network + 1
        last = broadcast - 1
    elif prefix == 31:
        # RFC 3021 treats both addresses on a point-to-point /31 as usable.
        first, last = network, broadcast
    else:
        # A /32 is a single host route, not a subnet with a broadcast address.
        first = last = network

    return _format_ipv4(first), _format_ipv4(last), _format_ipv4(broadcast)


class ForwardingTable:
    """Longest-prefix-match forwarding.

    add(cidr, next_hop)  ·  lookup(address) -> next_hop or None

    The default route 0.0.0.0/0 matches everything and is the shortest prefix,
    so it must lose to any other match. If two entries have the same prefix
    length, the table is malformed - say what you do.
    """

    def __init__(self):
        self._routes = {}

    def add(self, cidr, next_hop):
        network, prefix = parse_cidr(cidr)
        key = (network, prefix)
        if key in self._routes:
            raise ValueError(f"duplicate route for {cidr}")
        self._routes[key] = next_hop

    def lookup(self, address):
        destination = _parse_ipv4(address)
        best_prefix = -1
        best_hop = None

        for (network, prefix), next_hop in self._routes.items():
            mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
            if destination & mask == network and prefix > best_prefix:
                best_prefix = prefix
                best_hop = next_hop
        return best_hop


# ------------------------------------------------------------------- harness
RANGE_CASES = [
    ("192.168.0.0/24",  "192.168.0.1",   "192.168.0.254",  "192.168.0.255"),
    ("10.0.0.0/8",      "10.0.0.1",      "10.255.255.254", "10.255.255.255"),
    ("172.16.32.0/20",  "172.16.32.1",   "172.16.47.254",  "172.16.47.255"),
    ("203.0.113.64/26", "203.0.113.65",  "203.0.113.126",  "203.0.113.127"),
]

TABLE = [
    ("0.0.0.0/0",       "default-gw"),
    ("10.0.0.0/8",      "campus"),
    ("10.20.0.0/16",    "eng-building"),
    ("10.20.30.0/24",   "lab-floor"),
    ("10.20.30.64/26",  "lab-rack-2"),
    ("192.168.1.0/24",  "home"),
]

LOOKUP_CASES = [
    ("10.20.30.70",   "lab-rack-2"),     # inside all four 10.x entries
    ("10.20.30.10",   "lab-floor"),
    ("10.20.99.1",    "eng-building"),
    ("10.99.0.1",     "campus"),
    ("8.8.8.8",       "default-gw"),
    ("192.168.1.77",  "home"),
]


def verify():
    fails = 0
    for cidr, first, last, bcast in RANGE_CASES:
        try:
            got = network_range(cidr)
        except NotImplementedError:
            print("  network_range is still a stub"); return 1
        except Exception as e:
            print(f"  FAIL  {cidr:<18} raised {e!r}"); fails += 1; continue
        ok = tuple(got) == (first, last, bcast)
        print(f"  {'ok  ' if ok else 'FAIL'}  {cidr:<18} {got}")
        fails += not ok

    t = ForwardingTable()
    try:
        for cidr, hop in TABLE:
            t.add(cidr, hop)
    except NotImplementedError:
        print("  ForwardingTable is still a stub"); return 1

    for addr, expect in LOOKUP_CASES:
        got = t.lookup(addr)
        ok = got == expect
        print(f"  {'ok  ' if ok else 'FAIL'}  {addr:<16} -> {got}  (want {expect})")
        fails += not ok

    print(f"\n  {len(RANGE_CASES) + len(LOOKUP_CASES) - fails}"
          f"/{len(RANGE_CASES) + len(LOOKUP_CASES)} ok")
    return 1 if fails else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()
    raise SystemExit(verify() if a.verify else p.print_help())
