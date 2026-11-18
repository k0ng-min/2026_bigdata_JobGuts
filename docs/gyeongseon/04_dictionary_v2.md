# 04. 추출 수정과 기술명 사전 v2 (gyeongseon)

- 작업 일자: 2026-11-18
- 작업 브랜치: `gyeongseon`
- 선행 문서: [01_baseline_check.md](01_baseline_check.md), [02_foundation_fixes.md](02_foundation_fixes.md), [03_agent_design.md](03_agent_design.md)
- 테스트: **20개 → 45개**, 전부 통과 (실패 0)

## 커밋

| 커밋 | 내용 |
| --- | --- |
| `99748d7` | 추출 단계에서 기술명이 쪼개지던 문제 수정 |
| `604c35c` | 사전 v2 생성 (표준 이름은 `final_techs` 156개에서만) |

## 전후 숫자 한눈에 보기

| 항목 | 이전 | 이후 |
| --- | ---: | ---: |
| `final_techs` 대비 추출 재현율 | 70.5% | **75.2%** |
| 추출된 서로 다른 항목 | 42,010 | **27,581** |
| 추출 기준 규칙 수 | 1,998 | **2,627** |
| `Wi → Fi`, `CD → CI` 류 쪼개짐 규칙 | 있음 | **없음** |
| 사전의 표준 이름 수 | 14 | **127** |
| 사전의 표기(별칭) 수 | 40 | **253** |
| 89회 이상 후보 중 사전 해결 | 26종 (4.4%) | **130종 (21.9%)** |
| 등장 횟수 기준 사전 해결 | 6.5% | **40.7%** |
| 실제로 변환이 일어나는 표기 | 1종 (`Ajax`→`AJAX`) | **33종** |
| 에이전트 판단 대상 | 정의 없음 | **463종 (59.3%)** |

---

# 1. 추출 단계 수정

## 1-1. 무엇이 문제였나

[03_agent_design.md](03_agent_design.md)의 측정에 쓴 추출기는 **기술명에 속한 기호를 구분자로 취급**했습니다.
그 결과 "정리 전" 기준이 공고의 표기 때문이 아니라 **추출 코드 때문에** 지저분해졌습니다.

| 원문 | 수정 전 결과 | 문제 |
| --- | --- | --- |
| `C`, `C++`, `C#` | 모두 `C` 하나로 뭉침 | 서로 다른 세 언어가 한 항목이 됨 |
| `Wi-Fi` | `Wi` + `Fi` | 두 조각이 항상 함께 나와 `Wi → Fi` 규칙 생성 (interest 0.98) |
| `CI/CD` | `CI` + `CD` | 같은 이유로 `CD → CI` 규칙 생성 |
| `.NET` | 사라짐 (앞의 점이 잘림) | 항목 자체가 없어짐 |
| `Objective-C` | `Objective` + `C` | `C`의 등장 횟수를 부풀림 |
| `TCP/IP` | `TCP` + `IP` | 하나의 이름이 쪼개짐 |

이대로 두면 "정리 전은 원래 지저분하다"가 아니라 **"추출 코드가 일부러 지저분하게 만들었다"**가 되어
에이전트의 기여를 과대평가하게 됩니다.

## 1-2. 어떻게 고쳤나

`src/agent/extract.py`를 새로 만들고 세 가지를 바로잡았습니다.

### ① 이름에 속한 기호 보존

```python
_CORE = r"\.?[A-Za-z][A-Za-z0-9#+]*(?:[.\-][A-Za-z0-9#+]+)*"
```

- 앞의 점을 허용해 `.NET`을 살립니다.
- 뒤의 `+`, `#`를 이름의 일부로 둬서 `C++`, `C#`이 `C`와 구분됩니다.
- 내부의 점과 하이픈은 토큰을 끊지 않아 `Node.js`, `ASP.NET`, `Wi-Fi`가 한 덩어리로 남습니다.
- 문장 끝의 점(`Python.`)은 매치에서 제외됩니다.

