# 01. 베이스라인 점검 (gyeongseon)

- 점검 일자: 2026-11-18
- 점검 브랜치: `gyeongseon` (`origin/main`에서 분기 후 `origin/k0ng_min`을 fast-forward)
- 점검 기준 커밋: `5482b2a style: refine local dashboard`
- 실행 환경: WSL2 / Ubuntu / Python 3.12.3 / 로컬 가상환경 `.venv`
- 이 문서의 범위: **실행 검증과 진단만** 수행했고, 기존 코드는 한 글자도 고치지 않았습니다.

> 저장소 문서의 명령은 PowerShell 기준이라, WSL에서는 `Invoke-WebRequest` → `curl -fL`,
> `./scripts/run_pipeline.ps1` → 같은 순서의 `python -m ...` 직접 실행으로 바꿔서 확인했습니다.

---

## 요약 (먼저 읽을 결론)

| # | 결론 | 상태 |
|---|---|---|
| 1 | 데이터 받기 → 전처리 → 정규화 → 규칙 분석 → 테스트 → CLI까지 **전 구간이 실제로 돌아갑니다.** | 정상 |
| 2 | 10·11·12주차 산출물은 **비트 단위로 재현**됩니다 (차이는 Windows `\` vs Linux `/` 경로뿐). | 정상 |
| 3 | 테스트 8개 전부 통과, 실패 0. | 정상 |
| 4 | **정규화(11주차)는 사실상 아무 일도 하지 않습니다.** 별칭 변환 127건 전부가 `Ajax` → `AJAX` 한 종류입니다. | 중대 |
| 5 | `docs/weeks/week12_actual_results.md`의 숫자(18,163 / 707)는 **구버전 수치**입니다. 현재 코드는 17,796 / 694입니다. | 중대 |
| 6 | 13·14주차 산출물 3개는 **생성 코드가 저장소에 없고**, 일부는 재현되지 않습니다. | 중대 |
| 7 | 규칙은 694개 계산되지만 **파일에는 상위 50개만 저장**되어, 서비스는 전체의 7.2%만 봅니다. | 중대 |
| 8 | `경력무관` 6,597건이 `entry`(신입)로 분류됩니다. 10주차 문서가 선언한 원칙과 **정반대**입니다. | 중대 |
| 9 | 직무 분류는 94.1%가 `other_tech`입니다. 제목이 64.3%(25,950건) 비어 있어 구조적으로 불가능합니다. | 한계 |
| 10 | **LLM은 현재 어디에서도 호출되지 않습니다.** 과제 조건의 "에이전트" 4요소 중 충족된 것은 0개입니다. | 중대 |

데이터 원본은 `.gitignore`의 `data/raw/`로 이미 제외되어 있어, 추가 조치가 필요 없습니다.

---

# 1단계: 앞부분이 실제로 돌아가는지 확인

## 1-1. 데이터 수신과 SHA-256 검증

`docs/data_source.md`의 PowerShell 명령을 WSL용으로 바꿔 실행했습니다.

```bash
mkdir -p data/raw data/processed
curl -fL --retry 3 -o data/raw/korean_it_recruit_postings.json \
  "https://huggingface.co/datasets/young-cc/korean-it-recruit-dataset/resolve/main/master_merged_v5.json?download=true"
sha256sum data/raw/korean_it_recruit_postings.json
```

| 항목 | 값 | 결과 |
|---|---|---|
| 파일 크기 | 177,980,800 bytes (약 170 MiB) | — |
| `week10_actual_results.md` 기대 SHA-256 | `dc7cc15b1ee80dbf5f959095ee78aad0e8dd39d5156cf694e60591aa1bd9a58f` | — |
| 실제 계산 SHA-256 | `dc7cc15b1ee80dbf5f959095ee78aad0e8dd39d5156cf694e60591aa1bd9a58f` | **일치** |

원본 데이터셋이 그대로 보존되어 있어, 아래 모든 수치 비교가 의미를 갖습니다.

## 1-2. 가상환경과 패키지

```bash
python3 -m venv .venv
.venv/bin/pip install python-docx
```

- 파이프라인(`src/` 전체)이 쓰는 import는 **표준 라이브러리뿐**입니다. 외부 패키지가 전혀 필요 없습니다.
- 외부 패키지는 `scripts/build_weekly_reports.py`(주차 보고서 .docx 생성)의 `python-docx` **하나**입니다.
- 설치 위치를 확인해 시스템 파이썬을 건드리지 않았음을 검증했습니다.
  `docx.__file__` → `/home/userkks/projects/JobGuts/.venv/lib/python3.12/site-packages/docx/__init__.py`

> 참고: 저장소에 `requirements.txt` / `pyproject.toml`이 없습니다. 다른 팀원이 환경을 다시 만들 때 필요한 패키지를 알 방법이 없으므로, 의존성 파일 추가를 제안합니다.

## 1-3. 파이프라인 실행 (10~14주차)

`scripts/run_pipeline.ps1`과 동일한 순서로 직접 실행했습니다. 전 단계 성공했습니다.

| 순서 | 명령 | 소요 | 결과 |
|---|---|---|---|
| 1 | `python -m src.ingestion.run_week10 --input data/raw/... --config configs/data_scope.json --output-dir artifacts` | 3.6초 | 40,348행 처리 |
| 2 | `python -m src.normalization.run_week11 --input data/raw/... --output data/processed/postings_normalized.jsonl --artifact-dir artifacts` | 3.2초 | JSONL 생성 |
| 3 | `python -m src.analysis.run_week12` | 4.5초 | 규칙 산출 |
| 4 | `python -m unittest discover -s tests -v` | 0.004초 | 8개 통과 |
| 5 | `python -m src.service.app --skills TensorFlow` | 즉시 | `status: ok` |

13·14주차는 전용 실행 모듈(`run_week13.py` / `run_week14.py`)이 **없습니다.** 문서에 적힌 CLI 시나리오로 대체 검증했습니다.

| 시나리오 | 명령 | 결과 |
|---|---|---|
| 정상 추천 | `--skills TensorFlow` | `ok`, 추천 2건, 근거 3건 |
| 규칙 없음 | `--skills NotARealSkill` | `no_rules` + `next_action` |
| 직무 필터 | `--skills TensorFlow --role frontend` | `ok`, 근거 공고가 프론트엔드 공고로 교체됨 |
| 근거 부족 | `--skills .NET --role frontend --experience 1~3년차` | `insufficient_sample` |
| 13주차 문서 재현 명령 | `--skills LlamaIndex` | **`no_rules`** (아래 1-5 참조) |
| 로컬 웹 UI | `python -m src.service.web_server` | HTTP 200, `/api/recommend` 정상 |

`TensorFlow → PyTorch` 핵심 지표는 README와 **소수점까지 일치**했습니다.
support `0.030175`, confidence `0.948763`, interest `0.895942`, support_count `537`, transaction_count `17,796`.

### 확인된 동작상의 사실 두 가지

1. **직무 필터는 지표를 바꾸지 않습니다.** 규칙은 전체 공고로 미리 계산되고, 필터는 *근거 공고 선택*에만 적용됩니다.
   `--role frontend`를 줘도 support·confidence·interest는 전역 값 그대로입니다. 설계상 의도일 수 있지만,
   사용자는 "프론트엔드 기준 수치"로 오해하기 쉽습니다.
2. **`insufficient_sample`에는 `next_action`이 없습니다.** `week13_actual_results.md`는
   "근거 부족은 `insufficient_sample` 상태와 다음 행동을 반환한다"고 적었지만,
   `src/retrieval/repository.py:24`의 반환 딕셔너리에는 `next_action` 키가 없습니다.
   (`no_rules` 경로인 `repository.py:16`에만 있습니다.)

## 1-4. 테스트 결과

```
Ran 8 tests in 0.004s — OK
```

| 구분 | 개수 |
|---|---|
| 통과 | **8** |
| 실패 | **0** |
| 오류 | **0** |

| 테스트 파일 | 개수 |
|---|---|
| `test_apriori.py` | 1 |
| `test_ingestion_quality.py` | 3 |
| `test_llm_contracts.py` | 1 |
| `test_normalization.py` | 1 |
| `test_retrieval.py` | 1 |
| `test_week10_cli.py` | 1 |

8개 모두 소형 인라인 픽스처만 사용합니다. **실제 40,348행 데이터로 수치를 검증하는 테스트는 없습니다.**
즉 테스트 통과는 "코드가 깨지지 않았다"는 뜻이고, "문서 숫자가 맞다"는 보증은 아닙니다.
(이번 점검에서 실제로 숫자 불일치가 발견된 이유입니다.)

## 1-5. 문서 숫자 vs 실제 실행 숫자

### 10주차 — 전 항목 일치

| 항목 | 문서 | 실제 | 결과 |
|---|---|---|---|
| 입력 행 수 | 40,348 | 40,348 | 일치 |
| `source + job_id` 누락 행 | 0 | 0 | 일치 |
| `source + job_id` 중복 그룹 / 행 | 777 / 777 | 777 / 777 | 일치 |
| 동일 본문 의심 그룹 / 행 | 744 / 1,707 | 744 / 1,707 | 일치 |
| `raw_text` 결측 | 0 | 0 | 일치 |
| `final_techs` 빈 목록·결측 | 21,560 | 21,560 | 일치 |
| `hard_skills` 빈 목록·결측 | 9,268 | 9,268 | 일치 |
| 두 기술 필드 모두 존재 | 40,348 | 40,348 | 일치 |
| 두 집합 같음 / 다름 | 8,886 / 31,462 | 8,886 / 31,462 | 일치 |

### 11주차 — 전 항목 일치

| 항목 | 문서 | 실제 | 결과 |
|---|---|---|---|
| 입력 행 수 | 40,348 | 40,348 | 일치 |
| 사전 버전 | `tech-dictionary.v1` | `tech-dictionary.v1` | 일치 |
| 별칭 변환 수 | 127 | 127 | 일치 |
| 공고별 중복 제거 수 | 0 | 0 | 일치 |
| 사전 미등록 기술명 수 | 142 | 142 | 일치 |

### 12주차 — **문서와 불일치** (README는 일치)

| 항목 | `week12_actual_results.md` | README | 실제 실행 | 결과 |
|---|---|---|---|---|
| 분석 트랜잭션 | **18,163** | 17,796 | **17,796** | 문서 불일치 |
| 정규화 전 규칙 수 | **707** | 694 | **694** | 문서 불일치 |
| 정규화 후 규칙 수 | **707** | 694 | **694** | 문서 불일치 |
| 전후 공통 규칙 수 | **707** | — | **694** | 문서 불일치 |
| 키 중복 제외 행 | 777 | 777 | 777 | 일치 |
| 빈 기술 목록 제외 행 | **21,408** | — | **20,842** | 문서 불일치 |
| 동일 본문 제외 행 | **"자동 제외하지 않았다"** | 933 | **933** | 문서 불일치 |
| 최소 support / confidence / itemset | 0.005 / 0.2 / 2 | 동일 | 동일 | 일치 |

**원인을 git 이력에서 특정했습니다.** 11번째 커밋 `4d96ed8 feat: exclude duplicate posting bodies from analysis`에서
"서로 다른 ID의 동일 본문 933건 제외" 로직이 추가되어 18,163 → 17,796으로 바뀌었습니다.
그런데 `docs/weeks/week12_actual_results.md`는 7번째 커밋 `32c5260` 이후 **갱신되지 않았습니다.**

즉 코드가 맞고 **문서가 낡았습니다.** README(15번째 커밋)는 갱신된 수치를 담고 있습니다.

### 13주차 — 산출물이 구버전

`artifacts/week13_service_scenarios.json`에 기록된 값:

```json
"transaction_count": 18163,
"antecedent": ["LlamaIndex"], "consequent": ["LangChain"],
"support": 0.005120299509992842, "confidence": 0.9789473684210527, "support_count": 93
```

이 파일은 8번째 커밋 `5e7c8c9`가 마지막 수정이고, 중복 제거 커밋(11번째)보다 **앞섭니다.**
구버전 조건(동일 본문 제외 없음, 18,163 트랜잭션)을 재현해 보니 support `0.005120`, confidence `0.978947`로
**소수점 끝까지 똑같이** 나왔습니다. 구버전 산출물임이 확정됩니다.

그래서 13주차 문서의 재현 명령 `--skills LlamaIndex`가 지금은 `no_rules`를 돌려줍니다. 이유는 정확히 이렇습니다.

| | 구버전 | 현재 |
|---|---|---|
| 트랜잭션 수 | 18,163 | 17,796 |
| 최소 support 횟수 `ceil(n × 0.005)` | 91 | **89** |
| `LlamaIndex` & `LangChain` 동시 등장 | 93회 | **88회** |
| 규칙 통과 여부 | 통과 (93 ≥ 91) | **탈락 (88 < 89)** |

중복 공고 제거로 동시 등장이 93→88회로 줄어 임계값 89에 **1회 모자라** 규칙이 사라졌습니다.
버그가 아니라, 구버전 수치가 중복 공고로 부풀려져 있었다는 증거입니다. 문서의 예시 기술만 낡았습니다.

### 14주차 — 일부만 재현

| 항목 | 문서/README | 실제 | 결과 |
|---|---|---|---|
| 테스트 8개 통과 | 8 | 8 | 일치 |
| CLI 3개 시나리오 | 정상·규칙없음·필터 | 전부 동작 | 일치 |
| `week14_segment_comparison.json`의 `segments` 합계 | — | 18,788 | **재현됨** |
| `week14_segment_comparison.json`의 `top_triples` | — | — | **재현 불가** |
| README: `JavaScript + React + TypeScript` | 215회 | **647회** | 불일치 |
| README: `PyTorch + Python + TensorFlow` | 205회 | **431회** | 불일치 |
| `week14_skill_graph.json` 노드/엣지 | — | 46 / 50 | **불일치** (현재 코드로는 44 / 50) |

세부 확인 내용:

- **`segments` 블록은 재현됩니다.** `normalized_techs`가 비어 있지 않은 **18,788행**(중복 제거 없음)에
  `job_role × experience_segment`를 교차한 값과 17개 항목이 **완전히 일치**합니다.
  단, 이 18,788은 12주차의 분석 트랜잭션 17,796과 **다른 집합**입니다. 같은 보고서 안에 모집단이 두 개 섞여 있습니다.
- **`top_triples`는 어떤 방식으로도 재현되지 않았습니다.** `final_techs` / `normalized_techs` / `hard_skills` ×
  (중복 제거 on/off) 6가지 조합을 전부 돌려 상위 50개와 맞춰본 결과 **최대 1/50 일치**였습니다.
  `C + C++ + Python = 296`만 `hard_skills` 기준과 맞고 나머지는 전부 어긋나며, 순위 자체도 다릅니다.
- **생성 코드가 저장소에 없습니다.** `src/analysis/graph.py`의 `graph_from_rules()`는 **어디에서도 호출되지 않고**,
  `week13_service_scenarios.json` / `week14_segment_comparison.json` / `week14_skill_graph.json`을 쓰는 코드도 없습니다.
  (`scripts/build_weekly_reports.py`는 이 파일들을 *읽어 복사*만 합니다.) 커밋되지 않은 임시 스크립트로 만든 것으로 보입니다.

### 추가로 발견한 문서·코드 불일치

| 위치 | 문서의 서술 | 실제 |
|---|---|---|
| `week14_actual_results.md` | "HTTP API는 구현하지 않았다" | `src/service/web_server.py`에 HTTP 서버가 있고 동작합니다 |
| README 한계 섹션 | "현재는 CLI이며, 웹 UI는 향후 작업" | 로컬 웹 UI가 이미 동작합니다 (HTTP 200 확인) |
| `scripts/build_weekly_reports.py` | 산출물에서 수치를 읽는 형태 | 읽어온 `q`, `n`, `r` 변수를 **쓰지 않고** 숫자를 문자열로 하드코딩합니다 (`'17,796'`, `'694'`) |
| `src/service/contracts.py` | 응답 계약 정의 | **어디에서도 사용되지 않는 죽은 코드**이며, `EvidencePosting.excerpt`는 실제 응답의 `title`과 다릅니다 |

### 산출물 재현성 정리

| 산출물 | 마지막 생성 커밋 | 중복제거(11번째 커밋) 이후? | 재현 결과 |
|---|---|---|---|
| `week10_data_quality_summary.json` | `4d96ed8` 이후 | 예 | **완전 재현** (경로 구분자만 차이) |
| `week11_normalization_summary.json` | `4d96ed8` 이후 | 예 | **완전 재현** (경로 구분자만 차이) |
| `week12_rule_comparison.json` | `4d96ed8` | 예 | **완전 재현** (바이트 동일) |
| `week12_top_rules.json` | `4d96ed8` | 예 | **완전 재현** (바이트 동일) |
| `week13_service_scenarios.json` | `5e7c8c9` | **아니오** | 구버전 (18,163 기준) |
| `week14_skill_graph.json` | `5e7c8c9` | **아니오** | 구버전 / 생성 코드 없음 |
| `week14_segment_comparison.json` | `090a1b8` | 예 | `segments`만 재현, `top_triples` 불가 |

## 1-6. 공고 5건 무작위 표본 — 원문과 정규화 결과 대조

`random.seed(20261118)`로 재현 가능하게 추출했습니다. **5건 모두 `normalized_techs`가 `final_techs`와 완전히 동일**했습니다.

### 샘플 1 — `jobkorea` / `49215352`

- 제목: `장비지능화 IT과제 담당자 통합 모집 (계약직) - AI Agent 설계/개발`
- 분류: `other_tech` (fallback) / `경력무관` → **`entry`**
- `final_techs`: `['AI Agent', 'MLOps', 'AI', 'ML']`
- `normalized_techs`: `['AI Agent', 'MLOps', 'AI', 'ML']` → **변경 없음**
- 원문 일부: "SK㈜ AX 장비지능화 IT과제 담당자 통합 모집 … 모집요강 모집분야 Software Engineering … **합격자소서 인적성·면접 후기 자발적으로 최고 수준의 목표를 세우고 끈질기게 성취한 경험에 대해 서술해 주십시오** … 2020년 하반기 신입 앱개발자 4학년 여름 AI 연구 기관에서 …"

**판정: 정규화는 틀리지 않았으나, 항목 품질에 문제가 있습니다.**
`raw_text`의 상당 부분이 채용 요건이 아니라 **자기소개서 문항·합격 후기·기업 소개 보일러플레이트**입니다.
또 `AI`, `ML`은 기술이 아니라 **분야 개념**이고, `AI Agent`는 제품/역할 명칭입니다.
이런 항목이 Apriori의 item으로 들어가면 "AI와 ML이 함께 나온다"처럼 **정보량 없는 규칙**을 만듭니다.
(실제로 `AI`는 5,549회로 전체 1위입니다.)

### 샘플 2 — `saramin` / `53885838`

- 제목: **`None`** / `experience_level`: **`None`** → `other_tech` / `other`
- `final_techs`: `['Flutter', 'C', 'AI', 'DevOps', 'Android', 'Node.js', 'iOS', 'GCP', 'AWS', 'Java', 'Kotlin', 'JavaScript']`
- `normalized_techs`: 동일 → **변경 없음**
- 원문 기술 스택: "Amazon EC2 Android OS Flutter iOS Java JavaScript Kotlin Node.js **Objective-C** AWS"

**판정: 정규화 단계는 통과했지만 상위 추출 단계에 오류가 있습니다.**
원문에는 `Objective-C`가 있는데 `final_techs`에는 **`C`**만 있습니다. `Objective-C`에서 `C`를 잘못 뽑아낸
흔적으로 보입니다. 이 때문에 `C`(1,798회)와 `C + C++` 조합이 과대 집계될 수 있습니다.
`DevOps`는 기술이 아니라 **방법론**이고, `Amazon EC2` → `AWS` 매핑은 원본 데이터셋 단계에서 이미 수행되었습니다.
제목이 없어 직무 분류가 원천적으로 불가능한 케이스입니다.

### 샘플 3 — `wanted` / `309291`

- 제목: **`풀스텍 개발자`** (오타: 풀스**택** → 풀스**텍**)
- 분류: **`other_tech`** / `경력무관` → `entry`
- `final_techs` = `normalized_techs`: `['Spring', 'MySQL', 'Vue.js', 'React', 'AWS', 'Next.js', 'Java']` → **변경 없음**
- 원문: "프론트엔드 개발 (Web & Mobile App) • React, Next.js, **Vue** 등 … **JAVA** 백엔드 프레임워크 … MySQL … AWS 클라우드"

**판정: 기술 추출은 정확하지만 직무 분류가 실패했습니다.**
`src/normalization/metadata.py`의 `ROLE_TERMS`는 `"풀스택"`만 찾기 때문에 오타 `"풀스텍"`을 놓치고
`other_tech`로 떨어집니다. 원문에 프론트엔드·백엔드가 모두 있어 `fullstack`이 맞는 케이스입니다.
한편 원문의 `Vue` → `Vue.js`, `JAVA` → `Java` 표준화는 **우리 사전이 아니라 원본 데이터셋이 이미 해 둔 것**입니다
(`normalized_techs`가 `final_techs`와 같다는 점이 그 증거입니다).

### 샘플 4 — `wanted` / `356354`

- 제목: `머신러닝 엔지니어 (모델링 고도화)` → **`other_tech`** / `경력무관` → `entry`
- `final_techs` = `normalized_techs`: `['FastAPI', 'Docker', 'PyTorch', 'Python', 'Elasticsearch', 'Airflow', 'Kubeflow', 'Spark', 'Kubernetes', 'Kotlin', 'GitHub']` → **변경 없음**
- 원문: "모델 학습 : Python, PyTorch, Kubeflow • 모델 서빙 : Python, Kotlin, PyTorch, FastAPI, **Scylla**, Elasticsearch • 데이터 전처리 : Spark, **Ray**, Airflow • 코드 관리 & 배포 : Github / **Github Action**, Docker, Kubernetes"

**판정: 추출 정확도가 가장 좋은 케이스지만 누락이 있습니다.**
원문의 `Scylla`, `Ray`가 `final_techs`에서 빠졌고, `Github Action`은 `GitHub`로만 남아
**`GitHub Actions`가 소실**되었습니다. (사전에 `GitHub Actions` 항목이 있는데 전체 데이터에서 단 **3회**만
등장하는 이유가 이것으로 설명됩니다.) 제목의 "머신러닝"은 직무 신호로 쓰이지 않아 `other_tech`입니다.

### 샘플 5 — `wanted` / `356002`

- 제목: `프론트엔드 개발자` → **`frontend`** (`title_rule`) / `신입` → `entry`
- `final_techs` = `normalized_techs`: `['React Query', 'pnpm', 'WebSocket', 'TypeScript', 'React', 'Git', 'WebGL', 'REST API', 'Zustand']` → **변경 없음**
- 원문: "코어: Typescript, React • 상태 관리: Zustand, **Tanstack-Query** • UI: **Mantine** • 패키징: PnPm • 빌드: **Rspack, ESBuild**"

**판정: 5건 중 유일하게 직무·경력 분류가 모두 올바른 케이스입니다.**
`Tanstack-Query` → `React Query`, `PnPm` → `pnpm`, `Typescript` → `TypeScript` 표준화가 되어 있는데
이 역시 **원본 데이터셋의 작업**입니다. `Mantine`, `Rspack`, `ESBuild`는 누락되었습니다.

### 5건 종합 판정

| 관점 | 판정 |
|---|---|
| 정규화가 틀린 값을 만들었는가 | **아니오.** 5건 모두 잘못된 변환이 없습니다. |
| 정규화가 기여를 했는가 | **아니오.** 5건 모두 입력과 출력이 **완전히 동일**합니다. |
| 직무 분류 정확도 | 5건 중 **1건만** 정확 (샘플 5). 2건은 제목 없음·오타로 실패. |
| 경력 분류 정확도 | `경력무관` 3건이 모두 `entry`(신입)로 분류됨 — **부정확**. |
| 상위 기술 추출 품질 | `Objective-C`→`C` 오추출, `Scylla`/`Ray`/`Mantine` 등 누락, `AI`/`ML`/`DevOps` 등 비기술 항목 혼입. |

---

# 2단계: 부족한 부분 진단

## 2-1. 지금 LLM이 맡은 역할 — "역할이 없습니다"

`src/llm/` 폴더에는 파일이 4개뿐이고, 전부 합쳐 **약 40줄**입니다.

| 파일 | 내용 |
|---|---|
| `contracts.py` | `LLMRequest`(메시지+컨텍스트), `LLMResponse`(텍스트+제공자명+mock여부), `LLMProvider` 프로토콜 — **형태 선언만** |
| `fake_provider.py` | `f"Mock explanation for: {request.user_message}"` 문자열을 되돌려주는 가짜 구현 |
| `__init__.py` | 위 네 개를 내보내기 |

`docs/llm_boundary.md`가 정한 경계는 이렇습니다.

> 추천 규칙, 지표, 근거 공고는 분석·조회 계층이 결정한다. 언어 모델 계층은 **이미 결정된 결과를 설명하는 선택적 계층**이며, 추천을 재계산하거나 근거를 생성하지 않는다.

쉽게 말해 이런 설계입니다.

```
사용자 입력 → 사전 조회 → 저장된 규칙 조회 → 근거 공고 조회 → JSON 출력
                                                              └─ (LLM은 여기 붙을 "예정"이었음)
```

**그런데 실제로는 그 자리에도 붙어 있지 않습니다.** `src/llm`을 import하는 곳을 전부 찾아보면:

```
tests/test_llm_contracts.py:3:  from src.llm import FakeLLMProvider, LLMRequest
```

**테스트 파일 단 한 곳입니다.** `src/service/app.py`, `src/service/web_server.py`,
`src/retrieval/repository.py` 어디에도 LLM 호출이 없습니다.

정리하면 현재 LLM의 역할은:

- **지금 하는 일**: 없습니다. 실행 경로에서 한 번도 호출되지 않습니다.
- **설계상 맡기려던 일**: 확정된 추천 결과를 사람이 읽을 문장으로 바꿔주는 **설명 생성**뿐입니다.
- **의도적으로 제외한 일**: 추천 계산, 근거 생성, 실제 API·키·SDK·HTTP 호출.

설계 자체는 깔끔합니다. 숫자는 코드가 정하고 LLM은 말로 풀어주기만 하므로 **환각이 지표를 오염시킬 수 없습니다.**
문제는 과제 조건이 요구하는 것이 "설명기"가 아니라 **"에이전트"**라는 점입니다.

## 2-2. 과제 조건의 "LLM 에이전트" 기준 대비 현황

판정 기준: **추론**하고, **기억(사전 등)을 참조**하고, **도구를 호출**하고, **결과를 다시 반영**하는 구조.

| 기준 | 있어야 하는 것 | 지금 있는 것 | 빠진 것 | 판정 |
|---|---|---|---|---|
| **① 추론 (Reasoning)** | LLM이 입력을 해석해 "무엇을 할지" 스스로 판단 | LLM 호출 자체가 없음. 분기는 `if not candidates` 한 줄(`repository.py:15`)이고, 정렬은 `(-interest, -confidence)` 고정 규칙(`repository.py:14`) | LLM 호출, 의도 파악, 질의 재구성, 다단계 판단 | **없음** |
| **② 기억 참조 (Memory)** | 사전·이력·과거 대화를 조회해 판단에 반영 | `configs/tech_dictionary.json`(14개 항목)을 **코드가** 완전일치로 조회(`dictionary.py:32`). 세션·대화 이력 저장 없음 | LLM이 접근하는 기억, 유사도/의미 기반 조회, 사용자 이력, 미등록어 학습·축적 | **부분** (코드만 참조, LLM은 못 봄) |
| **③ 도구 호출 (Tool use)** | LLM이 함수 목록을 받아 **어떤 도구를 쓸지 선택**하고 인자를 채움 | `app.py:10`이 `RuleRepository(...).recommend(...)`를 **한 줄로 직접** 호출. 호출 순서가 코드에 고정 | 도구 스키마 정의, function/tool calling, 도구 선택 로직, 호출 실패 처리 | **없음** |
| **④ 결과 반영 (Observation → 재추론)** | 도구 결과를 보고 다시 판단해 재시도·전략 변경 | 단일 경로 1회 실행 후 `print()` 종료(`app.py:10`). 루프 없음 | 관찰→재추론 루프, 종료 조건, `no_rules`/`insufficient_sample` 시 자동 재시도(필터 완화 등) | **없음** |
| **(참고) LLM 호출** | 실제 모델 호출 | `FakeLLMProvider`가 고정 문자열 반환. 테스트에서만 사용 | 실제 provider 구현, 키 관리, 재시도·타임아웃 | **없음** |
| **(참고) 출력 신뢰성** | 환각 방지 장치 | 숫자·근거를 전부 코드가 결정하는 **구조적 분리** — 이 부분은 이미 잘 되어 있음 | — | **양호** |

**충족 0 / 4.** 현재 코드는 "규칙 기반 조회 CLI"이고, LLM 에이전트의 구성요소는 아직 하나도 들어오지 않았습니다.
다만 ④를 붙일 자리는 이미 마련돼 있습니다. `no_rules`와 `insufficient_sample`이라는 **명시적 실패 상태**가
존재하므로, 에이전트가 "실패를 관찰하고 필터를 완화해 다시 시도"하는 루프를 자연스럽게 걸 수 있습니다.

### 가장 빠르게 4요소를 채우는 방향 (제안)

`no_rules` / `insufficient_sample`을 "관찰"로 보고 재시도하는 루프 하나만 만들면 4요소가 동시에 채워집니다.

```
사용자: "저는 파이토치랑 도커 좀 다룹니다"
  ① 추론: LLM이 자연어에서 기술명 후보 추출 → ["PyTorch", "Docker"]
  ② 기억: 사전 + 미등록어 목록을 참조해 표기 확정
  ③ 도구: recommend(skills=[...], role=None) 호출을 LLM이 선택
  ④ 반영: insufficient_sample 관찰 → 필터를 완화해 재호출 → ok
  최종: 코드가 정한 지표·근거는 그대로 두고, LLM은 설명 문장만 생성
```

이 구조는 `docs/llm_boundary.md`의 "지표와 근거는 LLM이 만들지 않는다"는 원칙을 **깨지 않고** 유지합니다.

## 2-3. 사전에 없어서 정규화되지 않은 기술명

### 전체 그림

| 항목 | 값 |
|---|---|
| `final_techs`의 서로 다른 기술명(고유값) | **156개** |
| 사전에 등록된 이름 | **14개 (9.0%)** |
| **사전에 없는 이름** | **142개 (91.0%)** |
| 전체 기술 언급 횟수 | 90,796회 |
| 미등록 이름의 언급 횟수 | **73,264회 (80.7%)** |

### 상위 30개 (등장 횟수 기준)

| 순위 | 기술명 | 등장 | 순위 | 기술명 | 등장 |
|---:|---|---:|---:|---|---:|
| 1 | AI | 5,549 | 16 | Oracle | 1,075 |
| 2 | Python | 4,747 | 17 | PyTorch | 1,026 |
| 3 | Java | 4,120 | 18 | LLM | 1,003 |
| 4 | AWS | 3,375 | 19 | RDBMS | 978 |
| 5 | Linux | 2,777 | 20 | GCP | 947 |
| 6 | Git | 2,507 | 21 | Redis | 937 |
| 7 | Spring | 2,505 | 22 | Kotlin | 934 |
| 8 | C++ | 2,282 | 23 | ML | 934 |
| 9 | Docker | 2,219 | 24 | Deep Learning | 928 |
| 10 | SQL | 2,096 | 25 | Figma | 885 |
| 11 | C | 1,798 | 26 | CI/CD | 882 |
| 12 | REST API | 1,698 | 27 | Azure | 834 |
| 13 | C# | 1,255 | 28 | Jira | 804 |
| 14 | HTML | 1,181 | 29 | FastAPI | 701 |
| 15 | CSS | 1,172 | 30 | Kafka | 690 |

### 이 숫자를 어떻게 읽어야 하는가 — 중요

**"미등록 142개"는 "지저분한 142개"가 아닙니다.** `Python`, `Java`, `AWS`, `Docker`는 이미 완벽한 표준 표기입니다.
원본 데이터셋의 `final_techs`가 **이미 정제된 닫힌 어휘(156개)**이기 때문입니다.
따라서 이 142개는 "정규화가 필요한데 안 된 것"이 아니라, **"사전에 등재만 안 된 것"**입니다.

그 증거가 11주차의 별칭 변환 127건의 내역입니다. 전수 조사한 결과:

| 변환 | 건수 |
|---|---|
| `'Ajax'` → `'AJAX'` | **127** |
| 그 외 모든 항목 | **0** |
| **합계** | **127** |

**사전 14개 항목 중 13개는 단 한 번도 변환을 일으키지 않았습니다.**
`JavaScript`, `TypeScript`, `Node.js`, `React`, `Vue.js`, `Next.js`, `PostgreSQL`, `MySQL`,
`GitHub`, `GitHub Actions`, `Kubernetes`, `TensorFlow`, `ASP.NET` — 전부 원본이 이미 표준 표기입니다.
`AJAX` 항목만 원본이 `Ajax`로 들어와 대소문자가 바뀌었습니다.

**즉 11주차 정규화 계층이 실제로 수행한 작업은 "Ajax의 대문자화" 하나입니다.**
이것이 "정규화 전후 규칙 수가 694 / 694로 동일"했던 진짜 이유입니다.
12주차 문서는 이를 "사전 효과가 없다는 뜻은 아니다"라고 해석했지만, 전수 조사 결과는
**현재 사전이 이 데이터셋에서 사실상 무효**임을 보여줍니다.
(참고로 `AJAX` 자체는 `final_techs`에 0회, `Ajax`가 127회 등장합니다.)

### 142개 중 성격이 다른 항목들 (별도 분류가 필요)

| 분류 | 예시 | 문제 |
|---|---|---|
| 분야·개념 | `AI`(5,549), `ML`(934), `Deep Learning`(928), `LLM`(1,003) | 기술이 아니라 분야. `AI → ML` 같은 자명한 규칙을 만듦 |
| 방법론·관행 | `CI/CD`(882), `DevOps`, `RDBMS`(978), `REST API`(1,698) | 특정 도구가 아니라 방식 |
| 협업 도구 | `Jira`(804), `Figma`(885) | 개발 기술 스택과 성격이 다름 |
| 오추출 의심 | `C`(1,798) | `Objective-C`에서 잘못 분리된 사례 확인 (샘플 2) |

사전을 확장할 때 **단순히 142개를 등재하는 것만으로는 분석이 좋아지지 않습니다.**
"이 이름이 표준인가"와 "이 이름이 기술 item으로 적절한가"는 다른 문제이므로,
사전에 `category`(언어/프레임워크/인프라/개념/도구) 필드를 추가해 **개념·방법론 항목을 Apriori에서 제외**하는
선택지를 두는 쪽이 효과가 큽니다.

## 2-4. 에이전트를 추가할 때 건드릴 파일 / 새로 만들 파일

### 전제: 지금은 모든 파일이 경민 님 작업물입니다

`gyeongseon` 브랜치는 `origin/k0ng_min`을 fast-forward한 것이라, **현재 저장소의 모든 파일이 경민 님 커밋입니다.**
그리고 변경 이력을 보면 활발히 손대는 영역이 뚜렷합니다.

| 파일 | 변경 횟수 | 충돌 위험 |
|---|---:|---|
| `README.md` | 5 | **매우 높음** |
| `src/service/web_server.py` | 4 | **매우 높음** (최근 3개 커밋이 전부 이 파일) |
| `src/normalization/run_week11.py` | 3 | 높음 |
| `scripts/build_weekly_reports.py` | 3 | 높음 |
| `.gitignore` | 3 | 중간 |
| `src/normalization/metadata.py` | 2 | 중간 |
| `src/analysis/run_week12.py` | 2 | 중간 |
| `src/ingestion/loader.py` | 2 | 중간 |

특히 최근 4개 커밋(`6ba2365` → `f279ebe` → `0fbe847` revert → `5482b2a`)이 **모두 `web_server.py`**입니다.
경민 님이 지금 작업 중인 파일이므로 **절대 건드리지 않는 것이 좋습니다.**

### 권장: 새로 만들 파일 (충돌 위험 거의 없음)

| 경로 | 역할 |
|---|---|
| `src/agent/__init__.py` | 패키지 선언 |
| `src/agent/tools.py` | `recommend` / `lookup_dictionary` 등을 **도구 스키마**로 감싸기. 기존 함수를 호출만 하고 수정하지 않음 |
| `src/agent/loop.py` | 추론 → 도구 호출 → 관찰 → 재추론 루프 (④ 담당) |
| `src/agent/policy.py` | `no_rules` / `insufficient_sample` 시 완화 전략 (필터 해제 순서 등) |
| `src/agent/run_agent.py` | 새 CLI 진입점. `src/service/app.py`를 **고치지 않고 병행** |
| `src/llm/glm_provider.py` | 실제 provider 구현. `LLMProvider` 프로토콜만 만족시키면 되므로 기존 파일 수정 불필요 |
| `configs/agent.json` | 모델명·최대 반복 횟수·도구 목록 |
| `tests/test_agent_loop.py` | 루프 단위 테스트 (`FakeLLMProvider` 재사용) |
| `tests/test_agent_tools.py` | 도구 스키마·인자 검증 |
| `docs/gyeongseon/02_agent_design.md` | 설계 문서 (경민 님 문서와 분리) |
| `requirements.txt` | 의존성 고정 (현재 없음) |

**왜 안전한가:** git은 파일 단위로 병합합니다. 새 파일만 추가하면 경민 님이 기존 파일을 어떻게 바꾸든
**merge conflict가 발생하지 않습니다.** 특히 `src/llm/`은 `LLMProvider`가 `Protocol`로 정의되어 있어
(`contracts.py:22`) 기존 코드를 **한 줄도 고치지 않고** 새 provider를 끼울 수 있습니다. 설계가 잘 되어 있는 부분입니다.

### 불가피하게 건드려야 하는 파일 (최소 범위로, 사전 합의 후)

| 파일 | 필요한 변경 | 충돌 위험 | 완화 방법 |
|---|---|---|---|
| `src/analysis/run_week12.py:78` | `raw_rules[:50]` → 전체 저장 (694개를 서비스가 보게 하려면 필수) | 중간 | **별도 파일에 전체 규칙을 쓰고** 기존 파일은 그대로 두기. `--all-rules` 플래그 추가도 가능 |
| `configs/tech_dictionary.json` | 142개 항목·`category` 추가 | 중간 | 기존 파일 수정 대신 **`configs/tech_dictionary_v2.json`**을 새로 만들고 `--dictionary`로 지정 (CLI가 이미 지원: `app.py:8`) |
| `src/service/app.py` | 에이전트 모드 플래그 | 높음 | **건드리지 말고** `src/agent/run_agent.py`를 새 진입점으로 |
| `README.md` | 에이전트 사용법 | **매우 높음** | 내 문서는 `docs/gyeongseon/`에만 쓰고, README는 **합치는 시점에 한 줄 링크만** 추가 |
| `src/service/web_server.py` | UI에 에이전트 연결 | **매우 높음** | 경민 님 작업 중. 손대지 않음 |

### 특히 주의: 규칙이 50개만 저장되는 문제

| 항목 | 값 |
|---|---|
| 12주차가 계산하는 규칙 수 | **694개** |
| `week12_top_rules.json`에 저장되는 수 | **50개 (7.2%)** |
| 전체 694개 규칙의 선행 기술 종류 | **94종** |
| 저장된 50개의 선행 기술 종류 | **33종** |

`src/analysis/run_week12.py:78`의 `raw_rules[:50]`, `normalized_rules[:50]` 때문입니다.
`src/retrieval/repository.py:8`은 이 파일만 읽으므로, **서비스가 추천할 수 있는 기술은 33종뿐**입니다.
사용자가 `Python`이나 `AWS`를 입력해도 선행 기술 목록에 없으면 `no_rules`가 나옵니다.

에이전트를 붙이기 **전에** 이 부분을 먼저 해결해야 합니다. 그렇지 않으면 에이전트가 아무리 똑똑하게
추론해도 조회할 규칙 자체가 없습니다. 기존 파일을 건드리지 않는 방법은
**`artifacts/week12_all_rules.json`을 새로 쓰고, 에이전트는 그 파일을 읽게 하는 것**입니다.

### 병합 순서 제안

1. 경민 님께 `week12_actual_results.md` 수치와 13·14주차 산출물이 구버전이라는 점을 먼저 공유 (이 문서 1-5 참조)
2. 내 작업은 `src/agent/`, `tests/test_agent_*.py`, `docs/gyeongseon/`, `configs/agent.json`에만 추가
3. `src/analysis/run_week12.py`와 `configs/tech_dictionary.json`은 **합의 후** 별도 작은 커밋으로 분리
4. `README.md`, `src/service/app.py`, `src/service/web_server.py`는 마지막에 경민 님이 직접 반영

---

## 다음 단계 제안 (우선순위)

| 순위 | 할 일 | 이유 |
|---|---|---|
| 1 | 규칙 전체 저장 (694개) | 이걸 안 하면 에이전트가 쓸 재료가 33종뿐 |
| 2 | 사전 v2 (142개 + `category`) | 현재 사전은 `Ajax`→`AJAX` 하나만 동작 |
| 3 | `src/agent/` 신설 — 4요소 루프 | 과제 조건 충족 (현재 0/4) |
| 4 | `src/llm/glm_provider.py` 실제 연결 | `Protocol` 덕분에 기존 코드 수정 불필요 |
| 5 | `경력무관` → `entry` 매핑 재검토 | 10주차 원칙과 정반대, `entry`의 92%가 오분류 |
| 6 | 13·14주차 산출물 재생성 스크립트 작성 | 생성 코드가 없어 재현 불가 |
| 7 | `week12_actual_results.md` 수치 갱신 | 구버전 수치 (18,163 / 707) |
| 8 | `requirements.txt` 추가 | 환경 재현 수단이 없음 |

---

## 재현 명령 전체 (WSL)

```bash
cd ~/projects/JobGuts
git switch gyeongseon

# 1) 데이터 (PowerShell Invoke-WebRequest 대체)
mkdir -p data/raw data/processed
curl -fL --retry 3 -o data/raw/korean_it_recruit_postings.json \
  "https://huggingface.co/datasets/young-cc/korean-it-recruit-dataset/resolve/main/master_merged_v5.json?download=true"
sha256sum data/raw/korean_it_recruit_postings.json
# 기대값: dc7cc15b1ee80dbf5f959095ee78aad0e8dd39d5156cf694e60591aa1bd9a58f

# 2) 가상환경
python3 -m venv .venv
.venv/bin/pip install python-docx   # scripts/build_weekly_reports.py 에만 필요

# 3) 파이프라인 (scripts/run_pipeline.ps1 과 동일 순서)
.venv/bin/python -m src.ingestion.run_week10 --input data/raw/korean_it_recruit_postings.json \
  --config configs/data_scope.json --output-dir artifacts
.venv/bin/python -m src.normalization.run_week11 --input data/raw/korean_it_recruit_postings.json \
  --output data/processed/postings_normalized.jsonl --artifact-dir artifacts
.venv/bin/python -m src.analysis.run_week12
.venv/bin/python -m unittest discover -s tests -v

# 4) CLI 시나리오
.venv/bin/python -m src.service.app --skills TensorFlow
.venv/bin/python -m src.service.app --skills NotARealSkill
.venv/bin/python -m src.service.app --skills TensorFlow --role frontend
.venv/bin/python -m src.service.app --skills .NET --role frontend --experience 1~3년차

# 5) 로컬 웹 UI
.venv/bin/python -m src.service.web_server   # http://127.0.0.1:8765
```

## 점검 중 변경된 파일 (커밋하지 않았습니다)

| 파일 | 변경 내용 |
|---|---|
| `artifacts/week10_data_quality_summary.json` | `path` 값이 `data\raw\...` → `data/raw/...` (OS 경로 구분자) |
| `artifacts/week11_normalization_summary.json` | `output_path` 값이 `data\processed\...` → `data/processed/...` |

파이프라인 실행의 부수 효과이며, **수치는 전부 동일**합니다.
`data/raw/`, `data/processed/`, `.venv/`는 `.gitignore`에 포함되어 추적되지 않습니다.
원래대로 되돌리려면 `git restore artifacts/`를 실행하면 됩니다.
