# Task 2 · Break a Real Network and Time the Repair

**Files** — `scenario.sh`, `topology/`, and your own measurements
**Theory** — §5.2 link state, §5.3 OSPF
**Kind** — **hands-on. This one cannot be done from code alone.**

---

## Why this task exists

Task 1 computes a table. Task 3 makes the computing cheap. Neither tells you how
long a real network is **broken** while it works that out, and that number —
seconds, not milliseconds — is the reason routing protocols are designed the way
they are.

## Part A · Somebody else's routing, from your machine

```bash
traceroute www.korea.ac.kr   | tee out/traceroute.txt      # Windows: tracert
traceroute www.nic.cz        | tee -a out/traceroute.txt
traceroute 1.1.1.1           | tee -a out/traceroute.txt
```

| # | Requirement |
|---|---|
| A1 | Three targets: one domestic, one overseas, one anycast |
| A2 | Where does the domestic path leave your campus? Name the hop |
| A3 | Where does the overseas path cross the ocean? You can see it in the latencies |
| A4 | `1.1.1.1` is anycast. How many hops did it take, and what does that tell you about where the replica is? |
| A5 | Some hops show `* * *`. Give the two different reasons that happens — they are not the same problem |

A3 is readable: one hop adds ~100 ms and the rest add 1–2 ms. That single jump is
a submarine cable, and you can find which one by the city names in the hostnames.

## Part B · Your own OSPF area

Three FRR routers in containers, in a triangle.
The supplied Compose file pins each virtual link to the interface name used in
the FRR configs; this requires Docker Compose 2.36 or newer.

```bash
bash scenario.sh up          # bring the topology up; save stable initial tables and OSPF timers
bash scenario.sh routes      # display and save all three routers' tables
```

| # | Requirement |
|---|---|
| B1 | `out/route-before.txt` — all three tables once OSPF has converged |
| B2 | Confirm each router learned routes it has **no direct link to**. That is the protocol working |
| B3 | Cut a link and capture the tables again → `out/route-after.txt` |
| B4 | **Time the reconvergence** → `out/reconverge.txt`. From the cut to the moment the table is right again |
| B5 | Restore the link and time it again. The two numbers are different — say why |

```bash
bash scenario.sh cut         # save all-router tables before/after and time stable reconvergence
bash scenario.sh restore     # restore the link; save tables and time stable restoration
bash scenario.sh cost        # save tables and time an OSPF cost change (link stays up)
```

The script polls all three OSPF tables every 250 ms by default and requires
three consecutive identical route snapshots before stopping the timer. The
measured duration includes Docker CLI and polling overhead. Adjust
`POLL_SECONDS`, `STABLE_POLLS`, or `TIMEOUT_SECONDS` only if you record the
changed measurement method in your observation.

In WSL, Docker Desktop's WSL integration must be enabled for the `docker`
command to work. If it is not available but the Windows Docker CLI is
accessible from WSL, set `DOCKER_BIN` to that CLI's WSL path before running the
script.

B4 is the measurement that matters. It will be **seconds**. Compare it with the
Hello and Dead intervals captured from the running router in
`out/ospf-timers.txt`; FRR's default timers need not be written explicitly in
`topology/r1/frr.conf`.

B5 is the interesting half. Coming back is not symmetric with going away, and the
reason is in how a router learns that a neighbour is gone versus that one arrived.

## Part C · Move the traffic without breaking anything

```bash
bash scenario.sh cost
```

| # | Requirement |
|---|---|
| C1 | Change a link's cost so a path moves, without any link going down |
| C2 | Save all three tables before and after |
| C3 | How long did **this** take compared with B4? Explain the difference |

C3 is the point of the whole week: a cost change propagates as fast as the LSA
floods, while a failure has to be *noticed* first. That is the gap Task 3 lives in.

## Pass condition

The output includes the three traceroutes; all-router route tables before,
after, and restored; the failure, restoration, and cost-change timings; the
OSPF hello/dead timers; and `out/observation.md` answering A2–A5, B2, B4, B5,
and C3.

```bash
python3 test_tasks.py --task 2
```

## Path (B) · if Docker will not run

Part A needs only `traceroute` and works everywhere — do it in full.

For Parts B and C, if Docker Desktop will not install:

- use a classmate's `route-before.txt` / `route-after.txt`, **naming whose they are**
- you still must answer B4, B5 and C3 from their numbers
- and say explicitly what you did not observe yourself, and what that weakens

This is a real weakening. The timing is the finding, and reading somebody else's
timing is not the same as watching your own network sit broken.

## What to write in `observation.md`

- The ocean crossing hop from A3, and the cable it suggests
- Your reconvergence time, and whether it matches the hello/dead intervals in the config
- Why coming back up is not the same as going down
- C3: why a cost change is faster than a failure
