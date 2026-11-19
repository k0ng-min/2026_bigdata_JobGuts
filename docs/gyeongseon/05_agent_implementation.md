# 05. 에이전트 구현 (gyeongseon)

- 작업 일자: 2026-11-19 (최초), 2026-11-19 갱신 — `&` 쪼개짐 수정과 정밀도 원인 분석 반영
- 갱신 표기: 수치가 바뀐 곳은 **`이전 → 이후`** 로 적었습니다. `이전`은 `&` 수정 전 값입니다.
- 작업 브랜치: `gyeongseon`
- 선행 문서: [03_agent_design.md](03_agent_design.md) (설계), [04_dictionary_v2.md](04_dictionary_v2.md) (사전 v2)
- 테스트: **57개 → 132개** (최초 118 → 갱신 132), 전부 통과 (실패 0)
- 기본 실행은 **fake provider**이며, 모든 산출물에 `is_mock: true`가 박힙니다. 실제 LLM 성능이 아닙니다.

## 커밋

| 커밋 | 내용 |
| --- | --- |
| `d39b481` | 사전에 등록된 한글 표기만 원문에서 찾기 |
| `ec251d4` | fake 판단기와 GLM provider (요청할 때만 동작) |
| `3457228` | 에이전트 루프와 도구 호출 로그 |
| `38a8082` | 추천 실패 시 필터 완화와 범위 변경 고지 |
| `47640c2` | 정리 전·후·`final_techs` 3자 비교와 검수 시트 |
| `a125120` | **`&` 쪼개짐 수정, `Boot` 오매핑 수정, `comparison_key` 한글 보존** |

## 전후 숫자 한눈에 보기

| 항목 | 이전 | 이후 |
| --- | ---: | ---: |
| 추출 재현율 (`final_techs` 대비) | 75.2% | **79.6%** (갱신 전 80.2%) |
| 사전의 표준 이름 수 | 127 | **130** |
| 사전의 표기 수 | 253 | **314** (한글 61 추가) |
| 89회 이상 후보 중 사전 해결 (등장 기준) | 40.7% | **42.0%** (갱신 전 42.5%) |
| 에이전트 4요소 충족 | 0 / 4 | **4 / 4** |
| 판단 대상 후보 | 463종 (미처리) | **607종 판단 완료** (갱신 전 608) |
| 도구 호출 로그 | 없음 | **3,416회 전건 기록** (갱신 전 3,423) |
| 추천 실패 시 재시도 | 없음 | **있음 (고지 포함)** |
| 테스트 | 57 | **132** (갱신 전 118) |

---

# 1. 한글 기술명 추출

## 1-1. 일반 토큰화를 하지 않은 이유

[04_dictionary_v2.md](04_dictionary_v2.md) 3-2절에서 한글이 추출되지 않는다고 적었습니다.
해결 방식은 **사전에 등록된 표기만 찾는 닫힌 목록 조회**입니다. 한글은 띄어쓰기가 불규칙하고
단어 경계가 없어, 열린 토크나이저를 쓰면 후보 목록이 일반 명사로 뒤덮입니다.

등록된 표기는 **61종**, 표준 이름 **51개**에 연결됩니다. 모두 `final_techs`의 156개 안에 있습니다.

## 1-2. 두 가지 규칙

### 긴 표기 우선 + 구간 소모

```
'자바스크립트'        -> ['자바스크립트']        ('자바' 로 잡히지 않음)
'리액트 네이티브'      -> ['리액트 네이티브']      ('리액트' 로 잡히지 않음)
'자바스크립트 와 자바'  -> ['자바스크립트', '자바']   (별개 등장은 각각 인식)
```

표기를 길이 내림차순으로 시도하고, 매칭된 구간을 공백으로 덮습니다.
[04](04_dictionary_v2.md) 1-2절의 복합어 처리와 같은 방식입니다.

### 한글 경계 검사 — 이것이 없으면 전부 무너집니다

매칭 앞뒤 문자가 한글 음절이면 매칭을 버립니다. 효과를 실제로 측정했습니다.

| 표기 | 표준 이름 | 단순 포함 | 경계 적용 | 오탐의 정체 |
| --- | --- | ---: | ---: | --- |
| `뷰` | Vue.js | **3,257** | 27 | 코드 **리뷰** |
| `러스트` | Rust | 594 | **0** | 트**러스트**, 일**러스트** |
| `깃` | Git | 126 | **0** | **깃**허브, **깃**랩 |
| `펄` | Perl | 126 | **0** | **펄**크루트, **펄**사게이밍 |
| `루비` | Ruby | 39 | **0** | 그**루비** (Groovy) |
| `지라` | Jira | 36 | 6 | 할**지라**도 |
| `스파크` | Spark | 78 | 2 | 비지니**스파크** |
| `장고` | Django | 18 | 3 | 냉**장고** |
| `레스트` | REST API | 18 | **0** | 포**레스트** |
| `노드` | Node.js | 148 | 103 | 풀**노드**, **노드**서버 |

경계 검사만으로 오탐 대부분이 사라집니다. `루비`가 `그루비`(Groovy)를 잡던 것은
표준 이름을 완전히 틀리게 만드는 종류의 오류였습니다.

## 1-3. 의도적으로 등록하지 않은 표기 13종

경계 검사를 통과해도 애매한 것은 넣지 않았습니다. 이유를 `excluded_on_purpose`에 전부 기록했습니다.

| 표기 | 이유 |
| --- | --- |
| `뷰` | 일반 명사 "뷰". 경계 통과 27건도 대부분 "뷰 설계", "뷰 개발" |
| `노드` | 일반 명사 "노드". 풀노드·노드 서버는 블록체인·인프라 용어 |
| `비트` | bit, 업비트. Vite는 라틴 문자로 더 자주 씀 |
| `깃`·`펄`·`러스트`·`루비`·`레스트` | 경계 적용 후 0건. 전부 더 긴 단어의 조각 |
| `다트` | 피닉스다트 등 회사명 |
| `몽고` | 국가명 "몽고"가 DB 약어만큼 흔함 |
| `엘라스틱` | 조각. `엘라스틱서치`를 대신 등록 |
| `컨플루언스` | **Confluence가 `final_techs` 어휘에 없음** → 등록하면 표준 이름을 만드는 일이 됨 |
| `고랭` | 적격 공고에 등장 0건 → 근거 없음 |

## 1-4. 측정 결과

같은 공고 17,796건(12주차 동일 집합)입니다.

