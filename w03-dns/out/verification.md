# 검증 기록

- `python3 test_steering_unit.py`: 3 tests, OK.
- `python3 test_tasks.py --task 2`: 5 passed, 0 failed, 0 skipped.
- 실제 캡처: 질문 3개, 응답 3개. 위임 응답과 권한 A 응답을 직접 확인.
- 집 Wi-Fi와 다른 Wi-Fi에서 12개 사이트 × 3개 리졸버를 측정했다. 재시도 전 실패 기록도 chains.json에 보존했다.
- 사용자가 직접 저장한 화면 이미지 3장을 확인하여 dns-query.png, dns-referral.png, dns-answer.png로 포함했다. 각각 패킷 #1, #2, #6과 일치한다. DNS 상세 트리는 접혀 있어 상세 레코드 수치는 원본 캡처 분석으로 확인했다.

## 제공 테스트의 호환성 수정

이 환경의 TShark는 `dns.flags.response`를 `False/True`로 출력한다.
원본 test_tasks.py는 `0/1`만 세므로 올바른 캡처도 질문과 응답이 0개라고 잘못 판단한다.
작업 폴더의 test_tasks.py에서 두 Boolean 표현을 모두 인식하도록 해당 두 줄만 수정했다.
캡처에 질문과 응답이 둘 다 있어야 한다는 검증 조건은 바꾸지 않았다.
bench.py는 수정하지 않았다. 과제 1/3 전체 테스트를 통과했다는 의미는 아니다.
