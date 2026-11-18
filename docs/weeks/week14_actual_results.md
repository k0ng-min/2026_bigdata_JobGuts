# 14주차 실제 결과

## 완료 범위

- CLI를 사용자 인터페이스로 사용한다. HTTP API와 GLM 실제 연결은 구현하지 않았다.
- `artifacts/week14_skill_graph.json`은 규칙의 support, confidence, interest를 엣지 속성으로 갖는 기술 그래프 데이터다.
- `artifacts/week14_segment_comparison.json`에는 제목·경력 라벨 기반 세그먼트 표본 수와 상위 3개 기술 조합을 기록했다.

## 통합 검증

- 정상 추천: `python -m src.service.app --skills TensorFlow`
- 규칙 없음: `python -m src.service.app --skills NotARealSkill`
- 필터 변경: `python -m src.service.app --skills TensorFlow --role frontend`
- 단위·통합 테스트: 8개 통과

정상 추천 응답에는 추천 기술, support, confidence, interest, 적용 필터, 실제 공고의 `source`, `job_id`, `title`이 포함된다. 규칙이 없으면 `no_rules`와 다음 행동을 반환한다.

## 세그먼트 기준

직무는 제목의 명시적 backend, frontend, fullstack 신호로 분류하고 나머지는 `other_tech`으로 처리했다. 경력은 원본 라벨을 entry, 1~3년차, 3~5년차, 5년이상, other로 변환했다. 이 기준은 재현 가능한 서비스 필터용 메타데이터이며, 원본의 공식 직무 분류는 아니다.
