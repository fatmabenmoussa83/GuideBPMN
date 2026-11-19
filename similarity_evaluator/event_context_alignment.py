"""Recover unmatched events from fixed activity identities and compatible triggers.

A conservative deterministic heuristic, not a semantic equivalence proof.
Cosine matrices and their original semantic threshold are never modified.
"""
from xml.etree import ElementTree as ET
import numpy as np


def trigger(data):
    try:
        root = ET.fromstring(data.get("xml_excerpt", ""))
    except (ET.ParseError, ValueError):
        return None, None
    kinds, durations = [], []
    for child in root:
        kind = child.tag.rsplit("}", 1)[-1]
        if kind.endswith("EventDefinition"):
            kinds.append(kind)
            if kind == "timerEventDefinition":
                durations.extend((node.tag.rsplit("}",1)[-1], " ".join(node.itertext()).strip())
                                 for node in child)
    return tuple(sorted(kinds)), tuple(sorted(durations))


def recover_events(gold, generated, mapping, consensus, semantic, gold_index,
                   generated_index, *, minimum_cosine):
    used = set(mapping.values())
    candidates = []
    for a, left in gold.nodes(data=True):
        if a in mapping or left["type"] not in {"intermediateCatchEvent", "intermediateThrowEvent"}:
            continue
        expected = consensus.get(left.get("process_id"))
        if not expected:
            continue
        pred, succ = set(gold.predecessors(a)), set(gold.successors(a))
        # Every immediate neighbour must already have an independently chosen identity.
        if not pred or not succ or not (pred | succ) <= mapping.keys():
            continue
        for b, right in generated.nodes(data=True):
            if b in used or left["type"] != right["type"]:
                continue
            if right.get("process_id") != expected["generated_process_id"]:
                continue
            if bool(left.get("parent_subprocess_id")) != bool(right.get("parent_subprocess_id")):
                continue
            # Nested scopes need a confirmed parent match too.
            parent = left.get("parent_subprocess_id")
            if parent and mapping.get(parent) != right.get("parent_subprocess_id"):
                continue
            value = semantic[gold_index[a], generated_index[b]]
            if not np.isfinite(value) or value < minimum_cosine:
                continue
            lt, ld = trigger(left); rt, rd = trigger(right)
            if lt is None or rt is None:
                continue  # Truncated or missing XML cannot establish trigger compatibility.
            if lt and rt and lt != rt:
                continue
            if ld and rd and ld != rd:
                continue
            if {mapping[x] for x in pred} != set(generated.predecessors(b)):
                continue
            if {mapping[x] for x in succ} != set(generated.successors(b)):
                continue
            candidates.append({"gold_id": a, "generated_id": b,
                "semantic_cosine": round(float(value),6),
                "gold_trigger_types": list(lt), "generated_trigger_types": list(rt),
                "trigger_evidence": "both_explicit" if lt and rt else "unspecified_on_one_side",
                "predecessor_anchors": sorted(pred), "successor_anchors": sorted(succ),
                "basis": "same anchored process, exact mapped neighbours, compatible known triggers",
                "semantic_equivalence_proven": False})
    # No score-gap threshold: only unique recovery proposals are used.
    return [row for row in candidates
            if sum(x["gold_id"] == row["gold_id"] for x in candidates) == 1
            and sum(x["generated_id"] == row["generated_id"] for x in candidates) == 1]
