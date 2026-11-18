from __future__ import annotations
def graph_from_rules(rules: list[dict]) -> dict:
    nodes=sorted({x for r in rules for x in r["antecedent"]+r["consequent"]})
    return {"nodes":[{"id":n} for n in nodes],"edges":[{"source":r["antecedent"][0],"target":r["consequent"][0],"support":r["support"],"confidence":r["confidence"],"interest":r["interest"]} for r in rules]}
