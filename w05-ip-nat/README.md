# Week 5 Lab · Addresses, Subnets, NAT, DHCP

This folder contains the Week 5 implementations and submission outputs.

## Run

```text
python task1_forward.py --verify
python task2_myaddr.py --collect "network label"
python task2_myaddr.py --report
python bench.py --yours
python test_tasks.py
```

## Submission files

- `task1_forward.py` — integer-based CIDR parsing, subnet range calculation,
  and longest-prefix forwarding.
- `out/addresses.json` — two measured network records (wired Ethernet and
  Wi-Fi).
- `out/dhcp.pcapng` — live Wi-Fi DHCP capture containing Discover, Offer,
  Request, and Ack.
- `out/report.md` — measured address and DHCP analysis.
- `task3_lpm.py` and `out/bench.txt` — optimized lookup table and benchmark
  results.
- `out/observation.md` — observations for all three tasks.

`bench.py` and `test_tasks.py` are included as the supplied Week 5 harness and
checker; they are not submission outputs.
