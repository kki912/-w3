#!/usr/bin/env python3
"""Week 6 · does your work pass?"""
import argparse, importlib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
sys.path.insert(0, HERE)
PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
results = []


def record(task, name, status, detail=""):
    results.append((task, name, status, detail))
    print({PASS: "  ok  ", FAIL: " FAIL ", SKIP: " skip "}[status]
          + f" [{task}] {name}" + (f"  - {detail}" if detail else ""))


def test_task1():
    try:
        m = importlib.import_module("task1_linkstate")
    except Exception as e:
        return record(1, "task1_linkstate.py imports", FAIL, repr(e))
    src = open(os.path.join(HERE, "task1_linkstate.py"), encoding="utf-8").read()
    record(1, "R6 no networkx", FAIL if "import networkx" in src else PASS)
    try:
        rc = m.verify()
    except Exception as e:
        return record(1, "verify runs", FAIL, repr(e))
    record(1, "all checks", PASS if rc == 0 else FAIL)


def test_task2():
    needed = {
        "traceroute.txt": "A1 three traceroutes",
        "route-before.txt": "B1 tables before the cut",
        "route-after.txt": "B3 tables after the cut",
        "reconverge.txt": "B4 measured reconvergence time",
        "route-restored.txt": "B5 restored routing tables",
        "link-restore.txt": "B5 measured restoration time",
        "route-cost-before.txt": "C2 tables before cost change",
        "route-cost-after.txt": "C2 tables after cost change",
        "ospf-timers.txt": "Hello/dead timer evidence",
        "cost-change.txt": "C3 measured cost-change time",
        "observation.md": "A2-A5, B2, B4-B5, and C3 analysis",
    }
    for fname, label in needed.items():
        path = os.path.join(OUT, fname)
        if not os.path.exists(path):
            record(2, label, FAIL, f"out/{fname} missing")
            continue
        size = os.path.getsize(path)
        record(2, label, PASS if size > 0 else FAIL, f"{size:,} bytes")

    tr = os.path.join(OUT, "traceroute.txt")
    if os.path.exists(tr):
        text = open(tr, encoding="utf-8", errors="replace").read()
        hops = sum(1 for l in text.splitlines() if l.strip()[:2].strip().isdigit())
        record(2, "traceroute output has hops", PASS if hops >= 3 else FAIL,
               f"{hops} hop lines")

    for fname in ("route-before.txt", "route-after.txt", "route-restored.txt",
                  "route-cost-before.txt", "route-cost-after.txt"):
        path = os.path.join(OUT, fname)
        if os.path.exists(path):
            text = open(path, encoding="utf-8", errors="replace").read()
            routers = sum(1 for r in ("===== r1 =====", "===== r2 =====",
                                      "===== r3 =====") if r in text)
            record(2, f"{fname} includes all routers",
                   PASS if routers == 3 else FAIL, f"{routers}/3 router tables")

    restored_path = os.path.join(OUT, "route-restored.txt")
    if os.path.exists(restored_path):
        text = open(restored_path, encoding="utf-8", errors="replace").read()
        restored = "172.20.0.0/16 [110/10] is directly connected, eth1" in text
        record(2, "B5 r1-r2 direct route restored",
               PASS if restored else FAIL,
               "r1 eth1 is back in the OSPF table" if restored else "r1 eth1 route missing")

    before_path = os.path.join(OUT, "route-before.txt")
    if os.path.exists(before_path):
        text = open(before_path, encoding="utf-8", errors="replace").read()
        remote_routes = {
            "r1": "172.19.0.0/16",
            "r2": "172.21.0.0/16",
            "r3": "172.20.0.0/16",
        }
        missing = []
        for router, network in remote_routes.items():
            marker = f"===== {router} ====="
            section = text.split(marker, 1)[-1].split("=====", 1)[0]
            if network not in section:
                missing.append(f"{router}:{network}")
        record(2, "B2 routers learned non-direct OSPF networks",
               PASS if not missing else FAIL,
               "all three routers" if not missing else "missing " + ", ".join(missing))

    cost_before = os.path.join(OUT, "route-cost-before.txt")
    cost_after = os.path.join(OUT, "route-cost-after.txt")
    if os.path.exists(cost_before) and os.path.exists(cost_after):
        before_text = open(cost_before, encoding="utf-8", errors="replace").read()
        after_text = open(cost_after, encoding="utf-8", errors="replace").read()
        before_r1 = before_text.split("===== r1 =====", 1)[-1].split("===== r2 =====", 1)[0]
        after_r1 = after_text.split("===== r1 =====", 1)[-1].split("===== r2 =====", 1)[0]
        record(2, "C1 cost change rerouted traffic",
               PASS if before_r1 != after_r1 else FAIL,
               "r1 route table differs before/after" if before_r1 != after_r1
               else "r1 route table did not change")

    timers = os.path.join(OUT, "ospf-timers.txt")
    if os.path.exists(timers):
        text = open(timers, encoding="utf-8", errors="replace").read()
        ok = "Hello 10s" in text and "Dead 40s" in text
        record(2, "OSPF hello/dead intervals recorded",
               PASS if ok else FAIL, "expected Hello 10s / Dead 40s")

    observations = os.path.join(OUT, "observation.md")
    if os.path.exists(observations):
        text = open(observations, encoding="utf-8", errors="replace").read().lower()
        topics = {
            "A2 campus/upstream hop": "a2",
            "A3 overseas route": "a3",
            "A4 anycast": "a4",
            "A5 traceroute timeouts": "a5",
            "B2 remote OSPF routes": "b2",
            "B4 failure timing": "b4",
            "B5 restoration timing": "b5",
            "C3 cost-change comparison": "c3",
        }
        missing = [label for label, token in topics.items() if token not in text]
        record(2, "observation covers required discussion",
               PASS if not missing else FAIL,
               "all required topics" if not missing else "missing " + ", ".join(missing))


def test_task3():
    try:
        bench = importlib.import_module("bench")
        T = importlib.import_module("task3_reconverge")
    except Exception as e:
        return record(3, "modules import", FAIL, repr(e))
    graph, events = bench.build()
    base = bench.run(T.FullRecompute, "baseline", graph, events)
    try:
        mine = bench.run(T.YourRouter, "yours", graph, events, check=True)
    except NotImplementedError:
        return record(3, "YourRouter implemented", FAIL, "still a stub")
    except Exception as e:
        return record(3, "YourRouter runs", FAIL, repr(e))
    record(3, "R3 table correct after every event",
           PASS if mine["wrong"] == 0 else FAIL, f"{mine['wrong']} wrong")
    saved = 1 - mine["spf"] / base["spf"]
    record(3, "R4 fewer SPF runs", PASS if saved > 0.05 else FAIL,
           f"{saved:.0%} avoided")
    record(3, "R5 wall-time argument in observation.md", SKIP, "graded by a human")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--task", type=int, choices=[1, 2, 3])
    a = p.parse_args()
    os.makedirs(OUT, exist_ok=True)
    for n, fn in [(1, test_task1), (2, test_task2), (3, test_task3)]:
        if a.task in (None, n):
            print(f"\n=== Task {n}")
            fn()
    print()
    failed = sum(1 for *_, s, _ in results if s == FAIL)
    skipped = sum(1 for *_, s, _ in results if s == SKIP)
    print(f"  {len(results) - failed - skipped} passed, {failed} failed, {skipped} skipped")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
