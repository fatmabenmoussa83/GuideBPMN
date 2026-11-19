"""Execution-order similarity from matched-node precedence relations.

Labels are never rescored here. Hungarian/GED mappings identify corresponding
nodes, then directed sequenceFlow reachability is compared inside each process
or subprocess scope.
"""

import re

import networkx as nx
import numpy as np
from scipy.optimize import linear_sum_assignment

from config import OUTPUT_DIR, ROUND_DIGITS
from dataset_io import load_pair, write_json, write_matrix_csv, write_rows_csv
from elements import comparison_category
from graph_loader import load_bpmn_graph_from_string
from semantic_contextual_alignment import (
    compute_semantic_contextual_alignment,
    export_semantic_contextual_alignment,
    mapping_dict,
)
from semantic_family_similarity import (
    compute_semantic_family_similarity,
    load_embedding_model,
)
from trace import section, trace


def node_scope(graph, node_id):
    """Return the direct execution scope of one BPMN process node."""
    data = graph.nodes[node_id]
    parent = data.get("parent_subprocess_id")
    return f"subprocess:{parent}" if parent else f"process:{data.get('process_id', '')}"


def extract_scopes(graph):
    """Group every process node by its direct process/subprocess scope."""
    scopes = {}
    for node_id in graph.nodes:
        scopes.setdefault(node_scope(graph, node_id), []).append(node_id)
    return {key: sorted(nodes) for key, nodes in sorted(scopes.items())}


def pair_scopes(gold_graph, generated_graph, node_mapping):
    """One-to-one scope alignment maximizing already mapped node overlap."""
    gold_scopes = extract_scopes(gold_graph)
    generated_scopes = extract_scopes(generated_graph)
    gold_keys, generated_keys = list(gold_scopes), list(generated_scopes)
    matrix = np.zeros((len(gold_keys), len(generated_keys)), dtype=float)
    for i, gold_scope in enumerate(gold_keys):
        for gold_node in gold_scopes[gold_scope]:
            generated_node = node_mapping.get(gold_node)
            if not generated_node or generated_node not in generated_graph:
                continue
            generated_scope = node_scope(generated_graph, generated_node)
            if generated_scope in generated_scopes:
                matrix[i, generated_keys.index(generated_scope)] += 1.0

    pairs, paired_gold, paired_generated = [], set(), set()
    if gold_keys and generated_keys:
        rows, columns = linear_sum_assignment(matrix, maximize=True)
        for row, column in zip(rows, columns):
            i, j = int(row), int(column)
            if matrix[i, j] <= 0:
                continue
            paired_gold.add(gold_keys[i]); paired_generated.add(generated_keys[j])
            pairs.append({
                "gold_scope": gold_keys[i],
                "generated_scope": generated_keys[j],
                "mapped_node_overlap": int(matrix[i, j]),
                "status": "paired",
            })
    for key in gold_keys:
        if key not in paired_gold:
            pairs.append({"gold_scope": key, "generated_scope": "",
                          "mapped_node_overlap": 0, "status": "missing_generated_scope"})
    for key in generated_keys:
        if key not in paired_generated:
            pairs.append({"gold_scope": "", "generated_scope": key,
                          "mapped_node_overlap": 0, "status": "extra_generated_scope"})
    return pairs, gold_scopes, generated_scopes, matrix.tolist()


def _reachable_matrix(graph, ordered_nodes, traversal_nodes=None):
    """Reachability between ordered endpoints, allowing every node in the scope."""
    scoped = graph.subgraph(traversal_nodes or ordered_nodes).copy()
    matrix = []
    for source in ordered_nodes:
        descendants = nx.descendants(scoped, source)
        matrix.append([1 if source != target and target in descendants else 0
                       for target in ordered_nodes])
    return matrix


def _matrix_items(graph, node_ids):
    return [{
        "id": node_id,
        "type": graph.nodes[node_id]["type"],
        "category": comparison_category(graph.nodes[node_id]["type"]),
        "label": (graph.nodes[node_id].get("name", "")
                  if graph.nodes[node_id].get("has_name") else ""),
    } for node_id in node_ids]


