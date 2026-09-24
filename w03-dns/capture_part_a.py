#!/usr/bin/env python3
"""Capture real Task 1 packets using dumpcap; never synthesize a packet trace."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import time

from task1_resolve import Resolver

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--interface', default='eth0')
    args = parser.parse_args()
    for tool in ['dumpcap', 'tshark']:
        if not shutil.which(tool):
            raise SystemExit(f'{tool} is missing; install tshark first')
    OUT.mkdir(exist_ok=True)
    private = HERE / '.capture-private'
    private.mkdir(exist_ok=True)
    raw = private / 'dns-raw.pcapng'
    capture = OUT / 'dns.pcapng'
    metadata = {'time_utc': datetime.now(timezone.utc).isoformat(),
                'interface': args.interface, 'capture_filter': 'port 53',
                'command': f'python3 capture_part_a.py --interface {args.interface}',
                'resolver_call': "task1_resolve.Resolver().resolve('www.korea.ac.kr')",
                'equivalent_command': 'python3 task1_resolve.py www.korea.ac.kr',
                'interfaces': subprocess.run(['ip', '-j', 'addr'], capture_output=True, text=True).stdout,
                'exchanges': []}
    with (private / 'dumpcap.log').open('w') as log:
        process = subprocess.Popen(['dumpcap', '-i', args.interface, '-f', 'port 53',
                                    '-a', 'duration:20', '-w', str(raw)], stdout=log, stderr=log)
        time.sleep(1)
        if process.poll() is not None:
            raise SystemExit((private / 'dumpcap.log').read_text())
        resolver = Resolver()
        original = resolver._query
        def tracked(server, name):
            response = original(server, name)
            metadata['exchanges'].append({'server': server, 'name': name,
                                           'id': response.id if response is not None else None})
            return response
        resolver._query = tracked
        try:
            address, path = resolver.resolve('www.korea.ac.kr')
            metadata.update(address=address, path=path)
            print('www.korea.ac.kr', address, path, flush=True)
        finally:
            # dumpcap's duration limit closes the pcapng cleanly.
            process.wait(timeout=25)
            (private / 'capture_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    pairs = [(x['id'], x['server']) for x in metadata['exchanges'] if x['id'] is not None]
    if not pairs:
        raise SystemExit('No resolver response was observed; retained raw capture for diagnosis')
    identity = ' || '.join(f'(dns.id == {ident} && ip.addr == {server})' for ident, server in pairs if ':' not in server)
    display = f'dns.qry.name == "www.korea.ac.kr" && dns.flags.recdesired == 0 && ({identity})'
    subprocess.run(['tshark', '-r', str(raw), '-Y', display, '-F', 'pcapng', '-w', str(capture)], check=True)
    metadata.pop('interfaces')  # Do not submit unrelated adapter details.
    metadata['privacy_filter'] = display
    (OUT / 'capture_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print('Saved', capture, 'with only this resolver\'s matching DNS exchanges')


if __name__ == '__main__':
    main()
