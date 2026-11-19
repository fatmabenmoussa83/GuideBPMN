"""Grouped type comparison for the BPMN element inventory.

This is deliberately the FIRST and simplest comparison in the pipeline -- it
does not look at names or embeddings at all, only at type counts. It is a
cheap sanity check before anything semantic happens.

Only BPMN task specializations are collapsed to ``task`` because the Gold data
usually uses generic ``task`` while generators may produce ``userTask``,
``serviceTask``, etc. Gateways, events, subprocesses, and call activities keep
their exact type because those distinctions carry structural meaning.
"""

import json
from collections import Counter
from config import TASK_LIKE_TAGS
from trace import trace, section, trace_table


def normalize_type(tag: str) -> str:
    """Collapses task subtypes to 'task'; every other tag is returned unchanged
    (kept at its exact granularity)."""
    return "task" if tag in TASK_LIKE_TAGS else tag


def type_histogram(graph) -> Counter:
    """Count nodes after applying the official grouped-task normalization."""
    return Counter(normalize_type(d["type"]) for _, d in graph.nodes(data=True))


def _compute(gold_hist: Counter, gen_hist: Counter, label: str, variant: str):
    """Shared core: count-based matching per type, same principle already
    validated for gateways -- TP_type = min(gold_count, gen_count). No
    identity here, just 'did the right NUMBER of each type get produced'."""
    section("typematch", f"type matching ({variant}) {label}")

    all_types = sorted(set(gold_hist) | set(gen_hist))
    per_type = {}
    total_tp, total_fp, total_fn = 0, 0, 0
    rows = []
    for t in all_types:
        g_count, a_count = gold_hist.get(t, 0), gen_hist.get(t, 0)
        tp = min(g_count, a_count)
        fn = max(0, g_count - a_count)   # gold had more of this type -> missed
        fp = max(0, a_count - g_count)   # generated had more -> invented
        per_type[t] = {"gold_count": g_count, "gen_count": a_count,
                        "tp": tp, "fp": fp, "fn": fn}
        total_tp += tp; total_fp += fp; total_fn += fn
        rows.append((t, g_count, a_count, tp, fp, fn))

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    trace_table("typematch", rows, headers=["type", "gold_n", "gen_n", "TP", "FP", "FN"])
    trace("typematch", f"TOTAL  TP={total_tp}  FP={total_fp}  FN={total_fn}")
    trace("typematch", f"Precision={precision:.4f}  Recall={recall:.4f}  F1={f1:.4f}")

    return {"variant": variant, "per_type": per_type,
            "tp": total_tp, "fp": total_fp, "fn": total_fn,
            "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


def compute_type_precision_recall_grouped(g_gold, g_gen, label: str = ""):
    """Task subtypes collapsed to 'task'; gateways/events kept exact.
    This is the variant that should feed the rest of the pipeline."""
    return _compute(type_histogram(g_gold), type_histogram(g_gen), label, "grouped")


def export_type_matching_json(result: dict, out_path: str, entry_id: str = ""):
    """Writes the FULL detail of a type-matching result to a JSON file --
    every type, its gold/gen counts, and its own TP/FP/FN. Not just the totals.

    WHY this level of detail: the totals alone (tp=10, fp=0, fn=6) hide WHICH
    types are responsible. This file lets you open it and immediately see
    "gold expected 2 parallelGateway, generated produced 0" -- which is exactly
    the kind of specific fact a corrective rule needs to be built from.
    """
    per_type_rows = []
    for t, d in sorted(result["per_type"].items()):
        per_type_rows.append({
            "type": t,
            "gold_count": d["gold_count"],
            "gen_count": d["gen_count"],
            "tp": d["tp"],
            "fp": d["fp"],
            "fn": d["fn"],
        })

    output = {
        "id": entry_id,
        "variant": result["variant"],
        "per_type": per_type_rows,
        "totals": {
            "tp": result["tp"],
            "fp": result["fp"],
            "fn": result["fn"],
            "precision": result["precision"],
            "recall": result["recall"],
            "f1": result["f1"],
        },
        "types_with_tp": [r for r in per_type_rows if r["tp"] > 0],
        "types_with_fp": [r for r in per_type_rows if r["fp"] > 0],
        "types_with_fn": [r for r in per_type_rows if r["fn"] > 0],
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    trace("typematch", f"written -> {out_path}")
    return output


# Standalone test: change only these values.
TEST_ID = "01"
TEST_GENERATOR = "gpt"


def run_test(test_id=TEST_ID, generator=TEST_GENERATOR, generated_path=None):
    from config import OUTPUT_DIR
    from dataset_io import load_pair, write_json
    from graph_loader import load_bpmn_graph_from_string
    pair = load_pair(test_id, generator, generated_path=generated_path)
    gold = load_bpmn_graph_from_string(pair["gold_xml"], f"gold-{pair['id']}")
    gen = load_bpmn_graph_from_string(pair["generated_xml"], f"{generator}-{pair['id']}")
    grouped = compute_type_precision_recall_grouped(gold, gen, pair["id"])
    result = {"id": pair["id"], "generator": generator,
              "grouped_type_similarity": grouped}
    path = write_json(result, OUTPUT_DIR / f"type_matching_{generator}_{pair['id']}.json")
    trace("typematch", f"written -> {path}")
    return result


if __name__ == "__main__":      # python <module>.py <id> <generated.json>
    import sys
    run_test(*sys.argv[1:2], generated_path=(sys.argv[2] if len(sys.argv) > 2 else None))
