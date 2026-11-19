#!/usr/bin/env bash
# Full reproduction: weeks 10-14, then the cleanup agent and the comparison.
# The PowerShell twin is scripts/run_pipeline.ps1; keep the two in step.
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON=".venv/bin/python"
INPUT="data/raw/korean_it_recruit_postings.json"

[ -x "$PYTHON" ] || { echo "Virtual environment not found at $PYTHON. Create it first: python3 -m venv .venv" >&2; exit 1; }
[ -f "$INPUT" ] || { echo "Input export not found at $INPUT. See docs/data_source.md." >&2; exit 1; }

# Weeks 10-14
"$PYTHON" -m src.ingestion.run_week10 --input "$INPUT" --config configs/data_scope.json --output-dir artifacts
"$PYTHON" -m src.normalization.run_week11 --input "$INPUT" --output data/processed/postings_normalized.jsonl --artifact-dir artifacts
"$PYTHON" -m src.analysis.run_week12
"$PYTHON" -m src.service.run_week13
"$PYTHON" -m src.analysis.run_week14

# Cleanup agent. The default provider is fake: no API key and no network call.
"$PYTHON" -m src.agent.run_extract
"$PYTHON" -m src.agent.build_dictionary
"$PYTHON" -m src.agent.run_agent
"$PYTHON" -m src.agent.run_compare

# Tests, weekly reports, and one recommendation each way
"$PYTHON" -m unittest discover -s tests
"$PYTHON" scripts/build_weekly_reports.py
"$PYTHON" -m src.service.app --skills TensorFlow
"$PYTHON" -m src.agent.run_recommend --skills 파이썬
