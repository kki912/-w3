"""Finalize provenance and verification notes without altering DNS observations."""
import json
from pathlib import Path

out = Path(__file__).resolve().parent / 'out'
path = out / 'capture_metadata.json'
metadata = json.loads(path.read_text(encoding='utf-8'))
metadata['equivalent_command'] = metadata['command']
metadata['command'] = 'python3 capture_part_a.py --interface eth0'
metadata['resolver_call'] = "task1_resolve.Resolver().resolve('www.korea.ac.kr')"
metadata['network'] = 'other-wifi'
path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
