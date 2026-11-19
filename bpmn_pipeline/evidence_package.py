"""Evidence handed to the guideline agents, and the gold-leak check.

RULE: only the Similarity Evaluator reads the gold BPMN file. The Retriever
and Expert agents never receive that file; they receive the description, the
generated model, the validator report and the Similarity Evaluator's RESULTS,
as they are: metrics, counts per element type, matched and unmatched elements
with their labels on both sides, missing / extra / reversed flows. Label
comparison is part of those results (it is what a semantic failure is about).

The leak that matters is at the OUTPUT: a candidate guideline that copies a
label existing only in the reference is tied to that one example.
`assert_gold_blind` is the check applied to candidate guidelines.
"""
from __future__ import annotations

import io
import json
import contextlib
import re
from pathlib import Path

from pipeline_config import add_shared_paths
add_shared_paths()

import trace as _trace
_trace.TRACE_ENABLED = False

from graph_loader import load_bpmn_graph_from_string
from type_matching import compute_type_precision_recall_grouped
from semantic_family_similarity import compute_semantic_family_similarity
from semantic_contextual_alignment import (
    compute_semantic_contextual_alignment, mapping_dict,
)
from connection_matching import compute_connection_matching

WITHHELD = "<reference element, label withheld>"


class GoldLeak(AssertionError):
    """Reference-only content reached an agent-visible file."""


