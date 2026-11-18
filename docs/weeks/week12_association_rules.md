# 12주차 Apriori와 연관규칙 분석

## 목표

정규화 전후 동일 데이터에서 Apriori와 연관규칙을 실행하고 support, confidence, interest를 비교한다.

| 역할 | 작업 | 완료 기준 |
| --- | --- | --- |
| 데이터 | 입력 집합·필터·세그먼트별 표본 수 고정 | 데이터 버전과 공고 수 기록 |
| 정규화 | 사전 버전별 트랜잭션 제공 | 전후 비교 공고 식별자 집합 동일 |
| 분석 | itemset·규칙·지표·비교표 구현 | 계산 근거·파라미터 재현 가능 |
| 서비스 | 규칙 조회 DTO와 mock 응답 | 결과를 표현 가능 |

## 산출물

- `src/analysis/` 트랜잭션, Apriori, 규칙, 지표
- `configs/experiments.*` support/confidence/길이/세그먼트 설정
- `artifacts/week12_rule_comparison.*`, `artifacts/week12_top_rules.*`
- 고정 fixture에서 기대 규칙과 interest를 검증하는 테스트
- `docs/weeks/week12_actual_results.md`

## 계산 규칙과 인계

한 공고는 하나의 중복 없는 기술 트랜잭션이다. `interest(A -> B) = confidence(A -> B) - P(B)`의 `P(B)`는 같은 세그먼트에서 계산한다. 낮은 표본·support와 편향 가능성을 기록한다. 버전·세그먼트·파라미터가 명시된 규칙 테이블과 근거 공고 키를 13주차에 전달한다.
