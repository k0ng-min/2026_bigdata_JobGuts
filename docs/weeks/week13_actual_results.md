# 13주차 실제 결과

## 실행 상태

- 상태: 완료
- 확인 일자: 2026-11-18
- 입력: `artifacts/week12_all_rules.json` (694개 규칙), `data/processed/postings_normalized.jsonl`

## 완료 범위

- 저장된 규칙을 읽는 조회 계층과 보유 기술 기반 CLI 응답을 구현했다. 조회 계층은 규칙을 재계산하지 않는다.
- 응답에는 추천 기술의 지표, 적용 필터, 최대 3개의 실제 근거 공고 식별자와 제목을 포함한다.
- 규칙이 없으면 `no_rules` 상태와 다음 행동을 반환한다.
- 근거 공고가 필터를 만족하지 않으면 `insufficient_sample` 상태를 반환한다.
- 실제 GLM 연결은 포함하지 않았다.

## 검증한 응답 경로

`artifacts/week13_service_scenarios.json`에 아래 5개 시나리오의 질의와 응답을 그대로 기록한다.

| 시나리오 | 질의 | 응답 상태 |
| --- | --- | --- |
| `normal` | `--skills TensorFlow` | `ok` |
| `no_rules` | `--skills NotARealSkill` | `no_rules` |
| `role_filtered` | `--skills TensorFlow --role frontend` | `ok` |
| `entry_eligible` | `--skills TensorFlow --entry-eligible` | `ok` |
| `insufficient_sample` | `--skills .NET --role frontend --experience 1~3년차` | `insufficient_sample` |

직무·경력 필터는 저장된 규칙의 지표를 다시 계산하지 않는다. 필터는 근거 공고 선택에만 적용되므로,
필터를 바꿔도 support·confidence·interest는 전체 세그먼트 기준 값으로 유지된다.

## 알려진 차이

- `insufficient_sample` 응답에는 `next_action` 필드가 없다. `no_rules` 응답에만 포함된다. 두 경로를 모두 안내 문구로 처리하려면 `src/retrieval/repository.py`를 수정해야 한다.

## 재현 명령

```powershell
python -m src.service.run_week13
python -m src.service.app --skills TensorFlow
python -m unittest discover -s tests -v
```

## 수정 이력

- 2026-11-18: 산출물 생성 모듈 `src/service/run_week13.py`를 추가하고 `artifacts/week13_service_scenarios.json`을 현재 데이터 기준으로 다시 만들었다. 이전 판의 산출물은 트랜잭션 18,163 기준이었고, 생성 코드가 저장소에 없어 재현할 수 없었다.
- 2026-11-18: 재현 명령의 예시 기술을 `LlamaIndex`에서 `TensorFlow`로 바꿨다. `LlamaIndex`는 동일 본문 중복 제거 이후 `LangChain`과의 동시 등장이 93회에서 88회로 줄어 최소 support 횟수 89에 미달하여, 현재 데이터에서는 규칙이 존재하지 않는다.
