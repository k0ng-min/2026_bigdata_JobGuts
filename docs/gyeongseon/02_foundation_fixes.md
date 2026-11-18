# 02. 기반 수정 (gyeongseon)

- 작업 일자: 2026-11-18
- 작업 브랜치: `gyeongseon`
- 시작 커밋: `5482b2a style: refine local dashboard`
- 근거 문서: [01_baseline_check.md](01_baseline_check.md)
- 테스트: **8개 → 20개**, 전부 통과 (실패 0)
- 팀 합의: 각자 만든 버전 중 더 나은 쪽을 채택하기로 하여, 경민 님 파일도 이 브랜치에서 수정했습니다.

## 커밋 목록

| 커밋 | 내용 |
| --- | --- |
| `bbd7ad2` | 연관규칙 694개 전체 저장 (상위 50개 절단 제거) |
| `d80fe67` | `경력무관`을 `신입`으로 바꾸던 문제 수정 |
| `19470d5` | 13·14주차 산출물 생성 코드 신설 및 재생성 |
| `b8fdb36` | 낡은 수치 문서 갱신 + 보고서가 산출물에서 숫자를 읽도록 변경 |

## 전후 숫자 한눈에 보기

| 항목 | 이전 | 이후 |
| --- | ---: | ---: |
| 저장되는 규칙 수 | 50 | **694** |
| 추천 가능한 선행 기술 | 33종 | **94종** |
| `신입` 세그먼트 공고 수 | 7,151 (중 실제 신입 554) | **554** |
| `경력무관` 세그먼트 | 없음 (`entry`에 흡수) | **6,597 (독립)** |
| 신입 지원 가능 공고 (`entry_eligible`) | 필드 없음 | **7,151** |
| 기술 그래프 노드 · 엣지 | 46 · 50 | **94 · 694** |
| 14주차 기준 공고 수 | 18,788 (12주차와 불일치) | **17,796 (12주차와 동일)** |
| 13·14주차 생성 코드 | 없음 | **있음** |
| 12주차 문서의 트랜잭션 · 규칙 | 18,163 · 707 | **17,796 · 694** |
| 주차 보고서의 숫자 | 하드코딩 | **산출물에서 읽음** |
| 테스트 | 8개 | **20개** |

---

# 수정 1: 규칙 694개 중 50개만 저장되던 문제

## 무엇이 문제였나

`src/analysis/run_week12.py`의 마지막 줄이 이랬습니다.

```python
top_rules_path.write_text(json.dumps({"raw": raw_rules[:50], "normalized": normalized_rules[:50]}, ...))
```

`[:50]`은 "앞에서 50개만 잘라내라"는 뜻입니다. 694개를 계산해 놓고 50개만 파일에 적은 겁니다.
그리고 조회 계층(`src/retrieval/repository.py`)은 **이 파일을 전체 규칙으로 믿고** 읽었습니다.

쉽게 말해 이런 상황이었습니다.

```
계산:  694개 규칙  ──[:50]──>  파일: 50개  ──>  서비스: 50개만 보고 추천
                      ↑
                 644개가 여기서 사라짐
```

## 왜 심각했나

규칙은 `interest`(의외성) 높은 순으로 정렬됩니다. 그래서 상위 50개는 **드물지만 의외성이 큰 조합**으로 채워지고,
가장 흔한 기술은 뒤로 밀려 잘려 나갔습니다. 실제로 이런 기술들이 전부 `no_rules`로 응답됐습니다.

| 기술 | 등장 공고 수 | 이전 | 이후 |
| --- | ---: | --- | --- |
| AI | 5,549 | `no_rules` | 추천 가능 |
| Python | 4,747 | `no_rules` | 추천 가능 |
| Java | 4,120 | `no_rules` | 추천 가능 |
| AWS | 3,375 | `no_rules` | 추천 가능 |
| JavaScript | 3,184 | `no_rules` | 추천 가능 |
| Linux | 2,777 | `no_rules` | 추천 가능 |

**가장 많이 쓰이는 기술 6개가 모두 작동하지 않았습니다.** 사용자가 "저 파이썬 할 줄 알아요"라고 입력하면
추천이 하나도 안 나오는 상태였습니다.

## 무엇을 고쳤나

"전체 저장"과 "화면에 보여줄 상위 N개"를 **파일 두 개로 분리**했습니다.

