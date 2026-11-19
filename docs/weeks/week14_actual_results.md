# 14주차 실제 결과

## 완료 범위

- 사용자 인터페이스는 CLI가 기준이며, `src/service/web_server.py`에 로컬 확인용 웹 화면이 함께 있다. 외부 공개 API와 GLM 실제 연결은 구현하지 않았다.
- `artifacts/week14_skill_graph.json`은 규칙의 support, confidence, interest를 엣지 속성으로 갖는 기술 그래프 데이터다. 노드 94개, 엣지 694개로 전체 규칙을 보존한다.
- `artifacts/week14_segment_comparison.json`에는 세그먼트별 표본 수와 상위 3개 기술 조합을 기록했다.

## 기준 집합

세그먼트 표본 수와 기술 조합 빈도는 12주차가 규칙을 캐는 **동일한 적격 공고 집합(17,796건)** 에서 계산한다.
`src/analysis/run_week14.py`는 이 수가 `artifacts/week12_rule_comparison.json`의 트랜잭션 수와 다르면 실행을 중단한다.
따라서 두 주차의 숫자는 항상 같은 모집단을 가리킨다.

- 적격 공고: 17,796건
- 세그먼트 수: 21개 (`job_role` 4종 × `experience_segment` 6종 중 실제로 존재하는 조합)
- 신입 지원 가능(`신입` 또는 `경력무관`) 공고: 3,536건

상위 3개 기술 조합:

| 조합 | 공고 수 |
| --- | --- |
| AWS + Java + Spring | 724 |
| Java + JavaScript + Spring | 710 |
| CSS + HTML + JavaScript | 647 |

## 통합 검증

- 정상 추천: `python -m src.service.app --skills TensorFlow`
- 규칙 없음: `python -m src.service.app --skills NotARealSkill`
- 필터 변경: `python -m src.service.app --skills TensorFlow --role frontend`
- 신입 지원 가능: `python -m src.service.app --skills TensorFlow --entry-eligible`
- 근거 부족: `python -m src.service.app --skills .NET --role frontend --experience 1~3년차`
- 단위·통합 테스트: 20개 통과

정상 추천 응답에는 추천 기술, support, confidence, interest, 적용 필터, 실제 공고의 `source`, `job_id`, `title`이 포함된다. 규칙이 없으면 `no_rules`와 다음 행동을 반환한다.

## 세그먼트 기준

직무는 제목의 명시적 backend, frontend, fullstack 신호로 분류하고 나머지는 `other_tech`으로 처리했다.
제목이 없는 공고가 25,950건(64.3%)이어서 전체의 94.1%가 `other_tech`로 남는다. 직무별 비교는 이 제약을 전제로 해석해야 한다.

경력은 원본 라벨을 **변환하지 않고 그대로** 유지한다. `신입`, `경력무관`, `1~3년차`, `3~5년차`, `5년이상`이 각각 독립 세그먼트이며,
라벨이 없거나 인식되지 않으면 `unknown`이다. 신입 대상 추천에 필요한 "신입 지원 가능" 여부는
`entry_eligible` 필드(`신입` 또는 `경력무관`)로 따로 제공한다.

이 기준은 재현 가능한 서비스 필터용 메타데이터이며, 원본의 공식 직무 분류는 아니다.

## 재현 명령

```powershell
python -m src.analysis.run_week14
python -m unittest discover -s tests -v
```

## 수정 이력

- 2026-11-18: 산출물 생성 모듈 `src/analysis/run_week14.py`를 추가했다. 이전에는 `src/analysis/graph.py`의 `graph_from_rules()`가 어디에서도 호출되지 않았고, 두 산출물을 만드는 코드가 저장소에 없었다.
- 2026-11-18: 기준 집합을 12주차와 동일한 17,796건으로 통일했다. 이전 판의 세그먼트 합계는 18,788건(중복 제거 없음)이어서 같은 보고서 안에 모집단이 두 개 섞여 있었다.
- 2026-11-18: `top_triples`를 다시 계산했다. 이전 판의 수치(예: `C + C++ + Python` 296)는 기술 필드 3종과 중복 정책 2종의 조합 6가지 중 어느 것으로도 재현되지 않아(최대 50개 중 1개 일치), 억지로 맞추지 않고 현재 기준으로 교체했다.
- 2026-11-18: 그래프가 상위 50개 규칙만 담던 문제를 함께 해소해 전체 694개 엣지를 보존한다.
