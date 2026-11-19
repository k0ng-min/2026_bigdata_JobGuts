# 00. gyeongseon 브랜치 요약 (5분 판단용)

- 브랜치: `gyeongseon` (분기점 `5482b2a`)
- 기준 일자: 2026-11-19
- 테스트: **132개 전부 통과** (분기 시점 8개)
- 전체 파이프라인 재현 확인: 처음부터 두 번 돌려 산출물 동일

> **이 문서만 읽고 판단할 수 있게 썼습니다.** 근거가 필요한 항목은 각 줄의 링크를 따라가면 됩니다.
> 상세: [01 점검](01_baseline_check.md) · [02 기반 수정](02_foundation_fixes.md) · [03 에이전트 설계](03_agent_design.md) · [04 사전 v2](04_dictionary_v2.md) · [05 에이전트 구현](05_agent_implementation.md)

---

# 1. 한눈에 보기

| 영역 | 분기 시점 | 현재 |
| --- | ---: | ---: |
| 저장되는 연관규칙 | 50개 (694개 중) | **694개 전체** |
| 추천 가능한 기술 종류 | 33종 | **94종** |
| 기술명 사전 표준 이름 | 14개 | **130개** |
| 사전 표기 (별칭) | 40개 | **314개** (한글 61 포함) |
| 실제로 변환이 일어나는 표기 | **1종** (`Ajax`→`AJAX`, 그마저 오류) | **33종** |
| LLM 에이전트 4요소 | 0 / 4 | **4 / 4** (단서 있음, 4-2절) |
| 도구 호출 로그 | 없음 | **3,416회 전건** |
| 추천 실패 시 재시도 | 없음 | **있음** (범위 변경 고지 포함) |
| 13·14주차 산출물 생성 코드 | **없음** | **있음** |
| 테스트 | 8개 | **132개** |

---

# 2. 고친 문제 (기존 버전에 있던 결함)

링크는 근거 문서의 해당 절입니다.

| # | 문제 | 전 | 후 | 근거 |
| --- | --- | ---: | ---: | --- |
| 1 | `[:50]` 때문에 규칙 694개 중 50개만 저장 → `Python`·`Java`·`AWS` 가 `no_rules` | 33종 추천 | **94종** | [02](02_foundation_fixes.md) 1절 |
| 2 | `경력무관` 6,597건이 `신입`으로 분류 (`entry` 세그먼트의 92%가 오분류) | 7,151 혼합 | **신입 554 / 경력무관 6,597 분리** | [02](02_foundation_fixes.md) 2절 |
| 3 | 13·14주차 산출물에 **생성 코드가 없음**, 구버전 수치(18,163) | 재현 불가 | **재현 가능** | [02](02_foundation_fixes.md) 3절 |
| 4 | 12주차 문서 수치가 구버전 | 18,163 / 707 | **17,796 / 694** | [02](02_foundation_fixes.md) 4절 |
| 5 | 주차 보고서가 숫자를 하드코딩 (산출물을 읽고도 쓰지 않음) | 수동 | **산출물에서 자동** | [02](02_foundation_fixes.md) 4절 |
| 6 | `configs/experiments.json` 중복 정책 설명이 코드와 **반대** | 틀림 | **수정** | [02](02_foundation_fixes.md) 4절 |
| 7 | 사전 v1의 유일한 별칭이 **어휘 밖 이름**(`AJAX`)을 표준으로 삼음 | 오류 | **`Ajax` 로 정정** | [04](04_dictionary_v2.md) 2-4절 |
| 8 | 추출이 `C`/`C++`/`C#` 를 한 덩어리로 뭉갬, `.NET` 소실 | 구분 안 됨 | **구분** | [04](04_dictionary_v2.md) 1절 |
| 9 | 추출이 `Wi-Fi`→`Wi`+`Fi`, `CI/CD`→`CI`+`CD` 로 쪼갬 (`Wi → Fi` 가 interest 0.98 상위 규칙) | 노이즈 | **제거** | [04](04_dictionary_v2.md) 1절 |
| 10 | 추출이 `R&D`→`R`+`D` 로 쪼갬 — **`R`은 실제 언어** | `R` 1,971회 | **`R` 153회** (92%가 거짓) | [05](05_agent_implementation.md) 6-1절 |
| 11 | 한글 기술명이 전혀 추출되지 않음 | 0 | **61종 표기** | [05](05_agent_implementation.md) 1절 |
| 12 | 평가 비교 키가 한글을 제거 (`딥러닝`·`자바`·`파이썬` 이 모두 빈 문자열) | 버그 | **수정** | [05](05_agent_implementation.md) 5-5절 |
| 13 | fake 판단기가 `Boot`→`Spring Boot` 매핑 (사전이 **의도적으로 제외**한 판단) | 오답 1,192건 | **제거** | [05](05_agent_implementation.md) 5-5절 |

