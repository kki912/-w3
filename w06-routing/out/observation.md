# Task 1

- Equal-cost routes use the lexicographically smallest first-hop neighbour; real routers may use ECMP or implementation-specific selection.
- At `u`, traffic for `w` uses `x` because `u-x-y-w` costs 3, less than direct `u-w` at 5.
- After `u-x` fails, `w`, `x`, `y`, and `z` switch from hop `x` to `v`; `v` is unchanged.

# Task 2

- **A2-A5:** Domestic hop 1 is `175.203.124.1`; hop 2 `61.78.45.78` is the first responsive upstream hop, but the exact campus boundary is unconfirmed. For `www.nic.cz`, latency jumps from 5-6 ms at hop 5 to 131 ms at hop 6 before Palo Alto/San Jose and European hops, indicating a trans-Pacific crossing; traceroute cannot identify the exact cable. `1.1.1.1` replies in 8 hops (6-7 ms), consistent with a nearby anycast replica. `*` can mean filtered/rate-limited ICMP replies or probe loss.
- **B2-B5:** All three routers learned a non-direct transit network: r1 `172.19.0.0/16`, r2 `172.21.0.0/16`, r3 `172.20.0.0/16`. With 250 ms polling and three stable all-router snapshots, link failure took 4.38 s and restoration 4.34 s; Hello/Dead timers are 10/40 s. The interface-down event is detected locally, while restoration needs Hello exchange and adjacency/database synchronization; polling and Docker overhead make the small timing difference inconclusive.
- **C1-C3:** Raising r1 eth0 cost from 10 to 100 kept the link up and moved r1's route to `172.19.0.0/16` from equal-cost eth0/eth1 to eth1 only; measured all-router convergence was 7.30 s versus 4.38 s for failure. An LSA cost update does not wait for dead-neighbour detection, but Docker/polling overhead dominates these measurements.

# Task 3

- The router retains shortest distances and predecessors (O(V) additional memory); affected-subtree repair builds temporary queue/state.
- It repairs only affected shortest-path-tree subtrees on failures/cost increases and skips irrelevant changes; a possible improvement or tie after a link-up/cost decrease triggers full SPF via `dijkstra_table()`.
- Across 1,000 events, all tables were correct and SPF runs fell from 1,001 to 152 (85% avoided). The measured incremental run was slower (1.22 s vs 0.93 s) due to Python bookkeeping, but reducing CPU work during reconvergence can matter more on a router than this small benchmark's wall time.
