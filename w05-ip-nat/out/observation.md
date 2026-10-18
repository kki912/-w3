# Week 5 Observations

## Task 1 · Subnets and longest-prefix match

For `/31`, both point-to-point addresses are usable (RFC 3021); for `/32`, the single host is returned for both endpoints and repeated as a documented broadcast placeholder.
`10.20.30.70` matches `10.0.0.0/8`, `10.20.0.0/16`, `10.20.30.0/24`, and `10.20.30.64/26`; longest-prefix match selects `/26` (`lab-rack-2`).
An identical network/prefix added twice is rejected with `ValueError`; different networks may share a prefix length, as the supplied table itself has two `/24` routes.

## Task 2 · Address and DHCP study

Wired Ethernet used `211.46.209.31/24` and ipify saw the same address; Wi-Fi used private `192.168.0.254/24` while ipify saw `211.46.209.5`, proving at least one Wi-Fi NAT.
The public and interface addresses changed between networks; the exact NAT count beyond the Wi-Fi router is unknown without its WAN address (public WAN suggests one NAT, RFC 1918/`100.64.0.0/10` suggests upstream NAT/CGNAT).
The capture has DORA plus Release: Discover `0.0.0.0` → `255.255.255.255` because the client has no address and does not know the server; offered lease is 3,600 s, T1 renewal is normally at 1,800 s, and this ACK was broadcast.

## Task 3 · Fast longest-prefix match

`YourTable` groups routes into 33 prefix-length hash maps, using O(R + 33) memory; lookup checks at most 33 populated lengths with expected O(1) dictionary lookups.
The fixed-width bound is at most 33 checks (IPv4 has 32 bits), independent of route count; hardware favors a bit trie for its direct 32-bit walk, while Python hashes avoid per-bit interpreter work.
The recorded 20,000-query benchmark had 0 wrong answers and 1,051.5x speedup; timings vary by machine.
