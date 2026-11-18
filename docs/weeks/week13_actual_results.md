# 13주차 실제 결과

- 저장된 규칙을 읽는 조회 계층과 보유 기술 기반 CLI 응답을 구현했다.
- 응답에는 추천 기술의 지표, 적용 필터, 최대 3개의 실제 근거 공고 식별자와 제목을 포함한다.
- 규칙 없음은 `no_rules`, 근거 부족은 `insufficient_sample` 상태와 다음 행동을 반환한다.
- 실제 GLM 연결은 포함하지 않았다.

재현 명령: `python -m src.service.app --skills LlamaIndex`
