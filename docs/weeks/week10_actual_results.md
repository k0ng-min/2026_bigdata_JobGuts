# 10주차 실제 결과

## 실행 상태

- 상태: 완료
- 확인 일자: 2026-11-18
- 입력 파일: `data/raw/korean_it_recruit_postings.json`
- 원본: `young-cc/korean-it-recruit-dataset`의 `master_merged_v5.json`
- 파일 SHA-256: `dc7cc15b1ee80dbf5f959095ee78aad0e8dd39d5156cf694e60591aa1bd9a58f`
- 입력 행 수: 40,348

## 품질 점검 결과

- `source + job_id` 누락 행: 0
- `source + job_id` 중복 그룹: 777, 첫 행을 제외한 중복 행: 777
- 서로 다른 식별자에서 본문이 같은 의심 중복 그룹: 744, 해당 행: 1,707
- `raw_text` 결측: 0
- `final_techs` 빈 목록 또는 결측: 21,560
- `hard_skills` 빈 목록 또는 결측: 9,268
- 두 기술 필드가 모두 존재하는 행: 40,348
- 두 기술 집합이 같은 행: 8,886, 다른 행: 31,462

## 확정한 기준

- 정규화 전 출발 기술 배열은 `final_techs`다. `hard_skills`는 대조용으로 보존한다.
- 빈 기술 목록은 품질 보고에는 남기고 Apriori 트랜잭션에서는 제외한다.
- 원본에는 별도 직무 분류 열이 없으므로 제목을 직무 라벨로 사용하지 않는다. 직무 세그먼트는 이후 별도 기준으로 추출·검토한다.
- `experience_level`이 비어 있거나 모호한 경우에는 임의로 신입으로 분류하지 않는다.

## 재현 명령

```powershell
python -m src.ingestion.run_week10 --input data/raw/korean_it_recruit_postings.json --config configs/data_scope.json --output-dir artifacts
python -m unittest discover -s tests -v
```

## 11주차 인계

- 입력: `artifacts/week10_data_quality_summary.json`, `artifacts/week10_raw_text_samples.csv`, 원본 JSON 파일
- 주의: 중복 제거 확정은 원문 검토가 필요한 단계다. 현재 결과는 자동 집계이며 행을 삭제하지 않았다.

## 수정 이력

- 2026-11-18: 이 문서의 수치는 재실행 결과와 전 항목 일치했다(입력 파일 SHA-256 포함). 변경하지 않았다.
- 2026-11-18: "`experience_level`이 비어 있거나 모호한 경우에는 임의로 신입으로 분류하지 않는다"는 기준이 11주차 코드에서 지켜지지 않고 있었다(`경력무관` 6,597건이 `entry`로 분류). `src/normalization/metadata.py`를 고쳐 원본 라벨을 그대로 유지하도록 했고, 신입 지원 가능 여부는 `entry_eligible` 필드로 분리했다. 자세한 내용은 [02_foundation_fixes.md](../gyeongseon/02_foundation_fixes.md)에 있다.