| 파일 | 역할 | 규칙 수 |
| --- | --- | ---: |
| `artifacts/week12_all_rules.json` (신규) | 분석 결과 전체. 서비스가 읽는 파일 | 694 |
| `artifacts/week12_top_rules.json` (기존) | 보고용 미리보기. `--top-n`으로 조절 | 50 |

```bash
python -m src.analysis.run_week12            # 상위 미리보기 50개 (기본값)
python -m src.analysis.run_week12 --top-n 20 # 미리보기만 20개로, 전체 694개는 그대로
```

미리보기 파일에도 `rule_count`와 `source_artifact`를 같이 적어, **이 파일이 전체가 아니라는 사실이 파일 안에 드러나게** 했습니다.
이전에는 50개가 전부인지 잘린 것인지 파일만 봐서는 알 수 없었습니다.

## 수정한 파일

| 파일 | 변경 |
| --- | --- |
| `src/analysis/run_week12.py` | `--top-n` 옵션 추가, 전체 규칙 파일 분리 저장 |
| `src/service/app.py` | 기본 규칙 파일을 `week12_all_rules.json`으로 |
| `src/service/web_server.py` | 같음 |
| `tests/test_week12_cli.py` (신규) | 절단 여부 검증 2건 |

## 결과

```
추천 가능한 선행 기술: 33종 -> 94종 (+61종)
```

새로 가능해진 61종에는 `AI`, `Python`, `Java`, `AWS`, `JavaScript`, `Linux`, `React`, `Git`, `C++`,
`Docker`, `SQL`, `TypeScript`, `Kubernetes`, `MySQL` 등 상위 빈출 기술이 모두 포함됩니다.

---

# 수정 2: `경력무관`이 `신입`으로 바뀌던 문제

## 무엇이 문제였나

`src/normalization/metadata.py`가 이랬습니다.

```python
if value in {"신입", "경력무관"}: return "entry", "source_label"
```

`신입`과 `경력무관`을 **같은 하나의 값 `entry`로 합쳐** 버렸습니다. 그런데 이 둘은 뜻이 다릅니다.

- `신입` = 신입을 뽑는 공고
- `경력무관` = 경력을 따지지 않는 공고 (10년 경력자도 지원 가능)

합쳐진 결과 `entry` 세그먼트 7,151건 중 **실제 신입 공고는 554건(7.7%)뿐**이고
나머지 6,597건(92.3%)은 경력무관 공고였습니다. "신입 추천"을 뽑으면 92%가 신입 공고가 아니었던 셈입니다.

이건 단순 실수가 아니라 **팀이 스스로 정한 원칙을 어긴 것**이었습니다.

| 위치 | 선언된 원칙 |
| --- | --- |
| `docs/weeks/week10_actual_results.md` | "`experience_level`이 비어 있거나 모호한 경우에는 임의로 신입으로 분류하지 않는다" |
| `configs/data_scope.json` | `"retain_raw_label_and_text; ambiguous_or_conflicting_values_are_unknown_or_needs_review"` |
| `src/ingestion/quality.py:104` | `"preserve unknown or needs_review; never infer entry-level"` |

10주차 코드는 자기 출력물에 "never infer entry-level"이라고 적고 있었고, 11주차 코드가 바로 그걸 하고 있었습니다.

## 무엇을 고쳤나

팀 10주차 보고서 계획("신입용 추천은 신입 지원 가능 또는 경력무관 공고를 사용")에 맞춰 **두 가지를 분리**했습니다.

1. **경력 라벨은 원본 그대로** — 변환하지 않고 그대로 보존
2. **"신입 지원 가능" 여부는 별도 필드** — `entry_eligible` (신입 또는 경력무관이면 `true`)

```python
KNOWN_EXPERIENCE_LABELS = ("신입", "경력무관", "1~3년차", "3~5년차", "5년이상")
ENTRY_ELIGIBLE_LABELS = ("신입", "경력무관")

def classify_experience(label):
    """원본 라벨을 그대로 반환한다. 서로 다른 라벨을 합치지 않는다."""
    value = (label or "").strip()
    if value in KNOWN_EXPERIENCE_LABELS: return value, "source_label"
    return "unknown", "missing_or_unrecognized_label"

def is_entry_eligible(label):
    """원본 라벨이 신입 지원 가능을 명시한 경우에만 True."""
    return (label or "").strip() in ENTRY_ELIGIBLE_LABELS
```

