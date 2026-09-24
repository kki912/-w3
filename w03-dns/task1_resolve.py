#!/usr/bin/env python3
"""Walk DNS delegations ourselves. Run with a name or --verify.

Only the comparison helper uses the system's recursive resolver (via dig).
CDN address differences are reported, not evidence of correctness by themselves.
"""
import argparse
import ipaddress
import subprocess
import sys

import dns.exception
import dns.flags
import dns.message
import dns.name
import dns.query
import dns.rcode
import dns.rdatatype

ROOT_SERVERS = ["198.41.0.4", "199.9.14.201", "192.33.4.12"]
VERIFY_NAMES = [
    ("www.korea.ac.kr", "stable"),
    ("dns.google", "stable"),
    ("en.wikipedia.org", "stable"),
    ("www.stanford.edu", "stable"),
    ("www.microsoft.com", "cdn"),
]


class ResolutionError(RuntimeError):
    pass


class QueryLimitError(ResolutionError):
    pass


class Resolver:
    MAX_DEPTH = 20
    MAX_QUERIES = 200
    TIMEOUT = 2

    def _query(self, server, name):
        query = dns.message.make_query(name, "A", want_dnssec=False)
        query.flags &= ~dns.flags.RD
        try:
            response = dns.query.udp(query, server, timeout=self.TIMEOUT)
            if response.flags & dns.flags.TC:
                # This is another question to the same server; retain it in path.
                self._record(server)
                response = dns.query.tcp(query, server, timeout=self.TIMEOUT)
            return response
        except (dns.exception.DNSException, OSError, EOFError):
            return None

    def _record(self, server):
        if len(self.path) >= self.MAX_QUERIES:
            raise QueryLimitError("total DNS query limit exceeded")
        self.path.append(server)

    def resolve(self, name):
        """Return (IPv4 address, all contacted servers in chronological order)."""
        self.path = []
        self.trace = []
        self.glueless_lookups = []
        self.cnames = []
        current = dns.name.from_text(name).canonicalize()
        address = self._resolve(current, 0, frozenset())
        return address, self.path

    def _resolve(self, name, depth, active):
        if depth > self.MAX_DEPTH:
            raise ResolutionError(f"depth limit exceeded for {name}")
        if name in active:
            raise ResolutionError(f"name loop detected for {name}")
        return self._walk(name, ROOT_SERVERS, dns.name.root, depth,
                          active | {name}, frozenset())

    def _walk(self, name, servers, zone, depth, active, visited):
        if depth > self.MAX_DEPTH:
            raise ResolutionError(f"delegation depth limit exceeded for {name}")
        for server in dict.fromkeys(servers):
            pair = (name, server)
            if pair in visited:
                continue
            self._record(server)
            response = self._query(server, name.to_text())
            if response is None:
                self.trace.append((name.to_text(), server, "timeout/error"))
                continue
            self.trace.append((name.to_text(), server,
                               dns.rcode.to_text(response.rcode())))
            if response.rcode() != dns.rcode.NOERROR:
                continue

            if response.flags & dns.flags.AA:
                # Follow only a CNAME owned by the name we actually requested.
                cname = next((rr[0].target.canonicalize()
                              for rr in response.answer
                              if rr.name == name and rr.rdtype == dns.rdatatype.CNAME), None)
                if cname is not None:
                    self.cnames.append((name.to_text(), cname.to_text()))
                    try:
                        return self._resolve(cname, depth + 1, active)
                    except QueryLimitError:
                        raise
                    except ResolutionError:
                        continue
                answer = next((rr[0].address for rr in response.answer
                               if rr.name == name and rr.rdtype == dns.rdatatype.A), None)
                if answer is not None:
                    return answer

            # A referral must move down the hierarchy toward the requested name.
            referrals = [rr for rr in response.authority
                         if rr.rdtype == dns.rdatatype.NS
                         and name.is_subdomain(rr.name)
                         and rr.name.is_subdomain(zone) and rr.name != zone]
            if not referrals:
                continue
            referral = max(referrals, key=lambda rr: len(rr.name.labels))
            child_zone = referral.name.canonicalize()
            ns_names = list(dict.fromkeys(rr.target.canonicalize() for rr in referral))
            glue = {}
            for rr in response.additional:
                host = rr.name.canonicalize()
                # Use only addresses for the NS names actually delegated here.
                # Root referrals can include sibling glue (e.g. .com -> .net NS).
                if (host in ns_names
                        and rr.rdtype in (dns.rdatatype.A, dns.rdatatype.AAAA)):
                    glue.setdefault(host, []).extend(record.address for record in rr)
            ready = [ip for ns in ns_names for ip in glue.get(ns, [])]
            ready.sort(key=lambda ip: ":" in ip)  # Prefer IPv4 on IPv4-only hosts.
            branch = visited | {pair}
            if ready:
                try:
                    return self._walk(name, ready, child_zone, depth + 1, active, branch)
                except QueryLimitError:
                    raise
                except ResolutionError:
                    pass
            # Resolve missing NS addresses lazily, after trying supplied glue.
            for ns in ns_names:
                if ns in glue:
                    continue
                before = len(self.path)
                try:
                    address = self._resolve(ns, depth + 1, active)
                except QueryLimitError:
                    raise
                except ResolutionError:
                    continue
                finally:
                    self.glueless_lookups.append((ns.to_text(), len(self.path) - before))
                try:
                    return self._walk(name, [address], child_zone, depth + 1, active, branch)
                except QueryLimitError:
                    raise
                except ResolutionError:
                    continue
            # All delegated servers failed: try another parent/root server.
        raise ResolutionError(f"no usable authoritative A answer for {name}")