## 추가한 기능

| 기능 | 내용 | 근거 |
| --- | --- | --- |
| 한글 표기 추출 | 닫힌 목록 조회 + 긴 표기 우선 + 한글 경계 검사 | [05](05_agent_implementation.md) 1절 |
| 기술명 사전 v2 | 표준 이름 130개, 표기 314개, 각 항목에 규칙·분류·근거 | [04](04_dictionary_v2.md) 2절 |
| 에이전트 루프 | 사전 → 문맥 도구 → 판단 → 기억 반영, 4가지 결과 | [05](05_agent_implementation.md) 2절 |
| 도구 호출 로그 | 3,416회 전건, 13주차 증거용 | [05](05_agent_implementation.md) 2-6절 |
| GLM provider | 키는 환경 변수만, 기본 실행·테스트에서 미호출 | [05](05_agent_implementation.md) 3절 |
| 추천 재시도 | `insufficient_sample` 시 필터 완화 + 범위 변경 고지 | [05](05_agent_implementation.md) 4절 |
| 3자 비교 | 정리 전 / 정리 후 / `final_techs`, 어휘 안·밖 분리 | [05](05_agent_implementation.md) 5절 |
| 사람 검수 시트 | 상위 50×2 섞기, 판정 칸 비움, 검수자 2명분 | [05](05_agent_implementation.md) 5-4절 |

---

# 3. 과제 조건 충족 상태

## 3-1. 빅데이터 개념 — 충족

| 요소 | 현황 |
| --- | --- |
| 데이터 규모 | 공개 데이터셋 **40,348 공고 / 170 MiB**, SHA-256 고정 |
| 전처리 | 결측·중복(ID 777 / 동일 본문 933) 기준 확정, 분석 트랜잭션 **17,796** |
| 분석 기법 | **Apriori 연관규칙** (support 0.005, confidence 0.2) → 규칙 **694개** |
| 지표 | support, confidence, **interest = confidence − P(결과)** |
| 재현성 | 파이프라인 1회 실행으로 10~14주차 산출물 전체 재생성, 두 번 돌려 동일 확인 |
| 산출물 | 품질 요약·규칙·그래프(노드 94 / 엣지 694)·세그먼트(21개) |

**근거 파일**: `artifacts/week10_data_quality_summary.json`, `week12_rule_comparison.json`, `week12_all_rules.json`, `week14_skill_graph.json`

## 3-2. LLM 에이전트 — 구조는 충족, 실제 모델 미연결

4요소가 모두 구현되고 로그로 증명됩니다.

| 요소 | 구현 | 로그 증거 |
| --- | --- | ---: |
| ① 추론 | `judge.py` → provider | `judge` **447회** |
| ② 기억 참조 | 확정 사전 (`memory.py`) | `lookup_dictionary` **574회**, 적중 127 |
| ③ 도구 호출 | 도구 7개 (`tools.py`) | `get_context` **447회**, `get_cooccurrence` **447회** |
| ④ 결과 반영 | 학습 층 + `propose_canonical` | `lookup_learned` **447회 조회**, **실제 적중 0회** |

