# 데이터 준비 안내

## 원본 데이터셋

- 이름: `young-cc/korean-it-recruit-dataset`
- 주소: <https://huggingface.co/datasets/young-cc/korean-it-recruit-dataset>
- 선택한 원본 파일: `master_merged_v5.json`
- 라이선스: CC BY 4.0

분석에는 `source`, `job_id`, `raw_text`, `experience_level`, `final_techs`, `hard_skills` 열을 사용한다. 원본 데이터와 변환 중간 파일은 Git에 커밋하지 않는다.

## 준비 방법

아래 명령으로 공개 원본을 프로젝트의 Git 제외 경로에 저장한다.

```powershell
Invoke-WebRequest -Uri "https://huggingface.co/datasets/young-cc/korean-it-recruit-dataset/resolve/main/master_merged_v5.json?download=true" -OutFile data/raw/korean_it_recruit_postings.json
```

그 다음 품질 점검을 실행한다.

```powershell
python -m src.ingestion.run_week10 --input data/raw/korean_it_recruit_postings.json --config configs/data_scope.json --output-dir artifacts
```

생성되는 품질 요약에는 입력 파일 SHA-256, 파일 크기, 행 수와 적용한 범위 기준이 함께 남는다. 데이터셋이 갱신되면 새 export를 만들고 해당 요약을 다시 생성한다.
