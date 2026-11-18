# JobGuts

국내 IT 채용공고에서 함께 등장하는 기술을 분석하고, 사용자의 보유 기술과 연관된 기술을 근거 공고 및 지표와 함께 제시하는 프로젝트입니다.

## 팀

- 팀명: JOBGUTS
- 팀장: 서동균 (2021270664)
- 팀원: 김경선 (2022270656), 정비호 (2022270622), 설경민 (2022270643)

## 데이터셋

분석에는 [young-cc/korean-it-recruit-dataset](https://huggingface.co/datasets/young-cc/korean-it-recruit-dataset)을 사용합니다. 데이터셋 원본은 CC BY 4.0이며, 대용량 원본은 이 저장소에 커밋하지 않습니다. 내려받기와 변환 방법은 [데이터 준비 안내](docs/data_source.md)를 참고하세요.

## 문서

- [역할 분담 및 공통 운영 규칙](docs/01_team_roles_and_workflow.md)
- [데이터 준비 안내](docs/data_source.md)
- [10주차 계획](docs/weeks/week10_data_scope_and_quality.md)
- [11주차 계획](docs/weeks/week11_normalization_and_metadata.md)
- [12주차 계획](docs/weeks/week12_association_rules.md)
- [13주차 계획](docs/weeks/week13_retrieval_and_service_integration.md)
- [14주차 계획](docs/weeks/week14_segment_comparison_and_validation.md)
- [최종 보고서](docs/final_report.md)

## 저장소 구조

```text
.
├── data/
│   ├── raw/                 # 원본 데이터, Git 추적 제외
│   ├── interim/             # 단계별 중간 산출물, Git 추적 제외
│   └── processed/           # 분석 확정 데이터와 메타데이터
├── docs/                    # 계획, 기준, 실행 및 검증 기록
│   └── weeks/               # 주차별 상세 작업 명세
├── notebooks/               # 탐색용 노트북, 운영 로직은 src로 이관
├── src/
│   ├── ingestion/           # 데이터 로딩 및 스키마 검증
│   ├── normalization/       # 기술명 사전 및 정규화
│   ├── analysis/            # Apriori, 지표, 세그먼트 비교
│   ├── retrieval/           # 규칙 및 근거 공고 조회
│   ├── service/             # API 또는 UI 계층
│   └── llm/                 # 인터페이스만 정의, GLM 연결은 최종 단계
├── tests/                   # 단위 및 통합 테스트
├── configs/                 # 데이터 범위, 실험, 서비스 설정
├── artifacts/               # Git 추적 가능한 표·그래프·실행 요약
└── scripts/                 # 재현 실행 및 검증 명령
```

상세 구현 순서와 산출물 기준은 `docs/`의 문서를 따른다.

## 실행

원본 데이터를 준비한 뒤 `./scripts/run_pipeline.ps1`을 실행하면 품질 점검, 정규화, 규칙 분석, 테스트와 CLI 추천 예시를 순서대로 재현한다.
