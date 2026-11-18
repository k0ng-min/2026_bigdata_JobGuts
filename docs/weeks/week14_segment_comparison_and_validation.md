# 14주차 세그먼트 비교와 통합 검증

## 목표

표본이 충분한 직무·경력 집단별 결과를 비교하고 기술 연결 그래프 및 간단한 화면 또는 API를 완성한다.

| 역할 | 작업 | 완료 기준 |
| --- | --- | --- |
| 데이터 | 집단별 공고 수·제외 사유·표본 부족 표시 | 비교 가능 여부를 수치로 설명 |
| 정규화 | 세그먼트별 사전 적용·예외 점검 | 사전 버전과 미검토 항목 명시 |
| 분석 | 집단별 규칙 비교·그래프 데이터 생성 | 지표·표본·필터가 그래프와 연결 |
| 서비스 | UI/API 통합, mock 기반 전체 흐름 | 모든 시나리오 재현 |

## 산출물

- `src/analysis/` 세그먼트 비교·그래프 데이터, `src/service/` 표시/반환 계층
- `artifacts/week14_segment_comparison.*`, `artifacts/week14_skill_graph.*`, `artifacts/week14_end_to_end_validation.*`
- `docs/weeks/week14_actual_results.md`

## 검증 및 GLM 인계

정상 추천, 규칙 없음, 표본 부족, 미등록 기술, 필터 변경을 통합 테스트한다. 그래프의 모든 엣지는 규칙 테이블의 지표·세그먼트와 연결돼야 한다. GLM 최종 통합에는 provider interface, schema, mock contract test, 환경변수 이름, 오류 처리 정책만 넘긴다. 실제 키·모델명·SDK·HTTP·스트리밍은 그 별도 단계에서만 추가한다.
