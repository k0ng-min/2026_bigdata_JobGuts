from pathlib import Path
import json, shutil
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'reports'; WEEKLY=OUT/'weekly'; ASSETS=OUT/'assets'
WEEKLY.mkdir(parents=True, exist_ok=True)
q=json.loads((ROOT/'artifacts/week10_data_quality_summary.json').read_text(encoding='utf-8'))
n=json.loads((ROOT/'artifacts/week11_normalization_summary.json').read_text(encoding='utf-8'))
r=json.loads((ROOT/'artifacts/week12_rule_comparison.json').read_text(encoding='utf-8'))
weeks={
10:("데이터 범위와 품질 점검",[('데이터 품질 요약',[['입력 행','40,348'],['ID 중복 제외 후보','777'],['동일 본문 의심 행','1,707'],['final_techs 빈 목록 또는 결측','21,560']])],"원본 파일을 선정하고 로딩·결측·중복 기준을 확인했다.","기술명 정규화와 메타데이터 기준을 적용한다."),
11:("기술명 정규화와 메타데이터 확정",[('정규화 요약',[['입력 행','40,348'],['사전 버전','tech-dictionary.v1'],['별칭 변환','127'],['미등록 기술','142']])],"final_techs를 보존한 채 normalized_techs를 추가하고 fake provider 계약을 만들었다.","같은 공고 집합으로 규칙 분석을 수행한다."),
12:("Apriori와 연관규칙 분석",[('규칙 분석 요약',[['분석 트랜잭션','17,796'],['최소 support','0.005'],['최소 confidence','0.2'],['규칙 수','694']])],"support, confidence, interest를 계산하고 정규화 전후 규칙 집합을 비교했다.","규칙과 실제 공고 식별자를 조회 흐름에 연결한다."),
13:("규칙 조회와 서비스 통합",[('CLI 검증',[['정상 입력','TensorFlow'],['규칙 없음 입력','NotARealSkill'],['근거 공고','최대 3건']])],"저장된 규칙을 조회하고 실제 근거 공고를 반환하는 CLI를 구현했다. GLM 실제 호출은 제외했다.","세그먼트 요약과 기술 그래프를 검증한다."),
14:("세그먼트 비교와 통합 검증",[('통합 검증',[['테스트','8개 통과'],['그래프','week14_skill_graph.json'],['3개 기술 조합','week14_segment_comparison.json']])],"제목·경력 라벨 기반 세그먼트 요약과 기술 그래프 데이터를 생성하고 CLI 시나리오를 확인했다.","GLM 실제 연동은 별도 최종 통합 작업으로 남긴다."),}
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
 for line in ['프로젝트명: JobGuts','과목명: [직접 입력]','팀명: JOBGUTS','보고 기간: [직접 입력]','작성자: [직접 입력]']:
  d.add_paragraph(line).alignment=WD_ALIGN_PARAGRAPH.CENTER
 for h,text in [('1. 이번 주 목표',f'Week {w} 명세에 따라 {title} 작업을 진행했다.'),('2. 실제 진행 내용 및 증거',body)]: d.add_heading(h,1);d.add_paragraph(text)
 for t,rows in tables:add_table(d,t,rows)
 d.add_paragraph(f'그림. Week {w} 증거 파일 경로: reports/assets/week{w}/')
 d.add_heading('3. 문제점 및 차단 요인',1);d.add_paragraph('실제 GLM API 연결은 구현 범위에서 제외했다. 원본의 직무 분류 열 부재와 기술 라벨 한계는 결과 해석 시 유의했다.')
 d.add_heading('4. 다음 주 계획',1);d.add_paragraph(nexts)
 d.add_heading('5. 역할 분담 및 실제 수행 내역',1);add_table(d,'역할별 수행 내역',[['데이터 확보·전처리','입력 범위, 품질 요약, 중복 기준'],['기술명 정규화·검증','사전·정규화 배열·메타데이터'],['Apriori·연관규칙 분석','트랜잭션·지표·규칙 산출물'],['서비스·GLM 준비','CLI 조회·근거 공고·fake provider']])
 d.add_heading('6. 결론',1);d.add_paragraph(body+' 다음 주 인계 파일과 조건은 본문 및 assets에 기록했다.')
 d.save(WEEKLY/f'week{w}_project_progress_report.docx')
for w,x in weeks.items():
 (ASSETS/f'week{w}').mkdir(parents=True,exist_ok=True); build(w,*x)
 for f in ROOT.glob(f'artifacts/week{w}_*'): shutil.copy2(f,ASSETS/f'week{w}'/f.name)
(OUT/'README.md').write_text('# Weekly Reports\n\n| Week | Report | Evidence |\n|---|---|---|\n'+'\n'.join(f'| {w} | [DOCX](weekly/week{w}_project_progress_report.docx) | `assets/week{w}/` |' for w in weeks)+'\n',encoding='utf-8')