| 항목 | 한글 추출 없음 | 한글 추출 적용 |
| --- | ---: | ---: |
| 서로 다른 항목 | 27,581 | **27,788** (갱신 전 27,642) |
| 규칙 수 | 2,627 | **2,699** (갱신 전 2,757) |
| 재현율 (원문 표기 그대로) | 75.2% | 74.6% |
| **재현율 (사전이 한글을 접은 뒤)** | 75.2% | **79.6%** (갱신 전 77.2%) |
| 공고당 후보 수 | 20.7 | 21.0 |

원문 표기 기준 재현율이 그대로인 것은 당연합니다. `파이썬`은 `Python`과 글자가 다르므로
그 자체로는 정답과 일치하지 않습니다. **사전이 표준 이름으로 접었을 때 77.2%로 올라갑니다.**
즉 한글 추출의 가치는 사전과 함께 쓸 때만 나타납니다.

등장 횟수 상위: `인공지능`(1,421), `딥러닝`(1,120), `생성형 AI`(858), `머신러닝`(674),
`리눅스`(549), `자바`(319), `파이썬`(264), `안드로이드`(241). 한글 표기 합계 **7,098회**.

---

# 2. 에이전트 루프

## 2-1. 흐름 (설계 2-1절 그대로)

```
후보 1개
  ① 캐시                 적중 -> 끝 (LLM 호출 없음)
  ② 확정 사전 조회         적중 -> 표준 이름 (LLM 호출 없음)   [기억 참조]
  ③ 이번 실행 학습 조회      적중 -> 표준 이름 (LLM 호출 없음)   [결과 반영의 효과]
  ④ 호출 예산 확인         초과 -> needs_review
  ⑤ get_context          원문 문맥 다시 읽기               [도구 호출]
  ⑥ get_cooccurrence     같은 공고에 함께 나오는 이름         [도구 호출]
  ⑦ judge                판단                           [추론]
  ⑧ 신뢰도 하향            0.8 미만 -> 저신뢰 표시, 0.5 미만 -> needs_review
  ⑨ 결과를 기억에 기록       다음 후보가 사용                  [결과 반영]
  ⑩ 캐시에 기록
```

## 2-2. 4가지 판단 결과

`src/agent/judgement.py`에서 닫힌 집합으로 강제합니다.

| 결과 | 뜻 | 정리 결과에 미치는 영향 |
| --- | --- | --- |
| `canonical` | 어휘에 있는 기술 | 표준 이름으로 치환 |
| `not_a_technology` | 업무 약어·회사명·일반 명사 | 목록에서 제거 |
| `new_technology` | 어휘에 없는 실제 기술 | **원문 표기 그대로 보존** (표준 이름을 만들지 않음) |
| `needs_review` | 판단 불가 | 원문 표기 그대로 보존 |

`Judgement`는 생성 시점에 검증합니다. `canonical`인데 표준 이름이 없으면,
또는 `canonical`이 아닌데 표준 이름을 달고 있으면 예외가 납니다.

## 2-3. 기억을 두 층으로 나눈 이유

| 층 | 내용 | 모델이 바꿀 수 있나 |
| --- | --- | --- |
| 확정 (`confirmed`) | 사전 v2의 314개 표기 | **아니오** |
| 학습 (`learned`) | 이번 실행에서 판단한 것 | 예 |

모델이 어휘 밖 표준 이름을 제안하면 **기억이 거부**하고 `needs_review`로 떨어집니다.
`propose_canonical`이 `{"accepted": false}`를 돌려주고, 그 사실도 로그에 남습니다.
이것이 [04](04_dictionary_v2.md)의 "표준 이름을 만들지 않는다" 원칙을 런타임에서 지키는 장치입니다.

## 2-4. 실행 결과

```
provider=fake mock=True candidates=607
llm_calls=447 cache_hits=33 dictionary_hits=127 learned_hits=0
decisions={'canonical': 145, 'needs_review': 434, 'not_a_technology': 19, 'new_technology': 9}
```

갱신 전: `candidates=608 llm_calls=448 canonical=147 needs_review=433`.
`canonical`이 2 줄어든 것은 `Boot`·`boot` 오매핑을 제거한 결과입니다 (6-2절).

| 항목 | 값 |
| --- | ---: |
| 적격 공고 | 17,796 |
| 전체 고유 후보 | 27,787 (갱신 전 27,641) |
| 89회 이상 판단 대상 | **607** (갱신 전 608) |
| 후보 등장 총 횟수 | 217,243 (갱신 전 219,611) |
| 실제 LLM 호출 | **447** (갱신 전 448) |
| 캐시·기억으로 절약한 호출 | **216,796** (갱신 전 219,163) |
| 제거된 등장 횟수 | 22,657 (갱신 전 24,351) |

제거 상위: `SI`(2,584), `SW`(2,333), `PM`(2,326), `ERP`(1,960), `CRM`(1,521), `K`(1,414), `PO`(1,408), `DBA`(1,259)

**`D`가 제거 1위에서 사라졌습니다.** 갱신 전에는 2,729회로 1위였는데, 그 65%가 `R&D`에서
쪼개진 것이었습니다 (6-1절). `&`를 고친 뒤 `D`는 1,184회로 줄고 `R&D`가 1,767회로 따로 집계됩니다.

### 2회차 실행은 호출이 0입니다

```
1회차: llm_calls=447  cache_hits=33
2회차: llm_calls=0    cache_hits=607
```

판단 결과도 완전히 동일합니다. 캐시 키는 `정규화된 이름 + 사전 버전 + 프롬프트 버전`이므로
사전이나 프롬프트가 바뀌면 이전 답을 재사용하지 않습니다.

### 학습 계층에 대한 정직한 보고

**`learned_hits=0`입니다.** 캐시를 먼저 보기 때문에, 같은 키로 정규화되는 두 번째 표기는
학습 계층에 닿기 전에 캐시가 답해 버립니다. 그래서 `--no-cache`를 **캐시를 아예 쓰지 않는**
모드로 바꿔 학습 계층이 실제로 동작하는지 확인했습니다.

```
--no-cache: llm_calls=462  cache_hits=0  dictionary_hits=145  learned_hits=0
```

**갱신 후 `learned_hits=0`입니다.** 갱신 전에는 1건이었는데, 그 1건이 바로 `Boot` 다음에 온
`boot`였습니다. `Boot` 오매핑을 제거하자(6-2절) 학습 계층이 실제 데이터에서는 **한 번도
발동하지 않게 되었습니다.**

