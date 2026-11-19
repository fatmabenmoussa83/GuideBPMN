"""Semantic node identity refined with predecessor/successor context.

The labels decide whether two named activities may represent the same element.
Local graph context confirms or disambiguates that identity.  The resulting
shared match IDs are preprocessing for connection and order metrics.
"""

from collections import Counter

import numpy as np
from partial_assignment import partial_assignment, ambiguity_margin

from config import (
    NODE_MATCH_CONTEXT_FALLBACK_THRESHOLD,
    NODE_MATCH_INITIAL_CONTEXT_WEIGHT,
    NODE_MATCH_INITIAL_SEMANTIC_WEIGHT,
    NODE_MATCH_MAX_ITERATIONS,
    NODE_MATCH_PREDECESSOR_WEIGHT,
    NODE_MATCH_SUCCESSOR_WEIGHT,
    NODE_MATCH_BASE_WEIGHT,
    OUTPUT_DIR,
    ROUND_DIGITS,
    SIMILARITY_THRESHOLD,
)
from dataset_io import load_pair, write_json, write_matrix_csv, write_rows_csv
from elements import comparison_category
from graph_loader import load_bpmn_graph_from_string
from semantic_family_similarity import (
    compute_semantic_family_similarity,
    load_embedding_model,
)
from trace import section, trace


GENERIC_EVENT_LABELS = {
    "start", "start event", "begin", "beginning", "process start",
    "end", "end event", "finish", "finished", "process end",
}


def _normalise(text):
    return " ".join(str(text or "").strip().lower().replace("_", " ").split())


def _display_label(graph, node_id):
    data = graph.nodes[node_id]
    return data.get("name", "") if data.get("has_name") else ""


def _is_generic_event(graph, node_id):
    data = graph.nodes[node_id]
    return (
        data.get("type") in {"startEvent", "endEvent"}
        and _normalise(_display_label(graph, node_id)) in GENERIC_EVENT_LABELS
    )


def _count_similarity(a, b):
    return 1.0 if max(a, b) == 0 else 1.0 - abs(a - b) / max(a, b)


def _multiset_dice(left, right):
    a, b = Counter(left), Counter(right)
    size = sum(a.values()) + sum(b.values())
    if size == 0:
        return 1.0
    overlap = sum((a & b).values())
    return 2.0 * overlap / size


def _node_scope(graph, node_id):
    data = graph.nodes[node_id]
    parent = data.get("parent_subprocess_id")
    return f"subprocess:{parent}" if parent else f"process:{data.get('process_id', '')}"


def _terminal_activity_anchors(graph, node_id):
    """Nearest named activities in the event's own scope, without crossing tasks."""
    direction = graph.successors if graph.nodes[node_id]["type"] == "startEvent" else graph.predecessors
    scope = _node_scope(graph, node_id)
    pending = list(direction(node_id))
    visited = {node_id}
    anchors = []
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        if _node_scope(graph, current) != scope:
            continue
        data = graph.nodes[current]
        if comparison_category(data["type"]) == "activity":
            if data.get("has_name"):
                anchors.append(current)
            continue
        pending.extend(direction(current))
    return anchors


def _terminal_scope_guard(gold_graph, generated_graph, gold_id, generated_id,
                          semantic, gold_index, generated_index, threshold):
    if gold_graph.nodes[gold_id]["type"] not in {"startEvent", "endEvent"}:
        return None
    if generated_graph.nodes[generated_id]["type"] != gold_graph.nodes[gold_id]["type"]:
        return None  # Existing category policy handles this mismatch.
    if _node_scope(gold_graph, gold_id).split(":", 1)[0] != _node_scope(generated_graph, generated_id).split(":", 1)[0]:
        return "INCOMPATIBLE_TERMINAL_SCOPE_KIND"
    left = _terminal_activity_anchors(gold_graph, gold_id)
    right = _terminal_activity_anchors(generated_graph, generated_id)
    if not left or not right:
        return None  # No activity evidence: retain the existing event policy.
    for source in left:
        for target in right:
            if source not in gold_index or target not in generated_index:
                continue
            value = semantic[gold_index[source], generated_index[target]]
            if np.isfinite(value) and value >= threshold:
                return None
    return "UNSUPPORTED_TERMINAL_ACTIVITY_CONTEXT"


