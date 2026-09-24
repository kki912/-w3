"""Retry only failed latest observations; keep every original failure in JSON."""
import json
import task2_steering as m

path = m.OUT / 'chains.json'
data = json.loads(path.read_text(encoding='utf-8'))
for site, rows in data.items():
    latest = {}
    for row in rows:
        if row['network'] == 'other-wifi':
            latest[row['resolver']] = row
    for label, row in latest.items():
        if row['status'] == 'ok':
            continue
        for attempt in range(2):
            new = m.measure(site, label, row['servers'], m.now(), 'other-wifi')
            new['retry_of'] = row['run_id']
            rows.append(new)
            m.atomic_json(path, data)
            print(site, label, new['status'], new['addresses'], flush=True)
            if new['status'] == 'ok':
                break
m.report()