이렇게 하면 **정보가 사라지지 않습니다.** 신입만 보고 싶으면 `--experience 신입`,
신입이 지원할 수 있는 공고를 전부 보고 싶으면 `--entry-eligible`을 쓰면 됩니다.

## 전후 세그먼트 분포

| 세그먼트 | 이전 | 이후 |
| --- | ---: | ---: |
| `entry` | 7,151 | — (삭제) |
| `신입` | — | **554** |
| `경력무관` | — | **6,597** |
| `1~3년차` | 1,692 | 1,692 |
| `3~5년차` | 2,589 | 2,589 |
| `5년이상` | 2,966 | 2,966 |
| `other` | 25,950 | — |
| `unknown` | — | **25,950** |
| **`entry_eligible = true`** | 필드 없음 | **7,151** |

`other` → `unknown` 이름 변경은 `configs/data_scope.json`이 선언한 `..._are_unknown_or_needs_review`
문구에 맞춘 것입니다. 숫자는 그대로입니다.

## 새 필터 사용법

```bash
# 전체
python -m src.service.app --skills Java
#   근거: 355145 Java 백엔드/웹 개발자 (신입) / 360349 AX팀 풀스택 개발자 Junior / 314893 Java 백엔드 개발자 (1년~8년)

# 신입이 지원할 수 있는 공고만 (신입 + 경력무관)
python -m src.service.app --skills Java --entry-eligible
#   근거: 355145 Java 백엔드/웹 개발자 (신입) / 360817 주니어 풀스택 개발자 / 353354 Back-end

# 경력무관만 따로 보고 싶을 때
python -m src.service.app --skills Java --experience 경력무관
```

## 수정한 파일

| 파일 | 변경 |
| --- | --- |
| `src/normalization/metadata.py` | 라벨 원본 보존, `is_entry_eligible()` 추가 |
| `src/normalization/run_week11.py` | `entry_eligible` 필드 기록, 세그먼트 집계를 요약에 추가 |
| `src/retrieval/repository.py` | `entry_eligible` 필터 추가 |
| `src/service/app.py` | `--entry-eligible` 옵션 추가 |
| `tests/test_metadata.py` (신규) | 라벨 보존·미추론·eligibility·필터 검증 5건 |

규칙 수치(694개)는 영향받지 않았습니다. 경력 필드는 Apriori 항목이 아니기 때문입니다.

---

# 수정 3: 13·14주차 산출물 생성 코드 신설

## 무엇이 문제였나

세 산출물을 만드는 코드가 **저장소에 아예 없었습니다.**

| 산출물 | 상태 |
| --- | --- |
| `week13_service_scenarios.json` | 생성 코드 없음, 트랜잭션 18,163 기준 (구버전) |
| `week14_skill_graph.json` | 생성 코드 없음, 상위 50개 규칙만 담김 |
| `week14_segment_comparison.json` | 생성 코드 없음, 기준 집합이 12주차와 불일치 |

`src/analysis/graph.py`의 `graph_from_rules()` 함수는 **어디에서도 호출되지 않았습니다.**
즉 커밋되지 않은 임시 스크립트로 파일을 만들고, 그 스크립트는 사라진 상태였습니다.

데이터가 바뀌면 이 파일들을 다시 만들 방법이 없고, 숫자가 맞는지 검증할 방법도 없었습니다.

## 무엇을 만들었나

| 파일 | 역할 |
| --- | --- |
| `src/service/run_week13.py` (신규) | 5개 응답 경로를 실행해 질의·응답을 그대로 기록 |
| `src/analysis/run_week14.py` (신규) | 세그먼트 표본·상위 조합·기술 그래프 생성 |

`scripts/run_pipeline.ps1`에도 두 단계를 끼워 넣어, 이제 파이프라인 한 번으로 10~14주차 전부가 재생성됩니다.

```powershell
python -m src.ingestion.run_week10 ...
python -m src.normalization.run_week11 ...
python -m src.analysis.run_week12
python -m src.service.run_week13      # 추가
python -m src.analysis.run_week14     # 추가
python -m unittest discover -s tests -v
python -m src.service.app --skills TensorFlow
```

