#!/usr/bin/env python3
"""Week 6 · Task 3 — Reconverge without recomputing the world.

Textbook §5.2.1, §5.3.

A link flaps. Every router in the area has to decide what changed. `FullRecompute`
does the honest thing: throw the table away and run Dijkstra again, from scratch,
for every event. It is correct and it is what the first implementations did.

It is also why a single flapping link in a large area used to melt the CPU of
every router that could see it.

Beat it:

    python3 bench.py
    python3 bench.py --yours

Correctness first. `bench.py` compares your table against a full recompute after
**every single event**. A router that is fast and wrong black-holes traffic.
"""
import heapq

# The harness counts how many times you run a full SPF. This is the score:
# wall-clock time in Python says more about dictionary overhead than about
# routing, but "how many times did the CPU have to recompute the world" is
# exactly what melted real routers.
SPF_RUNS = 0
_LAST_SPF_STATE = None


def dijkstra_table(graph, source):
    """Reference shortest-path-first. Returns {destination: first_hop}.

    Use THIS function whenever you need a full recompute. Rolling your own to
    dodge the counter is not an optimisation, it is cheating the meter.
    """
    global SPF_RUNS
    global _LAST_SPF_STATE
    SPF_RUNS += 1
    best = {source: (0, None)}
    parents = {}
    pq, done = [(0, source, None)], set()
    while pq:
        cost, node, first_hop = heapq.heappop(pq)
        if node in done:
            continue
        done.add(node)
        best[node] = (cost, first_hop)
        for nbr, w in sorted(graph[node].items()):
            if nbr in done:
                continue
            hop = nbr if node == source else first_hop
            if cost + w < best.get(nbr, (float("inf"), None))[0]:
                best[nbr] = (cost + w, hop)
                parents[nbr] = node
                heapq.heappush(pq, (cost + w, nbr, hop))
    table = {d: h for d, (_, h) in best.items() if d != source and h}
    distances = {node: value[0] for node, value in best.items()}
    _LAST_SPF_STATE = (distances, parents)
    return table


class FullRecompute:
    """On every event, forget everything and run SPF again."""

    def __init__(self, graph, source):
        self.graph = {n: dict(e) for n, e in graph.items()}
        self.source = source
        self.table = dijkstra_table(self.graph, source)

    def link_change(self, a, b, cost):
        """cost=None means the link went down."""
        if cost is None:
            self.graph[a].pop(b, None)
            self.graph[b].pop(a, None)
        else:
            self.graph[a][b] = cost
            self.graph[b][a] = cost
        self.table = dijkstra_table(self.graph, self.source)


class YourRouter:
    """Your router. Same two methods, same table, less work per event.

    What is actually true after one link changes:

      * most destinations are not affected at all
      * a link that is not on any of your shortest paths, going *up*, can only
        matter if it creates something shorter
      * a link going *down* only matters if you were using it

    Deciding which of those applies, cheaply, without getting it wrong, is the
    task. Getting it wrong is worse than being slow - the harness will catch it
    on the event where it happens.
    """

    def __init__(self, graph, source):
        self.graph = {node: dict(edges) for node, edges in graph.items()}
        self.source = source
        self.table = {}
        self.distances = {}
        self.parents = {}
        self._recompute()

    def _recompute(self):
        self.table = dijkstra_table(self.graph, self.source)
        distances, parents = _LAST_SPF_STATE
        self.distances = distances
        self.parents = parents

    def _repair_affected_subtree(self, root):
        children = {node: [] for node in self.graph}
        for node, parent in self.parents.items():
            children[parent].append(node)

        affected = set()
        pending = [root]
        while pending:
            node = pending.pop()
            if node in affected:
                continue
            affected.add(node)
            pending.extend(children[node])

        for node in affected:
            self.distances.pop(node, None)
            self.table.pop(node, None)
            self.parents.pop(node, None)

        queue = []
        for node, distance in self.distances.items():
            heapq.heappush(queue, (distance, node, self.table.get(node)))

        settled = set()
        while queue:
            distance, node, first_hop = heapq.heappop(queue)
            if node in settled or distance != self.distances.get(node):
                continue
            if node != self.source and first_hop != self.table.get(node):
                continue
            settled.add(node)

            for neighbour, link_cost in sorted(self.graph[node].items()):
                if neighbour not in affected:
                    continue
                if neighbour in settled:
                    continue
                candidate = distance + link_cost
                if candidate < self.distances.get(neighbour, float("inf")):
                    next_hop = neighbour if node == self.source else first_hop
                    self.distances[neighbour] = candidate
                    self.table[neighbour] = next_hop
                    self.parents[neighbour] = node
                    heapq.heappush(queue, (candidate, neighbour, next_hop))

    def link_change(self, a, b, cost):
        old_cost = self.graph[a].get(b)
        if old_cost == cost:
            return

        a_is_parent = self.parents.get(b) == a
        b_is_parent = self.parents.get(a) == b

        if cost is None:
            self.graph[a].pop(b, None)
            self.graph[b].pop(a, None)
            if a_is_parent:
                self._repair_affected_subtree(b)
            elif b_is_parent:
                self._repair_affected_subtree(a)
            return

        if old_cost is None or cost < old_cost:
            self.graph[a][b] = cost
            self.graph[b][a] = cost
            # An equal-cost alternative can change the selected first hop too.
            if (
                self.distances.get(a, float("inf")) + cost
                <= self.distances.get(b, float("inf"))
                or self.distances.get(b, float("inf")) + cost
                <= self.distances.get(a, float("inf"))
            ):
                self._recompute()
            return

        self.graph[a][b] = cost
        self.graph[b][a] = cost
        if a_is_parent:
            self._repair_affected_subtree(b)
        elif b_is_parent:
            self._repair_affected_subtree(a)
