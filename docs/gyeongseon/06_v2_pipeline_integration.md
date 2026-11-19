# 06. 사전 v2 분석 파이프라인 연결 기록

## 변경 목적

사전 v2는 이미 후보 정리 모듈에서 사용했지만, 11~14주차 분석과 사용자 조회의 기본값은 v1에 남아 있었다. 이 기록은 사전 v2를 기본값으로 바꾸고 concept 범주를 Apriori 항목에서 제외한 뒤의 재현 결과다.

## 적용 범위

| 경로 | 변경 |
| --- | --- |
| `src/normalization/dictionary.py` | v1과 v2 JSON 형식을 모두 읽도록 호환 처리 |
| `run_week11.py` | 기본 사전 v2 |
| `run_week12.py` | concept 제외 옵션과 제외 수 기록 |
| `run_week14.py` | 12주차와 같은 제외 조건으로 세그먼트·그래프 생성 |
| `run_week13.py`, `service/app.py`, `web_server.py` | 기본 사전 v2 |
| `src/agent/extract.py` | 사전 등록 공백 복합 표기 조립 |

## 전후 비교

| 항목 | 변경 전 | 변경 후 |
| --- | ---: | ---: |
| 분석 트랜잭션 | 17,796 | 15,296 |
| 저장 규칙 | 694 | 670 |
| 그래프 노드 | 94 | 88 |
| concept 제외 항목 | 적용 안 함 | 11,775개 |
| 기본 사전 | v1 | v2 |

트랜잭션 수가 줄어든 이유는 concept 표기만 있던 공고가 기술 집합이 비어 분석 대상에서 빠졌기 때문이다. 이것은 데이터 손실을 숨기는 변경이 아니며, `artifacts/week12_rule_comparison.json`의 `excluded_category_item_count`와 `excluded_empty_transactions`로 확인할 수 있다.

## 재현 명령

~~~powershell
python -m src.normalization.run_week11 --input data/raw/korean_it_recruit_postings.json --output data/processed/postings_normalized.jsonl --artifact-dir artifacts
python -m src.analysis.run_week12
python -m src.service.run_week13
python -m src.analysis.run_week14
python scripts/build_visualizations.py
python -m unittest discover -s tests -q
~~~

이 실행에서 148개 테스트가 통과했다. 실제 결과 파일은 `artifacts/week11_normalization_summary.json`, `artifacts/week12_all_rules.json`, `artifacts/week13_service_scenarios.json`, `artifacts/week14_skill_graph.json`이다.

## 검수·어휘 확장 판단

두 사람의 독립 판정이 필요한 검수 시트는 아직 비어 있다. 작성자가 두 명의 검수자 결과를 대신 기입하면 실제 사람 검수가 아니므로 이 작업에서는 채우지 않았다.

어휘 밖 표기는 자동으로 표준 사전에 넣지 않는다. `new_technology` 후보 9종과 빈번한 업무 약어는 표기만으로 기술 여부를 확정하기 어렵다. 사람 검수에서 기술명·조합 타당성을 판정한 뒤, 사전과 정답지의 변경 전후 수치를 함께 남기는 별도 변경으로 처리한다.
