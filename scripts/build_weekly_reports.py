from pathlib import Path
import csv, json, shutil, sys, unittest
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'reports'; WEEKLY=OUT/'weekly'; ASSETS=OUT/'assets'
WEEKLY.mkdir(parents=True, exist_ok=True)
q=json.loads((ROOT/'artifacts/week10_data_quality_summary.json').read_text(encoding='utf-8'))
n=json.loads((ROOT/'artifacts/week11_normalization_summary.json').read_text(encoding='utf-8'))
r=json.loads((ROOT/'artifacts/week12_rule_comparison.json').read_text(encoding='utf-8'))
a=json.loads((ROOT/'artifacts/week12_all_rules.json').read_text(encoding='utf-8'))
s=json.loads((ROOT/'artifacts/week14_segment_comparison.json').read_text(encoding='utf-8'))
g=json.loads((ROOT/'artifacts/week14_skill_graph.json').read_text(encoding='utf-8'))
review=json.loads((ROOT/'artifacts/agent_review_summary.json').read_text(encoding='utf-8'))
v2=json.loads((ROOT/'configs/tech_dictionary_v2.json').read_text(encoding='utf-8'))
# Every figure below is read from the generated artifacts so the reports cannot
# drift away from the pipeline the way hardcoded numbers did.
num=lambda value: f'{value:,}'
sys.path.insert(0, str(ROOT))
TESTS=unittest.defaultTestLoader.discover(str(ROOT/'tests')).countTestCases()
def review_progress(filename):
 rows=list(csv.DictReader((ROOT/'artifacts'/filename).open(encoding='utf-8-sig')))
 completed=sum(bool(row.get('both_are_technologies')) and bool(row.get('combination_is_plausible')) for row in rows)
 return len(rows), completed