## 기준 집합을 하나로 통일 (중요)

이전에는 같은 보고서 안에 **모집단이 두 개** 섞여 있었습니다.

| 숫자 | 뜻 |
| ---: | --- |
| 17,796 | 12주차 규칙 분석의 트랜잭션 (ID 중복·동일 본문·빈 목록 제외) |
| 18,788 | 14주차 세그먼트 합계 (중복 제거를 **하지 않은** 집합) |

두 숫자가 섞이면 "규칙의 support 0.03"과 "세그먼트 표본 218건"이 서로 다른 분모를 쓰게 되어
비율 해석이 어긋납니다. 그래서 14주차를 **12주차와 동일한 17,796건**으로 통일했습니다.

그리고 다시 어긋나는 일을 막기 위해, 실행 시 교차 검증을 넣어 **수가 다르면 즉시 중단**하게 했습니다.

```python
expected = json.loads(args.comparison.read_text())["normalized"]["transaction_count"]
if len(rows) != expected:
    raise ValueError(
        f"eligible posting set ({len(rows)}) does not match the week-12 transaction count ({expected}); "
        "regenerate week 12 first so both artifacts describe the same population"
    )
```

이 가드는 실제로 작동했습니다. 테스트를 쓰면서 제가 적격 공고 수를 3개로 잘못 계산했는데(정답 2개),
가드가 바로 잡아내 테스트가 실패했습니다.

## 재현되지 않은 숫자 — 억지로 맞추지 않았습니다

**`week14_segment_comparison.json`의 `top_triples`(상위 3개 기술 조합) 수치는 재현에 실패했습니다.**

기술 필드 3종(`final_techs` / `normalized_techs` / `hard_skills`) × 중복 제거 2종(적용 / 미적용) =
**6가지 조합을 전부 계산해 상위 50개와 맞춰봤지만 최대 1개만 일치**했습니다.

| 조합 | 1순위 | 50개 중 일치 |
| --- | --- | ---: |
| `normalized_techs` | AWS+Java+Spring = 851 | 0 / 50 |
| `normalized_techs` + 중복제거 | AWS+Java+Spring = 724 | 0 / 50 |
| `final_techs` | AWS+Java+Spring = 851 | 0 / 50 |
| `final_techs` + 중복제거 | AWS+Java+Spring = 724 | 0 / 50 |
| `hard_skills` | Docker+Kubernetes+Python = 505 | 1 / 50 |
| `hard_skills` + 중복제거 | Docker+Kubernetes+Python = 429 | 1 / 50 |
| **구버전 파일에 적힌 값** | **C+C+++Python = 296** | — |

구버전 파일만 `C + C++ + Python`을 1순위로 꼽는데, 어떤 계산으로도 그 조합이 1순위가 되지 않습니다.
`296`이라는 수는 `hard_skills` 기준과 우연히 맞지만, 그 기준에서는 `Docker+Kubernetes+Python`이 505로 더 큽니다.

**어떤 방법으로 만든 숫자인지 알 수 없으므로, 맞추려 하지 않고 현재 기준으로 교체했습니다.**
문서에도 이 사실을 남겼습니다.

### 교체 전후

| 조합 | 구버전 | 현재 (17,796건 기준) |
| --- | ---: | ---: |
| AWS + Java + Spring | 226 | **724** |
| Java + JavaScript + Spring | 266 | **710** |
| CSS + HTML + JavaScript | 277 | **647** |
| JavaScript + React + TypeScript | 215 | **647** |
| C + C++ + Python | 296 | **556** |

구버전 상위 50개 중 27개만 현재 상위 50개에 남았습니다.

## 그 외 재생성 결과

| 산출물 | 이전 | 이후 |
| --- | --- | --- |
| `week14_skill_graph.json` | 노드 46, 엣지 50 | **노드 94, 엣지 694** |
| `week13_service_scenarios.json` | 2개 경로 (`normal`, `no_rules`), 18,163 기준 | **5개 경로, 17,796 기준** |

13주차 시나리오는 검증 경로를 5개로 늘렸습니다.

