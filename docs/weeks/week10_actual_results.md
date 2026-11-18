# 10주차 실제 결과

## 실행 상태

- 상태: 입력 데이터 부재로 실제 품질 수치 산출 보류
- 확인 일자: 2026-11-18
- 점검 경로: `data/raw/`에는 `.gitkeep`만 존재하며, 분석 가능한 JSON·JSONL·NDJSON·CSV 원본은 발견되지 않았다.
- 수치: 실제 공고 행 수, ID 누락, 중복, 기술 필드 차이, 직무·경력 분포는 데이터를 만들지 않기 위해 기록하지 않았다.

## 구현한 10주차 계약

- `configs/data_scope.json`에서 입력 경로, `source + job_id` 중복 기준, `final_techs` 출발 필드, 빈 목록 및 경력 모호성 정책을 고정했다.
- `src/ingestion/`은 JSON, JSONL, NDJSON, CSV 원본을 읽고 원본 행을 보존한다. `source + job_id` 중복과 서로 다른 ID를 가진 동일 본문 의심 중복을 별도로 집계한다.
- `final_techs`와 `hard_skills`의 결측·집합 차이를 별도로 기록하며, 분석용 항목은 기술명만 사용하도록 명시했다.
- `src/service/contracts.py`에 필터, 근거 공고, 빈 결과의 응답 상태 초안을 정의했다. 규칙 계산·정규화·GLM 연결은 아직 구현하지 않았다.

## 재현 명령

```powershell
python -m src.ingestion.run_week10 --input data/raw/korean_it_recruit_postings.json --config configs/data_scope.json --output-dir artifacts
python -m unittest discover -s tests -v
```

입력 파일이 없는 상태에서 첫 번째 명령을 실행하면 `artifacts/week10_data_quality_summary.json`에 `blocked_missing_input`만 기록하고, 숫자나 표본을 생성하지 않는다.

## 실제 검증 결과

- `python -m unittest discover -s tests -v`: 통과 (3개 테스트)
- `python -m compileall -q src tests`: 통과
- `git diff --check`: 통과 (새 저장소의 초기 추적 전 파일에는 diff가 없음)

## 데이터 확보 후 필요한 작업

1. 승인된 단일 공개 데이터 export를 `data/raw/korean_it_recruit_postings.json`에 저장하거나 `--input`으로 전달한다.
2. 위 재현 명령을 실행하여 SHA-256, 행 수, 결측·중복·기술 필드 차이와 원문 대조 표본을 실제 결과로 생성한다.
3. `suspected_same_body_distinct_id_examples` 및 경력 라벨/원문 표본을 검토한 뒤, 확정 공고 식별자 집합을 11주차에 전달한다.

## 11주차 인계

- 입력: 생성된 `artifacts/week10_data_quality_summary.json`, `artifacts/week10_raw_text_samples.csv`, 그리고 검토를 마친 확정 공고 식별자 집합
- 제약: `final_techs`를 정규화 전 출발 배열로 사용한다. `hard_skills`는 대조용으로 보존한다. 빈 기술 목록은 품질 보고에는 남기되 Apriori 트랜잭션에서는 제외한다.
- GLM: provider 인터페이스와 mock만 허용되며 키, SDK, HTTP 요청은 추가하지 않는다.