def compute_workflow_order_similarity(gold_graph, generated_graph, node_mapping):
    """Compare precedence relations per scope and return micro totals."""
    section("order", "precedence relations per process and subprocess")
    scope_pairs, gold_scopes, generated_scopes, scope_matrix = pair_scopes(
        gold_graph, generated_graph, node_mapping,
    )
    scope_results = []
    total_tp = total_fp = total_fn = total_mapped = 0
    for pair in scope_pairs:
        gold_scope, generated_scope = pair["gold_scope"], pair["generated_scope"]
        gold_nodes = gold_scopes.get(gold_scope, [])
        generated_nodes = generated_scopes.get(generated_scope, [])
        aligned_gold = [
            node for node in gold_nodes
            if node in node_mapping and node_mapping[node] in generated_nodes
        ]
        aligned_generated = [node_mapping[node] for node in aligned_gold]
        gold_matrix = _reachable_matrix(gold_graph, aligned_gold, gold_nodes)
        generated_matrix = _reachable_matrix(
            generated_graph, aligned_generated, generated_nodes,
        )
        relations = []
        tp = fp = fn = 0
        for i, gold_source in enumerate(aligned_gold):
            for j, gold_target in enumerate(aligned_gold):
                if i == j:
                    continue
                gold_before = bool(gold_matrix[i][j])
                generated_before = bool(generated_matrix[i][j])
                if not gold_before and not generated_before:
                    continue
                if gold_before and generated_before:
                    status = "correct"; tp += 1
                elif gold_before:
                    reverse = bool(generated_matrix[j][i])
                    status = "reversed" if reverse else "missing"
                    fn += 1
                else:
                    reverse = bool(gold_matrix[j][i])
                    status = "reversed" if reverse else "extra"
                    fp += 1
                relations.append({
                    "gold_scope": gold_scope,
                    "generated_scope": generated_scope,
                    "gold_source": gold_source,
                    "gold_source_label": gold_graph.nodes[gold_source].get("name", ""),
                    "gold_target": gold_target,
                    "gold_target_label": gold_graph.nodes[gold_target].get("name", ""),
                    "generated_source": aligned_generated[i],
                    "generated_source_label": generated_graph.nodes[aligned_generated[i]].get("name", ""),
                    "generated_target": aligned_generated[j],
                    "generated_target_label": generated_graph.nodes[aligned_generated[j]].get("name", ""),
                    "gold_precedes": gold_before,
                    "generated_precedes": generated_before,
                    "status": status,
                    "human_check": "",
                    "human_comment": "",
                })
        relation_denominator = tp + fp + fn
        consistency = tp / relation_denominator if relation_denominator else (
            1.0 if len(aligned_gold) >= 2 else None
        )
        coverage_denominator = max(len(gold_nodes), len(generated_nodes))
        coverage = len(aligned_gold) / coverage_denominator if coverage_denominator else None
        similarity = (
            consistency * coverage
            if consistency is not None and coverage is not None else None
        )
        scope_result = {
            **pair,
            "gold_nodes": gold_nodes,
            "generated_nodes": generated_nodes,
            "aligned_gold_nodes": aligned_gold,
            "aligned_generated_nodes": aligned_generated,
            "gold_order_matrix": gold_matrix,
            "generated_projected_order_matrix": generated_matrix,
            "relation_details": relations,
            "tp": tp, "fp": fp, "fn": fn,
            "order_consistency": None if consistency is None else round(consistency, ROUND_DIGITS),
            "matched_node_count": len(aligned_gold),
            "gold_node_count": len(gold_nodes),
            "generated_node_count": len(generated_nodes),
            "coverage": None if coverage is None else round(coverage, ROUND_DIGITS),
            "workflow_order_similarity": None if similarity is None else round(similarity, ROUND_DIGITS),
        }
        scope_results.append(scope_result)
        total_tp += tp; total_fp += fp; total_fn += fn
        total_mapped += len(aligned_gold)

    order_denominator = total_tp + total_fp + total_fn
    order_consistency = total_tp / order_denominator if order_denominator else None
    coverage_denominator = max(gold_graph.number_of_nodes(), generated_graph.number_of_nodes())
    coverage = total_mapped / coverage_denominator if coverage_denominator else None
    similarity = (
        order_consistency * coverage
        if order_consistency is not None and coverage is not None else None
    )
    result = {
        "method": "matched-node transitive precedence comparison per execution scope",
        "node_mapping": [
            {"gold_id": gold_id, "generated_id": generated_id}
            for gold_id, generated_id in sorted(node_mapping.items())
        ],
        "scope_pairing_matrix": scope_matrix,
        "scope_pairs": scope_pairs,
        "scopes": scope_results,
        "tp": total_tp, "fp": total_fp, "fn": total_fn,
        "order_consistency": (
            None if order_consistency is None else round(order_consistency, ROUND_DIGITS)
        ),
        "matched_node_count": total_mapped,
        "coverage_denominator": coverage_denominator,
        "coverage": None if coverage is None else round(coverage, ROUND_DIGITS),
        "workflow_order_similarity": (
            None if similarity is None else round(similarity, ROUND_DIGITS)
        ),
        "formula": "TP/(TP+FP+FN) * matched_nodes/max(gold_nodes,generated_nodes)",
        "note": "sequenceFlow topology is used; BPMN-DI x/y coordinates are ignored",
    }
    trace("order", f"consistency={result['order_consistency']} coverage={result['coverage']} score={result['workflow_order_similarity']}")
    return result