### ② 복합어와 부분어 중 **하나만** 내보내기

처음에는 복합어와 부분어를 둘 다 내보냈는데, **그러면 둘이 항상 같이 나타나므로**
`On-Premise → Premise`, `GLORY → KORNIC GLORY`처럼 interest가 1에 가까운 규칙이 생겼습니다.
`Wi → Fi`와 **똑같은 종류의 인공물**입니다.

그래서 어휘를 참조하지 않는 기계적 규칙 하나로 정리했습니다.

```
모든 부분이 3글자 이상  ->  부분어만 내보낸다
그렇지 않으면          ->  복합어만 내보낸다
```

| 원문 | 결과 | 이유 |
| --- | --- | --- |
| `Wi-Fi` | `Wi-Fi` | 부분이 2글자 → 복합어 유지 |
| `CI/CD` | `CI/CD` | 같음 |
| `TCP/IP` | `TCP/IP` | `IP`가 2글자 → 복합어 유지 |
| `Objective-C` | `Objective-C` | `C`가 1글자 → 복합어 유지. **`C` 과대 집계도 함께 해결** |
| `HTML/CSS/JavaScript` | `HTML`, `CSS`, `JavaScript` | 모두 3글자 이상 → 부분어 |
| `iOS/Android` | `iOS`, `Android` | 같음 |
| `Python-based` | `Python` | `based`는 불용어로 제거 |
| `Java/Objective-C` | `Java`, `Objective-C` | 슬래시를 먼저 풀고 각 부분에 같은 규칙 재적용 |

### ③ 띄어쓴 두 단어 이름은 조립하지 않음

`Spring Boot`, `REST API` 같은 이름을 만들어 보려고 "토큰 + 대문자로 시작하는 다음 토큰"을 묶었는데,
**세 가지 변형을 측정해 보니 손해였습니다.**

| 변형 | 재현율 | 자명 규칙 수 |
| --- | ---: | ---: |
| 두 단어 조립 안 함 | **75.9%** | **53** |
| 두 단어 조립 (부분어도 유지) | 77.9% | 173 |
| 두 단어 조립 (부분어 마스킹) | 72.7% | 65 |

재현율 2.0%p를 얻는 대가로 인공물 규칙이 3배가 됩니다. 게다가 `Java Spring MySQL`처럼
기술이 나열된 문장에서 `Java Spring`을 하나로 묶는 오류가 생깁니다.
**띄어쓴 이름의 경계는 어휘 없이 알 수 없고, 그 판단이 바로 에이전트의 일**이므로 조립하지 않습니다.

## 1-3. 수정 결과

같은 공고 17,796건(12주차와 동일 집합)에서 측정했습니다.

| 항목 | 수정 전 | 수정 후 |
| --- | ---: | ---: |
| 서로 다른 항목 수 | 42,010 | **27,581** |
| 규칙 수 | 1,998 | **2,627** |
| `final_techs` 대비 재현율 | 70.5% | **75.2%** |
| 복합어 ⊃ 부분어 자명 규칙 | 0 | 12 |
| 공고당 후보 수 | 19.8 | 20.7 |

항목 수가 42,010 → 27,581로 **줄었습니다.** 같은 이름이 여러 조각으로 흩어지지 않기 때문입니다.

### 쪼개짐 규칙이 사라졌는지

| 규칙 | 수정 전 | 수정 후 |
| --- | --- | --- |
| `Wi → Fi` | 있음 | **없음** |
| `Fi → Wi` | 있음 | **없음** |
| `CD → CI` | 있음 | **없음** |
| `CI → CD` | 있음 | **없음** |
| `Sr → Jr` | 있음 | 있음 (쪼개짐이 아니라 원문에 그렇게 있음) |

### 기호·복합 항목이 보존되는지

