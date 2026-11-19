"""Directed connection fidelity after semantic-contextual node matching.

Labels establish node identity upstream. Here a sequenceFlow is correct when
its already matched source and target are connected in the same direction.
"""

from config import OUTPUT_DIR, ROUND_DIGITS
from dataset_io import load_pair, write_json, write_rows_csv
from graph_loader import load_bpmn_graph_from_string
from semantic_contextual_alignment import (
    compute_semantic_contextual_alignment,
    export_semantic_contextual_alignment,
    mapping_dict,
    match_id_dict,
)
from semantic_family_similarity import (
    compute_semantic_family_similarity,
    load_embedding_model,
)
from trace import section, trace


def _label(graph, node_id):
    data = graph.nodes[node_id]
    return data.get("name", "") if data.get("has_name") else ""


def _edge_row(side, source, target, data, graph, match_ids):
    return {
        "side": side,
        "connection_id": data.get("id") or f"{source}->{target}",
        "source_id": source,
        "source_match_id": match_ids.get(source, ""),
        "source_type": graph.nodes[source]["type"],
        "source_label": _label(graph, source),
        "target_id": target,
        "target_match_id": match_ids.get(target, ""),
        "target_type": graph.nodes[target]["type"],
        "target_label": _label(graph, target),
        "scope_id": graph.nodes[source].get("parent_subprocess_id")
        or graph.nodes[source].get("process_id", ""),
        "canonical_connection": (
            f"{match_ids.get(source, 'UNMATCHED')} -> "
            f"{match_ids.get(target, 'UNMATCHED')}"
        ),
    }


def _neighbors(graph, node_id, match_ids, direction):
    iterable = (
        graph.predecessors(node_id)
        if direction == "predecessor" else graph.successors(node_id)
    )
    nodes = list(iterable)
    return {
        "ids": "; ".join(nodes),
        "match_ids": "; ".join(
            match_ids.get(node, "UNMATCHED") for node in nodes
        ),
    }


