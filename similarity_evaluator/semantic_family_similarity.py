"""Auditable cosine similarity for BPMN nodes, connections and collaboration.

This module measures semantic text only. Structural correctness remains in
TypeSim, WorkflowSim, CollaborationSim and GED. Every BPMN element is exported;
an element without usable text remains visible with an explicit N/A cell.
"""

import numpy as np
from partial_assignment import partial_assignment, ambiguity_margin

from config import EMBEDDING_MODEL, OUTPUT_DIR, ROUND_DIGITS, SIMILARITY_THRESHOLD
from dataset_io import load_pair, write_json, write_matrix_csv, write_rows_csv
from elements import semantic_category
from graph_loader import load_bpmn_graph_from_string
from trace import section, trace


def load_embedding_model(model_name=EMBEDDING_MODEL):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("Install dependencies with: pip install -r requirements.txt") from exc
    trace("embedding", f"loading model: {model_name}")
    return SentenceTransformer(model_name)


def extract_node_semantic_items(graph):
    """All flow nodes; only genuine BPMN names are embedded."""
    return [{
        "id": node_id,
        "type": data["type"],
        "category": semantic_category(data["type"]),
        "label": data.get("name", "") if data.get("has_name") else "",
        "text": data.get("name", "") if data.get("has_name") else "",
        "has_text": bool(data.get("has_name")),
        "source": "",
        "target": "",
    } for node_id, data in graph.nodes(data=True)]


def extract_collaboration_semantic_items(graph):
    """All collaboration elements; only genuine BPMN names are embedded."""
    result = []
    for element_id, data in graph.graph.get("participants", {}).items():
        text = data.get("name", "") if data.get("has_name") else ""
        result.append({
            "id": element_id, "type": "participant", "category": "pool",
            "label": text, "text": text, "has_text": bool(text),
            "source": "", "target": "",
        })
    for element_id, data in graph.graph.get("lanes", {}).items():
        text = data.get("name", "") if data.get("has_name") else ""
        result.append({
            "id": element_id, "type": "lane", "category": "lane",
            "label": text, "text": text, "has_text": bool(text),
            "source": "", "target": "",
        })
    for flow in graph.graph.get("message_flows", []):
        # Endpoints and direction belong to CollaborationStructureSim. They are
        # deliberately not embedded here, otherwise structure is counted twice.
        text = flow.get("name", "") if flow.get("has_name") else ""
        result.append({
            "id": flow.get("id") or f"{flow['source']}->{flow['target']}",
            "type": "messageFlow", "category": "messageFlow",
            "label": text, "text": text, "has_text": bool(text),
            "source": flow["source"], "target": flow["target"],
        })
    return result


def _encode(items, model):
    positions = [i for i, item in enumerate(items) if item["has_text"]]
    if not positions:
        return positions, np.empty((0, 0), dtype=float)
    vectors = model.encode(
        [items[i]["text"] for i in positions],
        normalize_embeddings=True, show_progress_bar=False,
    )
    return positions, np.asarray(vectors, dtype=float)


def _embedding_rows(items, positions, vectors):
    """Human-auditable embedding output; one vector is stored in one CSV cell."""
    by_position = {position: vectors[i] for i, position in enumerate(positions)}
    rows = []
    for index, item in enumerate(items):
        vector = by_position.get(index)
        rows.append({
            "matrix_index": index,
            "id": item["id"],
            "type": item["type"],
            "category": item["category"],
            "input_text": item["text"],
            "has_embedding": vector is not None,
            "embedding_dimension": 0 if vector is None else len(vector),
            "embedding_vector": "" if vector is None else "[" + ", ".join(
                f"{float(value):.9f}" for value in vector
            ) + "]",
        })
    return rows