| 항목 | 수정 전 | 수정 후 |
| --- | --- | --- |
| `C` | 없음 | **있음** |
| `C++` | 있음 | 있음 |
| `C#` | 있음 | 있음 |
| `.NET` | 없음 | **있음** |
| `ASP.NET` | 있음 | 있음 |
| `Wi-Fi` | 없음 | **있음** |
| `CI/CD` | 없음 | **있음** |
| `TCP/IP` | 없음 | **있음** |
| `Objective-C` | 없음 | **있음** |

## 1-4. 남은 노이즈는 성격이 바뀌었습니다

수정 후 상위 규칙입니다.

```
     GLORY -> KORNIC      int=0.9934    (회사명 'KORNIC GLORY')
    Cytiva -> Y           int=0.9915    (회사명)
     GLORY -> Ltd         int=0.9839    (회사명)
    Javasc -> ript        int=0.9837    (원문에 'Javasc ript' 로 공백이 들어 있음)
 Hibernate -> JPA         int=0.9509    (실제 기술 조합)
```

`Javasc ript`는 추출 코드 문제가 아닙니다. 원문 문자열에 **실제로 공백(0x20)이 들어 있습니다.**
문자 코드까지 확인했고, `saramin` 공고 여러 건에서 같은 형태로 나타납니다.

즉 남은 노이즈는 **회사명, 원문 오타, 업무 약어** 같은 *내용* 문제이며,
이것이 에이전트가 문맥을 보고 판단할 대상입니다. 추출기의 기계적 결함은 해소되었습니다.

---

# 2. 사전 v2

## 2-1. 설계 원칙

| 원칙 | 적용 |
| --- | --- |
| 표준 이름은 **만들지 않는다** | `final_techs`의 156개 이름만 표준으로 사용 |
| 사전은 **원문 표기 → 표준 이름** 연결표 | `JAVA` → `Java`, `k8s` → `Kubernetes` |
| 모든 항목에 **근거를 남긴다** | 적용된 규칙, 등장 횟수, 섹션 등장 횟수, 분류 |
| 애매하면 **넣지 않는다** | 판단 대상 목록으로 분리 |
| 89회 미만은 **다루지 않는다** | support 0.005 × 17,796 = 89. 그 아래는 어떤 규칙에도 들어갈 수 없음 |

## 2-2. 수록 규칙 4개

표기가 사전에 들어오는 경로는 네 가지뿐이고, 각 항목에 어느 경로였는지 기록됩니다.

| 규칙 | 뜻 | 수록 수 | 예시 |
| --- | --- | ---: | --- |
| `exact` | 이미 표준 이름과 동일 | 97 | `Python` → `Python` |
| `case` | 대소문자만 다름 | 16 | `JAVA` → `Java` |
| `punctuation` | 점·공백·하이픈만 다름 | 4 | `MS-SQL` → `MSSQL`, `Nest.js` → `NestJS` |
| `curated` | 사람이 검수한 항목 | 13 | `k8s` → `Kubernetes`, `RESTful` → `REST API` |

**기계적 규칙을 먼저 적용**하고, 그래도 안 되는 것만 검수 항목으로 처리합니다.
판단에 기대는 항목을 최소화하려는 의도입니다.

비교 키는 `+`와 `#`를 보존합니다. [03_agent_design.md](03_agent_design.md) 1-4절에서
기호를 지웠다가 `C`/`C++`/`C#`이 한 덩어리가 됐던 실수를 반복하지 않기 위한 조치입니다.

## 2-3. 의도적으로 넣지 않은 표기

`configs/tech_dictionary_curated.json`의 `excluded_on_purpose`에 이유까지 기록했습니다.