def compute_connection_matching(gold_graph, generated_graph, alignment_result):
    """Classify directed edges after semantically grounded node matching."""
    section("connection", "semantic match IDs -> exact directed sequenceFlow")
    gold_match_ids = match_id_dict(alignment_result, "gold")
    generated_match_ids = match_id_dict(alignment_result, "generated")

    node_mapping = []
    for assignment in alignment_result["assignments"]:
        if not assignment.get("accepted", True):
            continue
        gold_id = assignment["gold_id"]
        generated_id = assignment["generated_id"]
        gold_pred = _neighbors(gold_graph, gold_id, gold_match_ids, "predecessor")
        gold_succ = _neighbors(gold_graph, gold_id, gold_match_ids, "successor")
        gen_pred = _neighbors(
            generated_graph, generated_id, generated_match_ids, "predecessor",
        )
        gen_succ = _neighbors(
            generated_graph, generated_id, generated_match_ids, "successor",
        )
        node_mapping.append({
            "match_id": assignment["match_id"],
            "gold_id": gold_id,
            "gold_type": assignment["gold_type"],
            "gold_label": assignment["gold_label"],
            "gold_predecessor_ids": gold_pred["ids"],
            "gold_predecessor_match_ids": gold_pred["match_ids"],
            "gold_successor_ids": gold_succ["ids"],
            "gold_successor_match_ids": gold_succ["match_ids"],
            "generated_id": generated_id,
            "generated_type": assignment["generated_type"],
            "generated_label": assignment["generated_label"],
            "generated_predecessor_ids": gen_pred["ids"],
            "generated_predecessor_match_ids": gen_pred["match_ids"],
            "generated_successor_ids": gen_succ["ids"],
            "generated_successor_match_ids": gen_succ["match_ids"],
            "semantic_cosine": assignment["semantic_cosine"],
            "predecessor_consistency": assignment[
                "matched_predecessor_consistency"
            ],
            "successor_consistency": assignment[
                "matched_successor_consistency"
            ],
            "human_check": "",
            "human_comment": "",
        })

    gold_rows = [
        _edge_row("gold", source, target, data, gold_graph, gold_match_ids)
        for source, target, data in gold_graph.edges(data=True)
    ]
    generated_rows = [
        _edge_row(
            "generated", source, target, data, generated_graph,
            generated_match_ids,
        )
        for source, target, data in generated_graph.edges(data=True)
    ]
    generated_by_pair = {
        (row["source_match_id"], row["target_match_id"]): row
        for row in generated_rows
        if row["source_match_id"] and row["target_match_id"]
    }
    gold_by_pair = {
        (row["source_match_id"], row["target_match_id"]): row
        for row in gold_rows
        if row["source_match_id"] and row["target_match_id"]
    }

    used_generated = set()
    classified_gold = []
    reversed_pairs = []
    tp = fn = 0
    for row in gold_rows:
        source_match = row["source_match_id"]
        target_match = row["target_match_id"]
        pair = (source_match, target_match)
        reverse_pair = (target_match, source_match)
        if not source_match or not target_match:
            status = "FN_UNMAPPED_ENDPOINT"
            reason = "At least one Gold endpoint has no accepted semantic-contextual match."
            paired = ""
            fn += 1
        elif pair in generated_by_pair:
            status = "TP_EXACT"
            reason = "The same semantic identities are connected in the same direction."
            paired = generated_by_pair[pair]["connection_id"]
            used_generated.add(paired)
            tp += 1
        elif reverse_pair in generated_by_pair:
            status = "FN_REVERSED"
            reason = "The same semantic identities exist, but their direction is reversed."
            paired = generated_by_pair[reverse_pair]["connection_id"]
            used_generated.add(paired)
            reversed_pairs.append({
                "gold_connection_id": row["connection_id"],
                "generated_connection_id": paired,
                "gold_direction": row["canonical_connection"],
                "generated_direction": f"{target_match} -> {source_match}",
                "policy": "one reversed relation contributes FN=1 and FP=1",
                "human_check": "",
                "human_comment": "",
            })
            fn += 1
        else:
            status = "FN_MISSING"
            reason = "The expected connection between the matched identities is absent."
            paired = ""
            fn += 1
        classified_gold.append({
            **row,
            "paired_generated_connection_id": paired,
            "status": status,
            "tp_contribution": int(status == "TP_EXACT"),
            "fn_contribution": int(status != "TP_EXACT"),
            "identity_status": "unresolved" if status == "FN_UNMAPPED_ENDPOINT" else "mapped",
            "generation_defect_verified": False,
            "reason": reason,
            "human_check": "",
            "human_comment": "",
        })

    classified_generated = []
    fp = 0
    for row in generated_rows:
        pair = (row["source_match_id"], row["target_match_id"])
        reverse_pair = (row["target_match_id"], row["source_match_id"])
        if row["connection_id"] in used_generated and pair in gold_by_pair:
            status = "TP_EXACT"
            reason = "The same directed semantic match-ID pair exists in Gold."
            contribution = 0
        elif row["connection_id"] in used_generated and reverse_pair in gold_by_pair:
            status = "FP_REVERSED"
            reason = "This is the reverse of an expected Gold connection."
            contribution = 1
            fp += 1
        elif not row["source_match_id"] or not row["target_match_id"]:
            status = "FP_UNMAPPED_ENDPOINT"
            reason = "At least one endpoint has no accepted Gold semantic identity."
            contribution = 1
            fp += 1
        else:
            status = "FP_ADDITIONAL"
            reason = "This connection between matched identities does not exist in Gold."
            contribution = 1
            fp += 1
        classified_generated.append({
            **row,
            "paired_gold_connection_id": (
                gold_by_pair[pair]["connection_id"] if pair in gold_by_pair else ""
            ),
            "status": status,
            "fp_contribution": contribution,
            "identity_status": "unresolved" if status == "FP_UNMAPPED_ENDPOINT" else "mapped",
            "generation_defect_verified": False,
            "reason": reason,
            "human_check": "",
            "human_comment": "",
        })

    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else 0.0
    )
    jaccard = tp / (tp + fp + fn) if tp + fp + fn else None
    result = {
        "method": "exact directed comparison after semantic-contextual node alignment",
        "unmapped_gold_connection_count": sum(x["status"] == "FN_UNMAPPED_ENDPOINT" for x in classified_gold),
        "unmapped_generated_connection_count": sum(x["status"] == "FP_UNMAPPED_ENDPOINT" for x in classified_generated),
        "uncertainty_policy": "Unmapped endpoints reduce strict reference coverage; they do not prove missing work or a generation defect.",
        "uses_semantic_node_identity": True,
        "rescoring_labels_on_connections": False,
        "node_mapping": node_mapping,
        "gold_connections": classified_gold,
        "generated_connections": classified_generated,
        "tp_connections": [x for x in classified_gold if x["status"] == "TP_EXACT"],
        "fn_connections": [x for x in classified_gold if x["status"] != "TP_EXACT"],
        "fp_connections": [x for x in classified_generated if x["fp_contribution"]],
        "reversed_connections": reversed_pairs,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "reversed_count": len(reversed_pairs),
        "precision": None if precision is None else round(precision, ROUND_DIGITS),
        "recall": None if recall is None else round(recall, ROUND_DIGITS),
        "f1_workflow_relation_similarity": round(f1, ROUND_DIGITS),
        "jaccard": None if jaccard is None else round(jaccard, ROUND_DIGITS),
        "formula": "F1 = 2*TP / (2*TP + FP + FN)",
        "reversed_policy": "one reversed relation contributes FN=1 and FP=1",
        "note": (
            "Semantic similarity establishes node identity upstream. This step "
            "scores only connection existence and direction."
        ),
    }
    trace(
        "connection",
        f"TP={tp} FP={fp} FN={fn} reversed={len(reversed_pairs)} "
        f"F1={result['f1_workflow_relation_similarity']}",
    )
    return result