**정직하게 밝혀야 할 두 가지입니다.**

1. **실제 LLM은 아직 연결하지 않았습니다.** 기본 실행은 fake 판단기이고, 모든 산출물에
   `is_mock: true`와 경고문이 박혀 있습니다. **fake 결과는 성능이 아닙니다.**
2. **④의 실제 적중이 0회입니다.** 구현되고 447회 조회되지만, fake 판단기가 `canonical`로 판정하는
   표기가 이미 사전에 다 있어서 학습 층이 메울 틈이 없습니다. 테스트로만 발동을 확인했습니다.
   → 실제 GLM이 `needs_review` 434종을 판단하면 이 숫자가 의미를 갖습니다. ([05](05_agent_implementation.md) 2-4절)

**근거 파일**: `artifacts/agent_tool_log.json`, `agent_decisions.json`, `agent_run_summary.json`

## 3-3. 모델 — 규칙 기반 모델 있음, LLM은 미연결

| 항목 | 현황 |
| --- | --- |
| 분석 모델 | Apriori 연관규칙 **694개**. 선행 기술 94종 |
| 서비스 모델 | 저장된 규칙 조회 + 근거 공고 최대 3건. 규칙을 재계산하지 않음 |
| 응답 경로 | `ok` / `no_rules` / `insufficient_sample` 5개 시나리오 검증 |
| 언어 모델 | **미연결.** provider 인터페이스·fake 구현·GLM 파일까지 준비 완료 |
| 평가 준비 | 3자 비교 + 어휘 안/밖 분리 + 검수 시트 |

**평가에 대한 중요한 단서** ([05](05_agent_implementation.md) 5-5절):
정밀도 단독으로 판단하면 안 됩니다. 표준 이름을 `final_techs`에서 가져왔고 정답지도 같은
`final_techs`이므로 구조적 편향이 있습니다. 어휘 안 정밀도가 74.9% → 73.0%로 내려가지만
**전수 분석 결과 새로 생긴 오답 0건, 잃어버린 정답 0건**이고, 전부 버킷 이동 효과입니다.
봐야 할 숫자는 재현율(74.6% → **79.6%**)과 F1(74.9% → **76.3%**)입니다.

---

# 4. 처음부터 재현하는 명령

## 4-1. WSL · macOS · Linux

```bash
cd ~/projects/JobGuts
git fetch origin && git switch gyeongseon && git pull

# 1) 가상환경 (파이프라인은 표준 라이브러리만 사용, python-docx는 보고서용)
python3 -m venv .venv
.venv/bin/pip install python-docx

# 2) 원본 데이터 (약 170 MiB, Git 제외 경로)
mkdir -p data/raw data/processed
curl -fL --retry 3 -o data/raw/korean_it_recruit_postings.json \
  "https://huggingface.co/datasets/young-cc/korean-it-recruit-dataset/resolve/main/master_merged_v5.json?download=true"
sha256sum data/raw/korean_it_recruit_postings.json
# 기대값: dc7cc15b1ee80dbf5f959095ee78aad0e8dd39d5156cf694e60591aa1bd9a58f

# 3) 10~14주차
.venv/bin/python -m src.ingestion.run_week10 --input data/raw/korean_it_recruit_postings.json \
  --config configs/data_scope.json --output-dir artifacts
.venv/bin/python -m src.normalization.run_week11 --input data/raw/korean_it_recruit_postings.json \
  --output data/processed/postings_normalized.jsonl --artifact-dir artifacts
.venv/bin/python -m src.analysis.run_week12
.venv/bin/python -m src.service.run_week13
.venv/bin/python -m src.analysis.run_week14

# 4) 에이전트 (기본 provider=fake, 키·네트워크 불필요)
.venv/bin/python -m src.agent.run_extract
.venv/bin/python -m src.agent.build_dictionary
.venv/bin/python -m src.agent.run_agent
.venv/bin/python -m src.agent.run_compare

# 5) 테스트와 보고서
.venv/bin/python -m unittest discover -s tests          # 132 tests, OK
.venv/bin/python scripts/build_weekly_reports.py

# 6) 추천 확인
.venv/bin/python -m src.agent.run_recommend --skills 파이썬
.venv/bin/python -m src.agent.run_recommend --skills .NET --role frontend --experience 1~3년차
```