| 표기 | 넣지 않은 이유 |
| --- | --- |
| `REST` | REST는 아키텍처 양식이고 `REST API`는 다른 것. 연결하면 공고가 하지 않은 말을 하게 됨 |
| `AI/ML` | 두 개념 라벨을 한꺼번에 가리킴 |
| `C/C++` | 두 언어를 한꺼번에 가리킴 |
| `UI/UX` | 두 디자인 개념이고 둘 다 표준 어휘에 없음 |
| `Node` | `Node.js`일 수도, 그래프의 노드일 수도 있음 |
| `Boot` | 근처에 `Spring`이 있을 때만 `Spring Boot`. 문맥 판단이 필요 |
| `CV` | 공고에서 '이력서'로도 똑같이 자주 쓰임 |
| `TF` | '태스크포스'로도 쓰임 |
| `ES` | `Elasticsearch`일 수도, `ECMAScript`일 수도 있음 |
| `DL` | `Deep Learning`일 수도, '다운로드' 약어일 수도 있음 |
| `IDEA` | `IntelliJ IDEA`일 수도, 일반 단어일 수도 있음 |

## 2-4. v1에서 발견한 오류

**v1의 유일하게 작동하던 별칭이 틀렸습니다.**

| 확인 항목 | 값 |
| --- | --- |
| `final_techs` 안의 `Ajax` | **127회** |
| `final_techs` 안의 `AJAX` | **0회** |
| v1이 선언한 표준 이름 | `AJAX` |

v1은 표준 어휘에 **존재하지 않는 이름**을 표준으로 삼았습니다.
[01_baseline_check.md](01_baseline_check.md) 2-3절에서 "별칭 변환 127건 전부가 `Ajax` → `AJAX`"였다고
확인했는데, 그 변환은 데이터를 표준 어휘 **쪽으로** 보낸 것이 아니라 **밖으로** 내보낸 것이었습니다.

v2는 `Ajax`를 표준 이름으로 두고 `ajax`를 표기로 등록합니다.
테스트 `test_ajax_uses_the_spelling_that_the_data_actually_contains`가 이 회귀를 막습니다.

## 2-5. 분류

156개 표준 이름 전체에 분류를 부여했습니다 (`configs/tech_categories.json`).
사전 생성기는 **분류가 빠진 표준 이름이 있으면 실행을 중단**하므로, 데이터와 분류표가 어긋날 수 없습니다.

| 분류 | 사전 수록 수 |
| --- | ---: |
| 프레임워크·라이브러리 | 31 |
| 언어 | 19 |
| 개념·방법론 | 14 |
| 데이터·ML | 12 |
| 도구·협업 | 12 |
| 데이터베이스 | 12 |
| 데브옵스·CI/CD | 10 |
| 클라우드·인프라 | 8 |
| API·프로토콜 | 5 |
| 운영체제·플랫폼 | 4 |

### `concept` 분류를 따로 둔 이유

```
AI, CI/CD, Computer Vision, Deep Learning, DevOps, Generative AI,
LLM, ML, MLOps, NLP, NoSQL, OCR, RDBMS, Vector DB
```

[01_baseline_check.md](01_baseline_check.md) 2-3절에서 지적한 문제입니다.
`AI`는 등장 1위(5,549회)인데 기술이 아니라 분야입니다. `AI → ML` 같은 규칙은 자명해서 정보가 없습니다.
이제 분류가 있으므로 **Apriori 항목에서 `concept` 그룹을 제외하는 실험**을 별도로 돌릴 수 있습니다.
이번 작업에서는 분류만 부여하고 제외는 적용하지 않았습니다.

## 2-6. 적용 결과

### 사전 v1 대 v2

89회 이상 후보 593종(등장 213,161회)을 대상으로 측정했습니다.

| | 표준 이름 | 해결한 후보 | 등장 횟수 기준 | 실제 변환 발생 |
| --- | ---: | ---: | ---: | ---: |
| 사전 v1 | 14 | 26종 (4.4%) | 13,869회 (**6.5%**) | 14종 2,540회 |
| **사전 v2** | **127** | **130종 (21.9%)** | **86,798회 (40.7%)** | **33종 9,354회** |