| 항목 | 상태 |
| --- | --- |
| 구현 | 있음 (`memory.py` 학습 층, `propose_canonical`) |
| 조회 | `lookup_learned` **447회 호출** |
| 실제 적중 | **0회** |
| 검증 | 테스트 `test_a_judgement_is_reflected_back_and_serves_a_later_candidate`에서만 발동 |

이유는 분명합니다. fake 판단기가 `canonical`로 판정하는 표기는 대부분 이미 사전 v2에 있고,
남은 434종은 전부 `needs_review`라서 학습 층에 쌓이지 않습니다.
**실제 모델이 그 434종을 판단해야 이 계층이 의미를 갖습니다.**
④ 요소는 "구현되고 조회되지만 이 데이터·이 판단기에서는 발동하지 않는다"가 정확한 상태입니다.

## 2-5. 4요소 대비 (설계 2-2절의 0/4 → 4/4)

| 기준 | 구현 위치 | 증거 |
| --- | --- | --- |
| ① 추론 | `judge.py` → provider | 로그의 `judge` 호출 448건, 각 호출에 전달한 문맥 포함 |
| ② 기억 참조 | `memory.py` 확정 층 | `lookup_dictionary` 574회, 적중 127건 |
| ③ 도구 호출 | `tools.py` 7개 | `get_context` 447회, `get_cooccurrence` 447회 |
| ④ 결과 반영 | `memory.remember` + 학습 층 | `lookup_learned` 447회 조회, **실제 적중 0회** (위 참조) |

④는 **구현되고 447회 조회되지만, fake 판단기에서는 실제 적중이 0건**입니다.
테스트로만 발동을 확인했습니다. 과제 발표에서는 이 점을 숨기지 않는 쪽이 낫습니다.

## 2-6. 도구 호출 로그 — 13주차 증거

`artifacts/agent_tool_log.json`에 **3,416회 전건**이 순서대로 들어 있습니다 (갱신 전 3,423회).

| 도구 | 호출 수 |
| --- | ---: |
| `cache` | 607 |
| `lookup_dictionary` | 574 |
| `lookup_learned` | 447 |
| `get_context` | 447 |
| `get_cooccurrence` | 447 |
| `judge` | 447 |
| `mark_needs_review` | 428 |
| `mark_not_a_technology` | 19 |
| `propose_canonical` | 0 |

`propose_canonical`이 0인 것은 ④의 적중 0회와 같은 이유입니다. fake 판단기의 `canonical`
판정 145건이 전부 캐시나 확정 사전에서 처리되어 모델 경로까지 오지 않습니다.

### 경로별 실제 기록

| 경로 | 예시 | 호출된 도구 |
| --- | --- | --- |
| `dictionary` | `AI` → `canonical(AI)` conf 1.00 | `cache`, `lookup_dictionary` |
| `cache` | `JAVA` → `canonical(Java)` conf 1.00 | `cache` |
| `model` | `API` → `needs_review` conf 0.30 | 7개 전부 |

### 로그 1건 (후보 `D`, 발췌)

```json
{
  "candidate": "D", "occurrences": 2729,
  "steps": [
    {"tool": "cache", "arguments": {"name": "D"}, "result": {"hit": false}},
    {"tool": "lookup_dictionary", "result": {"canonical": null, "source": "confirmed"}},
    {"tool": "lookup_learned", "result": {"canonical": null, "confidence": 0.0}},
    {"tool": "get_context", "result": {
       "snippets": ["... 3) R&D - 모델 성능평가 및 프롬프팅 구조화 ...", "... D. 앱 개발자 공통 기술 질문 ...", "... 기상, 해양 분야 프로젝트 및 R&D 개발(GIS 시스템) ..."],
       "section": true, "section_occurrences": 177, "occurrences": 2729}},
    {"tool": "get_cooccurrence", "result": {"neighbours": [
       {"name": "AI", "count": 2160}, {"name": "R", "count": 1775}, {"name": "SW", "count": 770}]}},
    {"tool": "judge", "result": {"decision": "not_a_technology", "confidence": 0.85}},
    {"tool": "mark_not_a_technology", "result": {"accepted": true}}
  ],
  "outcome": {"decision": "not_a_technology", "route": "model"}
}
```

**이 로그 하나가 추출 결함을 하나 더 드러냈습니다** — 3-2절에서 다룹니다.

---

# 3. LLM 제공자

## 3-1. fake provider

| 조건 | 구현 |
| --- | --- |
| 결정적 | 규칙표 조회. 같은 입력 → 항상 같은 출력 |
| 모의임을 표시 | 모든 `Judgement`에 `is_mock: true`, 산출물 3개에 `is_mock`과 `mock_warning` |
| 네 경로 모두 재현 | `Javascript`→canonical, `SI`→not_a_technology, `RAG`→new_technology, `API`→needs_review |
| 추측 금지 | 규칙표에 없으면 `needs_review`, 신뢰도 `0.0` |
| 네트워크·키 사용 없음 | `docs/llm_boundary.md` 준수 |

산출물에 들어가는 경고문입니다.

```json
"is_mock": true,
"mock_warning": "Decisions came from a deterministic rule table, not from a language model. These numbers show that the flow runs end to end; they are not model performance."
```

## 3-2. GLM provider

`src/llm/glm_provider.py`를 만들었지만 **기본 실행과 테스트에서 절대 호출되지 않습니다.**

| 조건 | 구현 |
| --- | --- |
| import 시점에 아무것도 실행 안 함 | 모듈 수준 코드 없음 |
| 키는 환경 변수에서만 | `GLM_API_KEY`. `.env`도 환경 변수로 올려 읽음 |
| 이미 설정된 환경 변수를 덮지 않음 | `.env`보다 셸 export가 우선 |
| `--provider glm`일 때만 생성 | 기본값은 `fake` |
| 외부 패키지 불필요 | 표준 라이브러리 `urllib` |
| `.env` 커밋 금지 | `.gitignore`에 포함, `.env.example`만 커밋 |

### 키 없이 실행하면

생성 시점에 바로 멈춥니다. 후보를 하나라도 처리한 뒤 실패하지 않습니다.

```
GLM_API_KEY is not set, so the GLM provider cannot run.
  Set it for this shell:  export GLM_API_KEY=<your key>
  or copy .env.example to .env and fill in GLM_API_KEY.
  .env is excluded from version control; never commit a key.
  To run without a model, use --provider fake.
```

