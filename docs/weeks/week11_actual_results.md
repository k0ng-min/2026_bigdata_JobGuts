# 11주차 실제 결과

## 실행 상태

- 상태: 구현 완료, 실제 정규화 실행은 입력 데이터 부재로 보류
- 확인 일자: 2026-11-18
- 입력 상태: `data/raw/korean_it_recruit_postings.jsonl`이 아직 없어 변환 수·미등록 기술 수·전후 기술명 수를 생성하지 않았다.

## 구현 내용

- `configs/tech_dictionary.json`에 버전이 있는 기술명 사전과 별칭을 추가했다.
- `src/normalization/`은 `final_techs`를 출발 배열로 사용하고, 원본 배열·원본 행·공고 식별자는 보존한 채 `normalized_techs`를 추가한다.
- 별칭 변환, 공고별 중복 제거, 미등록 기술 보존을 분리해 기록한다.
- `configs/experiments.json`에 정규화 전후 동일 공고 집합 비교 계약을 추가했다. Apriori 파라미터는 실제 10주차 품질 결과가 나온 뒤에 확정한다.
- `src/llm/`에는 제공자 독립 계약과 fake provider만 있다. 실제 GLM 연결은 구현하지 않았다.

## 재현 명령

```powershell
python -m src.normalization.run_week11
python -m unittest discover -s tests -v
```

입력 파일이 없으면 첫 번째 명령은 `artifacts/week11_normalization_summary.json`에 `blocked_missing_input` 상태만 기록한다.

## 12주차 인계

- 입력: `data/processed/postings_normalized.jsonl`, `artifacts/week11_normalization_summary.json`, `configs/tech_dictionary.json`
- 비교 조건: 동일 공고 식별자 집합, `final_techs`와 `normalized_techs`, 동일한 필터와 Apriori 파라미터
- 주의: 직무와 경력은 필터·세그먼트 메타데이터이며 itemset에는 포함하지 않는다.
