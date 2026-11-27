"""Results of the final study, for one generator model.

  First      3 runs: documentation guidelines only, no learning (--no-learn
             --next-iterations 0 --replicate 1..3), all 55 descriptions
  Revised    3 runs: learning with 3 forced next iterations (--force-iterations
             --replicate 1..3), all 55 descriptions; the model kept after
             iteration 1 (Revised i1), 2 (Revised i2) and 3 (Learned)
  Reuse      1 run: stratified 5-fold cross-validation (--fold k, training with
             --force-iterations), the 55 test descriptions together

Every value is the mean over the 55 descriptions. With 3 runs it is the mean of
the 3 run means and their SD (variability between runs); for Reuse +- the SD of
the 5 fold means. Each configuration is compared with First by a paired
Wilcoxon signed-rank test over the 55 descriptions, each taking the mean of its
runs (* : p < 0.05). Validator: precision per level, TP / (TP + FP) (correct /
checked elements) for each model, and the average of the levels that apply to
the model.

    python study_report.py --generator openai:gpt-6-luna
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from pipeline_config import RUNS_DIR
import fold_report as fr

LEVELS = ("L1", "L2", "L3", "L4")
SIM = ("activity_label_precision", "activity_label_recall", "activity_label_f1",
       "connection_precision", "connection_recall", "connection_f1",
       "workflow_order_similarity", "alignment_coverage", "collaboration_similarity")
VAL = tuple(f"precision_{l}" for l in LEVELS) + ("precision_levels_average",)
OTHER = ("errors_total", "valid")
ALL = SIM + VAL + OTHER
CONFIGS = ("First", "Revised i1", "Revised i2", "Learned", "Reuse")


def _json(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def model_values(metrics: dict, levels: dict, errors: dict, valid: bool) -> dict:
    """The measures of one model."""
    out = {k: metrics.get(k) for k in SIM}
    precisions = []
    for level in LEVELS:
        row = (levels or {}).get(level) or {}
        checked = (row.get("correct") or 0) + (row.get("incorrect") or 0)
        value = (row.get("correct") or 0) / checked if row.get("result") is not None and checked else None
        out[f"precision_{level}"] = value
        # counts kept for the precision of the level over all models (TP and FP summed, then divided)
        out[f"tp_{level}"] = (row.get("correct") or 0) if value is not None else None
        out[f"fp_{level}"] = (row.get("incorrect") or 0) if value is not None else None
        if value is not None:
            precisions.append(value)
    out["precision_levels_average"] = sum(precisions) / len(precisions) if precisions else None
    out["errors_total"] = sum(int(v or 0) for v in (errors or {}).values())
    out["valid"] = 1.0 if valid else 0.0
    return out


def first_models(run: Path) -> dict:
    """{description: values of its final model} for a run without iterations."""
    out = {}
    for folder in sorted(run.glob("id_*")):
        doc, dec = _json(folder / "iterations.json"), _json(folder / "decisions.json")
        drafts = doc.get("iterations") or []
        if not drafts or not doc.get("final_metrics"):
            continue
        kept = next((d for d in drafts if d["round"] == doc.get("kept_round")), drafts[-1])
        out[str(doc["id"])] = model_values(doc["final_metrics"], kept.get("validator_levels"),
                                           dec.get("error_counts"), kept.get("valid"))
    return out


def iteration_models(run: Path, n: int = 3) -> list[dict]:
    """[{description: values}] for the model kept after iterations 1..n. A
    description that stopped earlier (no error left, nothing to send) keeps its
    last model."""
    out = [dict() for _ in range(n)]
    for folder in sorted(run.glob("id_*")):
        doc, dec = _json(folder / "iterations.json"), _json(folder / "decisions.json")
        drafts = doc.get("iterations") or []
        if not drafts or not doc.get("final_metrics"):
            continue
        eid = str(doc["id"])
        effects = doc.get("next_iterations") or []
        first = doc.get("first_pass") or {}
        kept0 = next((d for d in drafts if d["round"] == first.get("kept_round", 0)), drafts[0])
        last = model_values(first.get("metrics") or doc["final_metrics"], kept0.get("validator_levels"),
                            dec.get("first_pass_error_counts") or dec.get("error_counts"),
                            kept0.get("valid"))
        for i in range(n):
            if i < len(effects) and effects[i].get("metrics_after"):
                e = effects[i]
                last = model_values(e["metrics_after"], e.get("validator_levels_after"),
                                    e.get("errors_after"), e.get("valid_kept"))
            out[i][eid] = last
    return out


LEARNING_AGENTS = "tools"
FULL_DATASET = 55            # First and Revised runs cover the whole dataset


def find(generator: str) -> dict:
    """The runs of the study for one generator (First, Revised, Reuse training and
    tests), made with the tool-using guideline agents."""
    found = {"First": [], "Revised": [], "Reuse_tests": {}, "Reuse_train": {}}
    for path in sorted(RUNS_DIR.glob("batch_*/models.json")):
        m = _json(path)
        if m.get("dry_run") or (m.get("models") or {}).get("generator") != generator:
            continue
        if m.get("trial"):                 # a test on a few descriptions, not part of the study
            continue
        if m.get("learn", True) and (m.get("learning_agents") or "roles") != LEARNING_AGENTS:
            continue
        if m.get("arm") == "documentation+learned" and (m.get("learning_agents") or "roles") != LEARNING_AGENTS:
            continue
        run = path.parent
        if m.get("fold") and m.get("fold_role") == "train" and m.get("force_iterations"):
            found["Reuse_train"][int(m["fold"])] = run
        elif m.get("fold") and m.get("fold_role") == "test":
            found["Reuse_tests"][int(m["fold"])] = run
        elif m.get("replicate") and m.get("arm") == "documentation" and not m.get("fold") \
                and len((m.get("examples") or {}).get("ids") or []) >= FULL_DATASET:
            if not m.get("learn") and int(m.get("next_iterations") or 0) == 0:
                found["First"].append(run)
            elif m.get("learn") and m.get("force_iterations"):
                found["Revised"].append(run)
    # a test counts only if it comes after a training with forced iterations
    found["Reuse_tests"] = {k: v for k, v in found["Reuse_tests"].items()
                            if k in found["Reuse_train"] and v.name > found["Reuse_train"][k].name}
    return found


def mean_or_none(values):
    vals = [v for v in values if v is not None]
    return statistics.fmean(vals) if vals else None


def summarize(runs_values: list[dict], groups_sd: bool = False) -> dict:
    """runs_values: one {description: values} per run (or per fold for Reuse).
    Returns per measure the mean over descriptions and the SD between runs (folds)."""
    out = {}
    for key in ALL:
        if key.startswith("precision_L"):
            # precision of a level = TP / (TP + FP), TP and FP summed over the models of the run
            level = key.split("_")[1]
            per_run = []
            for run in runs_values:
                tp = sum(v.get(f"tp_{level}") or 0 for v in run.values() if v.get(f"tp_{level}") is not None)
                fp = sum(v.get(f"fp_{level}") or 0 for v in run.values() if v.get(f"fp_{level}") is not None)
                per_run.append(tp / (tp + fp) if tp + fp else None)
        else:
            per_run = [mean_or_none(v.get(key) for v in run.values()) for run in runs_values]
        per_run = [x for x in per_run if x is not None]
        out[key] = {"mean": round(statistics.fmean(per_run), 4) if per_run else None,
                    "sd": round(statistics.stdev(per_run), 4) if len(per_run) > 1 else 0.0,   # sample SD (n - 1)
                    "per_run": [round(x, 4) for x in per_run]}
    return out


def per_description_mean(runs_values: list[dict]) -> dict:
    ids = set().union(*[set(r) for r in runs_values]) if runs_values else set()
    return {eid: {k: mean_or_none(r[eid].get(k) for r in runs_values if eid in r) for k in ALL}
            for eid in ids}


def compare(first: dict, other: dict) -> dict:
    out = {}
    for key in ALL:
        pairs = [(first[e][key], other[e][key]) for e in sorted(set(first) & set(other))
                 if first[e].get(key) is not None and other[e].get(key) is not None]
        diff = [b - a for a, b in pairs]
        lower = key == "errors_total"
        out[key] = {"n": len(pairs), "change": round(statistics.fmean(diff), 4) if diff else None,
                    "better": sum((d < 0) if lower else (d > 0) for d in diff),
                    "worse": sum((d > 0) if lower else (d < 0) for d in diff),
                    "p": fr.wilcoxon([a for a, _ in pairs], [b for _, b in pairs])}
    return out


def build(generator: str) -> dict:
    runs = find(generator)
    first_runs = [first_models(r) for r in runs["First"]]
    revised_runs = [iteration_models(r) for r in runs["Revised"]]
    configs = {"First": first_runs,
               "Revised i1": [r[0] for r in revised_runs],
               "Revised i2": [r[1] for r in revised_runs],
               "Learned": [r[2] for r in revised_runs]}
    reuse_folds = [first_models(runs["Reuse_tests"][k]) for k in sorted(runs["Reuse_tests"])]
    report = {"generator": generator, "learning_agents": LEARNING_AGENTS,
              "runs": {"First": [r.name for r in runs["First"]],
                       "Revised": [r.name for r in runs["Revised"]],
                       "Reuse_train": {k: v.name for k, v in sorted(runs["Reuse_train"].items())},
                       "Reuse_tests": {k: v.name for k, v in sorted(runs["Reuse_tests"].items())}},
              "descriptions": {c: [len(r) for r in v] for c, v in configs.items()},
              "table": {}, "versus_first": {}}
    for name, values in configs.items():
        report["table"][name] = summarize(values)
    if reuse_folds:
        pooled = {}
        for fold in reuse_folds:
            pooled.update(fold)
        report["descriptions"]["Reuse"] = [len(pooled)]
        table = summarize(reuse_folds)                 # SD between the 5 folds
        together = summarize([pooled])                 # the mean is over the 55 test descriptions together
        for key in ALL:
            table[key]["mean"] = together[key]["mean"]
        report["table"]["Reuse"] = table
        configs["Reuse"] = [pooled]
    first = per_description_mean(first_runs) if first_runs else {}
    for name, values in configs.items():
        if name != "First" and first and values:
            report["versus_first"][name] = compare(first, per_description_mean(values))
    return report


def write(report: dict, out_root: Path | None = None) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = report["generator"].replace(":", "-").replace("/", "-")
    if report.get("learning_agents") == "tools":
        slug += "_agents"
    out = (out_root or RUNS_DIR / "_study_reports") / f"{slug}_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "study.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    cols = [c for c in CONFIGS if c in report["table"]]
    with open(out / "study_table.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["measure"] + [x for c in cols for x in (f"{c} mean", f"{c} sd", f"{c} vs First change", f"{c} p")])
        for key in ALL:
            row = [key]
            for c in cols:
                t, v = report["table"][c][key], report["versus_first"].get(c, {}).get(key, {})
                row += [t["mean"], t["sd"], v.get("change"), v.get("p")]
            w.writerow(row)
    lines = [f"# Study: {report['generator']}", "", "| measure | " + " | ".join(cols) + " |",
             "|---|" + "---|" * len(cols)]
    for key in ALL:
        cells = []
        for c in cols:
            t, v = report["table"][c][key], report["versus_first"].get(c, {}).get(key, {})
            star = "*" if (v.get("p") is not None and v["p"] < 0.05) else ""
            cells.append("-" if t["mean"] is None else f"{t['mean']:.3f} ({t['sd']:.3f}){star}")
        lines.append(f"| {key} | " + " | ".join(cells) + " |")
    (out / "study.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--generator", required=True)
    args = parser.parse_args()
    print(f"written: {write(build(args.generator))}")


if __name__ == "__main__":
    main()
