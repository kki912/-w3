# Task 1 — Reliable Delivery

- I chose stop-and-wait: a lost ACK can cause the same data packet to arrive again, so sequence numbers let the receiver ACK duplicates without appending them twice.
- For 2,000 bytes (250 packets minimum), seed 246 required 323 data-channel send attempts (1.29×); 40 were lost and 8 duplicated.
- The sender retransmits unacknowledged data; the receiver appends only the next expected sequence number, delivering the bytes in order and byte-identically.

## Task 2 — Measure Your Own Link

- In `out/tcp.pcapng` (this machine's Ethernet capture of the 5 MB HTTPS transfer), handshake packets are SYN #1, SYN-ACK #2, ACK #3; client/server initial sequence numbers are **2,279,456,005 / 596,840,717** (independent, nonzero values).
- SYN options: client MSS 1460, scale 8, SACK; server MSS 1400, scale 13, SACK; the client's initial advertised window is **255 × 2^8 = 65,280 bytes** (later 1,048,320), while max server-to-client in-flight was **55,480 bytes** (packet #887), so the receive window did not limit this transfer.
- Five-run medians/ranges/spreads/handshake medians: `current network` **92.05 Mbps**, 40.95–113.36, 78.7%, 18.5 ms; `second network` **259.50 Mbps**, 235.19–288.62, 20.6%, 7.4 ms. Variation can reflect RTT/setup, queueing, and capacity; the faster, lower-handshake second sample is consistent with TCP slow start, where higher RTT delays ACK-clocked congestion-window growth, but the two samples do not isolate RTT as the only cause.

## Task 3 — Beat the Fixed Window

- The baseline has the highest goodput (986.8/1000), but is worst for a shared link: 37.4% loss, 2,340 retransmissions, and average queue 8.8 impose wasted traffic and persistent delay on other flows.
- `YourControl` grows from slow start to an additive-increase cap of 22 packets, near the 20-packet bandwidth-delay product; it achieved 977.8/1000 goodput (99% of baseline), 0.0% loss, and average queue 2.0.
- With a 30-packet cap, gentler 90% instead of 80% backoff raised goodput from 964.0 to 976.5/1000, but loss rose 0.5%→0.8%, retransmissions 20→29, and queue 6.6→7.9; the gentler backoff cost more congestion and missed the queue target.
