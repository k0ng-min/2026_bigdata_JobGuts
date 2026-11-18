import json,tempfile,unittest
from pathlib import Path
from src.retrieval import RuleRepository
class RetrievalTests(unittest.TestCase):
 def test_returns_evidence(self):
  d=tempfile.TemporaryDirectory(); self.addCleanup(d.cleanup); p=Path(d.name); (p/'r.json').write_text(json.dumps({'normalized':[{'antecedent':['Java'],'consequent':['Spring'],'interest':.3,'confidence':.5}]})); (p/'p.jsonl').write_text(json.dumps({'source':'x','job_id':'1','title':'t','normalized_techs':['Java','Spring'],'job_role':'backend','experience_segment':'entry'})+'\n'); result=RuleRepository(p/'r.json',p/'p.jsonl').recommend(['Java']); self.assertEqual(result['status'],'ok'); self.assertEqual(result['evidence_postings'][0]['job_id'],'1')
