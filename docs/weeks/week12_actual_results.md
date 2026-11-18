# 12주차 실제 결과

## 실행 상태

- 상태: 완료
- 입력: `data/processed/postings_normalized.jsonl` (40,348행)
- 세그먼트: 직무·경력 구분 없이 전체 공고 집합
- 중복 기준: 같은 `source + job_id`는 첫 행만 유지하고, 서로 다른 ID의 동일 본문은 자동 제외하지 않았다.

## 실험 설정과 결과

- 최소 support: 0.005
- 최소 confidence: 0.2
- 최대 itemset 크기: 2
- 빈 `final_techs`와 키 중복을 제외한 트랜잭션: 18,163
- 키 중복 제외 행: 777
- 빈 기술 목록 제외 행: 21,408
- 정규화 전 규칙 수: 707
- 정규화 후 규칙 수: 707
- 전후 공통 규칙 수: 707

`interest(A -> B)`는 같은 전체 세그먼트에서 `confidence(A -> B) - P(B)`로 계산했다. 각 규칙에는 support 수, support, confidence, 결과 기술의 출현 확률, interest, 트랜잭션 수를 기록했다.

## 해석과 한계

- 현재 사전의 별칭 변환은 127건이었으나, 이 임계값에서 통과한 규칙 집합 수는 변하지 않았다. 이는 사전 효과가 없다는 뜻이 아니라, 현재 사전 범위와 임계값에서 상위 규칙의 포함 여부가 같았다는 뜻이다.
- 원본에는 직무 분류 열이 없어 이 결과는 전체 공고 기준이다. 직무별 비교는 제목·원문 기반 직무 분류 기준을 확정한 뒤 수행한다.
- 근거 공고 식별자 연결과 사용자 필터 조회는 13주차에서 구현한다.

## 재현 명령

```powershell
python -m src.analysis.run_week12
python -m unittest discover -s tests -v
```

## 13주차 인계

- 입력: `artifacts/week12_rule_comparison.json`, `artifacts/week12_top_rules.json`, 정규화된 공고 파일
- 규칙 조회는 분석 결과를 재계산하지 않고 저장된 규칙과 공고 식별자를 조회해야 한다.
- 결과가 없거나 표본이 부족할 때의 상태와 다음 행동을 응답에 포함해야 한다.
