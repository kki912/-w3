#!/usr/bin/env python3
"""Week 5 · Task 2 — Where exactly are you on the internet?

Collect raw local network configuration and the public address observed by an
external service. The local output is intentionally left for you to interpret.

    python task2_myaddr.py --collect "campus wifi"
    python task2_myaddr.py --collect "phone tethering"
    python task2_myaddr.py --report
"""
import argparse
import json
import os
import platform
import subprocess
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
ADDRESSES_PATH = os.path.join(OUT, "addresses.json")
REPORT_PATH = os.path.join(OUT, "report.md")


def sh(*cmd):
    """Return a command's raw stdout, and report failures instead of hiding them."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, errors="replace",
            timeout=15, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError(f"required command not found: {cmd[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"command timed out: {' '.join(cmd)}") from exc

    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(cmd)}"
            + (f"\n{detail}" if detail else ""))
    return result.stdout


def local_facts():
    """Collect raw OS output only; interpreting it is the student's job."""
    osname = platform.system()
    if osname == "Darwin":
        return {
            "os": osname,
            "ifconfig": sh("ifconfig"),
            "route": sh("route", "-n", "get", "default"),
            "dns": sh("scutil", "--dns"),
        }
    if osname == "Linux":
        return {
            "os": osname,
            "ip_addr": sh("ip", "addr"),
            "ip_route": sh("ip", "route"),
            "dns": sh("cat", "/etc/resolv.conf"),
        }
    if osname == "Windows":
        return {
            "os": osname,
            "ipconfig": sh("ipconfig", "/all"),
            "route": sh("route", "print"),
        }
    raise RuntimeError(f"unsupported operating system: {osname}")


def public_address():
    """Ask an external service which public IPv4 address it sees."""
    request = urllib.request.Request(
        "https://api.ipify.org", headers={"User-Agent": "week5-network-lab"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            address = response.read().decode("ascii").strip()
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"could not retrieve public address: {exc}") from exc
    if not address:
        raise RuntimeError("public-address service returned an empty response")
    return address


def _load_records():
    if not os.path.exists(ADDRESSES_PATH):
        return []
    with open(ADDRESSES_PATH, encoding="utf-8") as source:
        records = json.load(source)
    if not isinstance(records, list):
        raise ValueError(f"{ADDRESSES_PATH} must contain a JSON list")
    return records


def collect(label):
    label = label.strip()
    if not label:
        raise ValueError("network label must not be empty")

    # Finish collection before writing, so a failed command cannot create a
    # misleading partial record.
    record = {
        "label": label,
        "local": local_facts(),
        "public": public_address(),
    }
    os.makedirs(OUT, exist_ok=True)
    records = _load_records()
    records.append(record)
    with open(ADDRESSES_PATH, "w", encoding="utf-8") as destination:
        json.dump(records, destination, indent=2, ensure_ascii=True)
        destination.write("\n")

    print(f"  public address seen from outside: {record['public']}")
    print(f"  -> {ADDRESSES_PATH} ({len(records)} record(s))")
    print("\nRead the raw local output in addresses.json and identify the")
    print("interface address, subnet mask/prefix, and default gateway yourself.")


def report():
    records = _load_records()
    os.makedirs(OUT, exist_ok=True)

    labels = [str(record.get("label", "(unlabelled)")) for record in records]
    networks = "\n\n".join(
        f"### {label}\n"
        "- Interface and address:\n"
        "- Mask or prefix:\n"
        "- Subnet range (computed by hand; verify with Task 1):\n"
        "- Default gateway; inside the subnet range? Why?\n"
        "- Is the interface address RFC 1918 private or shared CGNAT space?\n"
        f"- Public address seen outside: {record.get('public') or '(not recorded)'}\n"
        "- NAT layers and evidence:\n"
        for label, record in zip(labels, records)
    ) or "Collect at least one network with `--collect LABEL` before filling this in."
    if len(set(labels)) < 2:
        comparison_note = (
            "Collect a second, differently labelled network (for example, phone "
            "tethering) before answering the comparison."
        )
    else:
        comparison_note = "Compare the two networks' private address, mask, gateway, and public address."

    contents = f"""# Week 5 Task 2 · Address and DHCP observations

## Part A and B · Address study

Collected network labels: {", ".join(labels) if labels else "(none yet)"}.
{comparison_note}

{networks}

### Comparison
- Did the public address change? Why?
- Did the private/interface address change? Why?
- How many NAT layers are supported by the evidence? Explain how you would
  distinguish one NAT from two (including `100.64.0.0/10` carrier-grade NAT).

## Part C · DHCP exchange

Capture `out/dhcp.pcapng` in Wireshark with capture filter `port 67 or port 68`
while disconnecting and reconnecting to a network. If live capture is blocked,
use the official DHCP trace and identify it here.

- Trace used (own capture or official trace):
- Discover source address:
- Discover destination address, and why it has that value:
- Lease time offered:
- Discover / Offer / Request / Ack present:
- What changed by Ack that can allow it not to be broadcast?
- At half the lease time, what does the client attempt?

Do not infer interface settings, lease details, or NAT layer count from the
collector alone; use your raw OS output and Wireshark capture as evidence.
"""
    with open(REPORT_PATH, "w", encoding="utf-8") as destination:
        destination.write(contents)
    print(f"  -> {REPORT_PATH}")
    print("Fill in the address and DHCP findings from your own measurements.")


def main():
    parser = argparse.ArgumentParser()
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument(
        "--collect", metavar="LABEL",
        help='collect raw network details, e.g. "campus wifi"')
    actions.add_argument(
        "--report", action="store_true",
        help="write a report template for your measured results")
    args = parser.parse_args()

    if args.collect is not None:
        collect(args.collect)
    else:
        report()


if __name__ == "__main__":
    main()