def compute_family(gold_items, generated_items, model, family,
                   threshold=SIMILARITY_THRESHOLD):
    """Full matrix + category-constrained one-to-one Hungarian assignments."""
    gold_positions, gold_vectors = _encode(gold_items, model)
    gen_positions, gen_vectors = _encode(generated_items, model)
    matrix = np.full((len(gold_items), len(generated_items)), np.nan, dtype=float)
    if gold_vectors.size and gen_vectors.size:
        local = np.clip(gold_vectors @ gen_vectors.T, -1.0, 1.0)
        for local_i, i in enumerate(gold_positions):
            for local_j, j in enumerate(gen_positions):
                if gold_items[i]["category"] == generated_items[j]["category"]:
                    matrix[i, j] = local[local_i, local_j]

    assignments, assigned_gold, assigned_gen = [], set(), set()
    contribution_sum = 0.0
    categories = sorted({x["category"] for x in gold_items + generated_items})
    denominator = 0
    for category in categories:
        gi = [i for i, x in enumerate(gold_items)
              if x["category"] == category and x["has_text"]]
        pj = [j for j, x in enumerate(generated_items)
              if x["category"] == category and x["has_text"]]
        denominator += max(len(gi), len(pj))
        if not gi or not pj:
            continue
        local = np.nan_to_num(matrix[np.ix_(gi, pj)], nan=-1.0)
        permitted = np.isfinite(local) & (local >= threshold)
        for row, col in partial_assignment(local, permitted, floor=threshold):
            i, j = gi[int(row)], pj[int(col)]
            score = float(matrix[i, j])
            margin = ambiguity_margin(local, permitted, int(row), int(col))
            accepted = True  # Below-threshold pairs never enter this table.
            contribution = score if accepted else 0.0
            contribution_sum += contribution
            assigned_gold.add(i); assigned_gen.add(j)
            assignments.append({
                "family": family, "category": category,
                "gold_index": i, "gold_id": gold_items[i]["id"],
                "gold_text": gold_items[i]["text"],
                "generated_index": j, "generated_id": generated_items[j]["id"],
                "generated_text": generated_items[j]["text"],
                "cosine_similarity": round(score, ROUND_DIGITS),
                "threshold": threshold, "accepted": accepted,
                "matching_status": "accepted",
                "alternative_margin": margin,
                "interpretation": "Reference resemblance only; neither equivalence nor a business defect is established.",
                "score_contribution": round(contribution, ROUND_DIGITS),
                "human_check": "", "human_comment": "",
            })

    unmatched = []
    for side, items, assigned in (
        ("gold", gold_items, assigned_gold),
        ("generated", generated_items, assigned_gen),
    ):
        for i, item in enumerate(items):
            if i not in assigned:
                unmatched.append({
                    "family": family, "side": side, "matrix_index": i,
                    "id": item["id"], "type": item["type"],
                    "category": item["category"], "text": item["text"],
                    "has_text": item["has_text"],
                    "reason": "NO_USABLE_TEXT" if not item["has_text"] else "NO_ACCEPTED_COUNTERPART",
                    "human_check": "", "human_comment": "",
                })

    display_matrix = []
    for i, gold in enumerate(gold_items):
        row = []
        for j, generated in enumerate(generated_items):
            if gold["category"] != generated["category"]:
                row.append("N/A_INCOMPATIBLE_TYPE")
            elif not gold["has_text"] or not generated["has_text"]:
                row.append("N/A_NO_TEXT")
            else:
                row.append(round(float(matrix[i, j]), ROUND_DIGITS))
        display_matrix.append(row)

    numeric_values = matrix[np.isfinite(matrix)]
    numeric_cell_count = int(numeric_values.size)
    numeric_cell_sum = float(numeric_values.sum()) if numeric_cell_count else 0.0
    numeric_mean = numeric_cell_sum / numeric_cell_count if numeric_cell_count else None

    applicable = denominator > 0
    score = contribution_sum / denominator if applicable else None
    return {
        "family": family, "applicable": applicable,
        "gold_items": gold_items, "generated_items": generated_items,
        "gold_embeddings": _embedding_rows(gold_items, gold_positions, gold_vectors),
        "generated_embeddings": _embedding_rows(
            generated_items, gen_positions, gen_vectors,
        ),
        "matrix": display_matrix, "assignments": assignments,
        "unmatched": unmatched, "denominator": denominator,
        "accepted_contribution_sum": round(contribution_sum, ROUND_DIGITS),
        "similarity": None if score is None else round(score, ROUND_DIGITS),
        "numeric_cell_count": numeric_cell_count,
        "numeric_cell_sum": round(numeric_cell_sum, ROUND_DIGITS),
        "matrix_numeric_mean": (
            None if numeric_mean is None else round(numeric_mean, ROUND_DIGITS)
        ),
        "matrix_numeric_mean_formula": (
            "sum(all numeric compatible cosine cells) / number of numeric cells; "
            "N/A cells are excluded"
        ),
        "formula": "sum(accepted Hungarian cosine >= tau) / sum_category max(scorable_gold, scorable_generated)",
    }