def dig_answer(name):
    """Independent reference only; never used by Resolver."""
    try:
        result = subprocess.run(["dig", "+short", "+time=2", "+tries=2", name, "A"],
                                capture_output=True, text=True, timeout=15, check=True)
    except FileNotFoundError as exc:
        raise RuntimeError("dig is required for --verify; run in the course container") from exc
    except (subprocess.SubprocessError, OSError) as exc:
        raise RuntimeError(f"dig failed for {name}: {exc}") from exc
    addresses = []
    for line in result.stdout.split():
        try:
            address = ipaddress.ip_address(line)
        except ValueError:
            continue
        if address.version == 4:
            addresses.append(str(address))
    if not addresses:
        raise RuntimeError(f"dig returned no A records for {name}")
    return addresses


def verify():
    failures = 0
    for name, kind in VERIFY_NAMES:
        resolver = Resolver()
        try:
            addr, path = resolver.resolve(name)
            expected = dig_answer(name)
        except (RuntimeError, dns.exception.DNSException) as exc:
            print(f"  FAIL  {name:<22} {exc}")
            failures += 1
            continue
        matches = addr in expected
        passed = matches or kind == "cdn"
        failures += not passed
        note = "" if matches else (
            "  <- CDN difference: record evidence in observation.md"
            if kind == "cdn" else "  <- should have matched")
        print(f"  {'ok' if passed else 'FAIL':<4}  {name:<22} "
              f"you={addr:<16} dig={','.join(expected)}   hops={len(path)}{note}")
        for ns, count in resolver.glueless_lookups:
            print(f"        no glue: {ns} -> {count} extra queries (including nested lookups)")
        if not matches:
            print("        path: " + " -> ".join(path))
            for source, target in resolver.cnames:
                print(f"        CNAME: {source} -> {target}")
    print(f"\n  {len(VERIFY_NAMES) - failures}/{len(VERIFY_NAMES)} ok")
    return int(failures != 0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?", default="www.korea.ac.kr")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        return verify()
    resolver = Resolver()
    try:
        address, path = resolver.resolve(args.name)
    except (RuntimeError, dns.exception.DNSException) as exc:
        print(f"Resolution failed: {exc}", file=sys.stderr)
        return 1
    for i, server in enumerate(path, 1):
        print(f"  {i}. asked {server}")
    print(f"\n  {args.name} -> {address}")
    for ns, count in resolver.glueless_lookups:
        print(f"  no glue: {ns}: {count} extra queries (including nested lookups)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
