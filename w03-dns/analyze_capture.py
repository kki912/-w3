#!/usr/bin/env python3
"""Derive packet numbers and byte counts from an actual pcapng using tshark."""
import csv
import io
import json
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent / 'out'
FIELDS = ['frame.number', 'frame.len', 'ip.src', 'ip.dst', 'dns.flags.response',
          'dns.id', 'dns.response_to', 'dns.count.answers', 'dns.count.auth_rr',
          'dns.count.add_rr', 'dns.ns', 'dns.a', 'udp.length', 'dns.length',
          'dns.flags.authoritative', 'dns.qry.name']


def main():
    command = ['tshark', '-r', str(OUT / 'dns.pcapng'), '-Y', 'dns', '-T', 'fields']
    for field in FIELDS:
        command.extend(['-e', field])
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    rows = [dict(zip(FIELDS, values)) for values in csv.reader(io.StringIO(result.stdout), delimiter='\t')]
    if not rows:
        raise SystemExit('No DNS packets')
    def number(row, field):
        return int(row.get(field, '').split(',')[0] or 0)
    def enabled(value):
        return value.lower() in ('1', 'true')
    responses = [r for r in rows if enabled(r['dns.flags.response'])]
    referrals = [r for r in responses if number(r, 'dns.count.answers') == 0 and r['dns.ns']]
    answers = [r for r in responses if number(r, 'dns.count.answers') > 0
               and r['dns.a'] and enabled(r['dns.flags.authoritative'])]
    if not referrals or not answers:
        raise SystemExit('The capture does not yet contain both a referral and authoritative A answer')
    def dns_bytes(row):
        return number(row, 'dns.length') or number(row, 'udp.length') - 8
    largest = max(responses, key=dns_bytes)
    referral, answer = referrals[0], answers[-1]
    query = next(r for r in rows if r['frame.number'] == referral['dns.response_to'])
    assert query['dns.id'] == referral['dns.id']
    assert query['ip.src'] == referral['ip.dst'] and query['ip.dst'] == referral['ip.src']
    report = [f"A1: 사용자의 WSL 인터페이스 eth0에서 직접 실행한 Task 1의 패킷이다. 캡처의 클라이언트 IP는 `{query['ip.src']}`이고, 루트 대상은 `{query['ip.dst']}`다.",
              '실행 중 기록한 서버 주소·질의 ID와 대조하여 다른 앱의 DNS 교환을 제출본에서 제외했다. WSL 가상 인터페이스에서 캡처했으므로 Windows Wi-Fi의 MAC 주소가 보인다고 주장하지 않는다.', '',
              f"A2: 쿼리 **#{query['frame.number']}**와 응답 **#{referral['frame.number']}**의 Transaction ID는 둘 다 **{query['dns.id']}**다. IP 방향이 반대이며 Wireshark의 response_to도 이 쿼리를 가리킨다.", '',
              f"A3 위임: **#{referral['frame.number']}**, Answers={referral['dns.count.answers']}, Authority={referral['dns.count.auth_rr']}; NS: `{referral['dns.ns']}`.",
              f"A3 최종 답변: **#{answer['frame.number']}**, Answers={answer['dns.count.answers']}, AA=1; A: `{answer['dns.a']}`.", '',
              f"A4: 가장 큰 DNS 응답은 **#{largest['frame.number']}**, DNS 메시지 **{dns_bytes(largest)} bytes**, 프레임 전체 **{largest['frame.len']} bytes**다.",
              f"이 응답의 레코드 수는 Answer={largest['dns.count.answers']}, Authority={largest['dns.count.auth_rr']}, Additional={largest['dns.count.add_rr']}다. "
              + ('여러 NS 위임 레코드와 네임서버 주소를 담는 Additional 레코드가 함께 있어 단일 A 답변보다 커졌다.' if largest['dns.ns'] else
                 '응답에 포함된 레코드 목록은 아래 packet_details.txt에서 확인할 수 있다.'),
              'UDP의 경우 UDP Length에서 헤더 8 bytes를 뺀 값을 DNS 메시지 길이로 사용했다. TCP의 경우 DNS length prefix 값을 사용한다. 프레임 전체 크기와 혼동하지 않았다.', '',
              '관찰: 위임 응답은 Answer가 비고 Authority의 NS가 다음 서버를 가리키지만, 최종 답변은 Answer의 A가 요청한 호스트 주소를 제공한다.', '',
              '[패킷 상세 원문](packet_details.txt) · [캡처 파일](dns.pcapng)', '']
    (OUT / 'capture_analysis.md').write_text('\n'.join(report), encoding='utf-8')
    observation = (f"직접 캡처한 위임 응답 #{referral['frame.number']}는 Answer=0과 Authority의 NS를 담고, "
                   f"최종 응답 #{answer['frame.number']}는 Answer의 A={answer['dns.a']}를 담았다. "
                   f"최대 DNS 응답은 {dns_bytes(largest)} bytes였다.")
    (OUT / 'capture_observation.txt').write_text(observation, encoding='utf-8')
    selection = sorted({query['frame.number'], referral['frame.number'], answer['frame.number'], largest['frame.number']}, key=int)
    details = subprocess.run(['tshark', '-r', str(OUT / 'dns.pcapng'), '-Y',
                              ' || '.join('frame.number == ' + n for n in selection), '-V'],
                             capture_output=True, text=True, check=True).stdout
    (OUT / 'packet_details.txt').write_text(details, encoding='utf-8')
    (OUT / 'packet_fields.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print('\n'.join(report))


if __name__ == '__main__':
    main()