def compute_semantic_family_similarity(gold_graph, generated_graph, model=None,
                                       model_name=EMBEDDING_MODEL,
                                       threshold=SIMILARITY_THRESHOLD):
    section("semantic", "cosine matrices: nodes and applicable collaboration")
    model = model or load_embedding_model(model_name)
    # Connection labels are not embedded a second time. Connections are checked
    # afterwards from already assigned endpoint nodes and grouped endpoint types.
    builders = {
        "nodes": extract_node_semantic_items,
        "collaboration": extract_collaboration_semantic_items,
    }
    families = {
        name: compute_family(builder(gold_graph), builder(generated_graph), model, name, threshold)
        for name, builder in builders.items()
    }
    total_denominator = sum(x["denominator"] for x in families.values())
    total_contribution = sum(x["accepted_contribution_sum"] for x in families.values())
    global_score = total_contribution / total_denominator if total_denominator else None
    trace("semantic", f"global={global_score} denominator={total_denominator}")
    return {
        "model": model_name, "threshold": threshold, "families": families,
        "total_denominator": total_denominator,
        "total_accepted_contribution": round(total_contribution, ROUND_DIGITS),
        "semantic_similarity": None if global_score is None else round(global_score, ROUND_DIGITS),
        "formula": "sum of family accepted cosine contributions / sum of family denominators",
        "note": "Matrices are semantic diagnostics; structural metrics do not reuse cosine values.",
    }


def _export(result, output_dir, prefix=""):
    summary = []
    for number, name in (("33", "nodes"), ("35", "collaboration")):
        family = result["families"][name]
        stem = f"{number}_{name}_semantic"
        write_matrix_csv(family["matrix"], family["gold_items"], family["generated_items"],
                         output_dir / f"{stem}_cosine_matrix.csv",
                         footer_rows=[{
                             "label": "ARITHMETIC_NUMERIC_CELL_MEAN",
                             "value": family["matrix_numeric_mean"],
                             "formula": family["matrix_numeric_mean_formula"],
                         }, {
                             "label": "HUNGARIAN_NORMALIZED_MEAN",
                             "value": family["similarity"],
                             "formula": family["formula"],
                         }])
        write_rows_csv(family["assignments"], output_dir / f"{stem}_hungarian_assignments.csv")
        write_rows_csv(family["unmatched"], output_dir / f"{stem}_unmatched.csv")
        item_fields = ["id", "type", "category", "label", "text", "has_text",
                       "source", "target"]
        embedding_fields = ["matrix_index", "id", "type", "category", "input_text",
                            "has_embedding", "embedding_dimension", "embedding_vector"]
        write_rows_csv(family["gold_items"], output_dir / f"{stem}_input_gold.csv",
                       item_fields)
        write_rows_csv(family["generated_items"], output_dir / f"{stem}_input_generated.csv",
                       item_fields)
        write_rows_csv(family["gold_embeddings"], output_dir / f"{stem}_embeddings_gold.csv",
                       embedding_fields)
        write_rows_csv(
            family["generated_embeddings"],
            output_dir / f"{stem}_embeddings_generated.csv",
            embedding_fields,
        )
        summary.append({
            "family": name, "applicable": family["applicable"],
            "gold_count": len(family["gold_items"]),
            "generated_count": len(family["generated_items"]),
            "scorable_denominator": family["denominator"],
            "accepted_contribution_sum": family["accepted_contribution_sum"],
            "matrix_numeric_cell_count": family["numeric_cell_count"],
            "matrix_numeric_mean": family["matrix_numeric_mean"],
            "hungarian_normalized_similarity": family["similarity"],
            "formula": family["formula"],
        })
    summary.append({
        "family": "GLOBAL", "applicable": result["total_denominator"] > 0,
        "gold_count": "", "generated_count": "",
        "scorable_denominator": result["total_denominator"],
        "accepted_contribution_sum": result["total_accepted_contribution"],
        "similarity": result["semantic_similarity"], "formula": result["formula"],
    })
    write_rows_csv(summary, output_dir / "36_semantic_summary.csv")


def json_ready(result):
    return result


# Standalone test: change only these values.
TEST_ID = "01"
TEST_GENERATOR = "gpt"  # "gpt" or "claude"


def run_test(test_id=TEST_ID, generator=TEST_GENERATOR, generated_path=None):
    pair = load_pair(test_id, generator, generated_path=generated_path)
    gold = load_bpmn_graph_from_string(pair["gold_xml"], f"gold-{pair['id']}")
    generated = load_bpmn_graph_from_string(pair["generated_xml"], f"{generator}-{pair['id']}")
    result = compute_semantic_family_similarity(gold, generated)
    output_dir = OUTPUT_DIR / f"semantic_families_{generator}_{pair['id']}"
    _export(result, output_dir)
    path = write_json({"id": pair["id"], "generator": generator, **result},
                      output_dir / "semantic_family_similarity.json")
    trace("semantic", f"written -> {path}")
    return result


if __name__ == "__main__":      # python <module>.py <id> <generated.json>
    import sys
    run_test(*sys.argv[1:2], generated_path=(sys.argv[2] if len(sys.argv) > 2 else None))