소요 시간: 데이터 받기 약 20초, 전 단계 합계 약 4분 (에이전트 1분, 비교 1분 20초 포함).

## 4-2. Windows PowerShell

```powershell
cd ~\projects\JobGuts
git fetch origin; git switch gyeongseon; git pull

# 1) 가상환경
python -m venv .venv
.\.venv\Scripts\pip install python-docx

# 2) 원본 데이터
New-Item -ItemType Directory -Force data\raw, data\processed | Out-Null
Invoke-WebRequest -Uri "https://huggingface.co/datasets/young-cc/korean-it-recruit-dataset/resolve/main/master_merged_v5.json?download=true" `
  -OutFile data\raw\korean_it_recruit_postings.json
Get-FileHash data\raw\korean_it_recruit_postings.json -Algorithm SHA256
# 기대값: DC7CC15B1EE80DBF5F959095EE78AAD0E8DD39D5156CF694E60591AA1BD9A58F

# 3) 10~14주차 (스크립트 한 번으로)
.\scripts\run_pipeline.ps1

# 또는 단계별로
.\.venv\Scripts\python -m src.ingestion.run_week10 --input data/raw/korean_it_recruit_postings.json `
  --config configs/data_scope.json --output-dir artifacts
.\.venv\Scripts\python -m src.normalization.run_week11 --input data/raw/korean_it_recruit_postings.json `
  --output data/processed/postings_normalized.jsonl --artifact-dir artifacts
.\.venv\Scripts\python -m src.analysis.run_week12
.\.venv\Scripts\python -m src.service.run_week13
.\.venv\Scripts\python -m src.analysis.run_week14

# 4) 에이전트
.\.venv\Scripts\python -m src.agent.run_extract
.\.venv\Scripts\python -m src.agent.build_dictionary
.\.venv\Scripts\python -m src.agent.run_agent
.\.venv\Scripts\python -m src.agent.run_compare

# 5) 테스트와 보고서
.\.venv\Scripts\python -m unittest discover -s tests
.\.venv\Scripts\python scripts\build_weekly_reports.py

# 6) 추천 확인
.\.venv\Scripts\python -m src.agent.run_recommend --skills 파이썬
```

### PowerShell에서 주의할 점 두 가지

| 항목 | 내용 |
| --- | --- |
| `--experience 1~3년차` | PowerShell에서 한글 인수가 깨지면 `--experience "1~3년차"` 로 따옴표를 씌웁니다 |
| 줄바꿈 diff | Windows는 CRLF, WSL은 LF로 파일을 씁니다. `reports/assets/week10/week10_raw_text_samples.csv` 가 내용 변화 없이 전체 diff로 보일 수 있습니다. 커밋 전에 `git diff` 로 확인하세요 (6-2절) |

## 4-3. 재현 확인 방법

```bash
# 두 번 돌려 산출물이 같은지
git status --short -- artifacts/ configs/
# 출력이 비어 있으면 완전 재현
```

단, `artifacts/week10_data_quality_summary.json`의 `path` 한 줄은 OS에 따라
`data\raw\...` 와 `data/raw/...` 로 달라집니다. 수치는 동일합니다.

---

# 5. GLM 연결 시 해야 할 일

현재는 **fake 판단기**가 기본이고, 실제 모델은 연결되어 있지 않습니다.
`src/llm/glm_provider.py`는 준비되어 있으며 `--provider glm` 일 때만 생성됩니다.

## 5-1. 키와 주소·모델 설정

결제 상품은 **Z.ai GLM Coding Plan Pro** 입니다.

```bash
cp .env.example .env
# .env 를 열어 세 값을 채웁니다
```

```
GLM_API_KEY=<발급받은 키>
GLM_BASE_URL=https://api.z.ai/api/coding/paas/v4
GLM_MODEL=GLM-5.3-Flash
```

| 변수 | 값 | 비고 |
| --- | --- | --- |
| `GLM_API_KEY` | 발급받은 키 | 커밋 금지 |
| `GLM_BASE_URL` | `https://api.z.ai/api/coding/paas/v4` | **API 루트만** 적습니다. 코드가 `/chat/completions` 를 붙입니다 |
| `GLM_MODEL` | `GLM-5.3` 또는 `GLM-5.3-Flash` | 표본 실행은 빠르고 싼 `GLM-5.3-Flash` 로 시작하는 것을 권합니다 |

