"""preprocess.py 핵심 로직 스모크 테스트 (실행 전 검증)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import preprocess as pp

ok = True


def check(name, got, want):
    global ok
    status = "PASS" if got == want else "FAIL"
    if got != want:
        ok = False
    print(f"[{status}] {name}: got={got!r} want={want!r}")


# --- 직무 분류 ---
check("job 백엔드", pp.classify_job("백엔드 개발자", "Spring 기반 API"), "Backend")
check("job AI개발자(제목)", pp.classify_job("AI 개발자 채용", "서비스 개발"), "Data/AI")
check("job React개발자(제목)", pp.classify_job("ERP시스템 구축 React개발자모집", "시스템"), "Frontend")
check("job Spring(제목)", pp.classify_job("Spring 서버 개발", "API"), "Backend")
check("job 본문 react 언급 오분류 방지", pp.classify_job("백엔드 개발자", "React 화면과 협업. React 컴포넌트 이해 필요."), "Backend")
check("job 프론트엔드", pp.classify_job("프론트엔드 개발자 채용", "React"), "Frontend")
check("job 풀스택", pp.classify_job("풀스택 개발자", "Node React"), "Fullstack")
check("job FE+BE동시(제목)", pp.classify_job("프론트엔드/백엔드 개발자", "Node React"), "Fullstack")
check("job 데이터엔지니어", pp.classify_job("데이터 엔지니어", "파이프라인 구축"), "Data/AI")
check("job 본문 BE 2회", pp.classify_job("개발자 채용", "서버 개발 담당. 서버 개발 경력 보유자."), "Backend")
check("job 본문 FE 2회", pp.classify_job("개발자 채용", "프론트엔드 개발. 프론트엔드 성능 최적화."), "Frontend")
check("job 본문 1회성 언급은 무시", pp.classify_job("개발자", "백엔드 개발자와 협업하는 프론트엔드 개발"), "Other")
check("job 기타", pp.classify_job("영업관리", "고객 응대"), "Other")

# --- 경력: 본문 판정 ---
cases = [
    ("경력무관 모집", "ENTRY"),
    ("신입/경력 모두 지원 가능", "ENTRY"),
    ("신입·경력 무관", "ENTRY"),
    ("인턴십 프로그램", "ENTRY"),
    ("경력 3년 이상", "EXP13"),
    ("3년차 이상의 경력자", "EXP13"),
    ("최소 2년", "EXP13"),
    ("2~3년 경력", "EXP13"),
    ("경력 5년 이상", "EXP3P"),
    ("4년 이상의 실무 경험", "EXP3P"),
    ("3년 이상 경력 우대", None),          # '우대' 인접 -> 신호 제거
    ("경력자 모집", "EXP_UNSPEC"),
    ("열정적인 동료", None),
    ("Django 웹 개발 경험 1년 이상 보유자", None),   # 기술 숙련 '경험'은 최소 경력 아님
    ("신입 또는 경력 2년 이하", "ENTRY"),            # '2년 이하'는 상한 -> 경력 요구 아님
    ("3년 이상의 협업 경험 (인턴 포함)", "EXP13"),   # '인턴 포함'은 경력 산정 방식
    ("실무 경험 3년 이상 보유자", "EXP13"),          # '실무 경험'은 경력 요구로 인정
    ("관련 경력 1년 이상 (신입 지원 가능, 단 프로젝트 경험 필요)", "ENTRY"),  # 같은 문장 병기
    ("경력 : 신입 / 경력 3년 이상", "ENTRY"),        # '신입 / 경력 N년' 병기
    ("신입 ~ 경력 3년", "ENTRY"),                    # 범위 표기
    ("신입 채용 공고입니다. 자격요건은 다음과 같습니다. 백엔드 개발 경력 5년 이상", "CONFLICT"),  # 멀리 떨어짐
    # jobkorea 보일러플레이트: 하단 추천공고의 경력 조건은 무시되어야 함
    ("지원자격 경력 신입·경력 모집요강 ... 우대조건 유관업무 경험자(인턴·알바) 관련 태그 "
     "백엔드개발자 데이터사이언티스트 본 채용정보는 무단전재 금지 [추천공고] 경력10년↑ 신입·경력", "ENTRY"),
    # '인턴·알바'는 우대 보일러플레이트 -> 신입 신호 아님
    ("고용형태 정규직. 지원자격 경력 경력 (10년이상). 우대조건 유관업무 경험자(인턴·알바)", "EXP3P"),
]
for text, want in cases:
    got = pp.analyze_text_career(text)["group"]
    check(f"text career '{text}'", got, want)

# --- 경력: 라벨+본문 결합 ---
r = pp.classify_career("신입", "경력무관 지원 가능")
check("career 라벨신입+본문경력무관", r["group"], "ENTRY")
r = pp.classify_career("경력무관", "경력 3년 이상 필요")
check("career 충돌->REVIEW", r["group"], "REVIEW")
r = pp.classify_career(None, "경력 2년 이상")
check("career saramin+본문2년", r["group"], "EXP13")
r = pp.classify_career(None, "열정 있는 분")
check("career 무신호->REVIEW", r["group"], "REVIEW")
r = pp.classify_career("1~3년차", "경력 2년 이상")
check("career 일치 EXP13", r["group"], "EXP13")
r = pp.classify_career("5년이상", "경력 3년 이상")
check("career 세부차이 본문우선", r["group"], "EXP13")

# --- 기술 패턴 ---
check("tech Java not in JavaScript", bool(pp._tech_pattern("Java").search("JavaScript 개발")), False)
check("tech Java in 'Java, Spring'", bool(pp._tech_pattern("Java").search("Java, Spring")), True)
m, t, _ = pp._tech_precision("React와 TypeScript 사용. CI/CD는 GitHub Actions", ["React", "TypeScript", "Docker"])
check("tech precision", (m, t), (2, 3))
m, t, _ = pp._tech_precision("Node.js 기반", ["Node.js"])
check("tech Node.js match", (m, t), (1, 1))

print()
print("SMOKE RESULT:", "ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
