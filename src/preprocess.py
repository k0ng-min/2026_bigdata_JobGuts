"""
JOBGUTS 1단계 — 데이터 수집 및 전처리
=====================================
대상 데이터셋: Hugging Face `young-cc/korean-it-recruit-dataset`
선정 파일    : master_merged_v5.json (저장소의 최신 단일 버전, 178.0MB)

처리 흐름
  [1] 원본 파일 확인/다운로드          -> data/raw/master_merged_v5.json
  [2] 로드 (JSON 배열)
  [3] 결측치 제거                      (source/job_id/company/title/raw_text)
  [4] 중복 제거
        (a) source + job_id 동일
        (b) 기업(company) + 제목(title) + 본문(raw_text) 동일 (정규화 비교)
        * 기술 목록(final_techs/hard_skills)은 중복 판단에 절대 사용하지 않는다.
  [5] 기술 목록 기준 필드 결정         (final_techs vs hard_skills, 표본 20건 원문 대조)
  [6] 직무 분류                        (Backend / Frontend / Fullstack / Data/AI / Other)
  [7] 경력 분류                        (라벨 + raw_text 본문 검사)
        - 신입/경력무관 그룹, 최소 1~3년 경력 그룹, 3년+ 경력 그룹
        - 라벨·본문 충돌/애매 -> data/processed/review_needed.csv 로 분리
  [8] 저장                             -> data/processed/cleaned_jobs.parquet
  [9] 직무·경력 집단별 최종 유효 공고 수 통계표 출력
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------- 경로/상수
BASE_DIR = Path(__file__).resolve().parents[1]
RAW_PATH = BASE_DIR / "data" / "raw" / "master_merged_v5.json"
RAW_URL = (
    "https://huggingface.co/datasets/young-cc/korean-it-recruit-dataset"
    "/resolve/main/master_merged_v5.json"
)
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CLEANED_PATH = PROCESSED_DIR / "cleaned_jobs.parquet"
REVIEW_PATH = PROCESSED_DIR / "review_needed.csv"

REQUIRED_COLS = ["source", "job_id", "company", "title", "raw_text"]
MIN_TEXT_LEN = 30        # 이보다 짧은 본문은 사실상 결측으로 본다
DATAAI_MIN_COUNT = 500   # 데이터/AI 직무를 분석 대상에 포함할 최소 유효 공고 수
SAMPLE_N = 20            # 기술 필드 검증용 표본 수
SAMPLE_SEED = 42

# 원본 경력 라벨 -> 그룹 코드 (ENTRY=신입/경력무관, EXP13=최소1~3년, EXP3P=3년+)
LABEL_MAP = {
    "신입": "ENTRY",
    "경력무관": "ENTRY",
    "1~3년차": "EXP13",
    "3~5년차": "EXP3P",
    "5년이상": "EXP3P",
}
CAREER_NAME = {
    "ENTRY": "신입/경력무관",
    "EXP13": "경력(최소1~3년)",
    "EXP3P": "경력(3년+)",
}
JOB_ORDER = ["Backend", "Frontend", "Fullstack", "Data/AI", "Other"]


# ================================================================ [1] 다운로드
def ensure_raw_file() -> Path:
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    if RAW_PATH.exists() and RAW_PATH.stat().st_size > 100_000_000:
        print(f"[1] 원본 파일 확인: {RAW_PATH.name} ({RAW_PATH.stat().st_size:,} bytes)")
        return RAW_PATH
    print(f"[1] 다운로드 시작: {RAW_URL}")
    with requests.get(RAW_URL, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done = 0
        with open(RAW_PATH, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                done += len(chunk)
                pct = f"{done * 100 // total}%" if total else f"{done:,}B"
                print(f"\r    {done:,}/{total:,} bytes ({pct})", end="", flush=True)
    print()
    print(f"    완료: {RAW_PATH} ({RAW_PATH.stat().st_size:,} bytes)")
    return RAW_PATH


# ================================================================ [2] 로드
def load_raw(path: Path) -> pd.DataFrame:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    print(f"[2] 로드 완료: {len(df):,}건, 컬럼 {list(df.columns)}")
    return df


# ================================================================ [3] 결측치 제거
def drop_missing(df: pd.DataFrame) -> pd.DataFrame:
    n0 = len(df)
    work = df.copy()
    for c in REQUIRED_COLS:
        work[c] = work[c].astype("string").str.strip()
    mask_required = work[REQUIRED_COLS].isna().any(axis=1)
    for c in REQUIRED_COLS:
        mask_required |= work[c].eq("")
    mask_short = work["raw_text"].str.len() < MIN_TEXT_LEN
    n_missing = int(mask_required.sum())
    n_short = int((~mask_required & mask_short).sum())
    out = work[~(mask_required | mask_short)].copy()
    for c in REQUIRED_COLS:
        out[c] = out[c].astype(str)
    print(f"[3] 결측치 제거: -{n_missing:,}건(필수 필드 결측) -{n_short:,}건(본문 {MIN_TEXT_LEN}자 미만)"
          f" -> {len(out):,}건")
    field_missing = {c: int(work[c].isna().sum() + (work[c] == "").sum()) for c in REQUIRED_COLS}
    print(f"    필드별 결측 수: {field_missing}")
    for src, n in work[mask_required]["source"].value_counts().items():
        print(f"    - source={src}: {n:,}건 제외 (공고 식별·중복 검사에 필요한 "
              f"company/title 등 메타데이터가 원본부터 결측)")
    return out


# ================================================================ [4] 중복 제거
def _norm_key(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    n0 = len(df)
    # (a) source + job_id 조합 완전 중복 (같은 사이트 재수집)
    df = df.drop_duplicates(subset=["source", "job_id"], keep="first")
    n_after_a = len(df)
    # (b) 동일 기업 + 제목 + 본문 (사이트 간 교차 중복 포함).
    #     기술 목록(final_techs/hard_skills)은 키에 전혀 사용하지 않는다.
    key = (
        df["company"].map(_norm_key) + "||" + df["title"].map(_norm_key) + "||"
        + df["raw_text"].map(_norm_key)
    )
    df = df.assign(_dup_key=key).drop_duplicates(subset=["_dup_key"], keep="first")
    n_after_b = len(df)
    print(f"[4] 중복 제거: (a) source+job_id -{n0 - n_after_a:,}건, "
          f"(b) 기업+제목+본문 -{n_after_a - n_after_b:,}건 -> {n_after_b:,}건")
    return df.drop(columns=["_dup_key"]).reset_index(drop=True)


# ================================================================ [5] 기술 목록 필드 검증
def _tech_pattern(tech: str) -> re.Pattern | None:
    """기술명 -> 본문 등장 확인용 정규식. 대소문자 무시, ASCII 단어 경계 사용.

    파이썬 \b 는 한글도 워드문자로 취급해 'React와' 같은 경우 매칭이 깨지므로,
    인접 문자가 ASCII 영숫자가 아님을 확인하는 룩어라운드로 경계를 만든다.
    """
    t = tech.strip()
    if not t:
        return None
    low = t.lower()
    # substring 오탐 방지: 'Java'가 'JavaScript'에 묻히지 않도록 부정형 lookahead
    if low == "java":
        return re.compile(r"(?<![A-Za-z0-9])Java(?!\s*Script)(?![A-Za-z0-9])", re.IGNORECASE)
    esc = re.escape(t)
    if re.match(r"^[A-Za-z0-9]", t) and re.search(r"[A-Za-z0-9]$", t):
        esc = r"(?<![A-Za-z0-9])" + esc + r"(?![A-Za-z0-9])"
    return re.compile(esc, re.IGNORECASE)


def _tech_precision(raw_text: str, techs) -> tuple[int, int, list[str]]:
    """목록 중 본문에 실제 등장하는 기술 수 반환 -> (matched, total, missing)."""
    if not isinstance(techs, list):
        return 0, 0, []
    text = raw_text or ""
    matched, missing = 0, []
    for tech in techs:
        pat = _tech_pattern(str(tech))
        if pat is None:
            continue
        if pat.search(text):
            matched += 1
        else:
            missing.append(str(tech))
    return matched, len(techs), missing


def validate_tech_field(df: pd.DataFrame) -> str:
    """final_techs vs hard_skills: 표본 20건의 raw_text와 대조해 정밀도가 높은 필드 선택."""
    sample = df.sample(n=min(SAMPLE_N, len(df)), random_state=SAMPLE_SEED)
    rows, agg = [], {"final_techs": [0, 0], "hard_skills": [0, 0]}
    for _, r in sample.iterrows():
        fm, ft, fmiss = _tech_precision(r["raw_text"], r["final_techs"])
        hm, ht, hmiss = _tech_precision(r["raw_text"], r["hard_skills"])
        agg["final_techs"][0] += fm
        agg["final_techs"][1] += ft
        agg["hard_skills"][0] += hm
        agg["hard_skills"][1] += ht
        rows.append((r["source"], (r["title"] or "")[:24], fm, ft, hm, ht))

    print(f"[5] 기술 목록 기준 필드 검증 (raw_text 표본 {len(sample)}건, seed={SAMPLE_SEED})")
    print("    표본별 본문 등장 확인 결과 (본문에 실제 언급된 기술 수 / 목록 총 기술 수)")
    print(f"    {'#':>2} {'source':<9} {'title':<26} {'final_techs':>12} {'hard_skills':>12}")
    for i, (src, title, fm, ft, hm, ht) in enumerate(rows, 1):
        print(f"    {i:>2} {src:<9} {title:<26} {fm}/{ft:>8} {hm}/{ht:>8}")

    stats = {}
    for field, (m, t) in agg.items():
        prec = m / t if t else 0.0
        stats[field] = prec
        print(f"    - {field:<12}: {m}/{t} 기술이 본문에 확인됨 (전체 정밀도 {prec:.1%})")

    chosen = max(stats, key=stats.get)  # 동률이면 dict 순서상 final_techs 우선
    other = "hard_skills" if chosen == "final_techs" else "final_techs"
    print(f"    >> 선택: {chosen}")
    print(f"    >> 근거: 표본 대조 결과 {chosen}의 본문 등장률 {stats[chosen]:.1%}가 "
          f"{other}의 {stats[other]:.1%}보다 높다. 목록에만 있고 본문에 없는 기술이 적다는 뜻으로,")
    print(f"       연관규칙 분석의 장바구니를 원문 근거에 가깝게 만든다. "
          f"(두 필드 모두 동일한 substring 규칙으로 측정한 공정한 비교다.)")
    return chosen


# ================================================================ [6] 직무 분류
FE_KW = ["프론트엔드", "프론트 앤드", "프론트앤드", "front-end", "frontend",
         "front end", "웹퍼블리셔", "웹 퍼블리셔", "퍼블리셔", "ui 개발", "ui개발",
         "ui/ux 개발", "마크업 개발", "마크업개발"]
BE_KW = ["백엔드", "백 앤드", "백앤드", "back-end", "backend", "back end",
         "서버 개발", "서버개발", "서버 사이드", "server side", "서버 엔지니어",
         "api 개발", "api개발", "플랫폼 개발"]
FS_KW = ["풀스택", "풀 스택", "풀스텍", "full stack", "full-stack", "fullstack"]
DA_KW = ["데이터 사이언", "데이터사이언", "데이터 엔지니어", "데이터엔지니어",
         "데이터 분석", "데이터분석", "머신러닝", "machine learning", "딥러닝",
         "deep learning", "ml 엔지니어", "ml엔지니어", "ai 엔지니어", "ai엔지니어",
         "인공지능", "mlops", "빅데이터", "big data", "data scientist",
         "data engineer", "data analyst", "llm", "추천 시스템", "검색 엔지니어",
         "알고리즘 엔지니어", "데이터베이스 관리자", "dba", "데이터 플랫폼"]
# 프레임워크명 등은 타 직무 본문에서도 자주 언급되므로 '제목' 판정에만 쓰는 보조 신호다.
FE_TITLE_EXTRA = ["react", "리액트", "vue", "뷰.js", "svelte", "angular",
                  "웹개발자", "웹 개발자", "웹 퍼블리싱"]
BE_TITLE_EXTRA = ["spring", "스프링", "django", "node.js", "nodejs", "nestjs",
                  "java 개발", "java개발", "자바 개발", "자바개발", "쿼리 튜닝"]
DA_TITLE_EXTRA = ["ai 개발자", "ai개발자", "ai 연구", "ai 리서치", "ai research",
                  "ai scientist", "데이터 파이프라인", "데이터파이프라인"]


def _kw_hits(text: str, kws: list[str]) -> list[str]:
    return [k for k in kws if k in text]


def _kw_count(text: str, kws: list[str]) -> int:
    return sum(text.count(k) for k in kws)


BODY_KW_MIN = 2  # 본문 판정에 필요한 최소 키워드 등장 횟수


def classify_job(title: str, raw_text: str) -> str:
    """제목 우선(1회 히트로 판정), 제목에 신호가 없으면 본문 키워드 등장 횟수로 분류.

    본문은 '프론트엔드 개발자와 협업' 같은 1회성 언급까지 직무 신호로 보면
    과대 분류되므로, 직무군 키워드가 2회 이상 등장할 때만 판정에 사용한다.
    """
    t = (title or "").lower()
    body = _signal_text(raw_text).lower()

    fs = _kw_hits(t, FS_KW)
    fe = _kw_hits(t, FE_KW) or _kw_hits(t, FE_TITLE_EXTRA)
    be = _kw_hits(t, BE_KW) or _kw_hits(t, BE_TITLE_EXTRA)
    da = _kw_hits(t, DA_KW) or _kw_hits(t, DA_TITLE_EXTRA)
    if fs:
        return "Fullstack"                      # 풀스택 명시가 최우선
    if da and not (fe or be):
        return "Data/AI"
    if fe and be:
        return "Fullstack"                      # 제목에 FE·BE 동시 = 풀스택성 공고
    if fe:
        return "Frontend"
    if be:
        return "Backend"
    if da:
        return "Data/AI"

    c_fs = _kw_count(body, FS_KW)
    c_fe, c_be, c_da = _kw_count(body, FE_KW), _kw_count(body, BE_KW), _kw_count(body, DA_KW)
    if c_fs >= BODY_KW_MIN:
        return "Fullstack"
    if c_da >= BODY_KW_MIN and not (c_fe or c_be):   # 본문만 근거일 때는 엄격히
        return "Data/AI"
    if c_fe >= BODY_KW_MIN and c_be >= BODY_KW_MIN:
        return "Fullstack"
    if c_fe >= BODY_KW_MIN:
        return "Frontend"
    if c_be >= BODY_KW_MIN:
        return "Backend"
    if c_da >= BODY_KW_MIN:
        return "Data/AI"
    return "Other"


def assign_job_group(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["job_group"] = [classify_job(t, b) for t, b in zip(df["title"], df["raw_text"])]
    vc = df["job_group"].value_counts()
    print(f"[6] 직무 분류: " + ", ".join(f"{k}={v:,}" for k, v in vc.items()))
    return df


# ================================================================ [7] 경력 분류
# 본문(raw_text)에서 '신입 지원 가능/경력무관' 신호를 찾는 패턴.
# '신입' 단어 단독은 맥락이 다양해 신호로 쓰지 않고, 뒤에 오는 단어와의 결합만 허용한다.
ENTRY_PATTERNS = [
    r"경력\s*무관",
    r"신입\s*[/·,∙\-~]\s*경력",          # 신입/경력, 신입·경력 (모두 지원 가능 관용구)
    r"신입\s*(?:및|과|와|또는)\s*경력",   # 신입 및 경력
    r"신입(?:\s*(?:도|도\s*지원|도\s*가능|지원\s*가능|가능|환영|모집|채용|공채|출신))",
    r"신입\s*(?:개발자|엔지니어|디자이너|기획자|분석가|매니저|사원)",
    # '인턴'은 신입 가능 신호이나, '경력 N년 (인턴 포함/합산)' 처럼 경력 산정 방식이나
    # '유관업무 경험자(인턴·알바)' 같은 우대 보일러플레이트는 신입 신호가 아니므로 제외한다.
    r"인턴(?:십|쉽)?(?!\s*(?:경력\s*)?(?:등?\s*)?(?:포함|합산|인정))(?!\s*[·/,]\s*알바)",
]
# 본문에서 '최소 경력 연수'를 뽑는 패턴(그룹1=최소 연수).
# - 기술 숙련 경험('Python 개발 경험 1년')은 최소 경력 요구가 아니므로 일반 '경험'은
#   제외하고 '경력'/'실무 경험'만 인정한다.
# - 'N년 이하/미만'은 상한 조건이므로 매칭 후처리에서 제외한다.
YEARS_PATTERNS = [
    r"(\d+)\s*년(?:차)?\s*[\-~∼]\s*\d+\s*년(?:차)?",               # 3~5년, 3년차~5년차 -> 최소값
    r"경력\s*(?:자\s*)?(\d+)\s*년(?:\s*이상)?",                     # 경력 3년, 경력자 3년 이상
    r"최소\s*(?:경력\s*)?(\d+)\s*년",                               # 최소 3년
    r"(\d+)\s*년(?:차)?\s*(?:이상의|이상)",                          # 3년 이상, 3년차 이상
    r"(\d+)\s*년(?:\s*이상)?\s*(?:관련\s*)?(?:경력|실무\s*경험)",    # 3년 경력/실무 경험
]
CAREER_ONLY_PATTERN = re.compile(r"경력(?:자|직)")                   # 연수 불명 경력 언급

# jobkorea의 raw_text는 페이지 전체를 긁은 것이라 하단에 다른 회사 추천공고·태그
# 내비게이션이 붙어 있다(예: 추천공고의 '경력10년↑', 태그 목록의 '데이터사이언티스트').
# 직무·경력 신호 추출에는 이 boilerplate 이후를 제거한 텍스트를 사용한다.
# (저장 결과의 raw_text는 원본 그대로 보존한다.)
BODY_TRUNCATE_MARKERS = ["관련 태그", "본 채용정보는", "무단전재"]


def _signal_text(raw_text: str) -> str:
    text = raw_text or ""
    cut = len(text)
    for marker in BODY_TRUNCATE_MARKERS:
        i = text.find(marker)
        if i != -1:
            cut = min(cut, i)
    return text[:cut]

_RE_ENTRY = [re.compile(p) for p in ENTRY_PATTERNS]
_RE_YEARS = [re.compile(p) for p in YEARS_PATTERNS]


def _context_around(text: str, pos: int, width: int = 18) -> str:
    return text[max(0, pos - width): pos + width].replace("\n", " ")


# 신입 허용 표현과 경력 연수 요구가 '같은 조건 문장'에 병기된 경우
# (예: '경력 1년 이상 (신입 지원 가능)', '신입 / 경력 3년 이상') 신입 지원 가능으로
# 해석하기 위한 근접 거리(문자 수). 이보다 멀리 떨어져 동시 등장하면 충돌로 본다.
ENTRY_YEARS_PROXIMITY = 25


def analyze_text_career(raw_text: str) -> dict:
    """본문만으로 경력 정보 판정. 반환: {group, entry_evidence, years_evidence, min_years}"""
    text = _signal_text(raw_text)
    entry_matches = [m for p in _RE_ENTRY for m in p.finditer(text)]
    entry_ev = list(dict.fromkeys(m.group(0).strip() for m in entry_matches))

    def near_entry(m) -> bool:
        for e in entry_matches:
            if abs(m.start() - e.end()) <= ENTRY_YEARS_PROXIMITY or abs(e.start() - m.end()) <= ENTRY_YEARS_PROXIMITY:
                return True
        return False

    min_years, years_ev, adjacent = None, [], []
    for pat in _RE_YEARS:
        for m in pat.finditer(text):
            after = text[m.end(): m.end() + 8]
            if "이하" in after or "미만" in after:
                continue  # 'N년 이하/미만'은 상한 조건이라 최소 경력 요구가 아니다
            if re.search(r"근무\s*가능|계약|근속", after):
                continue  # 'N년 근무 가능/계약기간/근속' 등은 근무 기간 조건이다
            pre = text[max(0, m.start() - 12): m.start()]
            if re.search(r"경험\s*$", pre) and not re.search(r"실무\s*경험\s*$", pre):
                continue  # '특정 기술 경험 N년'은 숙련 조건이지 최소 경력 요구가 아니다
            # 'N년 이상 경력 우대'는 요구가 아니므로 제외. 단 매칭 뒤 '우대'까지 사이에
            # 마침표 등 구분 기호가 있으면 다음 섹션 제목('우대조건')이므로 제외하지 않는다.
            seg_before = text[max(0, m.start() - 25): m.start()]
            seg_after = text[m.end(): m.end() + 15]
            if "우대" in seg_before:
                continue
            j = seg_after.find("우대")
            if j != -1 and not any(ch in seg_after[:j] for ch in ".·•\n"):
                continue
            if entry_matches and near_entry(m):
                # '경력 N년 이상 (신입 지원 가능)' 등 같은 문장 병기 -> 신입 허용 조건
                adjacent.append(m.group(0))
                continue
            ctx = _context_around(text, m.start(), 15)
            years_ev.append(f"{m.group(0)} (@{ctx})")
            y = int(m.group(1))
            min_years = y if min_years is None else min(min_years, y)

    only_career = bool(CAREER_ONLY_PATTERN.search(text))

    ev = ", ".join(entry_ev)
    if adjacent:
        ev = (ev + f" | 신입 허용과 병기된 경력조건: {', '.join(dict.fromkeys(adjacent))}").strip(" |")

    if entry_ev and min_years is not None:
        group = "CONFLICT"   # 신입 가능 언급과 (떨어진) 경력 연수 요구가 동시 존재
    elif min_years is not None:
        group = "EXP13" if min_years <= 3 else "EXP3P"
    elif entry_ev:
        group = "ENTRY"
    elif only_career:
        group = "EXP_UNSPEC"
    else:
        group = None
    return {
        "group": group,
        "entry_evidence": ev,
        "years_evidence": "; ".join(years_ev),
        "min_years": min_years,
    }


def classify_career(label, raw_text: str) -> dict:
    """원본 라벨 + 본문 판정을 결합해 경력 그룹과 검토 대상 여부를 결정."""
    lg = LABEL_MAP.get(str(label).strip()) if label is not None else None
    tx = analyze_text_career(raw_text)
    tg, out = tx["group"], tx.copy()
    out["label_group"] = lg

    def review(reason: str) -> dict:
        out.update(group="REVIEW", reason=reason)
        return out

    if tg == "CONFLICT":
        return review("본문 충돌: 신입 가능 언급과 경력 연수 요구가 동시에 존재")
    if lg is None:
        if tg is None:
            return review("라벨 없음 + 본문에 경력 신호 없음")
        if tg == "EXP_UNSPEC":
            return review("라벨 없음 + 본문에 연수 불명의 '경력자/경력직' 언급만 존재")
        out.update(group=tg,
                   reason=f"본문만으로 판정(라벨 결측), 근거={tx['entry_evidence'] or tx['years_evidence']}")
        return out
    # 라벨 존재
    if tg is None:
        out.update(group=lg, reason="라벨만 존재(본문에 경력 신호 없음)")
        return out
    if tg == "EXP_UNSPEC":
        if lg == "ENTRY":
            return review("라벨은 신입/경력무관이나 본문이 경력직 중심 모집으로 해석됨")
        out.update(group=lg, reason="경력 언급(연수 불명)과 경력 라벨 일치")
        return out
    # 라벨·본문 모두 존재
    if (lg == "ENTRY") != (tg == "ENTRY"):
        return review(f"라벨·본문 충돌: 라벨={lg}, 본문={tg} ({tx['years_evidence'] or tx['entry_evidence']})")
    if lg == tg:
        out.update(group=lg, reason="라벨·본문 일치")
    else:  # EXP13 vs EXP3P 등 세부 연수 차이: 본문에 명시된 연수를 더 신뢰
        out.update(group=tg, reason=f"같은 경력 계열 내 세부 차이(라벨={lg}, 본문 연수 기준={tg})")
    return out


def assign_career_group(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    results = [classify_career(lv, tx) for lv, tx in zip(df["experience_level"], df["raw_text"])]
    df["career_group"] = [r["group"] for r in results]
    df["career_label_group"] = [r["label_group"] for r in results]
    df["career_text_min_years"] = [r["min_years"] for r in results]
    df["career_evidence"] = [
        (r["entry_evidence"] + " | " + r["years_evidence"]).strip(" |") for r in results
    ]
    df["career_reason"] = [r["reason"] for r in results]
    vc = df["career_group"].value_counts()
    print(f"[7] 경력 분류: " + ", ".join(f"{CAREER_NAME.get(k, k)}={v:,}" for k, v in vc.items()))
    return df


# ================================================================ [8][9] 저장 및 통계
def save_outputs(df: pd.DataFrame, tech_field: str) -> pd.DataFrame:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    review = df[df["career_group"] == "REVIEW"]
    review_out = review[[
        "source", "job_id", "company", "title", "experience_level",
        "career_evidence", "career_reason", "job_group",
    ]].rename(columns={
        "experience_level": "원본_경력라벨",
        "career_evidence": "본문_근거",
        "career_reason": "검토_사유",
        "job_group": "직무_1차분류",
    })
    review_out.to_csv(REVIEW_PATH, index=False, encoding="utf-8-sig")
    print(f"[8] 검토 대상 저장: {REVIEW_PATH.name} ({len(review_out):,}건, utf-8-sig)")

    cleaned = df[df["career_group"] != "REVIEW"].copy()
    cleaned["career_group_kr"] = cleaned["career_group"].map(CAREER_NAME)
    cleaned["techs"] = cleaned[tech_field].map(lambda x: x if isinstance(x, list) else [])
    cleaned["n_techs"] = cleaned["techs"].map(len)
    keep = ["source", "job_id", "company", "title", "location",
            "experience_level", "career_group", "career_group_kr", "career_text_min_years",
            "job_group", "raw_text", "techs", "n_techs", "final_techs", "hard_skills"]
    cleaned = cleaned[keep].sort_values(["source", "job_id"]).reset_index(drop=True)
    cleaned.to_parquet(CLEANED_PATH, index=False)
    print(f"    정제 결과 저장: {CLEANED_PATH.name} ({len(cleaned):,}건, 기술 필드={tech_field})")
    return cleaned


def print_stats(cleaned: pd.DataFrame):
    print()
    print("=" * 74)
    print("최종 유효 공고 수 — 직무 × 경력 집단 교차표")
    print("=" * 74)
    cleaned = cleaned.copy()
    cleaned["career_kr"] = cleaned["career_group"].map(CAREER_NAME)
    order_c = ["신입/경력무관", "경력(최소1~3년)", "경력(3년+)"]
    tab = pd.crosstab(cleaned["job_group"], cleaned["career_kr"])
    tab = tab.reindex(index=[j for j in JOB_ORDER if j in tab.index],
                      columns=[c for c in order_c if c in tab.columns], fill_value=0)
    tab["합계"] = tab.sum(axis=1)
    tab.loc["합계"] = tab.sum()
    print(tab.to_string())
    print()

    by_job = cleaned["job_group"].value_counts()
    da = int(by_job.get("Data/AI", 0))
    target = ["Backend", "Frontend", "Fullstack"] + (["Data/AI"] if da >= DATAAI_MIN_COUNT else [])
    valid = cleaned[cleaned["job_group"].isin(target)]
    print(f"데이터/AI 유효 공고 {da:,}건 (포함 기준 {DATAAI_MIN_COUNT:,}건 이상) -> "
          f"{'분석 대상에 포함' if 'Data/AI' in target else '분석 대상에서 제외(수 부족)'}")
    print(f"1차 분석 대상 직무: {', '.join(target)}")
    print(f"분석 대상 최종 유효 공고: {len(valid):,}건 "
          f"(정제 전체 {len(cleaned):,}건 중 직무 Other {int(by_job.get('Other', 0)):,}건 제외)")
    print()
    by_career = valid["career_kr"].value_counts().reindex(order_c, fill_value=0)
    print("분석 대상의 경력 집단별 최종 유효 공고 수")
    for k, v in by_career.items():
        print(f"  - {k:<14}: {v:,}건")
    n_no_tech = int((valid["n_techs"] == 0).sum())
    print(f"  (참고) 분석 대상 중 기술 목록이 빈 공고: {n_no_tech:,}건")
    print("=" * 74)


# ================================================================ main
def main() -> int:
    print("=" * 74)
    print("JOBGUTS 1단계 — 데이터 수집 및 전처리")
    print("=" * 74)
    ensure_raw_file()                                  # [1]
    df = load_raw(RAW_PATH)                            # [2]
    df = drop_missing(df)                              # [3]
    df = drop_duplicates(df)                           # [4]
    tech_field = validate_tech_field(df)               # [5]
    df = assign_job_group(df)                          # [6]
    df = assign_career_group(df)                       # [7]
    cleaned = save_outputs(df, tech_field)             # [8]
    print_stats(cleaned)                               # [9]
    print("완료.")
    return 0


if __name__ == "__main__":
    sys.exit(main())



