# Week 7 observations

## Task 1 — Learning switch
- A switch must not reflect a frame onto its ingress port: that can create a link-layer loop and duplicate traffic. A router forwards by its IP routing table, or drops a packet when it has no matching route; it does not flood unknown destinations across interfaces.
- Aging by timeout forgets silent or disconnected stations without knowing they left; a more direct signal would be a link-down or explicit station-disconnect event.
- A timeout may forget a still-connected but idle station, so its next frame is flooded; this is the trade-off for aging stale locations without an explicit departure signal.

## Task 2 — ARP
- After flushing the Windows cache, the gateway entry `211.216.237.1` returned first when I pinged it; the host needed the gateway's MAC to send the ping on the local link. The table went from 9 entries (2 dynamic) before the clear to 6 (1 dynamic) after pinging the gateway and visiting the site; static multicast/broadcast entries remain, and the distant web server is absent because ARP resolves the local next hop, not remote hosts.
- In the official 9th-edition trace, the request asking for `128.119.247.1` is sent to `ff:ff:ff:ff:ff:ff`, the link-layer broadcast; its matching reply is sent to `c4:41:1e:75:b1:52`, the requesting host. Source: J.F. Kurose and K.W. Ross, *Computer Networking: A Top-Down Approach*, 9th ed., <https://gaia.cs.umass.edu/kurose_ross/>; Copyright 1996-2025.
- The trace has 178 broadcast requests and 1 unicast reply in 12.287 seconds: extrapolated, about 869 broadcast frames/minute reach a segment with M machines, or roughly 869(M-1) other-host receptions/minute (plus about 5 unicast replies/minute); this is a rate extrapolation, not a one-minute capture.

## Task 3 — Bounded switch table
- I estimate source frequency with a fixed four-row Count-Min Sketch, evict the least-frequent resident (LRU tie-break), and decline a new source unless its estimate exceeds the eviction candidate.
- On the supplied benchmark, wasted deliveries fell from 323,380 to 159,252 (51%); delivered frames remained 46,347 and missed frames remained 0, so admission control protected frequent stations.
- An attacker could flood the table with frames using many spoofed source MACs so legitimate destinations become unknown and get flooded; port security, per-port MAC limits, and rate limits reduce that risk.
