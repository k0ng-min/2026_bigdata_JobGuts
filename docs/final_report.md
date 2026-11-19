# JobGuts Final Report

## Project result

JobGuts analyzes co-occurring technologies in Korean IT job postings and returns related skills with association-rule metrics and supporting postings. The supported interface is a CLI.

## Reproducibility

Download the documented public source into `data/raw/korean_it_recruit_postings.json`, then run:

```powershell
./scripts/run_pipeline.ps1
```

The raw and processed data files are intentionally excluded from Git. Versioned configuration, executable code, tests, and summary artifacts are tracked.

## Implemented pipeline

1. Load the approved source export and record a SHA-256-based quality summary.
2. Remove exact `source + job_id` duplicates and duplicate bodies from analysis transactions.
3. Preserve `final_techs`, create `normalized_techs`, and record the dictionary version.
4. Mine two-technology association rules with support, confidence, and segment-local interest.
5. Produce triple summaries, graph data, and CLI recommendations with evidence postings.

## Demonstration scenarios

```powershell
python -m src.service.app --skills TensorFlow
python -m src.service.app --skills NotARealSkill
python -m src.service.app --skills TensorFlow --role frontend
```

The first command demonstrates a recommendation with evidence, the second shows the no-rule path, and the third changes the evidence filter.

## Limitations

- Job role is derived from title signals because the source has no authoritative role column.
- Experience metadata follows the source label and deterministic fallback rules.
- The current dictionary preserves unmatched technologies rather than inventing aliases.
- GLM is intentionally not connected. Only its provider-independent interface and fake provider are included.

## Team contributions

- Data preparation: source selection, quality checks, duplicate policy, reproducibility.
- Normalization: technology dictionary, normalized arrays, metadata rules.
- Analysis: transactions, association rules, interest, triple and graph outputs.
- Service: CLI recommendation flow, filters, evidence retrieval, empty-result handling.
