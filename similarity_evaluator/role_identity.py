"""Cross-kind role identity; BPMN representation remains a separate diagnostic."""
import numpy as np
from config import SIMILARITY_THRESHOLD, NODE_MATCH_CONTEXT_FALLBACK_THRESHOLD
from partial_assignment import partial_assignment, ambiguity_margin


def role_items(graph):
    items = []
    for key, kind in (("participants", "pool"), ("lanes", "lane")):
        for identity, data in graph.graph.get(key, {}).items():
            process = data.get("process_ref") if kind == "pool" else data.get("process_id")
            members = ({n for n, d in graph.nodes(data=True) if process and d.get("process_id") == process}
                       if kind == "pool" else set(data.get("flow_node_refs", [])))
            items.append(dict(id=identity, kind=kind, label=data.get("name", ""),
                              process_id=process, members=members))
    return items


def compare_role_identity(gold, generated, node_mapping, model):
    """Match labels across pools/lanes, refine by members, then report type differences.

    This diagnostic does not equate a lane with a participant, change structural
    scores, or directly modify BPMN. Ambiguous identities require investigation.
    """
    left, right = role_items(gold), role_items(generated)
    named_left = [x for x in left if x["label"].strip()]
    named_right = [x for x in right if x["label"].strip()]
    rows = []
    matched_left, matched_right = set(), set()
    if named_left and named_right:
        def encode(items):
            return np.asarray(model.encode([x["label"] for x in items],
                normalize_embeddings=True, show_progress_bar=False), dtype=float)
        cosines = np.clip(encode(named_left) @ encode(named_right).T, -1, 1)
        scores = cosines.copy()
        overlap = np.zeros_like(scores)
        support = np.zeros_like(scores)
        for i, a in enumerate(named_left):
            projected = {node_mapping[n] for n in a["members"] if n in node_mapping}
            for j, b in enumerate(named_right):
                support[i,j] = len(projected & b["members"])
                union = projected | b["members"]
                overlap[i,j] = len(projected & b["members"]) / len(union) if union else 0
                if projected and b["members"]:
                    scores[i,j] = .9 * cosines[i,j] + .1 * overlap[i,j]
        allowed = ((cosines >= SIMILARITY_THRESHOLD) |
                   ((cosines >= NODE_MATCH_CONTEXT_FALLBACK_THRESHOLD) &
                    (support >= 2) & (overlap >= .5)))
        for i,j in partial_assignment(scores, allowed, floor=0):
            a,b = named_left[i],named_right[j]
            margin = ambiguity_margin(scores,allowed,i,j)
            # Score gaps remain observable but do not veto the assignment.
            ambiguous = False
            matched_left.add(a["id"]); matched_right.add(b["id"])
            rows.append(dict(kind="role_identity", gold_id=a["id"], generated_id=b["id"],
                gold_label=a["label"], generated_label=b["label"],
                gold_type=a["kind"], generated_type=b["kind"],
                gold_process_id=a["process_id"], generated_process_id=b["process_id"],
                matching_basis="label" if cosines[i,j] >= SIMILARITY_THRESHOLD else "label_with_member_anchors",
                anchor_count=int(support[i,j]), semantic_cosine=round(float(cosines[i,j]),6), member_overlap=round(float(overlap[i,j]),6),
                score=round(float(scores[i,j]),6), alternative_margin=margin,
                status="ambiguous" if ambiguous else "accepted",
                representation_difference=(a["kind"] != b["kind"]),
                interpretation="Investigate identity" if ambiguous else (
                    "Same role candidate; BPMN representation differs from reference" if a["kind"] != b["kind"]
                    else "Same role candidate and same container type")))
    for side, items, matched in (("gold",left,matched_left),("generated",right,matched_right)):
        for item in items:
            if item["id"] not in matched:
                rows.append(dict(kind="unmatched_role", side=side, id=item["id"],
                    label=item["label"], container_type=item["kind"], status="unmatched"))
    return rows