### 실제로 변환이 일어나는 표기 상위 20

| 표기 | 표준 이름 | 규칙 | 등장 |
| --- | --- | --- | ---: |
| `JAVA` | `Java` | case | 2,568 |
| `java` | `Java` | case | 620 |
| `RESTful` | `REST API` | curated | 617 |
| `Javascript` | `JavaScript` | case | 549 |
| `Vue3` | `Vue.js` | curated | 547 |
| `python` | `Python` | case | 418 |
| `Vue` | `Vue.js` | curated | 360 |
| `HTML5` | `HTML` | curated | 268 |
| `Github` | `GitHub` | case | 250 |
| `Pytorch` | `PyTorch` | case | 214 |
| `RestAPI` | `REST API` | punctuation | 194 |
| `MS-SQL` | `MSSQL` | punctuation | 160 |
| `Typescript` | `TypeScript` | case | 160 |
| `kubernetes` | `Kubernetes` | case | 159 |
| `Tensorflow` | `TensorFlow` | case | 147 |
| `CSS3` | `CSS` | curated | 144 |
| `k8s` | `Kubernetes` | curated | 139 |
| `Tailwind` | `Tailwind CSS` | curated | 136 |
| `JS` | `JavaScript` | curated | 130 |
| `REACT` | `React` | case | 128 |

### 사전에 들어가지 않은 표준 이름 29개

89회 이상 후보로 등장하지 않아 수록되지 않았습니다. 표준 이름 자체는 유효하며, 등장이 적을 뿐입니다.

```
AI Agent, Bootstrap, Cassandra, CentOS, Dart, ELK Stack, Eclipse, Firestore,
Hadoop, IntelliJ, Keras, Kubeflow, Laravel, Lua, Milvus, NumPy, Perl, Pinecone,
Postman, Recoil, Ruby, Scala, Serverless, Swagger, Visual Studio, YOLO, Yarn,
npm, pnpm
```

## 2-7. 에이전트 판단 대상 463종

사전으로 해결되지 않은 후보입니다. 등장 횟수 기준 **59.3%**로, 아직 절반 이상이 남아 있습니다.
`artifacts/agent_review_candidates.json`에 전체 목록과 이유가 들어 있습니다.

### 상위 30

| 순위 | 후보 | 등장 | 섹션 등장 | 순위 | 후보 | 등장 | 섹션 등장 |
| ---: | --- | ---: | ---: | ---: | --- | ---: | ---: |
| 1 | `API` | 3,770 | 953 | 16 | `Claude` | 1,152 | 210 |
| 2 | `D` | 2,729 | 177 | 17 | `Boot` | 1,131 | 571 |
| 3 | `SI` | 2,584 | 672 | 18 | `SaaS` | 1,126 | 90 |
| 4 | `SW` | 2,335 | 159 | 19 | `Cloud` | 1,123 | 253 |
| 5 | `PM` | 2,326 | 69 | 20 | `B2B` | 1,103 | 47 |
| 6 | `AI/ML` | 2,021 | 64 | 21 | `Data` | 1,062 | 136 |
| 7 | `ERP` | 1,960 | 612 | 22 | `RAG` | 961 | 197 |
| 8 | `DB` | 1,927 | 262 | 23 | `REST` | 919 | 192 |
| 9 | `PL` | 1,695 | 29 | 24 | `QA` | 911 | 36 |
| 10 | `CRM` | 1,521 | 555 | 25 | `S/W` | 904 | 33 |
| 11 | `K` | 1,417 | 2 | 26 | `MD` | 832 | 4 |
| 12 | `PO` | 1,408 | 17 | 27 | `UI/UX` | 812 | 63 |
| 13 | `Agent` | 1,382 | 148 | 28 | `Web` | 807 | 69 |
| 14 | `DBA` | 1,259 | 27 | 29 | `DBMS` | 795 | 111 |
| 15 | `UI` | 1,219 | 151 | 30 | `Vision` | 795 | 90 |