| 시나리오 | 질의 | 상태 |
| --- | --- | --- |
| `normal` | `--skills TensorFlow` | `ok` |
| `no_rules` | `--skills NotARealSkill` | `no_rules` |
| `role_filtered` | `--skills TensorFlow --role frontend` | `ok` |
| `entry_eligible` | `--skills TensorFlow --entry-eligible` | `ok` |
| `insufficient_sample` | `--skills .NET --role frontend --experience 1~3년차` | `insufficient_sample` |

구버전에는 `insufficient_sample` 경로가 기록되어 있지 않았습니다.

## 수정한 파일

| 파일 | 변경 |
| --- | --- |
| `src/service/run_week13.py` (신규) | 68줄 |
| `src/analysis/run_week14.py` (신규) | 105줄, `graph_from_rules()`를 처음으로 호출 |
| `scripts/run_pipeline.ps1` | 2단계 추가 |
| `tests/test_week13_cli.py` (신규) | 시나리오 기록·입력 누락 처리 2건 |
| `tests/test_week14_cli.py` (신규) | 기준 집합·그래프 보존·드리프트 가드 3건 |

---

# 수정 4: 낡은 숫자가 남은 문서 갱신

## 12주차 문서

원인을 git 이력에서 특정했습니다. 11번째 커밋 `4d96ed8 feat: exclude duplicate posting bodies from analysis`가
동일 본문 933건 제외를 추가했는데, 문서는 7번째 커밋 `32c5260` 이후 갱신되지 않았습니다.

| 항목 | 문서에 적혀 있던 값 | 실제 값 |
| --- | ---: | ---: |
| 분석 트랜잭션 | 18,163 | **17,796** |
| 정규화 전 규칙 수 | 707 | **694** |
| 정규화 후 규칙 수 | 707 | **694** |
| 전후 공통 규칙 수 | 707 | **694** |
| 빈 기술 목록 제외 행 | 21,408 | **20,842** |
| 동일 본문 제외 행 | "자동 제외하지 않았다" | **933건 제외함** |

## 설정 파일의 설명 문구

`configs/experiments.json`의 `duplicate_policy`가 코드와 **반대로** 적혀 있었습니다.

```diff
- "duplicate_policy": "keep first source + job_id occurrence; do not auto-drop same-body distinct IDs",
+ "duplicate_policy": "keep first source + job_id occurrence; also keep only the first posting per distinct raw_text body",
```

이 문구는 `week12_rule_comparison.json`과 `week12_all_rules.json`에 그대로 복사되어 들어가기 때문에,
산출물을 읽는 사람 전부가 잘못된 설명을 보게 되는 상태였습니다. (수정 후 두 산출물도 재생성했습니다.)

## 주차 보고서가 숫자를 하드코딩하던 문제

`scripts/build_weekly_reports.py`는 산출물 3개를 `q`, `n`, `r` 변수로 읽어 놓고 **한 번도 쓰지 않았습니다.**
표에 들어가는 값은 전부 문자열로 박혀 있었습니다.

```python
q=json.loads((ROOT/'artifacts/week10_data_quality_summary.json').read_text())  # 읽고 안 씀
...
12:(...[['분석 트랜잭션','17,796'],['규칙 수','694']]...)   # 손으로 적은 값
```

이러면 코드가 바뀔 때마다 보고서가 조용히 낡습니다. 실제로 "테스트 8개 통과"가 그렇게 남아 있었습니다.

**모든 숫자를 산출물에서 읽도록 바꿨습니다.** 테스트 개수도 실제로 세어서 넣습니다.

```python
num=lambda value: f'{value:,}'
TESTS=unittest.defaultTestLoader.discover(str(ROOT/'tests')).countTestCases()
...
12:(...[['분석 트랜잭션',num(r['normalized']['transaction_count'])],['규칙 수',num(r['normalized']['rule_count'])]]...)
```

표뿐 아니라 본문 서술의 숫자 8곳도 같이 바꿨습니다. 이제 파이프라인을 다시 돌리면 보고서 숫자가 자동으로 따라옵니다.

재생성된 보고서에 실제로 들어간 값:

| 주차 | 표에 들어간 값 |
| --- | --- |
| 10 | 입력 행 40,348 / ID 중복 777 / 동일 본문 1,707 / final_techs 빈 21,560 |
| 11 | 입력 행 40,348 / 사전 tech-dictionary.v1 / 별칭 127 / 미등록 142 / **신입 지원 가능 7,151** |
| 12 | 트랜잭션 17,796 / support 0.005 / confidence 0.2 / 규칙 694 / **선행 기술 94종** |
| 13 | 정상 TensorFlow / 규칙 없음 NotARealSkill / **검증 경로 5개** / 근거 최대 3건 |
| 14 | **테스트 20개 통과** / 기준 공고 17,796 / 세그먼트 21개 / 그래프 94·694 |

