# 완료: 실제 Wireshark 스크린샷 3장

사용자가 직접 저장한 화면 3장을 확인하고 out 폴더에 제출용 이름으로 복사했다.
report.md에 이미지가 연결되어 있으며 과제 2 테스트는 5 passed, 0 failed다.
DNS 상세 트리는 접혀 있다. 패킷 요약은 보이지만 상세 필드를 화면에서도 명확히 보여주려면 아래 안내대로 펼쳐 다시 저장할 수 있다.

아래는 선택적인 화면 보완 안내다.

Wireshark에서 다음 파일을 연다:

`D:\컴퓨터네트워크\w03-dns\out\dns.pcapng`

WSL Wireshark에서의 경로:

`/mnt/d/컴퓨터네트워크/w03-dns/out/dns.pcapng`

각 패킷을 선택하고 하단의 Domain Name System 항목을 펼친 뒤 화면을 캡처한다.
Windows의 Win+Shift+S를 사용하여 Wireshark 영역만 선택하고 PNG로 저장하면 된다.

1. 패킷 #1: Transaction ID 0x98dc와 질문 www.korea.ac.kr이 보이도록 `dns-query.png`로 저장.
2. 패킷 #2: 같은 ID 0x98dc, Answer RRs=0, Authority RRs=6, Authoritative nameservers를 펼쳐 `dns-referral.png`로 저장. 프레임 383 bytes, UDP Length 349도 확인 가능하다.
3. 패킷 #6: Answers를 펼쳐 A=163.152.6.10과 AA 플래그가 보이도록 `dns-answer.png`로 저장.

저장 위치는 이 파일과 같은 `out` 폴더다. DNS 메시지 최대 크기는 349-8=341 bytes이며 프레임 크기 383 bytes와 다르다.

저장한 뒤 WSL에서:

```bash
cd /mnt/d/컴퓨터네트워크/w03-dns
python3 task2_steering.py --report
python3 test_tasks.py --task 2
```

report.md에 이미지가 자동으로 포함된다. Downloads 폴더의 사본 대신 이 작업 폴더를 최종 제출본으로 사용한다.