### 모델이 어휘 밖 이름을 제안하면

응답 파서가 거부합니다. 이것이 사전 v2의 원칙을 모델 앞에서 지키는 지점입니다.

| 응답 | 결과 |
| --- | --- |
| `{"decision":"canonical","canonical":"Java",...}` | 적용 |
| `{"decision":"canonical","canonical":"Groovy",...}` | **`needs_review`** — `Groovy`는 어휘에 없음 |
| `I think it is Java` (JSON 아님) | `needs_review` |
| `{"decision":"banana"}` | `needs_review` |
| `{"confidence":"high"}` | `needs_review` |

**읽을 수 없는 응답이 잘못된 매핑이 되는 일이 없습니다.** 전부 보류로 떨어집니다.

---

# 4. 추천 실패 시 재시도

## 4-1. 완화 순서

[03](03_agent_design.md) 7-2절 그대로입니다. 좁은 조건을 먼저 풉니다.

| 단계 | 푸는 조건 | 근거 |
| --- | --- | --- |
| 1 | `experience_segment` | 64.3%가 `unknown` |
| 2 | `job_role` | 94.1%가 `other_tech` |
| 3 | `entry_eligible` | 마지막 |
| — | **기술명은 절대 바꾸지 않음** | 바꾸면 다른 질문에 답하는 셈 |

`no_rules`는 완화하지 않습니다. 필터가 원인이 아니기 때문입니다.
대신 **표기를 한 번만 정규화해 재시도**하고, 그래도 없으면 멈춥니다.

## 4-2. 실제 동작

| 질의 | 결과 | 넓힘 | 비고 |
| --- | --- | --- | --- |
| `--skills TensorFlow` | `ok` | 아니오 | 완화 불필요 |
| `--skills Pytorch` | `ok` | 아니오 | `Pytorch` → `PyTorch` 정규화 후 성공 |
| `--skills 파이썬` | `ok` | 아니오 | **한글 입력** → `Python` 정규화 후 성공 |
| `--skills .NET --role frontend --experience 1~3년차` | `ok` | **예** | `experience_segment` 해제 |
| `--skills TensorFlow --role frontend --experience 1~3년차 --entry-eligible` | `ok` | **예** | 같음 |
| `--skills NotARealSkill` | `no_rules` | 아니오 | 완화하지 않고 안내 |

## 4-3. 범위를 바꿨다는 사실을 밝힙니다

```json
{
  "status": "ok",
  "requested_filters": {"skills": [".NET"], "job_role": "frontend", "experience_segment": "1~3년차"},
  "applied_filters": {"job_role": "frontend", "experience_segment": "all", "entry_eligible_only": false},
  "relaxation_steps": [{"step": 1, "released": "experience_segment", "reason": "insufficient_sample"}],
  "search_was_widened": true,
  "disclosure": "요청하신 조건에서는 근거 공고를 찾지 못해 experience_segment 조건을 풀고 검색한 결과입니다.",
  "metrics_scope": "all_postings",
  "metrics_note": "support, confidence and interest are computed over the whole transaction set. Filters select evidence postings only and do not re-compute the metrics."
}
```

`metrics_note`는 **넓히지 않은 응답에도 항상** 들어갑니다.
[01_baseline_check.md](01_baseline_check.md) 1-3절에서 확인한 "필터는 지표를 재계산하지 않는다"를
사용자가 오해하지 않게 하기 위한 것입니다.

---

# 5. 평가

## 5-1. 3자 비교 (같은 17,796건, support 0.005 / confidence 0.2)

| 실험 | 항목 수 | 규칙 수 | 선행 기술 |
| --- | ---: | ---: | ---: |
| `before_cleanup` (정리 전) | 27,788 (전 27,642) | **2,699** (전 2,757) | 435 |
| `after_agent` (에이전트 정리 후) | 27,368 (전 27,219) | **2,191** (전 2,197) | 390 |
| `final_techs` (원본 정리본) | 156 | **694** | 94 |

세 실험 모두 같은 공고 수를 쓰는지 테스트로 고정했습니다
(`test_all_three_experiments_use_the_same_posting_set`).

## 5-2. 규칙 겹침

| 비교 | 공통 | Jaccard | 상위 50 공통 |
| --- | ---: | ---: | ---: |
| 정리 전 ↔ 정리 후 | 1,877 | 0.6230 | 34 / 50 |
| 정리 후 ↔ `final_techs` | 563 | 0.2425 | 6 / 50 |
| 정리 전 ↔ `final_techs` | 486 | 0.1672 | 4 / 50 |

**정리가 `final_techs` 쪽으로 가까워졌습니다**: 486 → 563 공통, Jaccard 0.1672 → 0.2425.
다만 아직 멀고, fake 판단기가 19종만 제거했기 때문입니다.
(상위 50 공통은 7 → 6으로 바뀌었습니다. `&` 수정으로 상위 규칙 순위가 재배열된 결과입니다.)

### 상위 규칙의 변화

| 정리 전 | 정리 후 |
| --- | --- |
| `GLORY → KORNIC` 0.9934 | ~~제거됨~~ |
| `KORNIC → GLORY` 0.9934 | ~~제거됨~~ |
| `Cytiva → Y` 0.9916 | `Cytiva → Y` 0.9916 (여전히 남음) |
| `GLORY → Ltd` 0.9839 | ~~제거됨~~ |
| `Javasc → ript` 0.9837 | `Javasc → ript` 0.9837 (원문 오타, 고칠 수 없음) |
| — | `LlamaIndex → LangChain` 0.9556 (실제 기술 조합) |
| — | `Hibernate → JPA` 0.9509 (실제 기술 조합) |
| — | `ELT → ETL` 0.9341 (실제 기술 조합) |

회사명 `KORNIC GLORY`는 제거됐지만 `Cytiva`는 fake 규칙표에 없어 남았습니다.
**실제 모델이라면 둘 다 회사명으로 판정할 것이고, 그것이 fake와 실제의 차이입니다.**

## 5-3. 어휘 안/밖 지표 분리 — 04 문서 3-1절 대응

[04_dictionary_v2.md](04_dictionary_v2.md) 3-1절의 편향에 대한 대응입니다.
표준 이름을 `final_techs`에서 가져왔고 정답지도 같은 `final_techs`이므로, 하나의 숫자는 왜곡됩니다.

