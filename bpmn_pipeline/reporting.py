"""Aggregate metric reporting over a set of evaluated examples.

For every numeric metric: n, mean, std (population), min, q1, median, q3, max.
For the validator: overall validity rate, per-level pass rates and failure
counts. Types and connections carry true precision/recall (computed against
the gold diagram); order and collaboration get precision/recall derived from
their TP/FP/FN counts. The validator itself has no precision/recall - that
would need a labelled ground truth of true defects - so its block reports
rates, plus the gold sanity check (a flagged gold diagram would be a false
positive).
"""
import json
import statistics
from pathlib import Path

METRIC_KEYS = [
    "semantic_similarity", "activity_semantic_similarity",
    "activity_label_precision", "activity_label_recall", "activity_label_f1",
    "alignment_coverage",
    "connection_precision", "connection_recall", "connection_f1",
    "workflow_order_similarity", "order_consistency", "order_coverage",
    "order_precision", "order_recall",
    "collaboration_similarity", "collaboration_precision", "collaboration_recall",
    "type_precision_diagnostic", "type_recall_diagnostic", "type_f1_diagnostic",
    # strict values: the generated pools, lanes and message flows counted even
    # when the reference has no collaboration (see evaluation.py)
    "semantic_similarity_strict", "connection_f1_strict", "collaboration_similarity_strict",
]


def _stats(values: list[float]) -> dict:
    vals = [v for v in values if v is not None]
    if not vals:
        return {"n": 0}
    out = {"n": len(vals), "mean": statistics.fmean(vals),
           "std": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
           "min": min(vals), "max": max(vals),
           "median": statistics.median(vals)}
    if len(vals) >= 4:
        q = statistics.quantiles(vals, n=4)
        out["q1"], out["q3"] = q[0], q[2]
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in out.items()}


def derive_pr(row: dict) -> dict:
    """Add precision/recall derived from TP/FP/FN where only counts exist."""
    out = dict(row)
    for prefix in ("order", "collaboration"):
        tp = row.get(f"{prefix}_tp"); fp = row.get(f"{prefix}_fp"); fn = row.get(f"{prefix}_fn")
        if tp is None:
            continue
        out[f"{prefix}_precision"] = (tp / (tp + fp)) if (tp + fp) else None
        out[f"{prefix}_recall"] = (tp / (tp + fn)) if (tp + fn) else None
    return out


def aggregate(rows: list[dict]) -> dict:
    rows = [derive_pr(r) for r in rows]
    report = {"examples": len(rows), "metrics": {}}
    for key in METRIC_KEYS:
        report["metrics"][key] = _stats([r.get(key) for r in rows])
    # Validator block.
    levels = ("L1", "L2", "L3", "L4")
    valid = [bool(r.get("valid")) for r in rows if r.get("valid") is not None]
    block = {"overall_valid_rate": round(sum(valid) / len(valid), 4) if valid else None,
             "valid_count": sum(valid), "total": len(valid)}
    for level in levels:
        fails = [r for r in rows if level in (r.get("failed_levels") or [])]
        block[f"{level}_pass_rate"] = (round(1 - len(fails) / len(rows), 4)
                                        if rows else None)
        block[f"{level}_failures"] = len(fails)
    report["validator"] = block
    report["note"] = ("Types precision/recall compare grouped element histograms "
                      "against gold (composition diagnostic). The validator block "
                      "reports rates, not precision/recall: those would require a "
                      "labelled ground truth of true defects.")
    return report


def write_report(rows: list[dict], folder: Path, label: str) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    report = aggregate(rows)
    (folder / f"report_{label}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    # per-example CSV
    rows_pr = [derive_pr(r) for r in rows]
    cols = ["id", "valid", "failed_levels"] + METRIC_KEYS
    lines = [",".join(cols)]
    for r in rows_pr:
        cells = []
        for c in cols:
            v = r.get(c)
            if isinstance(v, list):
                v = "|".join(map(str, v))
            cells.append("" if v is None else str(v))
        lines.append(",".join(cells))
    (folder / f"per_example_{label}.csv").write_text("\n".join(lines) + "\n",
                                                     encoding="utf-8")
    return report
