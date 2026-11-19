"""Run the cleanup agent over the candidate inventory and write its evidence.

Default provider is ``fake``: no key, no network, and every artifact carries
``is_mock`` so a reader cannot mistake the run for model output. ``--provider
glm`` constructs the real provider, which fails immediately when GLM_API_KEY is
absent.

Outputs
    artifacts/agent_run_summary.json     counts, costs and the mock flag
    artifacts/agent_decisions.json       one record per candidate
    artifacts/agent_tool_log.json        every tool call in order
    artifacts/agent_cache.json           name-keyed answers for the next run
    data/processed/postings_agent_cleaned.jsonl   cleaned technology lists
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from src.analysis.run_week14 import _eligible_rows

from .cache import JudgementCache, NullCache
from .extract import extract_candidates, load_korean_spellings, load_stopwords
from .fake_judge import FakeJudgeProvider
from .judge import PROMPT_VERSION, ModelJudge
from .judgement import DECISION_MEANINGS
from .loop import LoopCounters, process_candidate
from .memory import AgentMemory, lookup_key
from .tools import AgentTools, ContextIndex


def build_judge(provider_name: str, memory: AgentMemory, dotenv_path: str):
    if provider_name == "fake":
        return FakeJudgeProvider()
    if provider_name == "glm":
        from src.llm.glm_provider import GLMProvider

        return ModelJudge(GLMProvider(dotenv_path=dotenv_path), memory.standard_names)
    raise ValueError(f"unknown provider {provider_name!r}; expected 'fake' or 'glm'")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/postings_normalized.jsonl"))
    parser.add_argument("--dictionary", type=Path, default=Path("configs/tech_dictionary_v2.json"))
    parser.add_argument("--config", type=Path, default=Path("configs/agent.json"))
    parser.add_argument("--stopwords", type=Path, default=Path("configs/extract_stopwords.json"))
    parser.add_argument("--korean", type=Path, default=Path("configs/tech_dictionary_korean.json"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--cleaned-output", type=Path, default=Path("data/processed/postings_agent_cleaned.jsonl"))
    parser.add_argument("--provider", default="fake", choices=("fake", "glm"))
    parser.add_argument("--dotenv", default=".env")
    parser.add_argument("--limit", type=int, default=0, help="Process only this many eligible postings (0 = all).")
    parser.add_argument("--no-cache", action="store_true",
                        help="Run without a cache at all, which makes the learned memory layer visible.")
    args = parser.parse_args()
    args.artifact_dir.mkdir(parents=True, exist_ok=True)

    config = json.loads(args.config.read_text(encoding="utf-8"))
    floor = config["minimum_occurrences_for_llm"]
    apply_threshold = config["confidence"]["apply"]
    flag_threshold = config["confidence"]["apply_with_flag"]
    max_calls = config["max_llm_calls"]

    stopwords = load_stopwords(args.stopwords)
    korean = load_korean_spellings(args.korean)
    memory = AgentMemory.from_dictionary(args.dictionary)

    with args.input.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    postings = _eligible_rows(records, "normalized_techs")
    if args.limit:
        postings = postings[: args.limit]
    extracted = [extract_candidates(row.get("raw_text") or "", stopwords, korean) for row in postings]

    occurrences: Counter[str] = Counter()
    for candidates in extracted:
        occurrences.update(candidate.name for candidate in candidates)
    targets = {name for name, count in occurrences.items() if count >= floor}

    index = ContextIndex.build(
        postings, extracted, targets,
        snippets_per_candidate=config["context"]["snippets_per_candidate"],
        window=config["context"]["snippet_window"],
    )
    tools = AgentTools(memory, index, neighbours_per_candidate=config["context"]["neighbours_per_candidate"])
    judge = build_judge(args.provider, memory, args.dotenv)
    cache_path = args.artifact_dir / "agent_cache.json"
    cache = (
        NullCache(memory.dictionary_version, PROMPT_VERSION)
        if args.no_cache
        else JudgementCache.load(cache_path, memory.dictionary_version, PROMPT_VERSION)
    )

    counters = LoopCounters()
    decisions: dict[str, dict] = {}
    logs = []
    # Frequent candidates first: a decision made on a common spelling is in
    # memory before the rarer spellings that may depend on it are reached.
    for name in sorted(targets, key=lambda item: (-occurrences[item], item)):
        remaining = max_calls - counters.llm_calls
        judgement, log, _ = process_candidate(
            name, occurrences[name], tools, cache, judge, counters,
            apply_threshold, flag_threshold, remaining,
        )
        memory.remember(judgement)
        decisions[name] = {**judgement.as_record(), **{k: v for k, v in (log.outcome or {}).items() if k in ("route", "low_confidence")}}
        logs.append(log.as_record())

    # Apply the decisions to every posting, including candidates below the
    # floor, which keep their original spelling.
    mapping = {lookup_key(name): record for name, record in decisions.items()}
    dropped: Counter[str] = Counter()
    args.cleaned_output.parent.mkdir(parents=True, exist_ok=True)
    with args.cleaned_output.open("w", encoding="utf-8") as handle:
        for row, candidates in zip(postings, extracted):
            cleaned: list[str] = []
            # Which spelling each cleaned name came from, so the comparison can
            # tell a genuinely new error from one that only changed bucket.
            origin: dict[str, str] = {}
            for candidate in candidates:
                confirmed = memory.lookup_confirmed(candidate.name)
                if confirmed:
                    cleaned.append(confirmed)
                    origin.setdefault(confirmed, candidate.name)
                    continue
                record = mapping.get(lookup_key(candidate.name))
                if record is None:
                    cleaned.append(candidate.name)
                    origin.setdefault(candidate.name, candidate.name)
                elif record["decision"] == "canonical" and record["canonical"]:
                    cleaned.append(record["canonical"])
                    origin.setdefault(record["canonical"], candidate.name)
                elif record["decision"] == "not_a_technology":
                    dropped[candidate.name] += 1
                else:
                    cleaned.append(candidate.name)
                    origin.setdefault(candidate.name, candidate.name)
            handle.write(json.dumps({
                "source": row.get("source"),
                "job_id": row.get("job_id"),
                "title": row.get("title"),
                "job_role": row.get("job_role"),
                "experience_segment": row.get("experience_segment"),
                "entry_eligible": row.get("entry_eligible"),
                "final_techs": row.get("final_techs"),
                "agent_techs": sorted(dict.fromkeys(cleaned)),
                "agent_origin": {name: origin[name] for name in sorted(dict.fromkeys(cleaned))},
            }, ensure_ascii=False) + "\n")

    cache.save(cache_path)
    decision_counts = Counter(record["decision"] for record in decisions.values())
    route_counts = Counter(record["route"] for record in decisions.values())
    is_mock = bool(getattr(judge, "is_mock", False))
    summary = {
        "status": "complete",
        "provider": args.provider,
        "is_mock": is_mock,
        "mock_warning": (
            "Decisions came from a deterministic rule table, not from a language model. "
            "These numbers show that the flow runs end to end; they are not model performance."
        ) if is_mock else None,
        "prompt_version": PROMPT_VERSION,
        "dictionary_version": memory.dictionary_version,
        "basis": {
            "posting_count": len(postings),
            "distinct_candidates": len(occurrences),
            "candidate_occurrences": sum(occurrences.values()),
            "minimum_occurrences_for_llm": floor,
            "candidates_considered": len(targets),
        },
        "decisions": dict(decision_counts),
        "decision_meanings": DECISION_MEANINGS,
        "routes": dict(route_counts),
        "cost": {
            **{k: v for k, v in vars(counters).items()},
            "cache": cache.statistics,
            "calls_avoided_by_cache_and_memory": sum(occurrences[name] for name in targets) - counters.llm_calls,
        },
        "memory": memory.statistics,
        "dropped_occurrences": sum(dropped.values()),
        "dropped_top": [{"name": name, "count": count} for name, count in dropped.most_common(20)],
        "cleaned_output": args.cleaned_output.as_posix(),
    }
    (args.artifact_dir / "agent_run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.artifact_dir / "agent_decisions.json").write_text(json.dumps({
        "status": "complete",
        "provider": args.provider,
        "is_mock": is_mock,
        "decision_meanings": DECISION_MEANINGS,
        "decisions": [
            {"name": name, **record}
            for name, record in sorted(decisions.items(), key=lambda item: -occurrences[item[0]])
        ],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.artifact_dir / "agent_tool_log.json").write_text(json.dumps({
        "status": "complete",
        "provider": args.provider,
        "is_mock": is_mock,
        "note": "Every tool call in the order it happened, with its arguments and result.",
        "tool_call_count": sum(len(entry["steps"]) for entry in logs),
        "entries": logs,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"provider={args.provider} mock={is_mock} candidates={len(targets)} "
        f"llm_calls={counters.llm_calls} cache_hits={counters.cache_hits} "
        f"dictionary_hits={counters.dictionary_hits} learned_hits={counters.learned_hits} "
        f"decisions={dict(decision_counts)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