| | 정밀도 | 재현율 | F1 |
| --- | ---: | ---: | ---: |
| **정리 전** | | | |
| overall | 16.8% (전 17.0%) | 74.6% (전 75.2%) | 27.5% |
| inside_vocabulary | 74.9% (전 73.8%) | 74.9% (전 75.4%) | 74.9% |
| outside_vocabulary | **0.3%** | 60.8% | 0.6% |
| **정리 후** | | | |
| overall | **19.3%** (전 19.5%) | **79.6%** (전 80.2%) | **31.1%** |
| inside_vocabulary | **73.0%** (전 71.0%) | **80.0%** (전 80.5%) | **76.3%** (전 75.5%) |
| outside_vocabulary | **0.3%** | 60.8% | 0.7% |

어휘 안 정밀도 하락 폭이 **2.8%p → 1.9%p**로 줄었고, 남은 1.9%p의 원인은 아래 5-5절에서
전부 규명했습니다.

### 이 표를 읽는 방법

- **`outside_vocabulary` 정밀도가 양쪽 0.3%** 입니다. 어휘 밖 이름은 정의상 정답지에 거의 없으므로
  **구조적으로 0에 가깝습니다.** 이 숫자는 모델 성능이 아니라 **평가 설계의 한계를 보여주는 수치**입니다.
- **`inside_vocabulary` 정밀도가 74.9% → 73.0%로 내려갔습니다.** 이 1.9%p의 원인은
  5-5절에서 규명했습니다. **에이전트의 새 오답은 0건**이고, 전부 버킷 이동 효과입니다.
- **`overall`은 두 버킷의 혼합이므로 단독으로 쓰면 안 됩니다.** 16.8% → 19.3%라는 개선은
  대부분 "어휘 밖 노이즈를 조금 지웠다"에서 나옵니다.

`artifacts/agent_comparison.json`이 이 경고를 자기 안에 담고 있습니다.

```json
"evaluation_bias_note": "Standard names come from final_techs and final_techs is the ground truth here, so the inside_vocabulary figures are structurally favourable. Read outside_vocabulary and the human review sheet alongside them."
```

## 5-4. 사람 검수 시트

| 항목 | 내용 |
| --- | --- |
| 파일 | `artifacts/agent_review_sheet.csv` (원본), `_reviewer1.csv`, `_reviewer2.csv` |
| 행 | 100 (정리 전 상위 50 + 정리 후 상위 50) |
| 순서 | `seed=31415`로 섞음 — 어느 쪽인지 알 수 없게 |
| 판정 칸 | `both_are_technologies`, `combination_is_plausible`, `reviewer_note` **전부 비어 있음** |
| 출처 칸 | `source_do_not_read_before_judging` (마지막 열) |

```csv
rule_id,antecedent,consequent,support,confidence,interest,support_count,both_are_technologies,combination_is_plausible,reviewer_note,source_do_not_read_before_judging
A036,Retrieval,LLM,0.005732,0.918919,0.808894,102,,,,after_agent
B011,V1,SK,0.005563,0.980198,0.94564,99,,,,before_cleanup
```

이 시트가 [03](03_agent_design.md) 6절의 두 질문을 재는 도구입니다.
`final_techs`를 쓰지 않으므로 5-3절의 편향에서 자유롭습니다.
팀원 두 명이 각자 사본을 채우고, 일치율도 함께 보고하면 됩니다(설계 6절 질문 1의 반증 조건 ③).

## 5-5. 어휘 안 정밀도가 내려간 원인 (규명 완료)

`inside_vocabulary` 정밀도가 정리 후 더 낮게 나오는 현상을 전수 추적했습니다.
원인은 **세 가지**였고, 성격이 서로 다릅니다.

| # | 원인 | 성격 | 처리 |
| --- | --- | --- | --- |
| 1 | fake 규칙표가 `Boot` → `Spring Boot` 로 매핑 | **에이전트 판단 오류** | **고쳤습니다** |
| 2 | `comparison_key`가 한글을 제거 | **평가 코드 버그** | **고쳤습니다** |
| 3 | 정리가 이름을 어휘 밖 → 어휘 안으로 옮김 | **평가 방식의 성질** | 측정해 드러냈습니다 |

### 원인 1 — `Boot` 오매핑 (에이전트 판단 오류, 고침)

`src/agent/fake_judge.py`의 규칙표에 `"boot": ("Spring Boot", 0.55)`가 있었습니다.
그런데 `configs/tech_dictionary_curated.json`은 같은 표기를 **의도적으로 제외**하고 있었습니다.

> `"Boot": "only means Spring Boot when Spring is nearby; that is a context judgement"`

**제가 사전에서 거부한 판단을 판단기가 하고 있었습니다.** 영향이 가장 컸습니다.

| 매핑 | 건수 |
| --- | ---: |
| `Spring Boot` ← `Boot` | 1,111 |
| `Spring Boot` ← `boot` | 81 |
| **합계** | **1,192** |

규칙표에서 제거해 `needs_review`로 보냈습니다. 어휘 안 정밀도가 **71.0% → 73.0%**로 올랐습니다.
회귀를 막는 테스트를 두 개 넣었습니다.

```python
def test_boot_is_not_mapped_to_spring_boot(self):
    result = self.judge.judge("Boot", {})
    self.assertEqual(result.decision, "needs_review")

def test_no_curated_exclusion_is_mapped_by_the_rule_table(self):
    for spelling in self.curated["excluded_on_purpose"]:
        self.assertNotEqual(self.judge.judge(spelling, {}).decision, "canonical")
```

두 번째 테스트가 중요합니다. **사전의 제외 목록과 판단기의 규칙표가 어긋나면 실패합니다.**

### 원인 2 — `comparison_key`가 한글을 지웠음 (평가 코드 버그, 고침)

`src/agent/run_compare.py`의 비교 키가 `[^a-z0-9+#./\- ]`를 제거하고 있었습니다.
한글이 전부 날아갑니다.

| 입력 | 수정 전 키 | 수정 후 키 |
| --- | --- | --- |
| `생성형 AI` | `'ai'` | `'생성형 ai'` |
| `딥러닝` | `''` (빈 문자열) | `'딥러닝'` |
| `자바` | `''` | `'자바'` |
| `파이썬` | `''` | `'파이썬'` |

