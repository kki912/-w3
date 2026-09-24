#!/usr/bin/env python3
"""Real DNS measurements. Run --collect --network 'home-wifi', then --report.

Repeat --collect on the second physical network with a different --network label.
Labels describe the user's connection; this program cannot change/verify Wi-Fi.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import re
from pathlib import Path
import socket

import dns.exception
import dns.flags
import dns.message
import dns.name
import dns.query
import dns.rcode
import dns.rdatatype
import dns.resolver

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
SITES = ['www.microsoft.com', 'www.netflix.com', 'www.adobe.com', 'www.cnn.com',
         'www.apple.com', 'www.korea.ac.kr', 'www.stanford.edu', 'www.bbc.co.uk',
         'www.spotify.com', 'www.github.com', 'www.wikipedia.org', 'www.nytimes.com']
RESOLVERS = {'system': None, 'google': '8.8.8.8', 'quad9': '9.9.9.9'}
PROVIDERS = {'akamaiedge.net': 'Akamai', 'edgekey.net': 'Akamai',
             'edgesuite.net': 'Akamai', 'akamai.net': 'Akamai',
             'fastly.net': 'Fastly', 'fastly-edge.com': 'Fastly',
             'cloudfront.net': 'Amazon CloudFront',
             'netlifyglobalcdn.com': 'Netlify', 'cdn.cloudflare.net': 'Cloudflare'}


def now():
    return datetime.now(timezone.utc).isoformat()


def within(name, suffix):
    return name == suffix or name.endswith('.' + suffix)


def last_two(name):
    return '.'.join(name.rstrip('.').lower().split('.')[-2:])


def atomic_json(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def exchange(name, kind, servers, queries):
    """Recursive questions to each chosen resolver are allowed in Task 2."""
    errors = []
    for server in servers:
        query = dns.message.make_query(name, kind)
        event = {'time_utc': now(), 'server': server, 'name': name, 'type': kind,
                 'id': query.id}
        try:
            response = dns.query.udp(query, server, timeout=3)
            event['transport'] = 'UDP'
            if response.flags & dns.flags.TC:
                response = dns.query.tcp(query, server, timeout=3)
                event['transport'] = 'UDP then TCP'
            event.update(rcode=dns.rcode.to_text(response.rcode()),
                         answer=[rr.to_text() for rr in response.answer],
                         authority=[rr.to_text() for rr in response.authority],
                         additional=[rr.to_text() for rr in response.additional])
            queries.append(event)
            if response.rcode() != dns.rcode.NOERROR:
                errors.append(event['rcode'])
                continue
            return response
        except (dns.exception.DNSException, OSError, EOFError) as exc:
            event['error'] = str(exc)
            queries.append(event)
            errors.append(str(exc))
    raise RuntimeError('; '.join(errors) or 'no configured DNS servers')


def measure(site, resolver, servers, run_id, network):
    result = {'run_id': run_id, 'network': network, 'resolver': resolver,
              'servers': servers, 'time_utc': now(), 'chain': [site],
              'addresses': [], 'queries': [], 'status': 'error'}
    current = site
    try:
        for _ in range(24):
            response = exchange(current, 'A', servers, result['queries'])
            owner = dns.name.from_text(current)
            alias = next((rr[0].target.to_text().rstrip('.').lower()
                          for rr in response.answer
                          if rr.name == owner and rr.rdtype == dns.rdatatype.CNAME), None)
            if alias:
                if alias in result['chain']:
                    raise RuntimeError('CNAME loop')
                result['chain'].append(alias)
                current = alias
                continue
            addresses = sorted({rr.address for rrset in response.answer
                                if rrset.name == owner and rrset.rdtype == dns.rdatatype.A
                                for rr in rrset})
            if not addresses:
                raise RuntimeError('no terminal A record')
            result.update(addresses=addresses, final_name=current, status='ok')
            # Determine an actual SOA zone, not the last two DNS labels.
            candidate = owner
            while len(candidate.labels) > 1:
                soa_response = exchange(candidate.to_text(), 'SOA', servers, result['queries'])
                soa = [rr for rr in soa_response.answer + soa_response.authority
                       if rr.rdtype == dns.rdatatype.SOA and owner.is_subdomain(rr.name)]
                if soa:
                    result['final_zone'] = max(soa, key=lambda rr: len(rr.name.labels)).name.to_text().rstrip('.')
                    break
                candidate = candidate.parent()
            return result
        raise RuntimeError('CNAME depth exceeded')
    except (RuntimeError, dns.exception.DNSException, OSError) as exc:
        # If addresses succeeded but SOA failed, retain successful address evidence.
        result['error'] = str(exc)
        return result


def collect(network):
    if not network:
        raise SystemExit('--collect requires --network (actual connection name)')
    OUT.mkdir(exist_ok=True)
    path = OUT / 'chains.json'
    data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {s: [] for s in SITES}
    run_id = now()
    system = [str(s) for s in dns.resolver.Resolver().nameservers]
    jobs = [(site, label, [server] if server else system, run_id, network)
            for site in SITES for label, server in RESOLVERS.items()]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for site, result in zip([j[0] for j in jobs], pool.map(lambda args: measure(*args), jobs)):
            data.setdefault(site, []).append(result)
            atomic_json(path, data)
            print(site, result['resolver'], result['status'], result['addresses'], flush=True)
    metadata_path = OUT / 'runs.json'
    runs = json.loads(metadata_path.read_text(encoding='utf-8')) if metadata_path.exists() else []
    runs.append({'run_id': run_id, 'network': network, 'host': socket.gethostname(),
                 'system_nameservers': system, 'finished_utc': now()})
    atomic_json(metadata_path, runs)
    print('Saved', path, flush=True)


def classify(site, chain):
    naive = last_two(site) != last_two(chain[-1])
    if site == 'www.wikipedia.org' and within(chain[-1], 'wikimedia.org'):
        return naive, '아니오 (Wikimedia 자체 CDN)', True, '동일 운영자의 다른 도메인: 단순 규칙의 거짓 양성'
    for name in chain:
        for suffix, provider in PROVIDERS.items():
            if within(name, suffix):
                return naive, '예 (' + provider + ')', True, '알려진 CDN 도메인 관찰'
    if site == 'www.netflix.com':
        return naive, '미확정 (웹 호스팅과 영상 CDN 구분)', False, 'Open Connect는 자체 영상 CDN; www의 운영자는 DNS만으로 단정 불가'
    return naive, '미확정', False, 'CNAME 유무/도메인 차이만으로 CDN 또는 운영자 확정 불가'


def report():
    data = json.loads((OUT / 'chains.json').read_text(encoding='utf-8'))
    networks = sorted({r['network'] for rows in data.values() for r in rows})
    dates = {network: sorted({r['time_utc'][:10] for rows in data.values() for r in rows
                             if r['network'] == network}) for network in networks}
    latest = {}
    for site, rows in data.items():
        for r in rows:
            latest[(site, r['network'], r['resolver'])] = r
    lines = ['# DNS / CDN 실제 측정 보고서', '', '## 측정 범위', '',
             '네트워크: ' + ', '.join(networks),
             '네트워크 이름: home-wifi = 집 Wi-Fi, other-wifi = 사용자가 전환을 확인한 다른 Wi-Fi.',
             '측정 날짜(UTC): ' + '; '.join(n + ' = ' + ', '.join(dates[n]) for n in networks),
             'Resolvers: system, Google 8.8.8.8, Quad9 9.9.9.9. 시각은 원본 JSON의 UTC.',
             'system은 JSON의 servers에 기록된 WSL DNS 프록시다. 최종 업스트림 리졸버 위치는 확인하지 않았다.',
             '동일 네트워크·리졸버의 최신 측정을 비교했다. 실패/빈 응답은 차이로 세지 않았다.',
             '체인 길이는 CNAME 간선 수다. 최종 구역은 SOA로 확인하며, 확인 실패는 미확정으로 표시한다.', '',
             '## Third-party 판정 규칙', '',
             '검사할 단순 규칙: 원래 이름과 마지막 이름의 마지막 두 레이블이 다르면 third-party로 판정한다.',
             '이는 등록 도메인/운영자 판정이 아니다. co.uk·ac.kr 같은 접미사와 동일 회사의 여러 도메인에서 오류가 난다.',
             '보정 판정: 알려진 CDN 도메인과 운영자 문서를 함께 확인한다. 근거 없는 경우 미확정이다.', '',
             '| 사이트 | 네트워크 / resolver | 체인 길이 | 최종 구역 | Third-party 보정 판정 | 단순 규칙 판결 |',
             '|---|---|---:|---|---|---|']
    cdn_sites = set()
    false_positives = []
    for (site, network, resolver), r in sorted(latest.items()):
        if r['status'] != 'ok':
            lines.append(f'| {site} | {network} / {resolver} | — | 오류 | 미확정 | 측정 실패 |')
            continue
        naive, verdict, cdn, reason = classify(site, r['chain'])
        if cdn:
            cdn_sites.add(site)
        if naive and verdict.startswith('아니오'):
            false_positives.append((site, r['chain']))
        lines.append(f"| {site} | {network} / {resolver} | {len(r['chain'])-1} | {r.get('final_zone', '미확정')} | {verdict} | {'제3자' if naive else '동일'} |")
    def original_addresses(r):
        # Prefer the A set returned for the original hostname, recorded verbatim.
        # Some resolvers return CNAME-only: in that case use our completed chain.
        records = r['queries'][0].get('answer', []) if r['queries'] else []
        found = {line.split()[4] for rr in records for line in rr.splitlines()
                 if len(line.split()) >= 5 and line.split()[3] == 'A'
                 and line.split()[0].rstrip('.').lower() in r['chain']}
        return sorted(found) or r['addresses']
    def different(rows):
        return len({tuple(original_addresses(r)) for r in rows if r['status'] == 'ok'}) > 1
    eligible, changed, cross_network = [], [], []
    for site in sorted(cdn_sites):
        rows = [r for (s, _, _), r in latest.items() if s == site and r['status'] == 'ok']
        if len(rows) >= 2:
            eligible.append(site)
            if different(rows):
                changed.append(site)
        if any(len({r['network'] for r in rows if r['resolver'] == label}) >= 2
               and different([r for r in rows if r['resolver'] == label]) for label in RESOLVERS):
            cross_network.append(site)
    lines += ['', '## Steering number (B5)', '',
              f'비교 가능한 CDN 호스팅 사이트 {len(eligible)}개 중 {len(changed)}개가 서로 다른 resolver 또는 네트워크에서 다른 A 주소 집합을 보였다.',
              '차이 발생 사이트: ' + (', '.join(changed) or '없음'),
              (f'같은 resolver를 두 네트워크에서 비교했을 때 차이 발생: {len(cross_network)}개.' if len(networks) >= 2 else
               '같은 resolver의 네트워크 간 차이: 아직 측정하지 않음 (0개라는 뜻이 아님).'),
              '이 분모는 CNAME 제공자 또는 Wikimedia 문서로 CDN 근거를 확보한 사이트만 포함한다. 미확정 사이트는 제외한다.']
    for network in networks:
        comparable = [s for s in cdn_sites if sum(1 for (site, n, _), r in latest.items()
                                                 if site == s and n == network and r['status'] == 'ok') >= 2]
        count = sum(different([r for (site, n, _), r in latest.items() if site == s and n == network]) for s in comparable)
        lines.append(f'- {network}: CDN {len(comparable)}개 중 {count}개가 resolver에 따라 달랐다.')
    lines += ['', '## 리졸버별 원본 주소 집합 (B2)', '',
              '원래 사이트 이름에 대한 첫 응답의 A 집합을 비교한다. CNAME만 받은 경우 전체 체인을 해결한 최종 집합을 사용한다.',
              '각 단계의 원문 응답, TTL, 질의 ID, 시각, 실제 DNS 서버 주소는 chains.json에 보존했다.', '',
              '| 사이트 | 네트워크 / resolver | A 주소 집합 |', '|---|---|---|']
    for (site, network, resolver), r in sorted(latest.items()):
        values = ', '.join(original_addresses(r)) if r['status'] == 'ok' else '측정 실패: ' + r.get('error', '')
        lines.append(f'| {site} | {network} / {resolver} | {values} |')
    lines += ['', '주소 차이는 DNS 응답의 변화라는 증거다. 가장 가까운 복제본이라는 증거는 아니다. 시간, 캐시, 부하 분산, ECS, anycast가 섞이며 위치·RTT를 측정하지 않았다.',
              '이번 측정은 네트워크마다 날짜도 다르므로 네트워크 간 차이를 위치 변화만의 효과로 분리할 수 없다.',
              'Google/Quad9 주소만으로 실제 처리 서버가 미국에 있다고 판단하지 않는다. 둘 다 지리적 관측점으로 자동 대체할 수 없다.', '',
              '## 규칙이 틀린 사이트', '']
    if false_positives:
        site, chain = false_positives[0]
        lines += [f"{site}: `{' → '.join(chain)}`. wikipedia.org와 wikimedia.org가 달라 단순 규칙은 제3자라고 판단하지만 Wikimedia 자체 CDN이다."]
    else:
        lines += ['미완료: 현재 측정에서 운영자 근거로 입증한 반례가 아직 없다. 추측으로 채우지 않았다.']
    lines += ['', '## Part A — 실제 패킷 캡처', '']
    capture = OUT / 'capture_analysis.md'
    lines += [capture.read_text(encoding='utf-8') if capture.exists() else
              '미완료: 실제 dns.pcapng, 쿼리/응답 ID, 위임·답변 패킷 번호, 최대 DNS 응답 바이트 수와 스크린샷이 필요하다.']
    lines += ['', '## 직접 캡처한 화면 이미지', '']
    lines += ['사용자가 직접 저장한 Wireshark 화면이다. 패킷 목록의 ID·NS/A 요약과 프레임 길이는 보이지만 DNS 상세 트리는 접혀 있다. Answer/Authority 개수와 DNS 메시지 길이는 원본 dns.pcapng 및 packet_details.txt 분석을 근거로 한다.', '']
    screenshots = [('dns-query.png', '쿼리와 Transaction ID'),
                   ('dns-referral.png', '위임 응답과 최대 응답 크기'),
                   ('dns-answer.png', '최종 A 답변')]
    for filename, caption in screenshots:
        if (OUT / filename).exists():
            lines.append(f'![{caption}]({filename})')
        else:
            lines.append(f'미완료: `{filename}` — Wireshark에서 {caption} 화면을 직접 저장해야 한다.')
    lines += ['', '## 완료 상태', '',
              ('집 Wi-Fi와 다른 Wi-Fi로 실제 연결을 전환하여 측정했다(사용자 확인).' if {'home-wifi', 'other-wifi'}.issubset(networks) else
               'B3 미완료: 현재 한 네트워크만 측정했다. 두 번째 실제 네트워크로 전환하여 재수집해야 한다.'), '',
              '## 출처', '',
              '- [Wikimedia CDN](https://wikitech.wikimedia.org/wiki/CDN)',
              '- [Wikimedia DNS routing](https://wikitech.wikimedia.org/wiki/Gdns)',
              '- [Netflix Open Connect](https://openconnect.netflix.com/)', '']
    (OUT / 'report.md').write_text('\n'.join(lines), encoding='utf-8')
    observation = ['# 과제 2 Observation', '',
                   ((OUT / 'capture_observation.txt').read_text(encoding='utf-8') if (OUT / 'capture_observation.txt').exists() else
                    'Part A 미완료: 직접 캡처한 위임 응답과 최종 답변을 아직 비교하지 못했다.'),
                   ('마지막 두 레이블 비교는 wikipedia.org → wikimedia.org를 제3자로 오판했다. 실제로는 Wikimedia 자체 CDN이다.' if false_positives else
                    '제3자 판정 규칙의 실제 반례 확인이 필요하다.'),
                   f"{', '.join(networks)}에서 비교 가능한 CDN {len(eligible)}개 중 {len(changed)}개가 다른 주소 집합을 보였지만, 측정 날짜도 달라 네트워크 효과를 분리하거나 최단 거리 유도를 입증할 수 없다." +
                   (' 두 번째 네트워크 측정은 미완료다.' if len(networks) < 2 else ''), '']
    observation_path = OUT / 'observation.md'
    existing = observation_path.read_text(encoding='utf-8') if observation_path.exists() else ''
    task2_section = '## 과제 2\n\n' + '\n'.join(observation[2:]).strip() + '\n'
    if existing.startswith('# 과제 2 Observation') or not existing.strip():
        combined = '# 3주차 Observation\n\n' + task2_section
    elif re.search(r'^## 과제 2(?:\s|$)', existing, re.MULTILINE):
        combined = re.sub(r'^## 과제 2[^\n]*\n.*?(?=^## |\Z)',
                          lambda _: task2_section + '\n', existing, flags=re.MULTILINE | re.DOTALL)
    else:
        combined = existing.rstrip() + '\n\n' + task2_section
    observation_path.write_text(combined, encoding='utf-8')
    print('Saved report.md and observation.md')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--collect', action='store_true')
    parser.add_argument('--network', help='actual network label, e.g. home-wifi or phone-hotspot')
    parser.add_argument('--report', action='store_true')
    args = parser.parse_args()
    if args.collect:
        collect(args.network)
    if args.report:
        report()
    if not (args.collect or args.report):
        parser.print_help()
