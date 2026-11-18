# 11주차 실제 결과

## 실행 상태

- 상태: 완료
- 확인 일자: 2026-11-18
- 입력 행 수: 40,348
- 사전 버전: `tech-dictionary.v1`

## 정규화 결과

- 출발 배열: `final_techs`
- 출력 배열: `normalized_techs`
- 별칭 변환 수: 127
- 공고별 중복 제거 수: 0
- 사전에 없는 기술명 수: 142
- 원본 행·공고 식별자·`final_techs`는 유지했고 `normalized_techs`와 사전 버전만 추가했다.

## 구현 내용

- `configs/tech_dictionary.json`에 버전이 있는 기술명 사전과 별칭을 추가했다.
- `src/normalization/`은 알려진 별칭만 표준 표기로 변환하고 미등록 기술은 원문대로 보존한다.
- `configs/experiments.json`에 정규화 전후 동일 공고 집합 비교 계약을 추가했다. Apriori 파라미터는 12주차에서 확정한다.
- `src/llm/`에는 제공자 독립 계약과 fake provider만 있다. 실제 GLM 연결은 구현하지 않았다.

## 재현 명령

```powershell
python -m src.normalization.run_week11 --input data/raw/korean_it_recruit_postings.json --output data/processed/postings_normalized.jsonl
python -m unittest discover -s tests -v
```

## 12주차 인계

- 입력: `data/processed/postings_normalized.jsonl`, `artifacts/week11_normalization_summary.json`, `configs/tech_dictionary.json`
- 비교 조건: 동일 공고 식별자 집합, `final_techs`와 `normalized_techs`, 동일한 필터와 Apriori 파라미터
- 주의: 직무와 경력은 필터·세그먼트 메타데이터이며 itemset에는 포함하지 않는다.