**세 값 모두 기본값이 없습니다.** 코드에 주소나 모델을 박아 두면 팀이 고르지 않은 곳으로
요청이 나가므로, 값이 비어 있으면 변수 이름을 알려 주고 멈춥니다.

```
GLM_BASE_URL is not set, so the GLM provider cannot run.
  It has no default on purpose: a hardcoded value would send the request
  somewhere the team did not choose.
  Set GLM_BASE_URL to the API root, for example https://api.z.ai/api/coding/paas/v4
  (the code appends /chat/completions itself).
  ...
  To run without a model, use --provider fake.
```

| 규칙 | 내용 |
| --- | --- |
| `.env` 는 **커밋하지 않습니다** | `.gitignore`에 포함. `.env.example` 만 커밋되어 있고 값은 모두 비어 있음 |
| 셸 export 가 우선 | `export GLM_API_KEY=...` 가 `.env` 값을 덮습니다 |
| 엔드포인트 결합은 한 곳 | `src/llm/glm_provider.py` 의 `chat_endpoint()`. 루트 뒤에 `/chat/completions` 를 붙이고, 이미 붙어 있으면 중복하지 않습니다 |

## 5-2. 연결 확인 (요청 1회)

표본 실행 전에 **한 번** 돌려 설정 오류를 한 번의 호출로 드러냅니다.

```bash
.venv/bin/python -m src.agent.check_glm
```

성공하면 이렇게 나옵니다. **키는 출력하지 않습니다** — 길이와 끝 두 글자만 보여 줍니다.

```
GLM connection check — sends exactly one short request.
  GLM_API_KEY: set (length 42, ends with ...7f)
  GLM_BASE_URL: https://api.z.ai/api/coding/paas/v4
  endpoint: https://api.z.ai/api/coding/paas/v4/chat/completions
  GLM_MODEL: GLM-5.3-Flash
  timeout: 20s

Sending one request...

OK
  provider: glm
  is_mock: False
  reply: 'ok'
```

실패하면 **원인 유형별로** 알려 줍니다. 유형마다 고치는 곳이 다릅니다.

| 유형 | 언제 | 고칠 곳 |
| --- | --- | --- |
| `configuration` | 세 값 중 하나가 비어 있음 | `.env` |
| `authentication` | 401 / 403 | `GLM_API_KEY` |
| `address` | 404 | `GLM_BASE_URL` (루트만 적었는지) |
| `model or request` | 400 / 422 | `GLM_MODEL` |
| `rate limit` | 429 | 잠시 후 재시도 |
| `network` | 연결 실패 | 네트워크·호스트명 |
| `response` | 응답 모양이 예상과 다름 | 모델 응답 형식 |
| `server` | 그 밖의 HTTP 오류 | 서버 상태 |

## 5-3. 표본부터 돌리는 순서 (비용 관리)

전체를 바로 돌리지 않습니다. [03](03_agent_design.md) 9-3절의 순서입니다.

