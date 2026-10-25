#!/usr/bin/env python3
"""Week 6 · Task 1 — Link state: build the forwarding table yourself.

Textbook §5.2 (link state and distance vector) and §5.3 (OSPF).

Each router computes shortest-path costs from the shared network map, then
installs one direct next hop for each reachable destination.

    python3 task1_linkstate.py --verify
"""
import argparse
import heapq

# Undirected weighted graph: node -> {neighbour: cost}
TOPOLOGY = {
    "u": {"v": 2, "w": 5, "x": 1},
    "v": {"u": 2, "w": 3, "x": 2},
    "w": {"u": 5, "v": 3, "x": 3, "y": 1, "z": 5},
    "x": {"u": 1, "v": 2, "w": 3, "y": 1},
    "y": {"w": 1, "x": 1, "z": 2},
    "z": {"w": 5, "y": 2},
}


def _shortest_paths(graph, source):
    """Return shortest costs and lexicographically smallest first hops."""
    distances = {source: 0}
    first_hops = {}
    queue = [(0, "", source)]

    while queue:
        cost, first_hop, node = heapq.heappop(queue)
        if cost != distances.get(node):
            continue
        if node != source and first_hop != first_hops.get(node):
            continue

        for neighbour, link_cost in graph[node].items():
            if neighbour == source:
                continue

            candidate_cost = cost + link_cost
            candidate_hop = neighbour if node == source else first_hop
            old_cost = distances.get(neighbour)
            old_hop = first_hops.get(neighbour)

            if (
                old_cost is None
                or candidate_cost < old_cost
                or (
                    candidate_cost == old_cost
                    and (old_hop is None or candidate_hop < old_hop)
                )
            ):
                distances[neighbour] = candidate_cost
                first_hops[neighbour] = candidate_hop
                heapq.heappush(queue, (candidate_cost, candidate_hop, neighbour))

    return distances, first_hops


def dijkstra(graph, source):
    """Return {node: cost}; unreachable nodes are absent."""
    distances, _ = _shortest_paths(graph, source)
    return {node: cost for node, cost in distances.items() if node != source}


def forwarding_table(graph, source):
    """Return {destination: direct first_hop}, omitting source/unreachable nodes.

    Equal-cost routes use the lexicographically smallest neighbour of source.
    """
    _, first_hops = _shortest_paths(graph, source)
    return first_hops


def link_down(graph, a, b):
    """A copy of `graph` with the link a-b removed, in both directions."""
    g = {n: dict(e) for n, e in graph.items()}
    g[a].pop(b, None)
    g[b].pop(a, None)
    return g


# Costs from the textbook's worked example, §5.2.1
EXPECTED_COST_U = {"v": 2, "w": 3, "x": 1, "y": 2, "z": 4}
EXPECTED_TABLE_U = {"v": "v", "w": "x", "x": "x", "y": "x", "z": "x"}


def verify():
    fails = 0
    cost = dijkstra(TOPOLOGY, "u")
    ok = cost == EXPECTED_COST_U
    print(f"  {'ok  ' if ok else 'FAIL'}  costs from u: {cost}")
    if not ok:
        print(f"        expected {EXPECTED_COST_U}")
    fails += not ok

    table = forwarding_table(TOPOLOGY, "u")
    ok = table == EXPECTED_TABLE_U
    print(f"  {'ok  ' if ok else 'FAIL'}  table at u:  {table}")
    if not ok:
        print(f"        expected {EXPECTED_TABLE_U}")
    fails += not ok

    for n in TOPOLOGY:
        t = forwarding_table(TOPOLOGY, n)
        missing = set(TOPOLOGY) - {n} - set(t)
        bad = [d for d, h in t.items() if h not in TOPOLOGY[n]]
        ok = not missing and not bad
        print(
            f"  {'ok  ' if ok else 'FAIL'}  table at {n} covers all, hops are neighbours"
            + (f"  missing={missing} bad={bad}" if not ok else "")
        )
        fails += not ok

    cut = link_down(TOPOLOGY, "u", "x")
    after = forwarding_table(cut, "u")
    ok = after != table
    print(f"  {'ok  ' if ok else 'FAIL'}  u reroutes when u-x goes down: {after}")
    fails += not ok

    print(f"\n  {'all ok' if not fails else str(fails) + ' failed'}")
    return 1 if fails else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        raise SystemExit(verify())
    parser.print_help()
