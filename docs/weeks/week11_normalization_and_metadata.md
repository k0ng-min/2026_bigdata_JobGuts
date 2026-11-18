# 11주차 기술명 정규화와 메타데이터 확정

## 목표

동일 기술의 다른 표기를 통일하고 직무·경력 처리 기준을 확정한다. GLM은 인터페이스와 mock만 만들며 연결하지 않는다.

| 역할 | 작업 | 완료 기준 |
| --- | --- | --- |
| 데이터 | 10주차 공고 집합 고정 | 입력 공고 수와 제외 사유 추적 가능 |
| 정규화 | 사전, 별칭, 공고별 중복 제거, 원문 표본 검증 | 사전 버전·변환 수·예외·전후 기술명 수 기록 |
| 분석 | 전후 비교 실험 설정 고정 | 트랜잭션·파라미터 설정 준비 |
| 서비스 | provider interface, 요청·응답 schema, fake provider | GLM 없이 계약 테스트 가능 |

## 산출물과 검증

- `src/normalization/`, `configs/tech_dictionary.*`, 원본·정규화 기술 배열을 함께 가진 `data/processed/`
- `src/llm/` provider interface와 fake/mock만 추가한다. 네트워크 호출·키·SDK는 금지한다.
- `artifacts/week11_normalization_summary.*`, `docs/weeks/week11_actual_results.md`

정규화 배열에는 중복이 없어야 하며 원문·공고 식별자는 바뀌면 안 된다. 사전 버전이 표시된 전·후 트랜잭션과 실험 설정을 12주차에 전달한다.