**`생성형 AI`가 `AI`와 같은 키가 되고, `딥러닝`·`자바`·`파이썬`이 모두 빈 문자열로 같아졌습니다.**
한글 후보가 어휘 안 버킷으로 잘못 분류되고 서로 구분되지 않았습니다.
[04_dictionary_v2.md](04_dictionary_v2.md) 1-4절의 "기호를 지우면 안 된다"와 **같은 종류의 실수**입니다.

### 원인 3 — 버킷 이동 (평가 방식의 성질, 측정해 드러냄)

남은 오답을 전수 분류했습니다. `artifacts/agent_comparison.json`의
`in_vocabulary_error_breakdown`에 들어 있습니다.

| 항목 | 값 |
| --- | ---: |
| 어휘 안에서 새로 생긴 오답 총계 | **3,711** |
| 그중 **버킷 이동** (원래도 오답이었음) | **3,711 (100.0%)** |
| 그중 **새로 생긴 오답** | **0** |
| 정리로 잃어버린 정답 | **0** |

**새로 생긴 오답이 0건이고, 잃어버린 정답도 0건입니다.**

버킷 이동이란 이것입니다.

```
정리 전: 후보 '생성형 AI'  -> 어휘 밖 버킷 (정밀도 구조적으로 0.3%)  -> 오답으로 집계
정리 후: 표준 'Generative AI'        -> 어휘 안 버킷 (정밀도 73.0%)        -> 오답으로 집계
                                   ↑
                    같은 오답이 버킷만 바꿨을 뿐
```

이동 상위 항목입니다.

| 매핑 | 건수 | 규칙 | 매핑이 틀렸나 |
| --- | ---: | --- | --- |
| `Generative AI` ← `생성형 AI` | 849 | korean | **아니오** — 공고에 실제로 "생성형 AI"라고 적혀 있음 |
| `Deep Learning` ← `딥러닝` | 437 | korean | 아니오 |
| `Vue.js` ← `Vue3` | 364 | curated | 아니오 |
| `ML` ← `머신러닝` | 277 | korean | 아니오 |
| `Computer Vision` ← `컴퓨터 비전` | 190 | korean | 아니오 |
| `MSSQL` ← `MS-SQL` | 138 | punctuation | 아니오 |
| `REST API` ← `RESTful` | 117 | curated | 판단의 여지 있음 |
| `NLP` ← `자연어 처리` | 97 | korean | 아니오 |

**매핑은 맞고, `final_techs`에 그 기술이 없습니다.**
공고가 "생성형 AI"라고 적어 놓았는데 `final_techs`에 `Generative AI`가 없으면,
올바른 추출·올바른 정규화가 오답으로 집계됩니다.

이것이 [04_dictionary_v2.md](04_dictionary_v2.md) 3-1절에서 예고한 편향이
**구체적 기제로 확인된 것**입니다. 그 문서는 이렇게 적었습니다.

> "원문에 있는 기술이 정답지에 없음 → 에이전트가 맞게 뽑아도 **오답으로 집계됨**"

### 결론 — 어떻게 읽어야 하나

| 질문 | 답 |
| --- | --- |
| 에이전트가 어휘 안 이름을 잘못 다뤘나 | **아니오.** 새 오답 0건, 정답 손실 0건 |
| 사전이 틀렸나 | **아니오.** 이동 상위 8개 중 7개는 매핑이 정확함 |
| 그럼 왜 정밀도가 내려가나 | **평가 방식** 때문입니다. 정밀도가 구조적으로 0에 가까운 버킷에서 이름이 넘어옴 |
| 고칠 수 있나 | 평가 설계를 바꾸지 않는 한 **고칠 수 없습니다.** 대신 측정해 드러냈습니다 |

`in_vocabulary_error_breakdown`이 자기 안에 이 설명을 담고 있습니다.

```json
"note": "A migrated error was already counted in the outside_vocabulary bucket before cleanup, where its precision is structurally near zero, so it lowers inside_vocabulary precision without the cleanup having made a new mistake."
```

### 그래서 어느 숫자를 봐야 하나

| 목적 | 봐야 할 숫자 |
| --- | --- |
| 에이전트가 해를 끼쳤는지 | `newly_introduced` = **0**, `correct_names_lost` = **0** |
| 에이전트가 기여했는지 | 재현율 74.6% → **79.6%**, F1 74.9% → **76.3%** |
| 노이즈를 걸렀는지 | 제거 22,657회, 상위 규칙에서 `KORNIC GLORY` 계열 소멸 |
| 결론이 바뀌었는지 | `final_techs`와의 Jaccard 0.1672 → **0.2425** |
| **정밀도 단독** | **쓰지 마세요** — 5-3절과 이 절의 이유 때문 |

---


# 6. 이번 작업에서 새로 발견한 문제

## 6-1. `&` 쪼개짐 — 발견하고 고쳤습니다

최초 작성 때 후보 `D`의 도구 로그를 읽다가 발견했고, 이번 갱신에서 고쳤습니다.
문맥 3개 중 2개가 `R&D`였습니다.

```
"... 3) R&D - 모델 성능평가 및 프롬프팅 구조화 ..."
"... 기상, 해양 분야 프로젝트 및 R&D 개발(GIS 시스템) ..."
```

[04_dictionary_v2.md](04_dictionary_v2.md) 1-2절에서 하이픈과 슬래시는 처리했지만 `&`는
처리하지 않았습니다. `Wi-Fi`를 `Wi`+`Fi`로 쪼갰던 것과 **같은 종류의 결함**이었습니다.

### 전수 확인 — 라틴 토큰 사이의 모든 기호

추측하지 않고 전체 공고에서 라틴 토큰 사이에 끼인 기호를 전부 세었습니다.

| 기호 | 등장 | 판정 | 근거 |
| --- | ---: | --- | --- |
| `.` | 91,252 | 이미 처리 | 토큰 내부 유지 (`Node.js`) |
| `-` | 44,066 | 이미 처리 | 복합어 규칙 |
| `/` | 35,048 | 이미 처리 | 복합어 규칙 |
| `:` | 19,536 | **쪼개는 게 맞음** | 시각 `09:00` |
| `·` | 9,460 | **쪼개는 게 맞음** | 목록 구분 `솔루션·SI·CRM` |
| `,` | 6,816 | **쪼개는 게 맞음** | 숫자 자릿수 `1,001` |
| `(` | 6,213 | **쪼개는 게 맞음** | 괄호 |
| `~` | 5,493 | **쪼개는 게 맞음** | 범위 `09:00~18:00` |
| **`&`** | **4,958** | **고쳤습니다** | **`R&D`, `Q&A`, `F&B`, `O&M`, `P&R`, `L&D`, `M&A`, `R&R`** |
| `@` | 1,524 | 쪼개는 게 맞음 | 이메일 |
| **`_`** | **452** | **고쳤습니다** | 식별자 문자. 같은 종류의 조각을 만듦 |
| `=`, `?`, `'`, `’` | 1,006 | 쪼개는 게 맞음 | URL·산문 |
| **`–`, `—`** | **120** | **고쳤습니다** | 하이픈처럼 쓰임 (`Edge–Cloud–Web`) |