### 판단 대상의 성격

| 성격 | 등장 횟수 | 예시 |
| --- | ---: | --- |
| 업무·사업 약어 (기술 아님) | 22,057 | `SI`, `SW`, `PM`, `ERP`, `CRM`, `PO`, `DBA`, `SaaS`, `B2B`, `MD`, `MES`, `QA` |
| 일반 명사·조각 | 15,510 | `D`, `K`, `B`, `Agent`, `Boot`, `Cloud`, `Data`, `Web`, `Vision`, `Software`, `Windows` |
| 어휘에 없는 실제 기술 | 6,579 | `RAG`, `JSP`, `GPU`, `IoT`, `MSA`, `ChatGPT`, `Cursor`, `Confluence`, `Objective-C` |
| 복합 표기 | 4,731 | `AI/ML`, `UI/UX`, `S/W`, `C/C++`, `H/W` |
| 회사·브랜드명 | 3,536 | `SK`, `LG`, `MS`, `LIG`, `Google`, `KORNIC`, `GLORY`, `Cytiva` |

**섹션 등장 횟수가 판단 단서가 됩니다.** `ERP`는 612회, `CRM`은 555회, `Boot`는 571회가
기술 목록 섹션 안에서 나왔습니다. 반면 `PL`(29회), `MD`(4회), `K`(2회)는 거의 본문에서만 나왔습니다.
[03_agent_design.md](03_agent_design.md) 1-3절에서 섹션 후보의 정확도가 41.7% 대 17.5%로
높았던 것과 일치합니다.

`어휘에 없는 실제 기술` 6,579회는 **사전으로 해결할 수 없는 종류**입니다.
표준 이름을 만들지 않는다는 원칙 때문이며, 팀이 표준 어휘를 확장하기로 결정하면
그때 `final_techs` 쪽을 늘리는 것이 맞는 순서입니다.

---

# 3. 한계

## 3-1. 평가가 `final_techs` 쪽으로 유리해집니다 — 가장 중요한 한계

**표준 이름을 `final_techs`에서 가져왔기 때문에, `final_techs`를 정답지로 쓰는 평가는
구조적으로 우리에게 유리하게 나옵니다.**

| 단계 | 사용한 것 |
| --- | --- |
| 사전의 표준 이름 | `final_techs`의 156개 |
| 평가의 정답지 | **같은** `final_techs` |

같은 출처를 양쪽에 쓰고 있습니다. 구체적으로 이런 편향이 생깁니다.

| 편향 | 내용 |
| --- | --- |
| 정밀도 과대평가 | 사전이 표준 어휘 안으로만 변환하므로, 변환된 값은 정의상 정답지와 일치합니다. 사전이 적중할수록 정밀도가 오르는데 이는 "정답지와 같은 어휘를 썼기 때문"입니다 |
| 어휘 밖 기술에 불리 | `RAG`, `JSP`, `IoT`는 실제 기술이지만 어휘에 없어 사전에 넣을 수 없고, 넣었다 해도 정답지에 없어 오답 처리됩니다 |
| 정답지 자체의 누락이 반영 안 됨 | [01_baseline_check.md](01_baseline_check.md) 1-6절의 `Scylla`, `Ray`, `Mantine` 누락과 `Objective-C` → `C` 오추출이 정답지에 그대로 들어 있습니다 |
| 분류도 같은 어휘에 묶임 | `configs/tech_categories.json`은 156개에만 분류를 부여하므로, 어휘 밖 기술은 분류조차 받지 못합니다 |

### 이 한계를 다루는 방법

