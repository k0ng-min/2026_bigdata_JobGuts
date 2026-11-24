"""최종 산출물 검증: parquet/CSV 로드, 무결성, 샘플 출력."""
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = Path(__file__).resolve().parents[1]

pq = BASE / "data" / "processed" / "cleaned_jobs.parquet"
csv = BASE / "data" / "processed" / "review_needed.csv"
print(f"cleaned_jobs.parquet: {pq.stat().st_size:,} bytes")
print(f"review_needed.csv   : {csv.stat().st_size:,} bytes")
print()

df = pd.read_parquet(pq)
print(f"cleaned rows={len(df):,}, columns={list(df.columns)}")
assert (df["career_group"] != "REVIEW").all(), "REVIEW가 cleaned에 포함됨"
assert df["job_group"].isin(["Backend", "Frontend", "Fullstack", "Data/AI", "Other"]).all()
assert df["career_group"].isin(["ENTRY", "EXP13", "EXP3P"]).all()
assert df[["source", "job_id", "company", "title", "raw_text"]].notna().all().all()
# 중복 재확인: source+job_id 유일, 기업+제목+본문 유일
assert df.duplicated(subset=["source", "job_id"]).sum() == 0, "source+job_id 중복 존재"
import re
key = (df["company"].map(lambda s: re.sub(r"\s+", "", s).lower()) + "||"
       + df["title"].map(lambda s: re.sub(r"\s+", "", s).lower()) + "||"
       + df["raw_text"].map(lambda s: re.sub(r"\s+", "", s)))
assert key.duplicated().sum() == 0, "기업+제목+본문 중복 존재"
assert df["techs"].map(lambda x: hasattr(x, "__len__") and not isinstance(x, str)).all(), "techs가 시퀀스가 아님"
assert (df["n_techs"] == df["techs"].map(len)).all(), "n_techs 불일치"
print("무결성 검사 통과: REVIEW 미포함 / 필수 필드 완비 / 중복 없음 / techs-list 정상")
print()

rv = pd.read_csv(csv, encoding="utf-8-sig")
print(f"review rows={len(rv):,}, columns={list(rv.columns)}")
print()
print("=== cleaned 샘플 3건 ===")
for _, r in df.head(3).iterrows():
    print(f"  [{r['job_group']}|{r['career_group_kr']}] {r['title'][:40]} | techs={r['techs'][:5]} (총 {r['n_techs']})")
print()
print("=== review 샘플 3건 ===")
for _, r in rv.head(3).iterrows():
    print(f"  label={r['원본_경력라벨']} | {r['title'][:35]} | 사유: {r['검토_사유'][:60]}")
print()
print("VERIFY DONE")