**실제 미처리 쪼갬은 `&` 하나였고, `_`와 en/em 대시를 같은 원칙으로 함께 처리했습니다.**
나머지 기호는 공고에서 **서로 다른 것을 구분**하므로 쪼개는 것이 맞습니다.
이 판정을 테스트로 고정했습니다 (`test_separators_that_divide_different_things_are_left_alone`).

### 후보 목록 쪽 확인

89회 이상 후보 608종 중 1~2글자 84종을 뽑아 도구 로그의 문맥을 읽었습니다.
`&` 유래가 확인된 것은 `D`, `QA`, `B`, `F`, `M`, `O`, `P`, `L`, `AP`, `CJ` 10종이었습니다.

### 수정 효과

| 후보 | 수정 전 | 수정 후 |
| --- | ---: | ---: |
| `R` | 1,971 | **153** (−92%) |
| `D` | 2,729 | **1,184** (−57%) |
| `R&D` | 없음 | **1,767** (신규) |
| `B` | 645 | 506 |
| `F` | 292 | 180 |
| `P` | 133 | 48 |
| `Q&A` / `F&B` / `O&M` | 없음 | 45 / 83 / 6 (신규) |

**`R`은 실제 언어입니다.** `R&D`가 많은 공고 때문에 1,971회로 집계되어 있었는데,
실제로는 153회였습니다. 92%가 거짓이었습니다.

| 지표 | 수정 전 | 수정 후 |
| --- | ---: | ---: |
| 서로 다른 항목 (정리 전) | 27,642 | 27,788 |
| 규칙 수 (정리 전) | 2,757 | **2,699** |
| 규칙 수 (정리 후) | 2,197 | **2,191** |
| 판단 대상 후보 | 608 | 607 |
| 제거된 등장 횟수 | 24,351 | 22,657 |

제거 횟수가 줄어든 것은 **`D` 2,729건이 더 이상 가짜로 부풀려지지 않기 때문**입니다.

## 6-2. 그 밖의 한계

| # | 한계 | 영향 |
| --- | --- | --- |
| 1 | **fake 결과는 성능이 아닙니다.** 규칙표에 없는 433종이 `needs_review`로 남음 | 정리 효과가 실제보다 작게 측정됨 |
| 2 | **`learned_hits=0`** — 학습 계층이 실제 데이터에서 발동하지 않음 | 2-4절에 사유 기록. 테스트로만 검증 |
| 3 | 원문 오타(`Javasc ript`)는 고칠 수 없음 | `Javasc → ript` 규칙 잔존 |
| 4 | 89회 하한 밖 27,033종은 판단하지 않음 | 규칙 분석에는 무영향, 개별 공고 품질은 낮음 |
| 5 | 띄어쓴 이름(`Spring Boot`)을 조립하지 않음 | `Boot`가 `needs_review`에 남음. 5-5절 원인 1 참조 |
| 6 | `concept` 분류 제외를 적용하지 않음 | `AI`가 여전히 Apriori 항목 |
| 7 | GLM 실제 호출을 검증하지 못함 | 키가 없어 응답 파서만 테스트로 검증 |
| 8 | 한글 표기 61종은 측정된 범위에서만 유효 | 새 export에서는 재측정 필요 |
| 9 | 어휘 안 정밀도 1.9%p 하락은 **평가 설계 때문** | 5-5절 원인 3. 고칠 수 없고 측정만 가능 |
| 10 | `@`·URL에서 나온 조각이 후보에 섞임 | 6-1절 전수 표. 쪼개는 것이 맞지만 조각은 남음 |

---

# 7. 테스트

**57개 → 132개**, 전부 통과 (최초 118 → 갱신 132).

| 파일 | 개수 | 검증 내용 |
| --- | ---: | --- |
| `test_agent_extract.py` | 28 | 한글 긴 표기 우선, 경계 검사, 열린 토큰화 금지, **`&` 복합어, 구분자 판정** |
| `test_agent_dictionary.py` | 15 | 한글 표기 목표·근거·중복, 제외 사유 존재 |
| `test_agent_providers.py` | 21 | 4경로, 결정성, 응답 파싱, 어휘 밖 이름 거부, 키 부재 메시지, `.env` 미커밋, **제외 목록 일치** |
| `test_agent_loop.py` | 16 | 사전 적중 시 모델 미호출, 학습 반영, 신뢰도 하향, 예산, 캐시, 로그 전건 |
| `test_agent_recommend.py` | 11 | 완화 순서, `no_rules` 비완화, 기술명 불변, 고지 필드 |
| `test_agent_compare.py` | 18 | 비교 키 기호·**한글** 보존, 어휘 안/밖 분리, **버킷 이동 분류**, 동일 집합, 검수 시트 |

## 갱신에서 추가한 테스트

```python
# & 복합어가 쪼개지지 않음
def test_rd_stays_whole_and_never_yields_r_or_d(self):
    names = self._names("연구 R&D 담당")
    self.assertEqual(names, {"R&D"})
    self.assertNotIn("R", names)   # R 은 실제 언어 -- 부풀리면 안 됨

# 쪼개는 것이 맞는 구분자는 건드리지 않음
def test_separators_that_divide_different_things_are_left_alone(self):
    self.assertEqual(self._names("09:00 ~ 18:00"), set())
    self.assertEqual(self._names("솔루션·SI·CRM"), {"SI", "CRM"})

# 사전의 제외 목록과 판단기의 규칙표가 어긋나면 실패
def test_no_curated_exclusion_is_mapped_by_the_rule_table(self):
    for spelling in self.curated["excluded_on_purpose"]:
        self.assertNotEqual(self.judge.judge(spelling, {}).decision, "canonical")

# 비교 키가 한글을 지우지 않음
def test_hangul_is_kept_so_korean_spellings_do_not_collapse(self):
    self.assertNotEqual(comparison_key("생성형 AI"), comparison_key("AI"))
    self.assertNotEqual(comparison_key("딥러닝"), "")
```