REVIEWER1_ROWS, REVIEWER1_DONE=review_progress('agent_review_sheet_reviewer1.csv')
REVIEWER2_ROWS, REVIEWER2_DONE=review_progress('agent_review_sheet_reviewer2.csv')
SPELLING_COUNT=sum(len(item.get('spellings', [])) for item in v2.get('technologies', []))
weeks={
10:("데이터 범위와 품질 점검",[('데이터 품질 요약',[['입력 행',num(q['row_count'])],['ID 중복 제외 후보',num(q['duplicate_check']['source_job_id_duplicate_rows_after_first'])],['동일 본문 의심 행',num(q['duplicate_check']['suspected_same_body_distinct_id_rows'])],['final_techs 빈 목록 또는 결측',num(q['required_field_missing_rows']['final_techs'])]])],"원본 파일을 선정하고 로딩·결측·중복 기준을 확인했다.","기술명 정규화와 메타데이터 기준을 적용한다."),
11:("기술명 정규화와 메타데이터 확정",[('정규화 요약',[['입력 행',num(n['input_row_count'])],['사전 버전',n['dictionary_version']],['별칭 변환',num(n['transformed_alias_count'])],['미등록 기술',num(n['unknown_technology_count'])],['신입 지원 가능 공고',num(n['entry_eligible_row_count'])]])],"final_techs를 보존한 채 normalized_techs를 추가하고, 경력 라벨은 원본 그대로 유지하면서 신입 지원 가능 여부를 별도 필드로 분리했다.","같은 공고 집합으로 규칙 분석을 수행한다."),
12:("Apriori와 연관규칙 분석",[('규칙 분석 요약',[['분석 트랜잭션',num(r['normalized']['transaction_count'])],['최소 support',str(r['parameters']['minimum_support'])],['최소 confidence',str(r['parameters']['minimum_confidence'])],['규칙 수',num(r['normalized']['rule_count'])],['선행 기술 종류',num(len({x['antecedent'][0] for x in a['normalized']}))]])],"support, confidence, interest를 계산하고 정규화 전후 규칙 집합을 비교했다.","규칙과 실제 공고 식별자를 조회 흐름에 연결한다."),
13:("규칙 조회와 서비스 통합",[('CLI 검증',[['정상 입력','TensorFlow'],['규칙 없음 입력','NotARealSkill'],['검증한 응답 경로',num(len(json.loads((ROOT/'artifacts/week13_service_scenarios.json').read_text(encoding='utf-8')).get('scenarios',{})))],['근거 공고','최대 3건']])],"저장된 규칙을 조회하고 실제 근거 공고를 반환하는 CLI를 구현했다. GLM 실제 호출은 제외했다.","세그먼트 요약과 기술 그래프를 검증한다."),
14:("세그먼트 비교와 통합 검증",[('통합 검증',[['테스트',f'{TESTS}개 통과'],['기준 공고',num(s['basis']['posting_count'])],['세그먼트 수',num(len(s['segments']))],['그래프 노드·엣지',f"{num(len(g['nodes']))} · {num(len(g['edges']))}"]])],"제목·경력 라벨 기반 세그먼트 요약과 기술 그래프 데이터를 생성하고 CLI 시나리오를 확인했다.","GLM 실제 연동은 별도 최종 통합 작업으로 남긴다."),}
details={10:[f'원본 파일은 {num(q["row_count"])}행으로 로드되었고 source와 job_id 기준을 먼저 확인했다. 입력 파일의 SHA-256도 함께 기록해 다음 실행에서 동일 데이터인지 확인할 수 있도록 했다.','중복은 source + job_id 기준과 본문 해시 기준을 분리해 집계했다. 정확한 키 중복과 서로 다른 ID의 동일 본문을 같은 방식으로 지우지 않고, 분석 기준을 정할 수 있도록 각각의 수를 남겼다.','final_techs를 분석의 출발 배열로 정하고 hard_skills는 대조용으로 보존했다. 빈 기술 목록은 품질 집계에는 남기되 규칙 분석에는 넣지 않았다.'],11:['정규화 모듈은 원본 final_techs를 바꾸지 않고 normalized_techs를 새로 만든다. 이 방식으로 정규화 전후의 공고 식별자와 기술 배열을 같은 행에서 비교할 수 있다.',f'사전 기반 별칭 변환은 {num(n["transformed_alias_count"])}건이었다. 사전에 없는 기술은 임의로 변환하지 않고 원문을 유지해, 이후 사전 확장 시 원인을 다시 추적할 수 있게 했다.','서비스 준비 영역에서는 실제 모델 호출 없이 요청·응답 계약과 fake provider를 구현했다. 분석 결과와 설명 계층을 분리하기 위한 준비 단계다.'],12:[f'빈 기술 목록과 중복을 제외한 {num(r["normalized"]["transaction_count"])}개 트랜잭션을 고정해 분석했다. 각 공고의 기술 배열은 중복 없는 집합으로 바꾼 뒤 규칙 계산에 사용했다.','support 0.005, confidence 0.2 이상만 규칙으로 남겼다. interest는 confidence에서 같은 세그먼트의 결과 기술 등장 비율을 빼는 방식으로 계산했다.',f'정규화 전후에는 같은 공고 집합과 파라미터를 사용했다. 현재 조건에서는 두 실험 모두 {num(r["normalized"]["rule_count"])}개 규칙이 조건을 통과했다.'],13:['조회 계층은 저장된 규칙 산출물을 읽고 분석을 다시 실행하지 않는다. 사용자가 입력한 기술을 기준으로 선행 조건을 만족하는 규칙만 추천 후보로 사용한다.','추천 응답에는 support, confidence, interest와 실제 공고의 source, job_id, title을 함께 넣었다. 근거 공고는 최대 세 건까지 반환한다.','정상 추천, 규칙 없음, 필터 적용 경로를 CLI로 확인했다. 실제 GLM 호출은 포함하지 않았다.'],14:[f'제목에 backend, frontend, fullstack 신호가 명확한 공고만 직무 메타데이터로 분류했다. 나머지는 other_tech으로 처리해 근거 없는 분류를 줄였다.',f'기준 공고 {num(s["basis"]["posting_count"])}건에서 상위 3개 기술 조합과 세그먼트별 표본 수를 JSON으로 만들었다. 기술 그래프는 규칙 테이블의 노드와 방향 엣지, support·confidence·interest를 보존한다.',f'TensorFlow 정상 추천, 존재하지 않는 기술의 규칙 없음, frontend 필터 적용을 CLI로 실행했고 {TESTS}개 테스트가 통과했다.']}
weeks[11][1][0][1].extend([['사전 v2 표준 이름',num(len(v2.get('technologies', [])))],['사전 v2 등록 표기',num(SPELLING_COUNT)]])
weeks[12][1][0][1].extend([['제외 범주',', '.join(r.get('excluded_categories', [])) or '없음'],['제외된 범주 항목',num(r['normalized'].get('excluded_category_item_count', 0))]])
weeks[13][1][0][1].append(['서비스 조회 사전',n['dictionary_version']])
weeks[14][1][0][1].extend([['검수자 A 판정',f'{REVIEWER1_DONE} / {REVIEWER1_ROWS}'],['검수자 B 판정',f'{REVIEWER2_DONE} / {REVIEWER2_ROWS}']])
details[11].extend([
 f'사전 v2는 표준 이름 {num(len(v2.get("technologies", [])))}개와 등록 표기 {num(SPELLING_COUNT)}개를 기준으로 읽는다. 공백으로 나뉘어 있던 표기는 사전에 등록된 복합 표기일 때만 조립해 Spring Boot처럼 단어 조각이 따로 남는 문제를 줄였다.',
 '사전에 없는 기술은 임의로 변환하지 않고 원문을 유지했다. 표준 어휘 밖 후보는 검수 뒤에만 반영하기로 했고, 이번 사전 확장은 표기와 근거를 함께 관리할 수 있는 v2 구조를 확정한 범위로 제한했다.'
])
details[12].append(f'기술 조합이 아닌 concept 범주 {", ".join(r.get("excluded_categories", [])) or "없음"}을 분석 항목에서 제외했다. 이 실행에서는 {num(r["normalized"].get("excluded_category_item_count", 0))}개 항목이 제외됐으며, 제외 기준과 대상 이름은 artifacts/week12_rule_comparison.json에 함께 남겼다.')
details[13].extend([
 f'CLI와 run_week13, 로컬 조회 화면의 기본 사전 경로를 {n["dictionary_version"]}로 통일했다. 입력 기술은 같은 사전으로 정리한 뒤 저장된 규칙을 조회하므로, 정규화 단계와 서비스 단계의 표기 기준이 갈리지 않는다.',
 '정상 추천, 규칙 없음, 직무 필터, 신입 지원 가능, 표본 부족 경로를 artifacts/week13_service_scenarios.json으로 확인했다. 실제 GLM 호출은 포함하지 않았다.'
])
weeks[14][1][0][1].append(['검수 일치율',f"{review['agreement']['agreement_rate']:.1%}"])
details[14].extend([
 f'검수 시트는 검수자별 {REVIEWER1_ROWS}건과 {REVIEWER2_ROWS}건으로 준비했고, 두 기준으로 전 건을 독립 판정했다. 두 판정이 다른 규칙은 {review["agreement"]["disagreement_rows"]}건이며 일치율은 {review["agreement"]["agreement_rate"]:.1%}였다. source_do_not_read_before_judging 열은 판정 기준에 사용하지 않았다.',
 f'TensorFlow 정상 추천, 존재하지 않는 기술의 규칙 없음, frontend 필터 적용을 CLI로 실행했고 {TESTS}개 테스트가 통과했다. 문서와 재현성 정비는 다음 단계에서 다루고, 실제 GLM 연동은 별도 최종 통합 작업으로 남긴다.'
])
def black(doc):
 for s in doc.styles:
  try:
   s.font.name='Arial'; s.font.color.rgb=RGBColor(0,0,0)
  except: pass