def _safe_scope_name(value):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value or "unpaired")


def export_workflow_order(result, gold_graph, generated_graph, folder):
    """Export every function input, matrix, relation and scope summary."""
    write_rows_csv(result["node_mapping"], folder / "45_order_input_node_mapping.csv")
    write_rows_csv(result["scope_pairs"], folder / "46_order_scope_pairing.csv")
    gold_scope_items = [{
        "id": scope,
        "type": "executionScope",
        "category": "executionScope",
        "label": scope,
    } for scope in extract_scopes(gold_graph)]
    generated_scope_items = [{
        "id": scope,
        "type": "executionScope",
        "category": "executionScope",
        "label": scope,
    } for scope in extract_scopes(generated_graph)]
    write_matrix_csv(
        result["scope_pairing_matrix"], gold_scope_items, generated_scope_items,
        folder / "46_order_scope_pairing_matrix.csv",
        footer_rows=[{
            "label": "MEANING",
            "formula": "cell = number of already mapped nodes shared by the scope pair",
            "value": "",
        }],
    )
    summaries = []
    all_relations = []
    for index, scope in enumerate(result["scopes"], start=1):
        scope_name = _safe_scope_name(scope["gold_scope"] or scope["generated_scope"])
        prefix = f"47_{index:02d}_{scope_name}"
        gold_items = _matrix_items(gold_graph, scope["aligned_gold_nodes"])
        projected_items = _matrix_items(gold_graph, scope["aligned_gold_nodes"])
        write_matrix_csv(
            scope["gold_order_matrix"], gold_items, gold_items,
            folder / f"{prefix}_gold_order_matrix.csv",
        )
        write_matrix_csv(
            scope["generated_projected_order_matrix"], projected_items, projected_items,
            folder / f"{prefix}_generated_projected_order_matrix.csv",
        )
        all_relations.extend(scope["relation_details"])
        summaries.append({
            "gold_scope": scope["gold_scope"],
            "generated_scope": scope["generated_scope"],
            "status": scope["status"],
            "gold_node_count": scope["gold_node_count"],
            "generated_node_count": scope["generated_node_count"],
            "matched_node_count": scope["matched_node_count"],
            "tp": scope["tp"], "fp": scope["fp"], "fn": scope["fn"],
            "order_consistency": scope["order_consistency"],
            "coverage": scope["coverage"],
            "workflow_order_similarity": scope["workflow_order_similarity"],
        })
    write_rows_csv(
        all_relations, folder / "48_order_relation_details.csv",
        ["gold_scope", "generated_scope", "gold_source", "gold_source_label",
         "gold_target", "gold_target_label", "generated_source",
         "generated_source_label", "generated_target", "generated_target_label",
         "gold_precedes", "generated_precedes", "status", "human_check",
         "human_comment"],
    )
    write_rows_csv(summaries, folder / "49_order_scope_summary.csv")
    write_rows_csv([{
        "tp": result["tp"], "fp": result["fp"], "fn": result["fn"],
        "order_consistency": result["order_consistency"],
        "matched_node_count": result["matched_node_count"],
        "coverage_denominator": result["coverage_denominator"],
        "coverage": result["coverage"],
        "workflow_order_similarity": result["workflow_order_similarity"],
        "formula": result["formula"], "note": result["note"],
    }], folder / "49_workflow_order_summary.csv")


TEST_ID = "01"
TEST_GENERATOR = "gpt"


def run_test(test_id=TEST_ID, generator=TEST_GENERATOR, generated_path=None):
    pair = load_pair(test_id, generator, generated_path=generated_path)
    gold = load_bpmn_graph_from_string(pair["gold_xml"], f"gold-{pair['id']}")
    generated = load_bpmn_graph_from_string(pair["generated_xml"], f"{generator}-{pair['id']}")
    model = load_embedding_model()
    semantic = compute_semantic_family_similarity(gold, generated, model=model)
    alignment = compute_semantic_contextual_alignment(
        gold, generated, semantic["families"]["nodes"],
    )
    mapping = mapping_dict(alignment)
    result = compute_workflow_order_similarity(gold, generated, mapping)
    folder = OUTPUT_DIR / f"workflow_order_{generator}_{pair['id']}"
    export_semantic_contextual_alignment(alignment, folder)
    export_workflow_order(result, gold, generated, folder)
    write_json(result, folder / "workflow_order_result.json")
    return result


if __name__ == "__main__":      # python <module>.py <id> <generated.json>
    import sys
    run_test(*sys.argv[1:2], generated_path=(sys.argv[2] if len(sys.argv) > 2 else None))
