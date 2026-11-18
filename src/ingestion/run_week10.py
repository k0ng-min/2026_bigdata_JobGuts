"""CLI that writes the required week-10 quality and raw-text sample artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .loader import load_postings
from .quality import build_week10_report, file_provenance


def _load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_samples(path: Path, postings: list) -> None:
    fields = ["row_number", "source", "job_id", "job_role", "experience_level", "raw_text_excerpt"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in postings[:20]:
            writer.writerow({
                "row_number": item.row_number,
                "source": item.source or "",
                "job_id": item.job_id or "",
                "job_role": item.job_role or "",
                "experience_level": item.experience_level or "",
                "raw_text_excerpt": (item.raw_text or "")[:300],
            })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="JSON, JSONL, NDJSON, or CSV export")
    parser.add_argument("--config", type=Path, default=Path("configs/data_scope.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    config = _load_config(args.config)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "week10_data_quality_summary.json"
    samples_path = args.output_dir / "week10_raw_text_samples.csv"
    if args.input is None or not args.input.is_file():
        expected = args.input or Path(config["input_file_contract"]["expected_path"])
        report = {
            "report_schema_version": "week10.v1",
            "status": "blocked_missing_input",
            "input": {"expected_path": str(expected)},
            "next_action": "Place one approved export at the expected path or pass --input, then rerun this command.",
        }
        summary_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _write_samples(samples_path, [])
        print(f"Wrote blocked-input record: {summary_path}")
        return 0
    postings = load_postings(args.input)
    report = build_week10_report(postings, file_provenance(args.input, config["version"]))
    report["status"] = "complete"
    summary_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_samples(samples_path, postings)
    print(f"Wrote {summary_path} and {samples_path} for {len(postings)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