| 방법 | 내용 |
| --- | --- |
| 지표를 두 개로 나눠 보고 | ① 어휘 안 항목만으로 계산한 지표, ② 어휘 밖 항목을 포함한 지표. 두 숫자를 함께 적습니다 |
| 사람 검수 100건 | [03_agent_design.md](03_agent_design.md) 5-4절대로, **원문 기준**으로 판정합니다. 정답지가 아니라 원문이 기준입니다 |
| 규칙 단위 평가를 병행 | [03_agent_design.md](03_agent_design.md) 6절의 두 질문은 "상위 규칙이 사람 눈에 타당한가"를 묻습니다. 이 평가는 `final_techs`를 쓰지 않아 편향에서 자유롭습니다 |
| 어휘 확장은 별도 결정으로 | 표준 어휘를 늘리면 사전과 정답지가 함께 바뀝니다. 그때는 확장 전후 지표를 모두 보고해야 합니다 |

**이 편향 때문에, 사전 v2의 적중률(40.7%)을 "에이전트 성능"으로 읽어서는 안 됩니다.**
그것은 "데이터가 자기 어휘로 얼마나 일관되게 쓰여 있는가"에 더 가깝습니다.

## 3-2. 그 밖의 한계

| # | 한계 | 영향 |
| --- | --- | --- |
| 1 | **한글 기술명을 추출하지 못합니다.** 추출기는 ASCII 토큰만 봅니다. `자바`, `파이썬`, `리액트` 같은 표기는 후보가 되지 않습니다 | 설계 문서의 예시(`자바 → Java`)는 아직 작동하지 않습니다. 사전에 넣어도 후보로 들어오지 않습니다 |
| 2 | **띄어쓴 이름을 조립하지 않습니다.** `Spring Boot`는 `Spring` + `Boot`로 들어옵니다 | `Boot`(1,131회)가 판단 대상 17위에 올라 있습니다. 에이전트가 문맥으로 해결할 대상입니다 |
| 3 | **89회 하한 아래는 다루지 않습니다.** 고유 후보 27,580종 중 593종(2.2%)만 대상 | 규칙 분석에는 영향이 없지만, 개별 공고의 정리 품질은 낮습니다 |
| 4 | **원문 자체의 오타는 고칠 수 없습니다.** `Javasc ript`는 원문에 공백이 있습니다 | `Javasc → ript` 규칙이 남아 있습니다 |
| 5 | **`curated` 13종은 판단에 기댑니다.** 기계적 규칙이 아닙니다 | 각 항목에 `rule: "curated"`를 남겨 감사할 수 있게 했습니다 |
| 6 | **섹션 헤더 목록이 고정입니다.** 13개 표현만 봅니다 | 공고의 32.1%만 섹션으로 인식됩니다 |
| 7 | **`concept` 제외를 적용하지 않았습니다.** 분류만 부여했습니다 | `AI`(1위)가 여전히 Apriori 항목으로 들어갑니다 |

---

# 4. 테스트

**20개 → 45개**, 전부 통과.

| 파일 | 추가 | 검증 내용 |
| --- | ---: | --- |
| `tests/test_agent_extract.py` | 14 | 기호 보존, 하이픈·슬래시 복합어, 섹션 라벨 |
| `tests/test_agent_dictionary.py` | 11 | 비교 키, 사전 무결성, `Ajax` 회귀 방지, 기존 로더 호환 |

## 요청하신 두 테스트

### 기호 보존 (`C++`, `C#`)

```python
def test_plus_and_hash_suffixes_survive_extraction(self):
    names = set(candidate_names("C, C++, C# 개발 경험", self.stopwords))
    self.assertEqual(names, {"C", "C++", "C#"})

def test_c_family_names_do_not_collapse_into_one_candidate(self):
    names = candidate_names("C++ 와 C# 를 모두 씁니다", self.stopwords)
    self.assertIn("C++", names)
    self.assertIn("C#", names)
    self.assertNotIn("C", names)     # C++ 에서 C 를 떼어내지 않음
```

사전 쪽에서도 같은 성질을 검증합니다.