def _local_context(graph, node_id):
    predecessors = [
        comparison_category(graph.nodes[x]["type"])
        for x in graph.predecessors(node_id)
    ]
    successors = [
        comparison_category(graph.nodes[x]["type"])
        for x in graph.successors(node_id)
    ]
    return {
        "in_degree": graph.in_degree(node_id),
        "out_degree": graph.out_degree(node_id),
        "predecessor_categories": predecessors,
        "successor_categories": successors,
        "scope_kind": _node_scope(graph, node_id).split(":", 1)[0],
    }


def _local_context_score(gold_context, generated_context):
    parts = {
        "in_degree_similarity": _count_similarity(
            gold_context["in_degree"], generated_context["in_degree"],
        ),
        "out_degree_similarity": _count_similarity(
            gold_context["out_degree"], generated_context["out_degree"],
        ),
        "predecessor_type_similarity": _multiset_dice(
            gold_context["predecessor_categories"],
            generated_context["predecessor_categories"],
        ),
        "successor_type_similarity": _multiset_dice(
            gold_context["successor_categories"],
            generated_context["successor_categories"],
        ),
        "scope_kind_similarity": float(
            gold_context["scope_kind"] == generated_context["scope_kind"]
        ),
    }
    return sum(parts.values()) / len(parts), parts


def _numeric_semantic_matrix(node_semantic):
    matrix = node_semantic["matrix"]
    result = np.full((len(matrix), len(matrix[0]) if matrix else 0), np.nan)
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            if isinstance(value, (int, float)):
                result[i, j] = float(value)
    return result


def _candidate_policy(gold_graph, generated_graph, gold_id, generated_id,
                      semantic_score, local_score, threshold):
    gold_data = gold_graph.nodes[gold_id]
    generated_data = generated_graph.nodes[generated_id]
    gold_category = comparison_category(gold_data["type"])
    generated_category = comparison_category(generated_data["type"])
    if gold_category != generated_category:
        return False, "INCOMPATIBLE_CATEGORY", None

    exact_type = gold_data["type"] == generated_data["type"]
    is_gateway = gold_data["type"].endswith("Gateway")
    is_terminal_event = gold_data["type"] in {"startEvent", "endEvent"}
    label_available = np.isfinite(semantic_score)
    generic_event = _is_generic_event(gold_graph, gold_id) or _is_generic_event(
        generated_graph, generated_id,
    )

    if is_gateway:
        if not exact_type:
            return False, "INCOMPATIBLE_GATEWAY_TYPE", None
        return True, "EXACT_GATEWAY_TYPE_PLUS_CONTEXT", local_score

    if is_terminal_event and exact_type and (generic_event or not label_available):
        return True, "EVENT_TYPE_PLUS_CONTEXT", local_score

    if label_available and semantic_score >= threshold:
        initial = (
            NODE_MATCH_INITIAL_SEMANTIC_WEIGHT * semantic_score
            + NODE_MATCH_INITIAL_CONTEXT_WEIGHT * local_score
        )
        return True, "SEMANTIC_LABEL_PLUS_LOCAL_CONTEXT", initial

    if exact_type and not gold_data.get("has_name") and not generated_data.get("has_name"):
        if gold_data["type"] in {
            "startEvent", "endEvent", "intermediateCatchEvent",
            "intermediateThrowEvent", "boundaryEvent",
        }:
            return True, "UNNAMED_EVENT_TYPE_PLUS_CONTEXT", local_score

    if not label_available:
        return False, "NO_USABLE_LABEL", None
    return False, "SEMANTIC_BELOW_THRESHOLD", None


def _solve_by_category(scores, allowed, gold_ids, generated_ids,
                       gold_graph, generated_graph):
    pairs = {}
    categories = sorted({
        comparison_category(data["type"])
        for _, data in list(gold_graph.nodes(data=True))
        + list(generated_graph.nodes(data=True))
    })
    for category in categories:
        gi = [
            i for i, node_id in enumerate(gold_ids)
            if comparison_category(gold_graph.nodes[node_id]["type"]) == category
        ]
        pj = [
            j for j, node_id in enumerate(generated_ids)
            if comparison_category(generated_graph.nodes[node_id]["type"]) == category
        ]
        if not gi or not pj:
            continue
        local = np.full((len(gi), len(pj)), -1_000_000.0)
        for row, i in enumerate(gi):
            for column, j in enumerate(pj):
                if allowed[i, j] and (scores[i, j] >= NODE_MATCH_CONTEXT_FALLBACK_THRESHOLD):
                    local[row, column] = scores[i, j]
        permitted = local > -1_000_000.0
        for row, column in partial_assignment(local, permitted):
            i, j = gi[int(row)], pj[int(column)]
            if allowed[i, j]:
                pairs[gold_ids[i]] = generated_ids[j]
    return pairs


