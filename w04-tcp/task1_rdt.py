#!/usr/bin/env python3
"""Week 4 · Task 1 — Build reliable delivery on top of an unreliable channel.

Textbook §3.4 (reliable data transfer) and §3.5 (TCP's sequence numbers).

`UnreliableChannel` below loses packets, reorders them, duplicates them, and
delays them. It is the network as §3.4 models it. Your job is to move a file
across it and have the bytes arrive intact and in order.

That is the whole of TCP's reliability story with the congestion control taken
out, and it is worth building once by hand before you ever trust a socket again.

    python3 task1_rdt.py --verify
"""
import argparse, hashlib, random

PAYLOAD = 8            # bytes per packet - small, so you see the sequencing
RETRANSMIT_AFTER = 8   # sender.step() calls without a matching ACK


class UnreliableChannel:
    """Loses 10%, duplicates 3%, reorders, and delays. Deterministic by seed.

    You may not make it nicer. You may not read its internals. It is the only
    way your sender can reach your receiver.
    """

    def __init__(self, seed=246, loss=0.10, dup=0.03, reorder=0.10):
        self.rng = random.Random(seed)
        self.loss, self.dup, self.reorder = loss, dup, reorder
        self.wire = []          # packets in flight, in no particular order
        self.stats = {"sent": 0, "lost": 0, "duplicated": 0, "delivered": 0}

    def send(self, packet):
        """Hand a packet to the network. It may never come out."""
        self.stats["sent"] += 1
        if self.rng.random() < self.loss:
            self.stats["lost"] += 1
            return
        copies = 2 if self.rng.random() < self.dup else 1
        self.stats["duplicated"] += copies - 1
        for _ in range(copies):
            if self.rng.random() < self.reorder and self.wire:
                self.wire.insert(self.rng.randrange(len(self.wire)), packet)
            else:
                self.wire.append(packet)

    def receive(self):
        """Take the next packet out, or None if the network has nothing."""
        if not self.wire:
            return None
        self.stats["delivered"] += 1
        return self.wire.pop(0)


class Sender:
    """Your sender.

    Requirements are in task1.md. The short version:

      - break `data` into PAYLOAD-sized pieces and number them
      - retransmit what is not acknowledged
      - do not assume an ACK means what you think it means until you have
        checked the number on it

    You choose the protocol: stop-and-wait is the easiest to get right and the
    slowest; a sliding window is the point of §3.4.3. Say which you chose and
    why in observation.md.
    """

    def __init__(self, data_channel, ack_channel, data):
        self.data_channel = data_channel
        self.ack_channel = ack_channel
        self.packets = [
            bytes(data[offset:offset + PAYLOAD])
            for offset in range(0, len(data), PAYLOAD)
        ]
        self.next_sequence = 0
        self.awaiting_ack = None
        self.steps = 0
        self.last_sent_step = 0

    def step(self):
        """Do one unit of work. Return False when you believe you are done."""
        if self.next_sequence == len(self.packets) and self.awaiting_ack is None:
            return False

        self.steps += 1
        ack = self.ack_channel.receive()
        if (
            isinstance(ack, tuple)
            and len(ack) == 2
            and ack[0] == "ACK"
            and self.awaiting_ack is not None
            and ack[1] == self.awaiting_ack
        ):
            self.next_sequence += 1
            self.awaiting_ack = None

        if self.awaiting_ack is None:
            if self.next_sequence == len(self.packets):
                return False
            self.awaiting_ack = self.next_sequence
            self.data_channel.send(
                ("DATA", self.awaiting_ack, self.packets[self.awaiting_ack])
            )
            self.last_sent_step = self.steps
        elif self.steps - self.last_sent_step >= RETRANSMIT_AFTER:
            self.data_channel.send(
                ("DATA", self.awaiting_ack, self.packets[self.awaiting_ack])
            )
            self.last_sent_step = self.steps

        return True


class Receiver:
    """Your receiver. Hands back the reassembled bytes via `.data()`."""

    def __init__(self, data_channel, ack_channel):
        self.data_channel = data_channel
        self.ack_channel = ack_channel
        self.expected_sequence = 0
        self.received = bytearray()

    def step(self):
        packet = self.data_channel.receive()
        if packet is None:
            return

        if (
            not isinstance(packet, tuple)
            or len(packet) != 3
            or packet[0] != "DATA"
            or not isinstance(packet[1], int)
            or not isinstance(packet[2], bytes)
        ):
            return

        sequence, payload = packet[1], packet[2]
        if sequence == self.expected_sequence:
            self.received.extend(payload)
            self.expected_sequence += 1
            acknowledged = sequence
        elif sequence < self.expected_sequence:
            acknowledged = sequence
        else:
            acknowledged = self.expected_sequence - 1

        self.ack_channel.send(("ACK", acknowledged))

    def data(self):
        """The bytes reassembled so far."""
        return bytes(self.received)


# ------------------------------------------------------------------- harness
def verify(seed=246, size=2000, max_steps=200_000):
    original = bytes(random.Random(seed).getrandbits(8) for _ in range(size))
    up, down = UnreliableChannel(seed), UnreliableChannel(seed + 1)

    # Data goes out over `up`, ACKs come back over `down`. Both are unreliable.
    sender = Sender(up, down, original)
    receiver = Receiver(up, down)

    for _ in range(max_steps):
        alive = sender.step()
        receiver.step()
        if not alive and len(receiver.data() or b"") >= size:
            break

    got = receiver.data() or b""
    ok = hashlib.sha256(got).hexdigest() == hashlib.sha256(original).hexdigest()
    print(f"  bytes    sent {size}   received {len(got)}")
    print(f"  channel  {up.stats}")
    print(f"  result   {'IDENTICAL' if ok else 'CORRUPTED OR INCOMPLETE'}")
    return 0 if ok else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--verify", action="store_true")
    p.add_argument("--seed", type=int, default=246)
    a = p.parse_args()
    raise SystemExit(verify(a.seed) if a.verify else p.print_help())
