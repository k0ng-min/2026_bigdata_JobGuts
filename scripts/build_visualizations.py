"""Create README-ready visual summaries from tracked analysis artifacts.

The script never reads the raw job-posting file.  It consumes the versioned
rule and graph artifacts so the figures can be regenerated after the analysis
pipeline has completed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib import font_manager


def _configure_font() -> None:
    """Use a Korean-capable font when the host provides one."""
    candidates = [
        Path("C:/Windows/Fonts/malgun.ttf"),
        Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            font_manager.fontManager.addfont(str(candidate))
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(candidate)).get_name()
            break
    plt.rcParams["axes.unicode_minus"] = False


def _rules(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "complete":
        raise ValueError(f"Rule artifact is not complete: {path}")
    return payload["normalized"]


def _label(rule: dict) -> str:
    return f"{', '.join(rule['antecedent'])} → {', '.join(rule['consequent'])}"


def _save_top_rules(rules: list[dict], output: Path) -> None:
    selected = rules[:12][::-1]
    labels = [_label(rule) for rule in selected]
    values = [rule["interest"] for rule in selected]
    fig, ax = plt.subplots(figsize=(11, 6.5))
    bars = ax.barh(labels, values, color="#303030")
    ax.bar_label(bars, labels=[f"{value:.3f}" for value in values], padding=4, fontsize=9)
    ax.set_xlim(0, min(1, max(values) + 0.08))
    ax.set_xlabel("interest = confidence(A → B) - P(B)")
    ax.set_title("상위 연관규칙: interest 기준", loc="left", fontweight="bold")
    ax.grid(axis="x", color="#dddddd", linewidth=0.7)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(output, dpi=170, bbox_inches="tight")
    plt.close(fig)


def _save_scatter(rules: list[dict], output: Path) -> None:
    support = [rule["support"] for rule in rules]
    confidence = [rule["confidence"] for rule in rules]
    interest = [rule["interest"] for rule in rules]
    fig, ax = plt.subplots(figsize=(9.5, 6.2))
    points = ax.scatter(support, confidence, c=interest, cmap="Greys", s=28, alpha=0.85, edgecolors="none")
    ax.set_xlabel("support")
    ax.set_ylabel("confidence")
    ax.set_title("연관규칙 분포: support와 confidence", loc="left", fontweight="bold")
    colorbar = fig.colorbar(points, ax=ax)
    colorbar.set_label("interest")
    ax.grid(color="#dddddd", linewidth=0.7)
    fig.tight_layout()
    fig.savefig(output, dpi=170, bbox_inches="tight")
    plt.close(fig)


def _save_network(graph_path: Path, output: Path, edge_limit: int) -> None:
    payload = json.loads(graph_path.read_text(encoding="utf-8"))
    edges = sorted(payload["edges"], key=lambda edge: edge["interest"], reverse=True)[:edge_limit]
    graph = nx.DiGraph()
    for edge in edges:
        graph.add_edge(edge["source"], edge["target"], interest=edge["interest"])
    positions = nx.spring_layout(graph, seed=42, k=1.25 / max(len(graph), 1) ** 0.5, iterations=120)
    fig, ax = plt.subplots(figsize=(11, 8))
    degrees = dict(graph.degree())
    nx.draw_networkx_nodes(
        graph, positions, node_size=[120 + 28 * degrees[node] for node in graph.nodes],
        node_color="#f3f3f3", edgecolors="#202020", linewidths=0.8, ax=ax,
    )
    nx.draw_networkx_edges(
        graph, positions, width=[1 + 4 * graph[u][v]["interest"] for u, v in graph.edges],
        edge_color="#555555", arrows=True, arrowsize=11, alpha=0.65, ax=ax,
    )
    nx.draw_networkx_labels(graph, positions, font_size=8, font_color="#111111", ax=ax)
    ax.set_title(f"기술 연결 그래프: interest 상위 {len(edges)}개 방향 규칙", loc="left", fontweight="bold")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--output-dir", type=Path, default=Path("docs/assets"))
    parser.add_argument("--network-edges", type=int, default=60)
    args = parser.parse_args()
    _configure_font()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rules = _rules(args.artifact_dir / "week12_all_rules.json")
    _save_top_rules(rules, args.output_dir / "top_rules_interest.png")
    _save_scatter(rules, args.output_dir / "support_confidence_scatter.png")
    _save_network(args.artifact_dir / "week14_skill_graph.json", args.output_dir / "skill_graph_top_edges.png", args.network_edges)
    print(f"Wrote 3 figures to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