def _activity_process_consensus(gold_graph, generated_graph, mapping):
    """Conservative, many-to-one process evidence from named activity matches.

    Two or more anchors and a 75% majority are required. No process names or
    dataset-specific labels enter this guard. Activities are not constrained.
    """
    votes = {}
    for gold_id, generated_id in mapping.items():
        left, right = gold_graph.nodes[gold_id], generated_graph.nodes[generated_id]
        if comparison_category(left["type"]) != "activity" or comparison_category(right["type"]) != "activity":
            continue
        if not left.get("has_name") or not right.get("has_name"):
            continue
        source, target = left.get("process_id"), right.get("process_id")
        if source and target:
            votes.setdefault(source, Counter())[target] += 1
    result = {}
    for source, counts in votes.items():
        target, support = counts.most_common(1)[0]
        total = sum(counts.values())
        if support >= 2 and support / total >= 0.75:
            result[source] = {"generated_process_id": target, "support": support, "total": total}
    return result


def _neighbor_consistency(gold_graph, generated_graph, gold_id, generated_id,
                          mapping, direction):
    if direction == "predecessor":
        gold_neighbors = list(gold_graph.predecessors(gold_id))
        generated_neighbors = list(generated_graph.predecessors(generated_id))
    else:
        gold_neighbors = list(gold_graph.successors(gold_id))
        generated_neighbors = list(generated_graph.successors(generated_id))
    projected = [mapping[x] for x in gold_neighbors if x in mapping]
    return _multiset_dice(projected, generated_neighbors)


def _item(graph, node_id):
    data = graph.nodes[node_id]
    return {
        "id": node_id,
        "type": data["type"],
        "category": comparison_category(data["type"]),
        "label": _display_label(graph, node_id),
    }