def export_connection_matching(result, folder):
    write_rows_csv(result["node_mapping"], folder / "40_node_mapping_for_connections.csv")
    write_rows_csv(result["gold_connections"], folder / "41_gold_connections_classified.csv")
    write_rows_csv(result["generated_connections"], folder / "42_generated_connections_classified.csv")
    write_rows_csv(
        result["gold_connections"] + result["generated_connections"],
        folder / "43_all_connection_decisions.csv",
    )
    write_rows_csv(result["tp_connections"], folder / "43_tp_correct_connections.csv")
    write_rows_csv(result["fn_connections"], folder / "43_fn_missing_connections.csv")
    write_rows_csv(result["fp_connections"], folder / "43_fp_additional_connections.csv")
    write_rows_csv(
        result["reversed_connections"], folder / "43_reversed_connections.csv",
        ["gold_connection_id", "generated_connection_id", "gold_direction",
         "generated_direction", "policy", "human_check", "human_comment"],
    )
    write_rows_csv([{
        "method": result["method"],
        "uses_semantic_node_identity": result["uses_semantic_node_identity"],
        "rescoring_labels_on_connections": result["rescoring_labels_on_connections"],
        "gold_connection_count": len(result["gold_connections"]),
        "generated_connection_count": len(result["generated_connections"]),
        "tp": result["tp"], "fp": result["fp"], "fn": result["fn"],
        "reversed_count": result["reversed_count"],
        "precision": result["precision"], "recall": result["recall"],
        "f1_workflow_relation_similarity": result["f1_workflow_relation_similarity"],
        "jaccard": result["jaccard"], "formula": result["formula"],
        "reversed_policy": result["reversed_policy"], "note": result["note"],
    }], folder / "44_connection_summary.csv")


TEST_ID = "01"
TEST_GENERATOR = "gpt"


def run_test(test_id=TEST_ID, generator=TEST_GENERATOR, generated_path=None):
    pair = load_pair(test_id, generator, generated_path=generated_path)
    gold = load_bpmn_graph_from_string(pair["gold_xml"], f"gold-{pair['id']}")
    generated = load_bpmn_graph_from_string(
        pair["generated_xml"], f"{generator}-{pair['id']}",
    )
    model = load_embedding_model()
    semantic = compute_semantic_family_similarity(gold, generated, model=model)
    alignment = compute_semantic_contextual_alignment(
        gold, generated, semantic["families"]["nodes"],
    )
    folder = OUTPUT_DIR / f"connections_{generator}_{pair['id']}"
    export_semantic_contextual_alignment(alignment, folder)
    result = compute_connection_matching(gold, generated, alignment)
    export_connection_matching(result, folder)
    write_json(result, folder / "44_connection_result.json")
    return result


if __name__ == "__main__":      # python <module>.py <id> <generated.json>
    import sys
    run_test(*sys.argv[1:2], generated_path=(sys.argv[2] if len(sys.argv) > 2 else None))