## 갱신한 문서

| 문서 | 변경 |
| --- | --- |
| `docs/weeks/week10_actual_results.md` | 수치는 전 항목 일치해 그대로. 경력 원칙이 코드로 지켜지게 된 사실만 이력에 추가 |
| `docs/weeks/week12_actual_results.md` | 수치 전면 갱신, 산출물 표 추가, 사전 효과 설명 보강 |
| `docs/weeks/week13_actual_results.md` | 5개 경로 표 추가, 예시 기술 `LlamaIndex` → `TensorFlow`, `next_action` 차이 명시 |
| `docs/weeks/week14_actual_results.md` | 기준 집합·세그먼트·그래프 갱신, 경력 라벨 설명 교체 |
| `README.md` | 조합 수치, 그래프 규모, 테스트 수(8→20), 웹 UI 현황, WSL 실행법, 사전 한계 |
| `configs/experiments.json` | `duplicate_policy` 문구 수정 |

### 13주차 예시 기술을 바꾼 이유

문서의 재현 명령이 `--skills LlamaIndex`였는데 지금은 `no_rules`가 나옵니다. 계산해 보면 이렇습니다.

| | 구버전 | 현재 |
| --- | ---: | ---: |
| 트랜잭션 수 | 18,163 | 17,796 |
| 최소 support 횟수 `ceil(n × 0.005)` | 91 | **89** |
| `LlamaIndex` & `LangChain` 동시 등장 | 93회 | **88회** |
| 규칙 통과 | 통과 | **탈락 (89에 1회 모자람)** |

중복 공고를 제거하자 동시 등장이 93→88회로 줄어 임계값에 1회 모자라 규칙이 사라졌습니다.
**버그가 아니라, 구버전 수치가 중복 공고로 부풀려져 있었다는 증거입니다.** 문서의 예시만 교체했습니다.

### README에서 바로잡은 사실 서술

| 이전 서술 | 실제 |
| --- | --- |
| "현재는 CLI이며, 웹 UI·운영 배포·모니터링은 향후 작업입니다" | `src/service/web_server.py`에 로컬 웹 화면이 있고 동작합니다 (HTTP 200 확인) |
| `JavaScript + React + TypeScript` 215회 | 현재 기준 647회 |
| `PyTorch + Python + TensorFlow` 205회 | 현재 기준 431회 |

---

# 테스트

**8개 → 20개.** 전부 통과, 실패 0.

| 파일 | 개수 | 검증 내용 |
| --- | ---: | --- |
| `test_apriori.py` | 1 | (기존) interest 계산 |
| `test_ingestion_quality.py` | 3 | (기존) 품질 집계 |
| `test_llm_contracts.py` | 1 | (기존) fake provider 표시 |
| `test_normalization.py` | 1 | (기존) 별칭·중복 처리 |
| `test_retrieval.py` | 1 | (기존) 근거 반환 |
| `test_week10_cli.py` | 1 | (기존) 입력 누락 처리 |
| **`test_week12_cli.py`** | **2** | 전체 규칙이 `--top-n`에 절단되지 않음 / 모든 선행 기술이 조회 가능 |
| **`test_metadata.py`** | **5** | 라벨 원본 보존 / 신입 추론 금지 / eligibility 범위 / `경력무관`≠`신입` / 필터 동작 |
| **`test_week13_cli.py`** | **2** | 5개 시나리오 기록 / 입력 누락 시 결과 조작 금지 |
| **`test_week14_cli.py`** | **3** | 12주차와 동일 기준 집합 / 그래프가 전체 규칙 보존 / 기준 불일치 시 중단 |

추가한 테스트는 **이번에 고친 문제가 다시 생기면 실패하도록** 설계했습니다.
예를 들어 누군가 `[:50]`을 되살리면 `test_all_rules_artifact_is_not_truncated_by_the_display_top_n`이 실패하고,
`경력무관`을 다시 `entry`로 합치면 `test_경력무관_is_not_collapsed_into_the_신입_segment`가 실패합니다.