```python
def test_plus_and_hash_are_preserved_so_the_c_family_stays_apart(self):
    keys = {canonical_key(name) for name in ("C", "C++", "C#")}
    self.assertEqual(len(keys), 3)
```

### 하이픈 단어 (`Wi-Fi`)

```python
def test_wifi_stays_whole_and_never_yields_its_fragments(self):
    names = set(candidate_names("Wi-Fi 환경 구축", self.stopwords))
    self.assertEqual(names, {"Wi-Fi"})
    self.assertNotIn("Wi", names)
    self.assertNotIn("Fi", names)
```

그리고 인공물이 생기는 조건 자체를 막는 테스트를 함께 뒀습니다.

```python
def test_a_compound_and_its_own_fragment_are_never_emitted_together(self):
    for text in ("Wi-Fi", "CI/CD", "HTML/CSS", "Objective-C", "TCP/IP", "ETL/ELT", "On-Premise"):
        names = set(candidate_names(text, self.stopwords))
        for name in names:
            fragments = set(name.replace("/", "-").split("-"))
            self.assertFalse(fragments & (names - {name}))
```

복합어와 부분어가 함께 나오면 interest가 1에 가까운 규칙이 **반드시** 생기므로,
결과를 검사하는 대신 **원인 조건**을 검사합니다.

---

# 5. 재현 명령

```bash
# 1) 후보 추출 (12주차와 동일한 17,796건으로 제한, 수가 어긋나면 중단)
.venv/bin/python -m src.agent.run_extract

# 2) 사전 v2 생성 + 판단 대상 목록
.venv/bin/python -m src.agent.build_dictionary

# 3) 테스트
.venv/bin/python -m unittest discover -s tests   # 45 tests, OK
```

| 옵션 | 용도 |
| --- | --- |
| `run_extract --limit 200` | 작은 표본으로 빠르게 확인 (집합 교차 검증 생략) |
| `build_dictionary --minimum-occurrences 1` | 89회 하한을 풀고 전체 후보 처리 |

## 산출물

| 파일 | 내용 |
| --- | --- |
| `configs/tech_dictionary_v2.json` | 사전 v2. 표준 이름 127개, 표기 253개, 각 항목에 규칙·분류·근거 |
| `configs/tech_categories.json` | 156개 표준 이름의 분류 (생성기가 누락 시 중단) |
| `configs/tech_dictionary_curated.json` | 검수 별칭과 **의도적 제외 목록 + 이유** |
| `configs/extract_stopwords.json` | 불용어 365개. 업무 약어는 일부러 넣지 않음 |
| `artifacts/agent_candidates.json` | 후보 27,580종, 등장 368,579회, 섹션 등장 횟수 포함 |
| `artifacts/agent_review_candidates.json` | 에이전트 판단 대상 463종과 이유 |

불용어에 `SI`, `ERP` 같은 업무 약어를 **넣지 않았습니다.** 조용히 지우면
정리 전 기준이 실제보다 깨끗해 보여서, 에이전트의 기여를 다시 과대평가하게 됩니다.

---

# 6. 다음 단계

| 순위 | 할 일 | 근거 |
| --- | --- | --- |
| 1 | `src/agent/` 에이전트 루프 구현 (4요소) | 판단 대상 463종 59.3%가 남아 있음 |
| 2 | 한글 기술명 추출 추가 | 3-2절 1번. 설계 문서의 예시가 아직 작동하지 않음 |
| 3 | `concept` 제외 실험 | 2-5절. `AI`가 등장 1위인 채로 Apriori에 들어감 |
| 4 | [03](03_agent_design.md) 6절 두 질문 측정 | 정리 전 기준이 준비되었으므로 비교 가능 |
| 5 | 표준 어휘 확장 여부 결정 | `RAG`, `JSP`, `IoT` 등 6,579회. 3-1절 편향과 함께 판단 |