def _number(value):
    """The evaluator writes some scores as text ('' when not applicable)."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _norm(text) -> str:
    return " ".join(str(text or "").strip().casefold().split())


def _named(graph, element_id) -> str:
    """A pool, lane or flow node of one model, by its kind and name."""
    if element_id in graph.graph.get("participants", {}):
        return 'pool "%s"' % (graph.graph["participants"][element_id].get("name") or "")
    if element_id in graph.graph.get("lanes", {}):
        return 'lane "%s"' % (graph.graph["lanes"][element_id].get("name") or "")
    if element_id in graph:
        data = graph.nodes[element_id]
        return '%s "%s"' % (data.get("type"), data.get("name", ""))
    return "an element outside the model"


def collaboration_differences(gold, gen, node_mapping: dict, model) -> list[dict]:
    """The pool, lane, membership and message-flow relations on which the two
    models differ, as the Similarity Evaluator found them (same comparison as
    the collaboration score). Empty when neither model has a collaboration."""
    from collaboration_similarity import compute_collaboration_similarity
    with contextlib.redirect_stdout(io.StringIO()):
        result = compute_collaboration_similarity(gold, gen, node_mapping, model=model)
    if not result.get("applicable"):
        return []
    wording = {
        "pool_exists": lambda g, s, t: _named(g, s),
        "lane_exists": lambda g, s, t: _named(g, s),
        "lane_in_pool": lambda g, s, t: "%s inside %s" % (_named(g, s), _named(g, t)),
        "node_in_lane": lambda g, s, t: "%s placed in %s" % (_named(g, s), _named(g, t)),
        "message_flow": lambda g, s, t: "message flow from %s to %s" % (_named(g, s), _named(g, t)),
    }
    out = []
    for row in result.get("relation_comparison", []):
        status = row["status"]
        if status in ("missing", "reversed"):
            kind = row["gold_relation_type"]
            what = wording[kind](gold, row["gold_source"], row["gold_target"])
            text = ("reference %s exists in the generated model in the opposite direction" % what
                    if status == "reversed"
                    else "reference %s has no counterpart in the generated model" % what)
            out.append({"side": "reference", "relation": kind, "text": text})
        elif status == "extra":
            kind = row["projected_generated_relation_type"]
            what = wording[kind](gen, row["projected_generated_source"],
                                 row["projected_generated_target"])
            out.append({"side": "generated", "relation": kind,
                        "text": "generated %s has no counterpart in the reference" % what})
    return out


def build_similarity_results(gold_xml: str, generated_xml: str, metrics: dict,
                            model) -> dict:
    from evaluation import comparable_generated
    generated_xml, _ = comparable_generated(gold_xml, generated_xml)   # same rule as the metrics
    with contextlib.redirect_stdout(io.StringIO()):
        gold = load_bpmn_graph_from_string(gold_xml, "gold")
        gen = load_bpmn_graph_from_string(generated_xml, "generated")
        types = compute_type_precision_recall_grouped(gold, gen)
        sem = compute_semantic_family_similarity(gold, gen, model=model)
        align = compute_semantic_contextual_alignment(gold, gen, sem["families"]["nodes"])
        conn = compute_connection_matching(gold, gen, align)
    gold_to_gen = mapping_dict(align)                      # gold id -> generated id

    def gen_ref(gold_id):
        """A reference node, named only through its generated counterpart."""
        gid = gold_to_gen.get(gold_id)
        if gid is None:
            return None
        data = gen.nodes[gid]
        return {"generated_id": gid, "type": data.get("type"),
                "label": data.get("name", "")}

    matched_pairs = [
        {"type": a.get("gold_type"), "reference_label": a.get("gold_label", ""),
         "generated_id": a.get("generated_id"),
         "generated_label": a.get("generated_label", ""),
         "label_similarity": _number(a.get("semantic_cosine"))}
        for a in align["assignments"] if a.get("accepted", True)]
    matched_generated = set(gold_to_gen.values())
    unmatched_generated = [
        {"generated_id": n, "type": d.get("type"), "label": d.get("name", "")}
        for n, d in gen.nodes(data=True) if n not in matched_generated]

    missing = []
    for node, data in gold.nodes(data=True):
        if node in gold_to_gen:
            continue
        preds = [gen_ref(p) for p in gold.predecessors(node)]
        succs = [gen_ref(s) for s in gold.successors(node)]
        missing.append({
            "type": data.get("type"),
            "label": data.get("name", ""),
            "after_generated": [p for p in preds if p],
            "before_generated": [s for s in succs if s],
            "unmatched_neighbours": sum(1 for x in preds + succs if x is None),
        })

    def flow_view(row):
        """A reference flow expressed with generated endpoints only."""
        src, tgt = gen_ref(row.get("source_id")), gen_ref(row.get("target_id"))
        return {"from": src or {"type": row.get("source_type"),
                                "label": row.get("source_label", ""),
                                "matched": False},
                "to": tgt or {"type": row.get("target_type"),
                              "label": row.get("target_label", ""),
                              "matched": False}}

    def own_flow(row):
        return {"from": {"generated_id": row.get("source_id"),
                         "type": row.get("source_type"), "label": row.get("source_label", "")},
                "to": {"generated_id": row.get("target_id"),
                       "type": row.get("target_type"), "label": row.get("target_label", "")}}

    per_type = types.get("per_type") or {}
    if isinstance(per_type, dict):
        type_counts = {k: {kk: vv for kk, vv in v.items()
                           if isinstance(vv, (int, float))}
                       for k, v in per_type.items() if isinstance(v, dict)}
    else:
        type_counts = {str(r.get("type")): {kk: vv for kk, vv in r.items()
                                            if isinstance(vv, (int, float))}
                       for r in per_type if isinstance(r, dict)}

    return {
        "source": "Similarity Evaluator results (the gold BPMN file itself is not included).",
        "metrics": {k: v for k, v in metrics.items()
                    if isinstance(v, (int, float)) or v is None},
        "element_counts_by_type": type_counts,
        "counts": {"reference_elements": gold.number_of_nodes(),
                   "generated_elements": gen.number_of_nodes(),
                   "matched_elements": len(gold_to_gen)},
        "matched_elements": matched_pairs,
        "generated_elements_without_counterpart": unmatched_generated,
        "reference_elements_without_counterpart": missing,
        "reference_flows_absent_from_generated": [
            flow_view(r) for r in conn.get("fn_connections", [])],
        "generated_flows_absent_from_reference": [
            own_flow(r) for r in conn.get("fp_connections", [])],
        "flows_in_reversed_direction": len(conn.get("reversed_connections", [])),
        "collaboration_differences": collaboration_differences(gold, gen, gold_to_gen, model),
    }


def reference_only_strings(gold_xml: str, generated_xml: str, description: str) -> dict:
    """Labels and ids that exist in the reference and nowhere an agent may look."""
    with contextlib.redirect_stdout(io.StringIO()):
        gold = load_bpmn_graph_from_string(gold_xml, "gold")
        gen = load_bpmn_graph_from_string(generated_xml, "generated")
    desc = _norm(description)
    gen_labels = {_norm(d.get("name")) for _, d in gen.nodes(data=True)}
    labels = set()
    for _, d in gold.nodes(data=True):
        label = _norm(d.get("name"))
        # short generic words would give false alarms; they carry no content
        if len(label) >= 6 and label not in gen_labels and label not in desc:
            labels.add(label)
    for collection in ("participants", "lanes"):       # pool and lane names of the reference
        own = {_norm(v.get("name")) for v in gen.graph.get(collection, {}).values()}
        for value in gold.graph.get(collection, {}).values():
            label = _norm(value.get("name"))
            if len(label) >= 6 and label not in own and label not in gen_labels and label not in desc:
                labels.add(label)
    gen_ids = set(gen.nodes)
    for collection in ("participants", "lanes"):
        gen_ids |= set(gen.graph.get(collection, {}))
    ids = {n for n in gold.nodes if n not in gen_ids and len(str(n)) >= 6
           and str(n) not in generated_xml}
    return {"labels": labels, "ids": ids}


def assert_gold_blind(text: str, gold_xml: str, generated_xml: str,
                      description: str) -> None:
    """Raise GoldLeak when reference-only content appears in agent-visible text."""
    secret = reference_only_strings(gold_xml, generated_xml, description)
    low = _norm(text)
    leaked = [s for s in secret["labels"] if s in low]
    leaked += [i for i in secret["ids"]
               if re.search(r"(?<![\w-])" + re.escape(str(i)) + r"(?![\w-])", text)]
    if leaked:
        raise GoldLeak(f"reference-only content in agent evidence: {sorted(leaked)[:5]}")


def write_evidence_package(run_dir: Path, entry: dict, generated_xml: str,
                           validation: dict, metrics: dict, model) -> dict:
    """Write the only files the guideline agents may read, then verify them."""
    run_dir = Path(run_dir)
    validator_dir, similarity_dir = run_dir / "validator", run_dir / "similarity"
    validator_dir.mkdir(parents=True, exist_ok=True)
    similarity_dir.mkdir(parents=True, exist_ok=True)

    report = build_similarity_results(entry["bpmn_xml"], generated_xml, metrics, model)
    files = {
        validator_dir / "process_description.txt": entry["description"],
        validator_dir / "generated_model.bpmn": generated_xml,
        validator_dir / "validation_profile.json": json.dumps(
            {"id": entry["id"], "validation_profile": validation.get("profile", {})},
            ensure_ascii=False, indent=1),
        similarity_dir / "similarity_results.json": json.dumps(
            report, ensure_ascii=False, indent=1, default=str),
    }
    for path, text in files.items():
        path.write_text(text, encoding="utf-8")
    # the agents never get the gold BPMN file itself
    for path, text in files.items():
        if "gold" in path.name.lower() or (text == entry["bpmn_xml"]
                                           and path.name != "generated_model.bpmn"):
            raise GoldLeak(f"the gold BPMN file reached the agents: {path.name}")
    return {"report": report, "files": [str(p) for p in files]}
