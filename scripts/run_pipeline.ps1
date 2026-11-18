$ErrorActionPreference = "Stop"

python -m src.ingestion.run_week10 --input data/raw/korean_it_recruit_postings.json --config configs/data_scope.json --output-dir artifacts
python -m src.normalization.run_week11 --input data/raw/korean_it_recruit_postings.json --output data/processed/postings_normalized.jsonl --artifact-dir artifacts
python -m src.analysis.run_week12
python -m unittest discover -s tests -v
python -m src.service.app --skills TensorFlow
