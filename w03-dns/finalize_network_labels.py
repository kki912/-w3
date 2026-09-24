import json
from pathlib import Path

out = Path(__file__).resolve().parent / 'out'
for filename in ['chains.json', 'runs.json']:
    path = out / filename
    data = json.loads(path.read_text(encoding='utf-8'))
    rows = [r for samples in data.values() for r in samples] if isinstance(data, dict) else data
    for row in rows:
        if row['network'] == 'network-2':
            row['network'] = 'other-wifi'
            row['network_description'] = '다른 Wi-Fi (사용자가 실제 전환 확인)'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