## 재현성 확인

파이프라인을 처음부터 두 번 연속 실행해 `artifacts/`에 차이가 없음을 확인했습니다.

```bash
python -m src.ingestion.run_week10 ...
python -m src.normalization.run_week11 ...
python -m src.analysis.run_week12
python -m src.service.run_week13
python -m src.analysis.run_week14
python -m unittest discover -s tests   # 20 tests, OK
git status --short -- artifacts/        # 출력 없음 = 완전 재현
```

---

# 아직 남은 문제

이번 작업 범위(4개 항목)에 들어가지 않은 항목입니다.

| # | 문제 | 근거 | 영향 |
| --- | --- | --- | --- |
| 1 | **LLM 에이전트 미구현** — 추론·기억·도구·반영 4요소 모두 없음. `src/llm`은 테스트에서만 import됨 | [01](01_baseline_check.md) 2-1, 2-2 | 과제 조건 미충족 |
| 2 | **사전이 사실상 무효** — 별칭 변환 127건 전부가 `Ajax`→`AJAX`. 원본 어휘 156개 중 14개만 등재 | [01](01_baseline_check.md) 2-3 | 정규화 단계가 기여 없음 |
| 3 | **직무 분류 94.1%가 `other_tech`** — 제목이 64.3%(25,950건) 비어 있음. 오타(`풀스텍`)도 놓침 | [01](01_baseline_check.md) 1-6 | 직무별 비교 불가 |
| 4 | **상위 기술 추출 오류** — `Objective-C`→`C` 오추출, `Scylla`·`Ray`·`Mantine` 누락, `GitHub Actions` 소실(전체 3회) | [01](01_baseline_check.md) 1-6 | `C` 과대 집계 |
| 5 | **비기술 항목 혼입** — `AI`(5,549), `ML`, `Deep Learning`, `LLM`, `CI/CD`, `DevOps`, `Jira`, `Figma` | [01](01_baseline_check.md) 2-3 | 정보량 없는 규칙 생성 |
| 6 | **`insufficient_sample`에 `next_action` 없음** — `no_rules`에만 있음 | [01](01_baseline_check.md) 1-3 | 문서와 코드 불일치 (문서에 명시해 둠) |
| 7 | **`src/service/contracts.py`가 죽은 코드** — 어디서도 사용되지 않고 `EvidencePosting.excerpt`는 실제 응답의 `title`과 다름 | [01](01_baseline_check.md) 1-5 | 혼란 유발 |
| 8 | **필터가 지표를 재계산하지 않음** — `--role frontend`도 support·confidence는 전역 값 | [01](01_baseline_check.md) 1-3 | 세그먼트별 수치 오해 가능 |
| 9 | **`requirements.txt` 없음** — 필요한 패키지를 알 방법이 없음 | [01](01_baseline_check.md) 1-2 | 환경 재현 어려움 |
| 10 | **원문 텍스트가 커밋되어 있음** — `.gitignore`는 `artifacts/week10_raw_text_samples.csv`를 막는데 `reports/assets/week10/week10_raw_text_samples.csv`(공고 원문 214줄)는 커밋됨 | 이번 작업 중 발견 | 데이터 커밋 금지 원칙과 불일치 |
| 11 | **줄바꿈 문자 충돌** — 같은 파일이 Windows(CRLF)와 WSL(LF)에서 전체 diff로 보임 | 이번 작업 중 발견 | 불필요한 충돌. `.gitattributes` 필요 |

10번과 11번은 팀 합의가 필요한 사항이라 손대지 않았습니다.
11번은 `.gitattributes`에 `* text=auto`를 넣으면 해결되지만, 이미 커밋된 CRLF 파일들이 한 번에
재정규화되어 큰 diff가 발생하므로 팀이 함께 결정하는 편이 안전합니다.

## 다음 작업 제안

1. `src/agent/` 신설 — 에이전트 4요소 ([01](01_baseline_check.md) 2-4의 충돌 회피 전략 참고)
2. `configs/tech_dictionary_v2.json` — 142개 등재 + `category` 필드로 개념·방법론 항목을 Apriori에서 제외
3. `requirements.txt` 추가
4. `.gitattributes` 추가 (팀 합의 후)
