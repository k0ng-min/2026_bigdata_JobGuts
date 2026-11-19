# Full reproduction: weeks 10-14, then the cleanup agent and the comparison.
# Run from the repository root after creating .venv and downloading the input.
#
# The virtual environment's interpreter is called directly, so the script works
# whether or not the environment has been activated and never falls back to a
# system Python that may lack python-docx.

$ErrorActionPreference = "Stop"

$Python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Error "Virtual environment not found at $Python. Create it first: python -m venv .venv"
}
Set-Location (Join-Path $PSScriptRoot "..")

# PowerShell has an automatic variable named $Input, so that name is avoided here.
$InputPath = "data/raw/korean_it_recruit_postings.json"
if (-not (Test-Path $InputPath)) {
    Write-Error "Input export not found at $InputPath. See docs/data_source.md."
}

# Weeks 10-14
& $Python -m src.ingestion.run_week10 --input $InputPath --config configs/data_scope.json --output-dir artifacts
& $Python -m src.normalization.run_week11 --input $InputPath --output data/processed/postings_normalized.jsonl --artifact-dir artifacts
& $Python -m src.analysis.run_week12
& $Python -m src.service.run_week13
& $Python -m src.analysis.run_week14

# Cleanup agent. The default provider is fake: no API key and no network call.
& $Python -m src.agent.run_extract
& $Python -m src.agent.build_dictionary
& $Python -m src.agent.run_agent
& $Python -m src.agent.run_compare

# Tests, weekly reports, and one recommendation each way
& $Python -m unittest discover -s tests
& $Python scripts/build_weekly_reports.py
& $Python -m src.service.app --skills TensorFlow
& $Python -m src.agent.run_recommend --skills "파이썬"
