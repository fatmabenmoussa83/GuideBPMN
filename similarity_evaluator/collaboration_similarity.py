"""Collaboration relations after semantic-contextual flow-node alignment.

Pools and lanes are aligned from mapped membership context. MessageFlow
direction is then compared without re-scoring endpoint labels.
"""

from collections import Counter

import numpy as np
from partial_assignment import partial_assignment

from config import OUTPUT_DIR, ROUND_DIGITS, SIMILARITY_THRESHOLD
from dataset_io import load_pair, write_json, write_rows_csv
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


def _pool_members(graph, pool_id):
    process_ref = graph.graph.get("participants", {}).get(pool_id, {}).get("process_ref")
    return {node for node, data in graph.nodes(data=True)
            if process_ref and data.get("process_id") == process_ref}


def _lane_members(graph, lane_id):
    return set(graph.graph.get("lanes", {}).get(lane_id, {}).get("flow_node_refs", []))


def _mapped_jaccard(gold_members, generated_members, node_mapping):
    projected = {node_mapping[node] for node in gold_members if node in node_mapping}
    if not projected and not generated_members:
        return 0.0
    if not projected or not generated_members:
        return 0.0
    return len(projected & generated_members) / len(projected | generated_members)


def _container_label(graph, graph_key, container_id):
    return (graph.graph.get(graph_key, {}).get(container_id, {}) or {}).get("name", "") or ""


def _normalised(text):
    return " ".join(str(text).strip().casefold().split())


def build_collaboration_mapping(gold_graph, generated_graph, node_mapping, model=None):
    """Map pools and lanes from their already matched member identities.

    Containers WITHOUT flow-node members (black-box pools such as "Customer",
    or empty lanes) can never obtain a member overlap, so they fall back to
    label identity: exact normalised label equality, or, when an embedding
    model is available, cosine similarity above SIMILARITY_THRESHOLD. Without
    this fallback a correctly reproduced black-box pool and every one of its
    message flows is wrongly counted missing AND extra (observed on dataset
    examples 23 and 38 compared with themselves: 0.38 / 0.68 instead of 1.0).
    """
    mapping, sources, audit = {}, {}, []
    for kind, graph_key, member_function in (
        ("pool", "participants", _pool_members),
        ("lane", "lanes", _lane_members),
    ):
        gold_ids = list(gold_graph.graph.get(graph_key, {}))
        generated_ids = list(generated_graph.graph.get(graph_key, {}))
        if not gold_ids or not generated_ids:
            continue
        matrix = np.zeros((len(gold_ids), len(generated_ids)), dtype=float)
        for i, gold_id in enumerate(gold_ids):
            for j, generated_id in enumerate(generated_ids):
                matrix[i, j] = _mapped_jaccard(
                    member_function(gold_graph, gold_id),
                    member_function(generated_graph, generated_id),
                    node_mapping,
                )
        # A positive overlap is required; disjoint MEMBERED pools stay unmatched.
        for row, column in partial_assignment(matrix, matrix > 0.0, floor=0.0):
            i, j = int(row), int(column)
            gold_id, generated_id = gold_ids[i], generated_ids[j]
            mapping[gold_id] = generated_id
            sources[gold_id] = "semantic_member_context_hungarian"
            audit.append({
                "kind": kind, "gold_id": gold_id,
                "generated_id": generated_id,
                "mapping_source": sources[gold_id],
                "mapping_score": round(float(matrix[i, j]), ROUND_DIGITS),
                "uses_labels": False,
                "uses_semantic_similarity": True,
                "uses_ged": False,
                "human_check": "", "human_comment": "",
            })

        # Fallback: memberless (black-box / empty) containers matched by label.
        leftover_gold = [
            g for g in gold_ids
            if g not in mapping and not member_function(gold_graph, g)
        ]
        taken = set(mapping.values())
        leftover_generated = [
            g for g in generated_ids
            if g not in taken and not member_function(generated_graph, g)
        ]
        if not leftover_gold or not leftover_generated:
            continue
        gold_labels = [_container_label(gold_graph, graph_key, g) for g in leftover_gold]
        generated_labels = [
            _container_label(generated_graph, graph_key, g) for g in leftover_generated
        ]
        label_matrix = np.zeros((len(leftover_gold), len(leftover_generated)), dtype=float)
        for i, gl in enumerate(gold_labels):
            for j, pl in enumerate(generated_labels):
                if gl.strip() and pl.strip() and _normalised(gl) == _normalised(pl):
                    label_matrix[i, j] = 1.0
        if model is not None and any(
            not label_matrix[i].any() and gold_labels[i].strip() for i in range(len(leftover_gold))
        ):
            texts = gold_labels + generated_labels
            vectors = np.asarray(model.encode(
                texts, normalize_embeddings=True, show_progress_bar=False,
            ), dtype=float)
            gv, pv = vectors[:len(gold_labels)], vectors[len(gold_labels):]
            cosine = np.clip(gv @ pv.T, -1.0, 1.0)
            for i, gl in enumerate(gold_labels):
                for j, pl in enumerate(generated_labels):
                    if label_matrix[i, j] == 0.0 and gl.strip() and pl.strip():
                        label_matrix[i, j] = float(cosine[i, j])
        permitted = label_matrix >= SIMILARITY_THRESHOLD
        for row, column in partial_assignment(label_matrix, permitted,
                                              floor=SIMILARITY_THRESHOLD):
            i, j = int(row), int(column)
            gold_id, generated_id = leftover_gold[i], leftover_generated[j]
            mapping[gold_id] = generated_id
            sources[gold_id] = "memberless_label_fallback"
            audit.append({
                "kind": kind, "gold_id": gold_id,
                "generated_id": generated_id,
                "mapping_source": sources[gold_id],
                "mapping_score": round(float(label_matrix[i, j]), ROUND_DIGITS),
                "uses_labels": True,
                "uses_semantic_similarity": label_matrix[i, j] < 1.0,
                "uses_ged": False,
                "human_check": "", "human_comment": "",
            })
    return mapping, sources, audit