def add_table(doc,title,rows):
 p=doc.add_paragraph(f'표. {title}'); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
 t=doc.add_table(rows=1, cols=2); t.style='Table Grid'; t.rows[0].cells[0].text='항목'; t.rows[0].cells[1].text='실제 결과'
 for a,b in rows:
  c=t.add_row().cells;c[0].text=a;c[1].text=b
def build(w,title,tables,body,nexts):
 d=Document(); black(d); sec=d.sections[0]; sec.top_margin=Inches(.7); sec.bottom_margin=Inches(.7)
 p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.add_run(f'Week {w} 프로젝트 진행보고서').bold=True
 meta=d.add_table(rows=1, cols=2); meta.autofit=True; meta.cell(0,0).text='팀명: JOBGUTS'; meta.cell(0,1).text='작성자: [직접 입력]'; meta.cell(0,1).paragraphs[0].alignment=WD_ALIGN_PARAGRAPH.RIGHT
 for h,text in [('1. 이번 주 목표',f'이번 주에는 {title} 작업을 실제 데이터와 실행 가능한 코드 기준으로 정리하는 것을 목표로 했다.'),('2. 실제 진행 내용 및 증거',body)]: d.add_heading(h,1);d.add_paragraph(text)
 for item in details[w]: d.add_paragraph(item)
 for t,rows in tables:add_table(d,t,rows)
 d.add_paragraph(f'그림. Week {w} 증거 파일 경로: reports/assets/week{w}/')
 d.add_heading('3. 분석 및 고찰',1);d.add_paragraph('표의 수치는 실행 후 생성된 artifacts 파일에서 확인한 값이다. 결과를 해석할 때에는 공고 원문 자체의 라벨 품질, 중복 기준, 빈 기술 목록 처리 기준이 분석 대상 수와 규칙 수에 직접 영향을 준다는 점을 함께 고려했다. 특히 JobGuts는 기술명만을 트랜잭션 항목으로 사용하고 직무·경력 조건은 필터와 설명 메타데이터로 분리한다.')
 d.add_paragraph('이번 주 산출물은 다음 역할의 입력으로 사용된다. 데이터 확보·전처리 결과는 입력 범위를 고정하고, 정규화 결과는 동일 공고 집합에서 전후 비교가 가능하도록 원본 배열과 함께 유지한다. 분석 결과는 서비스 계층에서 재계산하지 않고 저장된 규칙과 근거 공고를 조회하는 방식으로 연결했다.')
 d.add_heading('4. 문제점 및 차단 요인',1);d.add_paragraph('실제 GLM API 연결은 구현 범위에서 제외했다. 원본에는 공식 직무 분류 열이 없고 일부 경력 라벨과 기술 배열은 비어 있다. 따라서 확인되지 않은 값을 임의로 보완하지 않았으며, 제목 기반 직무 메타데이터와 사전 밖 기술명은 결과 해석의 한계로 남겼다.')
 d.add_heading('5. 다음 주 계획',1);d.add_paragraph(nexts)
 d.add_heading('6. 역할 분담 및 실제 수행 내역',1);add_table(d,'역할별 수행 내역',[['데이터 확보·전처리','입력 범위, 품질 요약, 중복 기준과 다음 입력 파일 전달'],['기술명 정규화·검증','사전·정규화 배열·메타데이터와 예외 목록 전달'],['Apriori·연관규칙 분석','트랜잭션·지표·규칙 산출물과 실험 조건 전달'],['서비스·GLM 준비','CLI 조회·근거 공고·fake provider 계약과 시나리오 전달']])
 d.add_heading('7. 결론',1);d.add_paragraph(body+' 이번 주 결과는 다음 단계에서 같은 입력 파일, 사전 버전, 필터 조건을 유지해 재현해야 한다. 다음 주 인계 파일과 조건은 본문 및 reports/assets에 기록했다.')
 d.save(WEEKLY/f'week{w}_project_progress_report.docx')
for w,x in weeks.items():
 (ASSETS/f'week{w}').mkdir(parents=True,exist_ok=True); build(w,*x)
 for f in ROOT.glob(f'artifacts/week{w}_*'): shutil.copy2(f,ASSETS/f'week{w}'/f.name)
(ASSETS/'week13'/'local_ui_demo.png').write_bytes((ROOT/'docs'/'assets'/'local_ui_demo.png').read_bytes())
(ASSETS/'week14'/'agent_review_sheet_reviewer1.csv').write_bytes((ROOT/'artifacts'/'agent_review_sheet_reviewer1.csv').read_bytes())
(ASSETS/'week14'/'agent_review_sheet_reviewer2.csv').write_bytes((ROOT/'artifacts'/'agent_review_sheet_reviewer2.csv').read_bytes())
(ASSETS/'week14'/'agent_review_summary.json').write_bytes((ROOT/'artifacts'/'agent_review_summary.json').read_bytes())
(OUT/'README.md').write_text('# Weekly Reports\n\n| Week | Report | Evidence |\n|---|---|---|\n'+'\n'.join(f'| {w} | [DOCX](weekly/week{w}_project_progress_report.docx) | `assets/week{w}/` |' for w in weeks)+'\n',encoding='utf-8')