def compute_semantic_contextual_alignment(gold_graph, generated_graph,
                                          node_semantic,
                                          threshold=SIMILARITY_THRESHOLD):
    """Align nodes semantically, then refine the assignment with graph context."""
    section("alignment", "semantic identity + predecessor/successor refinement")
    gold_ids = [item["id"] for item in node_semantic["gold_items"]]
    generated_ids = [item["id"] for item in node_semantic["generated_items"]]
    semantic = _numeric_semantic_matrix(node_semantic)
    gold_index = {node: index for index, node in enumerate(gold_ids)}
    generated_index = {node: index for index, node in enumerate(generated_ids)}
    local_context = np.full(semantic.shape, np.nan)
    initial = np.full(semantic.shape, -1_000_000.0)
    allowed = np.zeros(semantic.shape, dtype=bool)
    policies = {}
    local_parts = {}
    gold_context = {node: _local_context(gold_graph, node) for node in gold_ids}
    generated_context = {
        node: _local_context(generated_graph, node) for node in generated_ids
    }

    for i, gold_id in enumerate(gold_ids):
        for j, generated_id in enumerate(generated_ids):
            context_score, parts = _local_context_score(
                gold_context[gold_id], generated_context[generated_id],
            )
            local_context[i, j] = context_score
            semantic_score = semantic[i, j]
            permit, policy, score = _candidate_policy(
                gold_graph, generated_graph, gold_id, generated_id,
                semantic_score, context_score, threshold,
            )
            scope_rejection = _terminal_scope_guard(
                gold_graph, generated_graph, gold_id, generated_id,
                semantic, gold_index, generated_index, threshold,
            ) if permit else None
            if scope_rejection:
                permit, policy, score = False, scope_rejection, None
            policies[(i, j)] = policy
            local_parts[(i, j)] = parts
            if permit:
                allowed[i, j] = True
                initial[i, j] = score

    activity_allowed = allowed.copy()
    for i, gold_id in enumerate(gold_ids):
        if comparison_category(gold_graph.nodes[gold_id]["type"]) != "activity":
            activity_allowed[i, :] = False
    anchors = _solve_by_category(initial, activity_allowed, gold_ids, generated_ids, gold_graph, generated_graph)
    process_consensus = _activity_process_consensus(gold_graph, generated_graph, anchors)
    for i, gold_id in enumerate(gold_ids):
        # Apply process scope to every node category after establishing anchors.
        # Several Gold processes may map to one Generated process (a merge).
        expected = process_consensus.get(gold_graph.nodes[gold_id].get("process_id"))
        if expected is None:
            continue  # Sparse or ambiguous role evidence must not force a process identity.
        for j, generated_id in enumerate(generated_ids):
            actual = generated_graph.nodes[generated_id].get("process_id")
            if allowed[i, j] and actual and actual != expected["generated_process_id"]:
                allowed[i, j] = False
                initial[i, j] = -1_000_000.0
                policies[(i, j)] = "CONFLICT_WITH_ACTIVITY_PROCESS_ANCHORS"
    mapping = _solve_by_category(
        initial, allowed, gold_ids, generated_ids, gold_graph, generated_graph,
    )
    from event_context_alignment import recover_events
    recovered_events = recover_events(
        gold_graph, generated_graph, mapping, process_consensus, semantic,
        gold_index, generated_index, minimum_cosine=NODE_MATCH_CONTEXT_FALLBACK_THRESHOLD)
    for recovered in recovered_events:
        a, b = recovered["gold_id"], recovered["generated_id"]
        i, j = gold_index[a], generated_index[b]
        allowed[i, j] = True
        initial[i, j] = (NODE_MATCH_INITIAL_SEMANTIC_WEIGHT * semantic[i,j]
                         + NODE_MATCH_INITIAL_CONTEXT_WEIGHT * local_context[i,j])
        policies[(i,j)] = "EVENT_CONTEXT_CONFIRMED_BELOW_THRESHOLD"
        mapping[a] = b
    refined = initial.copy()
    iterations = 1
    for iteration in range(1, NODE_MATCH_MAX_ITERATIONS + 1):
        for i, gold_id in enumerate(gold_ids):
            for j, generated_id in enumerate(generated_ids):
                if not allowed[i, j]:
                    continue
                pred = _neighbor_consistency(
                    gold_graph, generated_graph, gold_id, generated_id,
                    mapping, "predecessor",
                )
                succ = _neighbor_consistency(
                    gold_graph, generated_graph, gold_id, generated_id,
                    mapping, "successor",
                )
                refined[i, j] = (
                    NODE_MATCH_BASE_WEIGHT * initial[i, j]
                    + NODE_MATCH_PREDECESSOR_WEIGHT * pred
                    + NODE_MATCH_SUCCESSOR_WEIGHT * succ
                )
            
        new_mapping = _solve_by_category(
            refined, allowed, gold_ids, generated_ids, gold_graph, generated_graph,
        )
        iterations = iteration + 1
        if new_mapping == mapping:
            break
        mapping = new_mapping

    # Recompute the displayed/final scores once with the final assignment.
    # This keeps every exported matrix cell consistent with the predecessor
    # and successor match IDs written to the assignment CSV.
    for i, gold_id in enumerate(gold_ids):
        for j, generated_id in enumerate(generated_ids):
            if not allowed[i, j]:
                continue
            pred = _neighbor_consistency(
                gold_graph, generated_graph, gold_id, generated_id,
                mapping, "predecessor",
            )
            succ = _neighbor_consistency(
                gold_graph, generated_graph, gold_id, generated_id,
                mapping, "successor",
            )
            refined[i, j] = (
                NODE_MATCH_BASE_WEIGHT * initial[i, j]
                + NODE_MATCH_PREDECESSOR_WEIGHT * pred
                + NODE_MATCH_SUCCESSOR_WEIGHT * succ
            )

    reverse_gold = {node: i for i, node in enumerate(gold_ids)}
    reverse_generated = {node: j for j, node in enumerate(generated_ids)}
    assignments = []
    accepted_mapping = {}
    for gold_id in gold_ids:
        if gold_id not in mapping:
            continue
        generated_id = mapping[gold_id]
        i, j = reverse_gold[gold_id], reverse_generated[generated_id]
        policy = policies[(i, j)]
        fallback = "TYPE_PLUS_CONTEXT" in policy or policy == "EVENT_CONTEXT_CONFIRMED_BELOW_THRESHOLD"
        final_score = float(refined[i, j])
        accepted = (
            final_score >= NODE_MATCH_CONTEXT_FALLBACK_THRESHOLD
            if fallback else np.isfinite(semantic[i, j]) and semantic[i, j] >= threshold
        )
        if not accepted:
            continue
        match_id = f"M{len(assignments) + 1:03d}"
        pred = _neighbor_consistency(
            gold_graph, generated_graph, gold_id, generated_id,
            mapping, "predecessor",
        )
        succ = _neighbor_consistency(
            gold_graph, generated_graph, gold_id, generated_id,
            mapping, "successor",
        )
        margin = ambiguity_margin(refined, allowed, i, j)
        # Margins are diagnostic only; eligible Hungarian assignments are retained.
        accepted_mapping[gold_id] = generated_id
        assignments.append({
            "match_id": match_id,
            "matching_status": "accepted",
            "alternative_margin": margin,
            "gold_index": i,
            "gold_id": gold_id,
            "gold_type": gold_graph.nodes[gold_id]["type"],
            "gold_label": _display_label(gold_graph, gold_id),
            "generated_index": j,
            "generated_id": generated_id,
            "generated_type": generated_graph.nodes[generated_id]["type"],
            "generated_label": _display_label(generated_graph, generated_id),
            "category": comparison_category(gold_graph.nodes[gold_id]["type"]),
            "matching_basis": policy,
            "semantic_cosine": (
                "" if not np.isfinite(semantic[i, j])
                else round(float(semantic[i, j]), ROUND_DIGITS)
            ),
            "initial_local_context": round(float(local_context[i, j]), ROUND_DIGITS),
            "matched_predecessor_consistency": round(pred, ROUND_DIGITS),
            "matched_successor_consistency": round(succ, ROUND_DIGITS),
            "final_matching_score": round(final_score, ROUND_DIGITS),
            "accepted": True,
            "human_check": "",
            "human_comment": "",
        })

    assigned_gold = set(accepted_mapping)
    assigned_generated = set(accepted_mapping.values())
    unmatched = []
    for side, ids, graph, assigned in (
        ("gold", gold_ids, gold_graph, assigned_gold),
        ("generated", generated_ids, generated_graph, assigned_generated),
    ):
        for index, node_id in enumerate(ids):
            if node_id in assigned:
                continue
            data = graph.nodes[node_id]
            unmatched.append({
                "side": side,
                "index": index,
                "id": node_id,
                "type": data["type"],
                "category": comparison_category(data["type"]),
                "label": _display_label(graph, node_id),
                "reason": "NO_ACCEPTED_SEMANTIC_CONTEXTUAL_MATCH",
                "human_check": "",
                "human_comment": "",
            })

    cell_details = []
    final_display = []
    semantic_display = []
    local_display = []
    for i, gold_id in enumerate(gold_ids):
        final_row, semantic_row, local_row = [], [], []
        for j, generated_id in enumerate(generated_ids):
            semantic_value = semantic[i, j]
            final_row.append(
                round(float(refined[i, j]), ROUND_DIGITS)
                if allowed[i, j] else f"N/A_{policies[(i, j)]}"
            )
            semantic_row.append(
                round(float(semantic_value), ROUND_DIGITS)
                if np.isfinite(semantic_value) else "N/A_NO_COSINE"
            )
            local_row.append(round(float(local_context[i, j]), ROUND_DIGITS))
            pred = _neighbor_consistency(
                gold_graph, generated_graph, gold_id, generated_id,
                mapping, "predecessor",
            ) if allowed[i, j] else None
            succ = _neighbor_consistency(
                gold_graph, generated_graph, gold_id, generated_id,
                mapping, "successor",
            ) if allowed[i, j] else None
            cell_details.append({
                "gold_index": i,
                "gold_id": gold_id,
                "gold_label": _display_label(gold_graph, gold_id),
                "generated_index": j,
                "generated_id": generated_id,
                "generated_label": _display_label(generated_graph, generated_id),
                "candidate_policy": policies[(i, j)],
                "semantic_cosine": (
                    "" if not np.isfinite(semantic_value)
                    else round(float(semantic_value), ROUND_DIGITS)
                ),
                "local_context_score": round(float(local_context[i, j]), ROUND_DIGITS),
                **{
                    key: round(value, ROUND_DIGITS)
                    for key, value in local_parts[(i, j)].items()
                },
                "matched_predecessor_consistency": (
                    "" if pred is None else round(pred, ROUND_DIGITS)
                ),
                "matched_successor_consistency": (
                    "" if succ is None else round(succ, ROUND_DIGITS)
                ),
                "final_matching_score": (
                    "" if not allowed[i, j]
                    else round(float(refined[i, j]), ROUND_DIGITS)
                ),
            })
        final_display.append(final_row)
        semantic_display.append(semantic_row)
        local_display.append(local_row)

    denominator = max(len(gold_ids), len(generated_ids))
    coverage = len(accepted_mapping) / denominator if denominator else None
    result = {
        "method": "semantic Hungarian with local context and iterative predecessor/successor refinement",
        "threshold": threshold,
        "assignment_version": "partial-v2",
        "event_context_recovery": recovered_events,
        "ambiguity_margin": None,
        "assignment_acceptance_policy": "eligible_hungarian_no_margin_veto",
        "process_anchor_guard": {"version": 1, "minimum_support": 2, "minimum_share": 0.75, "consensus": process_consensus},
        "iterations": iterations,
        "weights": {
            "initial_semantic": NODE_MATCH_INITIAL_SEMANTIC_WEIGHT,
            "initial_local_context": NODE_MATCH_INITIAL_CONTEXT_WEIGHT,
            "refined_base": NODE_MATCH_BASE_WEIGHT,
            "refined_predecessor": NODE_MATCH_PREDECESSOR_WEIGHT,
            "refined_successor": NODE_MATCH_SUCCESSOR_WEIGHT,
        },
        "gold_items": [_item(gold_graph, node) for node in gold_ids],
        "generated_items": [_item(generated_graph, node) for node in generated_ids],
        "semantic_matrix": semantic_display,
        "local_context_matrix": local_display,
        "final_matching_matrix": final_display,
        "cell_details": cell_details,
        "assignments": assignments,
        "unmatched": unmatched,
        "gold_node_count": len(gold_ids),
        "generated_node_count": len(generated_ids),
        "matched_node_count": len(accepted_mapping),
        "ambiguous_proposal_count": sum(not row["accepted"] for row in assignments),
        "coverage_denominator": denominator,
        "alignment_coverage": None if coverage is None else round(coverage, ROUND_DIGITS),
        "note": (
            "Terminal events require compatible scope kinds and, when available, "
            "supporting nearby activity semantics. Labels establish semantic identity. Predecessor/successor context "
            "confirms and disambiguates it. Shared IDs are then reused by "
            "connection and order metrics without re-scoring labels."
        ),
    }
    trace(
        "alignment",
        f"mapped={len(assignments)} unmatched={len(unmatched)} "
        f"coverage={result['alignment_coverage']} iterations={iterations}",
    )
    return result