def extract_collaboration_relations(graph):
    """Return typed existence, containment, membership and message relations."""
    relations = []
    participants = graph.graph.get("participants", {})
    lanes = graph.graph.get("lanes", {})
    for pool_id in participants:
        relations.append(("pool_exists", pool_id, ""))
    for lane_id, lane in lanes.items():
        relations.append(("lane_exists", lane_id, ""))
        process_id = lane.get("process_id")
        owner = next((pool_id for pool_id, pool in participants.items()
                      if pool.get("process_ref") == process_id), "")
        if owner:
            relations.append(("lane_in_pool", lane_id, owner))
        for node_id in lane.get("flow_node_refs", []):
            relations.append(("node_in_lane", node_id, lane_id))
    for flow in graph.graph.get("message_flows", []):
        relations.append(("message_flow", flow["source"], flow["target"]))
    return relations


def _project_relation(relation, complete_mapping):
    kind, source, target = relation
    projected_source = complete_mapping.get(source)
    if not projected_source:
        return None
    if not target:
        return kind, projected_source, ""
    projected_target = complete_mapping.get(target)
    return (kind, projected_source, projected_target) if projected_target else None


def _relation_row(side, relation):
    kind, source, target = relation
    return {"side": side, "relation_type": kind, "source": source, "target": target}


def compute_collaboration_similarity(gold_graph, generated_graph, node_mapping, model=None):
    """Compare relations after semantic identities have been established."""
    section("collab", "pools, lanes, memberships and directed messageFlow")
    container_mapping, _, mapping_audit = build_collaboration_mapping(
        gold_graph, generated_graph, node_mapping, model=model,
    )
    complete_mapping = {**node_mapping, **container_mapping}
    gold_relations = extract_collaboration_relations(gold_graph)
    generated_relations = extract_collaboration_relations(generated_graph)
    remaining = Counter(generated_relations)
    comparison = []
    tp = fn = 0
    for relation in gold_relations:
        projected = _project_relation(relation, complete_mapping)
        if projected is not None and remaining[projected] > 0:
            remaining[projected] -= 1
            status = "matched"; tp += 1
        else:
            status = "missing"
            if projected and relation[0] == "message_flow":
                reversed_relation = (projected[0], projected[2], projected[1])
                if remaining[reversed_relation] > 0:
                    status = "reversed"
            fn += 1
        comparison.append({
            "status": status,
            "gold_relation_type": relation[0],
            "gold_source": relation[1], "gold_target": relation[2],
            "projected_generated_relation_type": projected[0] if projected else "",
            "projected_generated_source": projected[1] if projected else "",
            "projected_generated_target": projected[2] if projected else "",
            "human_check": "", "human_comment": "",
        })
    extras = []
    for relation, count in remaining.items():
        for _ in range(count):
            extras.append(relation)
            comparison.append({
                "status": "extra",
                "gold_relation_type": "", "gold_source": "", "gold_target": "",
                "projected_generated_relation_type": relation[0],
                "projected_generated_source": relation[1],
                "projected_generated_target": relation[2],
                "human_check": "", "human_comment": "",
            })
    fp = len(extras)
    applicable = bool(gold_relations or generated_relations)
    denominator = tp + fp + fn
    score = tp / denominator if denominator else None
    result = {
        "applicable": applicable,
        "independence": {
            "uses_labels": False,
            "memberless_label_fallback": any(
                row.get("mapping_source") == "memberless_label_fallback"
                for row in mapping_audit
            ),
            "uses_semantic_similarity": True,
            "uses_ged": False,
        },
        "container_mapping": mapping_audit,
        "role_identity_diagnostics": (__import__("role_identity").compare_role_identity(
            gold_graph, generated_graph, node_mapping, model) if model is not None else []),
        "partition_diagnostics": participant_partition_diagnostics(gold_graph, generated_graph, node_mapping),
        "gold_relations": [_relation_row("gold", relation) for relation in gold_relations],
        "generated_relations": [
            _relation_row("generated", relation) for relation in generated_relations
        ],
        "relation_comparison": comparison,
        "tp": tp, "fp": fp, "fn": fn,
        "structural_similarity": None if score is None else round(score, ROUND_DIGITS),
        "formula": "TP / (TP + FP + FN) over collaboration relations",
        "included_relations": (
            "pool_exists; lane_exists; lane_in_pool; node_in_lane; directed message_flow"
        ),
    }
    trace("collab", f"applicable={applicable} TP={tp} FP={fp} FN={fn} structure={result['structural_similarity']}")
    return result