| 순서 | 명령 | 예상 호출 | 통과 조건 |
| --- | --- | ---: | --- |
| 0 | `python -m src.agent.check_glm` | **1** | `OK` 출력 |
| 1 | `run_agent --provider fake --limit 300` | 0 | 네 경로 모두 1건 이상, 두 번 돌려 결과 동일 |
| 2 | `run_agent --provider glm --limit 187` (1%) | 약 100~200 | 판단 품질을 사람이 50건 직접 확인 |
| 3 | `run_agent --provider glm --limit 939` (5%) | 약 400~600 | 2단계와 지표 차이 5%p 이내 |
| 4 | `run_agent --provider glm` (전체) | **약 447** | 최종 산출물 |

```bash
# 2단계 예시 — 기존 산출물을 덮지 않도록 별도 경로에 씁니다
.venv/bin/python -m src.agent.run_agent --provider glm --limit 187 \
  --artifact-dir artifacts/glm_sample --cleaned-output data/processed/postings_glm_sample.jsonl
```

2단계에서 품질이 목표에 크게 못 미치면 **3·4단계로 넘어가지 않습니다.**
프롬프트(`src/agent/judge.py`)나 임계값(`configs/agent.json`)을 고치고 2단계를 다시 돌립니다.

### 비용 안전장치 (이미 들어 있음)

| 장치 | 설정 | 효과 |
| --- | --- | --- |
| 등장 횟수 하한 | `minimum_occurrences_for_llm: 89` | 후보 27,787종 → **607종**만 판단 |
| 이름 단위 캐시 | `artifacts/agent_cache.json` | 2회차 실행 호출 **0회** |
| 호출 상한 | `max_llm_calls: 5000` | 초과 시 중단하고 그때까지 결과 저장 |
| 짧은 문맥 | `snippet_window: 120` | 토큰 수 억제 |

하한 89의 근거: support 0.005 × 17,796 트랜잭션 = 89. **89회 미만은 어떤 규칙에도 들어갈 수 없습니다.**

## 5-4. 연결 후 바로 확인할 것

```bash
.venv/bin/python -m src.agent.run_compare
```

| 확인 | 기대 |
| --- | --- |
| `is_mock` | **`false`** 로 바뀌었는지 |
| `needs_review` | 434종에서 줄어들었는지 |
| `learned_hits` | 0에서 늘어났는지 (④ 요소가 실제로 발동하는지) |
| `newly_introduced` | **0을 유지하는지** (새 오답을 만들지 않았는지) |
| `correct_names_lost` | **0을 유지하는지** |
| 상위 규칙 | `Cytiva → Y` 같은 회사명 규칙이 사라졌는지 |

---

# 6. 남은 한계

## 6-1. 과제 평가에 직접 영향

| # | 한계 | 상태 |
| --- | --- | --- |
| 1 | **실제 LLM 미연결** — fake 결과는 성능이 아님 | 키만 있으면 5절 순서로 진행 |
| 2 | **④ 결과 반영 실제 적중 0회** — 구현·조회는 되지만 fake에서 발동 안 함 | 실제 모델 연결 시 해소 예상 |
| 3 | `needs_review` **434종**이 미판단으로 남음 (등장 기준 58.0%) | 같음 |
| 4 | 어휘 안 정밀도 1.9%p 하락은 **평가 설계 탓** | 측정해 드러냄. 재현율·F1로 판단 ([05](05_agent_implementation.md) 5-5절) |

## 6-2. 데이터·도구 한계