def mapping_dict(result):
    return {row["gold_id"]: row["generated_id"] for row in result["assignments"] if row.get("accepted", True)}


def match_id_dict(result, side):
    key = "gold_id" if side == "gold" else "generated_id"
    return {row[key]: row["match_id"] for row in result["assignments"] if row.get("accepted", True)}


def export_semantic_contextual_alignment(result, folder):
    write_matrix_csv(
        result["semantic_matrix"], result["gold_items"], result["generated_items"],
        folder / "38_node_matching_semantic_matrix.csv",
    )
    write_matrix_csv(
        result["local_context_matrix"], result["gold_items"], result["generated_items"],
        folder / "38_node_matching_local_context_matrix.csv",
    )
    write_matrix_csv(
        result["final_matching_matrix"], result["gold_items"], result["generated_items"],
        folder / "38_node_matching_final_matrix.csv",
        footer_rows=[{
            "label": "MATCHING_COVERAGE",
            "value": result["alignment_coverage"],
            "formula": "accepted shared IDs / max(Gold nodes, Generated nodes)",
        }],
    )
    write_rows_csv(result["cell_details"], folder / "38_node_matching_cell_details.csv")
    write_rows_csv(result["assignments"], folder / "39_node_matching_assignments.csv")
    write_rows_csv(result["unmatched"], folder / "39_node_matching_unmatched.csv")
    write_rows_csv([{
        "method": result["method"],
        "semantic_threshold": result["threshold"],
        "iterations": result["iterations"],
        "gold_node_count": result["gold_node_count"],
        "generated_node_count": result["generated_node_count"],
        "matched_node_count": result["matched_node_count"],
        "coverage_denominator": result["coverage_denominator"],
        "alignment_coverage": result["alignment_coverage"],
        "note": result["note"],
    }], folder / "39_node_matching_summary.csv")
    write_json(result, folder / "39_node_matching_result.json")


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
    result = compute_semantic_contextual_alignment(
        gold, generated, semantic["families"]["nodes"],
    )
    folder = OUTPUT_DIR / f"semantic_contextual_alignment_{generator}_{pair['id']}"
    export_semantic_contextual_alignment(result, folder)
    return result


if __name__ == "__main__":      # python <module>.py <id> <generated.json>
    import sys
    run_test(*sys.argv[1:2], generated_path=(sys.argv[2] if len(sys.argv) > 2 else None))
