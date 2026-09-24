# 과제 2 실행 및 제출 안내

이 폴더의 측정은 실제 DNS 트래픽으로 수집한다. 네트워크 이름만 바꾸고 같은 연결에서 실행하면 두 네트워크 측정이 아니다.

## 파일

- `task2_steering.py`: 수집 및 보고서 생성
- `capture_part_a.py`: Wireshark의 dumpcap/tshark로 자신의 Task 1 트래픽 캡처
- `out/chains.json`: 사이트별 모든 네트워크/리졸버의 CNAME 경로, A 응답, TTL, 질의 시각/ID
- `out/runs.json`: 측정 회차 및 실제 시스템 DNS 주소
- `out/report.md`: 측정 표, 주소 집합, 차이 집계, 규칙 반례, 캡처 해석
- `out/observation.md`: 과제 2 요약 (과제 1/3 요약은 최종 제출 때 합치기)
- `out/dns.pcapng`: 실제 캡처가 성공한 뒤 생성됨
- `.capture-private/`: 원본 단기 캡처와 로컬 진단 정보. 제출하지 않음

## 측정

WSL Ubuntu에서 이 폴더로 이동한다. dnspython, dig, tshark가 필요하다.

```bash
sudo apt update
sudo apt install -y python3-dnspython dnsutils tshark
python3 task2_steering.py --collect --network home-wifi --report
```

Wi-Fi를 끄고 휴대폰 테더링 등 다른 실제 네트워크로 전환한 뒤:

```bash
python3 task2_steering.py --collect --network phone-hotspot --report
```

이미 수집한 첫 네트워크 자료는 JSON에 남는다. 같은 라벨로 재수집해도 원본을 보존하며, 보고서는 조합별 최신 측정만 비교한다.

## 실제 캡처

```bash
dumpcap -D
ip route
python3 capture_part_a.py --interface eth0
```

`eth0`는 예시다. 자신의 WSL 기본 경로가 사용하는 인터페이스 이름을 확인한다.
권한 오류가 나면 임의 캡처 파일을 만들지 말고 권한 설정을 확인한다.
캡처 시작 후 Task 1 리졸버를 실행하며, 20초 뒤 캡처를 닫는다.
제출본은 해당 리졸버의 질의 ID·상대 IP·질의 이름·RD=0에 해당하는 교환만 남긴다.
개인 정보가 섞인 원본은 `.capture-private`에만 보관한다.

Wireshark에서 `out/dns.pcapng`를 열고 다음을 확인해 직접 스크린샷을 저장한다.

1. 쿼리와 응답의 동일한 Transaction ID.
2. Answers=0이고 Authority에 NS가 있는 위임 응답.
3. Answer에 A가 있는 최종 응답.
4. 가장 큰 DNS 응답의 DNS 메시지 길이와 Ethernet 프레임 길이를 구분해 기록.

## 검증

```bash
python3 task2_steering.py --report
python3 test_tasks.py --task 2
```

테스트 통과만으로 두 네트워크 측정, 캡처 이미지, 보고서 해석까지 충족했다고 판단하지 않는다.
최종 제출에는 저장소의 `w03-dns` 폴더에 코드와 `out`을 넣고 커밋한다.