| # | 한계 | 영향 |
| --- | --- | --- |
| 5 | 직무 분류 **94.1%가 `other_tech`** (제목이 64.3% 비어 있음) | 직무별 비교 불가 |
| 6 | 원문 오타는 고칠 수 없음 (`Javasc ript` 에 실제 공백) | `Javasc → ript` 규칙 잔존 |
| 7 | 띄어쓴 이름(`Spring Boot`)을 조립하지 않음 | `Boot` 가 `needs_review` 에 남음 |
| 8 | `concept` 분류(14개) 제외를 적용하지 않음 | `AI`(등장 1위)가 Apriori 항목으로 들어감 |
| 9 | 89회 하한 밖 27,180종 미판단 | 규칙 분석엔 무영향, 개별 공고 품질은 낮음 |
| 10 | 필터가 지표를 재계산하지 않음 | 응답에 `metrics_note` 로 항상 고지 |

## 6-3. 팀 합의가 필요한 사항

| # | 사항 | 설명 |
| --- | --- | --- |
| 11 | **원문 텍스트가 커밋되어 있음** | `.gitignore`는 `artifacts/week10_raw_text_samples.csv` 를 막는데, 같은 내용이 `reports/assets/week10/` 에 공고 원문 214줄로 커밋되어 있습니다. "데이터 커밋 금지" 원칙과 어긋납니다 |
| 12 | **줄바꿈 문자 충돌** | 같은 파일이 Windows(CRLF)와 WSL(LF)에서 전체 diff로 보입니다. `.gitattributes` 로 해결되지만 기존 커밋 파일이 한꺼번에 재정규화되어 큰 diff가 생기므로 함께 결정하는 편이 안전합니다 |
| 13 | **표준 어휘 확장 여부** | `RAG`·`JSP`·`IoT` 등 어휘 밖 실제 기술이 등장 6,579회. 확장하면 사전과 정답지가 함께 바뀌므로 전후 지표를 모두 보고해야 합니다 |

---

# 7. 다음 작업 (권장 순서)

| 순위 | 할 일 | 왜 지금인가 |
| --- | --- | --- |
| 1 | **GLM 키 받아 표본 1%(187건) 실행** | 5-2절 순서가 준비됨. `needs_review` 434종이 대기 중 |
| 2 | **검수 시트 2명 판정** → [03](03_agent_design.md) 6절 두 질문 측정 | 시트가 이미 생성되어 있고, `final_techs`를 쓰지 않아 편향에서 자유로움 |
| 3 | `concept` 14개를 Apriori에서 제외하는 실험 | 분류가 이미 부여되어 있어 설정만 바꾸면 됨 |
| 4 | 띄어쓴 이름 조립을 에이전트에 맡기기 | `Boot` 등이 `needs_review` 에 남아 있음 |
| 5 | `.gitattributes` 와 원문 커밋 정리 | 6-3절. 팀 합의 후 |

---

# 8. 커밋 목록

```
51ddf16  docs: record the agent implementation ...
47640c2  feat: compare before, after and final_techs, and prepare human review
38a8082  feat: widen filters on an empty result and disclose that it happened
3457228  feat: add the cleanup agent loop with a full tool-call log
ec251d4  feat: add the fake judge and a GLM provider that only runs when asked
d39b481  feat: find registered Korean technology spellings in raw_text
8fb9577  docs: design the LLM agent for raw_text technology cleanup
8a8e7f2  docs: record the extraction fix and dictionary v2 ...
604c35c  feat: build dictionary v2 from the data's own vocabulary
99748d7  feat: extract uncleaned technology candidates without splitting names
25190ae  docs: use team-wide wording in gyeongseon docs
57a4e24  docs: record the foundation fixes with before and after figures
b8fdb36  docs: refresh stale weekly figures and derive report numbers from artifacts
19470d5  feat: add runners that regenerate the week-13 and week-14 artifacts
d80fe67  fix: stop relabelling 경력무관 postings as entry level
bbd7ad2  fix: persist every association rule instead of only the top 50
00c299c  docs: add baseline reproducibility check for k0ng_min pipeline
```
그 뒤로 `a125120`(`&` 쪼개짐·`Boot`·비교 키 수정), `05dd114`(05 문서 갱신)이 이어집니다.

`main`, `dev`, `k0ng_min` 브랜치는 **건드리지 않았습니다.**
