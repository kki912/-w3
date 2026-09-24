A1: 사용자의 WSL 인터페이스 eth0에서 직접 실행한 Task 1의 패킷이다. 캡처의 클라이언트 IP는 `172.30.29.167`이고, 루트 대상은 `198.41.0.4`다.
실행 중 기록한 서버 주소·질의 ID와 대조하여 다른 앱의 DNS 교환을 제출본에서 제외했다. WSL 가상 인터페이스에서 캡처했으므로 Windows Wi-Fi의 MAC 주소가 보인다고 주장하지 않는다.

A2: 쿼리 **#1**와 응답 **#2**의 Transaction ID는 둘 다 **0x98dc**다. IP 방향이 반대이며 Wireshark의 response_to도 이 쿼리를 가리킨다.

A3 위임: **#2**, Answers=0, Authority=6; NS: `c.dns.kr,e.dns.kr,d.dns.kr,g.dns.kr,f.dns.kr,b.dns.kr`.
A3 최종 답변: **#6**, Answers=1, AA=1; A: `163.152.6.10`.

A4: 가장 큰 DNS 응답은 **#2**, DNS 메시지 **341 bytes**, 프레임 전체 **383 bytes**다.
이 응답의 레코드 수는 Answer=0, Authority=6, Additional=10다. 여러 NS 위임 레코드와 네임서버 주소를 담는 Additional 레코드가 함께 있어 단일 A 답변보다 커졌다.
UDP의 경우 UDP Length에서 헤더 8 bytes를 뺀 값을 DNS 메시지 길이로 사용했다. TCP의 경우 DNS length prefix 값을 사용한다. 프레임 전체 크기와 혼동하지 않았다.

관찰: 위임 응답은 Answer가 비고 Authority의 NS가 다음 서버를 가리키지만, 최종 답변은 Answer의 A가 요청한 호스트 주소를 제공한다.

[패킷 상세 원문](packet_details.txt) · [캡처 파일](dns.pcapng)
