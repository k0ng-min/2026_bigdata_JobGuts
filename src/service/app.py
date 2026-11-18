"""Small JSON CLI service flow, independent of any LLM provider."""
from __future__ import annotations
import argparse, json
from src.normalization.dictionary import TechnologyDictionary
from src.retrieval import RuleRepository

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--skills", nargs="+", required=True); p.add_argument("--role"); p.add_argument("--experience"); p.add_argument("--rules", default="artifacts/week12_all_rules.json"); p.add_argument("--postings", default="data/processed/postings_normalized.jsonl"); p.add_argument("--dictionary", default="configs/tech_dictionary.json"); a=p.parse_args()
    d=TechnologyDictionary.from_json(a.dictionary); skills=[d.canonicalize(x) or x for x in a.skills]
    print(json.dumps(RuleRepository(a.rules,a.postings).recommend(skills,a.role,a.experience),ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