## 요청하신 항목의 테스트

```python
# 긴 표기 우선 — '자바스크립트'가 '자바'로 잡히지 않음
def test_the_longest_spelling_wins_so_자바스크립트_is_not_자바(self):
    self.assertEqual(self._names("자바스크립트"), {"자바스크립트"})

# 경계 검사 — 일반 단어 오탐 방지
def test_a_spelling_inside_a_longer_hangul_run_does_not_count(self):
    self.assertEqual(self._names("코드 리뷰 진행"), set())   # 뷰
    self.assertEqual(self._names("그루비 스크립트"), set())   # 루비 (Groovy)
    self.assertEqual(self._names("냉장고 유지보수"), set())   # 장고
    self.assertEqual(self._names("일러스트 작업"), set())     # 러스트

# 열린 토큰화를 하지 않음
def test_unregistered_hangul_is_not_tokenised(self):
    self.assertEqual(self._names("우대사항 협업 능력 커뮤니케이션"), set())

# 사전 적중 시 모델을 부르지 않음 (비용의 핵심)
def test_a_confirmed_dictionary_hit_never_reaches_the_model(self):
    ...
    self.assertEqual(judge.calls, [])
    self.assertEqual([step["tool"] for step in log.steps], ["cache", "lookup_dictionary"])

# 결과 반영 — 앞선 판단이 뒤의 후보를 처리함
def test_a_judgement_is_reflected_back_and_serves_a_later_candidate(self):
    _run("SpringBoot", ...)
    judgement, log, called = _run("springboot", ...)
    self.assertEqual(judge.calls, ["SpringBoot"])   # 두 번 묻지 않음
    self.assertEqual(counters.learned_hits, 1)
```

---

# 8. 재현 명령

```bash
# 10~14주차 (변경 없음)
.venv/bin/python -m src.ingestion.run_week10 --input data/raw/korean_it_recruit_postings.json \
  --config configs/data_scope.json --output-dir artifacts
.venv/bin/python -m src.normalization.run_week11 --input data/raw/korean_it_recruit_postings.json \
  --output data/processed/postings_normalized.jsonl --artifact-dir artifacts
.venv/bin/python -m src.analysis.run_week12
.venv/bin/python -m src.service.run_week13
.venv/bin/python -m src.analysis.run_week14

# 후보 추출 -> 사전 v2 -> 에이전트 -> 비교
.venv/bin/python -m src.agent.run_extract
.venv/bin/python -m src.agent.build_dictionary
.venv/bin/python -m src.agent.run_agent                 # 기본 provider=fake
.venv/bin/python -m src.agent.run_compare

# 추천 (재시도 포함)
.venv/bin/python -m src.agent.run_recommend --skills 파이썬
.venv/bin/python -m src.agent.run_recommend --skills .NET --role frontend --experience 1~3년차

.venv/bin/python -m unittest discover -s tests          # 118 tests, OK
```

| 옵션 | 용도 |
| --- | --- |
| `run_agent --limit 300` | 작은 표본 스모크 |
| `run_agent --no-cache` | 캐시 없이 실행해 학습 계층 확인 |
| `run_agent --provider glm` | 실제 모델. 키 없으면 즉시 중단 |
| `run_compare --reviewers 3` | 검수 사본 개수 변경 |

## 새 파일

| 파일 | 역할 |
| --- | --- |
| `src/agent/judgement.py` | 4가지 판단 결과와 검증 |
| `src/agent/fake_judge.py` | 규칙표 기반 가짜 판단기 |
| `src/agent/judge.py` | 프롬프트, 응답 파싱, 어휘 밖 이름 거부 |
| `src/agent/memory.py` | 확정·학습 두 층, v2 사전 로더 |
| `src/agent/cache.py` | 이름 단위 캐시, `NullCache` |
| `src/agent/tools.py` | 도구 7개, 1패스 문맥 인덱스 |
| `src/agent/loop.py` | 후보 1개 처리와 단계 로그 |
| `src/agent/run_agent.py` | 정리 실행 |
| `src/agent/recommend.py` | 완화와 고지 |
| `src/agent/run_recommend.py` | 추천 CLI |
| `src/agent/run_compare.py` | 3자 비교와 검수 시트 |
| `src/llm/glm_provider.py` | GLM. 요청할 때만 생성 |
| `configs/agent.json` | 임계값, 하한, 예산 |
| `configs/tech_dictionary_korean.json` | 한글 표기 61종과 제외 13종 |
| `.env.example` | 키 자리만 (값 없음) |

## 산출물

| 파일 | 내용 |
| --- | --- |
| `artifacts/agent_run_summary.json` | 판단 분포, 비용, `is_mock` |
| `artifacts/agent_decisions.json` | 후보 608종의 최종 판단 |
| `artifacts/agent_tool_log.json` | **도구 호출 3,423회 전건** |
| `artifacts/agent_comparison.json` | 3자 비교, 어휘 안/밖 지표, 편향 경고 |
| `artifacts/agent_review_sheet*.csv` | 검수 시트 (원본 + 검수자 2명분) |
| `artifacts/agent_cache.json` | 캐시. **`.gitignore` 대상** (재생성 가능) |
| `data/processed/postings_agent_cleaned.jsonl` | 정리된 기술 목록. `.gitignore` 대상 |

---

# 9. 다음 단계

| 순위 | 할 일 | 근거 |
| --- | --- | --- |
| ~~1~~ | ~~`&` 쪼개짐 수정~~ | **완료** (6-1절) |
| 1 | 실제 GLM 연결 후 표본 1%(187건) 검증 | [03](03_agent_design.md) 9-3절 순서. `needs_review` 434종이 대기 |
| 2 | 검수 시트 2명 판정 → [03](03_agent_design.md) 6절 두 질문 측정 | 5-4절 시트 준비 완료. `final_techs`를 쓰지 않으므로 5-5절 편향에서 자유로움 |
| 3 | `concept` 분류 제외 실험 | `AI`가 등장 1위인 채로 Apriori에 들어감 |
| 4 | 띄어쓴 이름 조립을 에이전트에 맡기기 | `Boot` 등 `needs_review` 잔존 (5-5절 원인 1) |
| 5 | 표준 어휘 확장 여부 결정 | `new_technology` 9종 + 어휘 밖 6,579회. 확장하면 5-5절 버킷 이동도 줄어듦 |