def export_collaboration(result, folder):
    """Export exact inputs, mappings, comparison decisions and summary."""
    write_rows_csv(
        result["container_mapping"], folder / "50_collaboration_container_mapping.csv",
        ["kind", "gold_id", "generated_id", "mapping_source", "mapping_score",
         "uses_labels", "uses_semantic_similarity", "uses_ged",
         "human_check", "human_comment"],
    )
    write_json(result.get("partition_diagnostics", []), folder / "55_collaboration_partition_diagnostics.json")
    write_json(result.get("role_identity_diagnostics", []), folder / "56_collaboration_role_identity.json")
    relation_fields = ["side", "relation_type", "source", "target"]
    write_rows_csv(result["gold_relations"], folder / "51_collaboration_input_gold_relations.csv",
                   relation_fields)
    write_rows_csv(result["generated_relations"], folder / "52_collaboration_input_generated_relations.csv",
                   relation_fields)
    write_rows_csv(
        result["relation_comparison"], folder / "53_collaboration_relation_comparison.csv",
        ["status", "gold_relation_type", "gold_source", "gold_target",
         "projected_generated_relation_type", "projected_generated_source",
         "projected_generated_target", "human_check", "human_comment"],
    )
    write_rows_csv([{
        "applicable": result["applicable"],
        "uses_labels": result["independence"]["uses_labels"],
        "uses_semantic_similarity": result["independence"]["uses_semantic_similarity"],
        "uses_ged": result["independence"]["uses_ged"],
        "tp": result["tp"], "fp": result["fp"], "fn": result["fn"],
        "structural_similarity": result["structural_similarity"],
        "formula": result["formula"],
        "included_relations": result["included_relations"],
    }], folder / "54_collaboration_summary.csv")


TEST_ID = "24"
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
    node_mapping = mapping_dict(alignment)
    result = compute_collaboration_similarity(gold, generated, node_mapping)
    folder = OUTPUT_DIR / f"collaboration_{generator}_{pair['id']}"
    export_semantic_contextual_alignment(alignment, folder)
    export_collaboration(result, folder)
    write_json(result, folder / "collaboration_result.json")
    return result


if __name__ == "__main__":      # python <module>.py <id> <generated.json>
    import sys
    run_test(*sys.argv[1:2], generated_path=(sys.argv[2] if len(sys.argv) > 2 else None))


def participant_partition_diagnostics(gold_graph, generated_graph, node_mapping):
    """Explain merged/split responsibility from accepted member matches.

    These are partition differences from the reference, not extra penalty units.
    Empty/black-box participants provide no member evidence and remain unknown.
    """
    gold_members = {p: _pool_members(gold_graph, p) for p in gold_graph.graph.get("participants", {})}
    generated_members = {p: _pool_members(generated_graph, p) for p in generated_graph.graph.get("participants", {})}
    links = []
    for left, members in gold_members.items():
        for right, targets in generated_members.items():
            anchors = [(g, node_mapping[g]) for g in members if g in node_mapping and node_mapping[g] in targets]
            if anchors:
                links.append({"gold_pool": left, "generated_pool": right, "anchors": sorted(anchors)})
    rows = []
    for side, key, other in (("generated", "generated_pool", "gold_pool"), ("gold", "gold_pool", "generated_pool")):
        ids = generated_members if side == "generated" else gold_members
        for pool in ids:
            group = [row for row in links if row[key] == pool]
            if len(group) > 1:
                rows.append({"kind": "merged_reference_pools" if side == "generated" else "split_reference_pool",
                    "pool_id": pool, "counterpart_pool_ids": [row[other] for row in group],
                    "member_evidence": group, "interpretation": "Reference partition differs; verify XML ownership before correction."})
    return rows
