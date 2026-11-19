"""Results of a run and of the stratified k-fold cross-validation.

1. write_run_summary(run_dir), called at the end of every run: for the first
   model and for the final model of each description, every metric with its
   mean, SD (population), min and max over the descriptions, the errors per type
   (T1-T7), and the accuracy of each validator level,
       accuracy = correct elements / (correct + incorrect elements),
   summed over the models where the level applies (plus the mean, SD, min and
   max of the accuracy of each model). Saved as metrics_summary.json and .csv.

2. The cross-validation report (command line), for one generator model:
       python fold_report.py --generator openai:gpt-6-luna
   It finds the 5 training runs (Reuse training, --fold k), the 5 test runs
   (Reuse test, --fold k) and the First run (documentation guidelines only,
   all 55 descriptions, no learning) of that model and writes, in
   runs/_cv_reports/<model>_<date>/:
     test_per_fold.csv      baseline vs B on the 11 test descriptions of each fold
     test_over_folds.csv    mean, SD, min, max of the fold means
     test_pooled.csv        the 55 test descriptions together, paired Wilcoxon test
     rq2_per_fold.csv       first vs final model on the 44 training descriptions
     rq2_per_description.csv  each description, mean over the folds where it trained
     guidelines_per_fold.csv  learned, confirmed, example-specific, abstained...
     levels.csv             accuracy per validator level, every configuration
     cv_report.json and cv_report.md (everything, readable)
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from pipeline_config import RUNS_DIR, resolve_path

LEVELS = ("L1", "L2", "L3", "L4")
TYPES = ("T1", "T2", "T3", "T4", "T5", "T6", "T7")
METRICS = ("activity_label_precision", "activity_label_recall", "activity_label_f1",
           "connection_precision", "connection_recall", "connection_f1",
           "workflow_order_similarity", "alignment_coverage",
           "semantic_similarity", "activity_semantic_similarity", "collaboration_similarity")
ERRORS = tuple(f"errors_{t}" for t in TYPES) + ("errors_total",)


# ------------------------------------------------------------ one run ---
def stats(values) -> dict:
    vals = [float(v) for v in values if v is not None]
    if not vals:
        return {"n": 0, "mean": None, "sd": None, "min": None, "max": None}
    return {"n": len(vals), "mean": round(statistics.fmean(vals), 4),
            "sd": round(statistics.pstdev(vals), 4) if len(vals) > 1 else 0.0,
            "min": round(min(vals), 4), "max": round(max(vals), 4)}


def _json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def example_rows(run_dir: Path) -> list[dict]:
    """One row per finished description: its first and its final model."""
    out = []
    for folder in sorted(Path(run_dir).glob("id_*")):
        doc, dec = _json(folder / "iterations.json"), _json(folder / "decisions.json")
        drafts = doc.get("iterations") or []
        if not drafts or not doc.get("final_metrics"):
            continue
        first = doc.get("first_pass") or {}

        def model(kept_round, metrics, valid, failed, errors):
            draft = next((d for d in drafts if d["round"] == kept_round), drafts[-1])
            counts = {t: int((errors or {}).get(t) or 0) for t in TYPES}
            row = {"round": draft["round"], "valid": bool(valid), "failed_levels": list(failed or []),
                   "levels": draft.get("validator_levels") or {}}
            row.update({k: metrics.get(k) for k in METRICS})
            if not metrics.get("collaboration_applicable", True):
                row["collaboration_similarity"] = None
            row.update({f"errors_{t}": counts[t] for t in TYPES})
            row["errors_total"] = sum(counts.values())
            return row

        final_round = doc.get("kept_round", drafts[-1]["round"])
        final_draft = next((d for d in drafts if d["round"] == final_round), drafts[-1])
        final = model(final_round, doc["final_metrics"], final_draft.get("valid"),
                      final_draft.get("failed_levels"), dec.get("error_counts"))
        if first:
            start = model(first.get("kept_round", 0), first.get("metrics") or {}, first.get("valid"),
                          first.get("failed_levels"),
                          dec.get("first_pass_error_counts") or first.get("error_counts"))
        else:
            start = final
        out.append({"id": str(doc.get("id") or folder.name[3:]), "first": start, "final": final,
                    "next_iterations": len(doc.get("next_iterations") or [])})
    return out


def level_block(models: list[dict]) -> dict:
    out = {}
    for level in LEVELS:
        rows = [m["levels"].get(level) for m in models if m["levels"].get(level)]
        applicable = [r for r in rows if r.get("result") is not None]
        correct = sum(r.get("correct", 0) for r in applicable)
        incorrect = sum(r.get("incorrect", 0) for r in applicable)
        per_model = [r["correct"] / (r["correct"] + r["incorrect"])
                     for r in applicable if (r.get("correct", 0) + r.get("incorrect", 0))]
        out[level] = {"models_pass": sum(r.get("result") is True for r in rows),
                      "models_fail": sum(r.get("result") is False for r in rows),
                      "models_not_applicable": sum(r.get("result") is None for r in rows),
                      "elements_correct": correct, "elements_incorrect": incorrect,
                      "accuracy": round(correct / (correct + incorrect), 4)
                      if correct + incorrect else None,
                      "accuracy_per_model": stats(per_model)}
    return out


def block(models: list[dict]) -> dict:
    return {"descriptions": len(models),
            "valid_models": sum(m["valid"] for m in models),
            "metrics": {k: stats(m.get(k) for m in models) for k in METRICS + ERRORS},
            "levels": level_block(models)}


def summarize(rows: list[dict]) -> dict:
    return {"first": block([r["first"] for r in rows]),
            "final": block([r["final"] for r in rows]),
            "descriptions_with_next_iterations": sum(r["next_iterations"] > 0 for r in rows)}


def _stat_rows(name: str, summary: dict) -> list[list]:
    out = []
    for key, s in summary["metrics"].items():
        out.append([name, key, s["n"], s["mean"], s["sd"], s["min"], s["max"]])
    for level, b in summary["levels"].items():
        out.append([name, f"accuracy_{level}", b["elements_correct"] + b["elements_incorrect"],
                    b["accuracy"], None, None, None])
        p = b["accuracy_per_model"]
        out.append([name, f"accuracy_{level}_per_model", p["n"], p["mean"], p["sd"], p["min"], p["max"]])
    return out


def write_run_summary(run_dir) -> dict:
    run_dir = Path(run_dir)
    rows = example_rows(run_dir)
    summary = summarize(rows)
    summary["run"] = run_dir.name
    summary["per_description"] = [{"id": r["id"],
                                   "first": {k: v for k, v in r["first"].items() if k != "levels"},
                                   "final": {k: v for k, v in r["final"].items() if k != "levels"}}
                                  for r in rows]
    (run_dir / "metrics_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    with open(run_dir / "metrics_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "metric", "n", "mean", "sd", "min", "max"])
        for name in ("first", "final"):
            w.writerows(_stat_rows(name, summary[name]))
    return summary


# ------------------------------------------------- cross-validation ---
def _runs(generator: str) -> list[tuple[Path, dict]]:
    found = []
    for path in sorted(RUNS_DIR.glob("batch_*/models.json")):
        m = _json(path)
        if m.get("dry_run") or (m.get("models") or {}).get("generator") != generator:
            continue
        found.append((path.parent, m))
    return found


def find_runs(generator: str, baseline: str | None = None) -> dict:
    runs = _runs(generator)
    chosen = {"train": {}, "test": {}, "baseline": None}
    for folder, m in runs:                      # sorted by date: the latest wins
        if m.get("fold") and m.get("fold_role") in ("train", "test"):
            chosen[m["fold_role"]][int(m["fold"])] = folder
        elif (m.get("arm") == "documentation" and not m.get("fold")
              and (not m.get("learn") or int(m.get("next_iterations") or 0) == 0)
              and len((m.get("examples") or {}).get("ids") or []) == 55):
            chosen["baseline"] = folder
    if baseline:
        chosen["baseline"] = RUNS_DIR / baseline
    return chosen


def wilcoxon(x, y) -> float | None:
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    if len(pairs) < 2 or all(a == b for a, b in pairs):
        return None
    try:
        from scipy.stats import wilcoxon as test
        return round(float(test([a for a, _ in pairs], [b for _, b in pairs]).pvalue), 4)
    except Exception:
        return None


def compare(before: list[dict], after: list[dict]) -> dict:
    """Paired comparison of two lists of models of the same descriptions."""
    out = {}
    for key in METRICS + ERRORS:
        x = [m.get(key) for m in before]
        y = [m.get(key) for m in after]
        pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
        diff = [b - a for a, b in pairs]
        lower_is_better = key.startswith("errors")
        out[key] = {"before": stats(x), "after": stats(y), "change": stats(diff),
                    "better": sum((d < 0) if lower_is_better else (d > 0) for d in diff),
                    "worse": sum((d > 0) if lower_is_better else (d < 0) for d in diff),
                    "equal": sum(d == 0 for d in diff), "wilcoxon_p": wilcoxon(x, y)}
    return out


def guideline_counts(train_dir: Path, test_dir: Path | None) -> dict:
    m = _json(train_dir / "models.json")
    path = resolve_path(m.get("learned_catalogue") or "")
    if not path.is_file() and m.get("fold"):       # saved on another system (e.g. a Windows path)
        import guideline_store
        path = (guideline_store.catalogue_for_model((m.get("models") or {}).get("generator", ""))
                .parent / "folds" / f"fold_{int(m['fold'])}" / "learned_guidelines.json")
    store = _json(path)
    guidelines = store.get("guidelines") or []
    by_status = {}
    for g in guidelines:
        by_status[g.get("status", "?")] = by_status.get(g.get("status", "?"), 0) + 1
    promoted = [g for g in guidelines if g.get("status") == "promoted"]
    outcomes = {}
    for d in train_dir.glob("id_*/decisions.json"):
        for o in _json(d).get("guidelines") or []:
            outcomes[o.get("status", "?")] = outcomes.get(o.get("status", "?"), 0) + 1
    history = {}
    for d in train_dir.glob("_redone/id_*/decisions.json"):      # first attempts run again
        for o in _json(d).get("guidelines") or []:
            history[o.get("status", "?")] = history.get(o.get("status", "?"), 0) + 1
    superseded = sum(len((g.get("confirmation") or {}).get("superseded_tests") or [])
                     for g in guidelines)
    given = _json(test_dir / "learned_guidelines_used.json").get("count") if test_dir else None
    return {"catalogue": m.get("learned_catalogue"), "in_catalogue": len(guidelines),
            "by_status": by_status, "general_promoted": len(promoted),
            "general_confirmed": sum(bool((g.get("confirmation") or {}).get("confirmed"))
                                     for g in promoted),
            "agent_outcomes": outcomes, "given_to_test": given,
            "redone_descriptions": [r["id"] for r in m.get("redone") or []],
            "history_outcomes_of_first_attempts": history,
            "confirmation_tests_moved_to_history": superseded}


def _fmt(s: dict) -> str:
    if not s or s.get("mean") is None:
        return "-"
    return f"{s['mean']:.3f} ({s['sd']:.3f}) [{s['min']:.3f}–{s['max']:.3f}]"


def _progress(folder: Path | None) -> dict | None:
    if folder is None:
        return None
    m = _json(folder / "models.json")
    expected = len((m.get("examples") or {}).get("ids") or [])
    done = len(example_rows(folder))
    return {"run": folder.name, "done": done, "expected": expected,
            "finished": any(folder.glob("report_*.json")) and done == expected}


class NoBaseline(ValueError):
    pass


def build_cv(generator: str, baseline: str | None = None) -> dict:
    """Everything of the cross-validation of one generator model, as a dict
    (the website shows it; cv_report writes it to files)."""
    runs = find_runs(generator, baseline)
    if runs["baseline"] is None:
        raise NoBaseline(f"No First run of {generator}: run the documentation arm without learning "
                         "(--no-learn --next-iterations 0) on the 55 descriptions first")
    base_rows = {r["id"]: r["final"] for r in example_rows(runs["baseline"])}
    report = {"generator": generator, "baseline_run": runs["baseline"].name,
              "status": {"baseline": _progress(runs["baseline"]),
                         "folds": {f: {"train": _progress(runs["train"].get(f)),
                                       "test": _progress(runs["test"].get(f))}
                                   for f in range(1, 6)}},
              "train_runs": {k: v.name for k, v in sorted(runs["train"].items())},
              "test_runs": {k: v.name for k, v in sorted(runs["test"].items())},
              "folds": {}, "pooled": None, "over_folds": {}, "rq2": {}}
    pooled_base, pooled_b, fold_means = [], [], {}
    per_description = {}
    rows_fold, rows_rq2, rows_guid, rows_levels = [], [], [], []
    for fold in range(1, 6):
        entry = {}
        test_dir, train_dir = runs["test"].get(fold), runs["train"].get(fold)
        if test_dir:
            tested = example_rows(test_dir)
            b = [r["final"] for r in tested]
            base = [base_rows.get(r["id"]) for r in tested]
            keep = [i for i, x in enumerate(base) if x is not None]
            b, base = [b[i] for i in keep], [base[i] for i in keep]
            entry["test"] = {"descriptions": [tested[i]["id"] for i in keep],
                             "baseline": block(base), "B": block(b), "comparison": compare(base, b)}
            pooled_base += base
            pooled_b += b
            for key, c in entry["test"]["comparison"].items():
                fold_means.setdefault(key, {"baseline": [], "B": [], "change": []})
                fold_means[key]["baseline"].append(c["before"]["mean"])
                fold_means[key]["B"].append(c["after"]["mean"])
                fold_means[key]["change"].append(c["change"]["mean"])
                rows_fold.append([fold, key, _fmt(c["before"]), _fmt(c["after"]),
                                  c["change"]["mean"], c["better"], c["worse"], c["wilcoxon_p"]])
            for name, models in (("baseline", base), ("B", b)):
                for level, lb in level_block(models).items():
                    rows_levels.append([f"fold {fold} test", name, level, lb["accuracy"],
                                        lb["elements_correct"], lb["elements_incorrect"],
                                        _fmt(lb["accuracy_per_model"]), lb["models_fail"]])
        if train_dir:
            trained = example_rows(train_dir)
            first, final = [r["first"] for r in trained], [r["final"] for r in trained]
            entry["rq2"] = {"descriptions": len(trained), "first": block(first),
                            "final": block(final), "comparison": compare(first, final)}
            for key, c in entry["rq2"]["comparison"].items():
                rows_rq2.append([fold, key, _fmt(c["before"]), _fmt(c["after"]),
                                 c["change"]["mean"], c["better"], c["worse"], c["wilcoxon_p"]])
            for r in trained:
                per_description.setdefault(r["id"], []).append(r)
            for name, models in (("first", first), ("final", final)):
                for level, lb in level_block(models).items():
                    rows_levels.append([f"fold {fold} training", name, level, lb["accuracy"],
                                        lb["elements_correct"], lb["elements_incorrect"],
                                        _fmt(lb["accuracy_per_model"]), lb["models_fail"]])
            entry["guidelines"] = guideline_counts(train_dir, test_dir)
            g = entry["guidelines"]
            rows_guid.append([fold, g["in_catalogue"], g["general_promoted"], g["general_confirmed"],
                              g["by_status"].get("example_specific", 0), g["given_to_test"],
                              json.dumps(g["agent_outcomes"]), ",".join(g["redone_descriptions"]),
                              json.dumps(g["history_outcomes_of_first_attempts"]),
                              g["confirmation_tests_moved_to_history"]])
        report["folds"][fold] = entry
    if pooled_b:
        report["pooled"] = {"descriptions": len(pooled_b), "baseline": block(pooled_base),
                            "B": block(pooled_b), "comparison": compare(pooled_base, pooled_b)}
        for name, models in (("baseline", pooled_base), ("B", pooled_b)):
            for level, lb in level_block(models).items():
                rows_levels.append(["pooled test", name, level, lb["accuracy"], lb["elements_correct"],
                                    lb["elements_incorrect"], _fmt(lb["accuracy_per_model"]),
                                    lb["models_fail"]])
    report["over_folds"] = {k: {n: stats(v) for n, v in d.items()} for k, d in fold_means.items()}
    rq2_desc = []
    for eid, rows in sorted(per_description.items()):
        row = {"id": eid, "folds": len(rows)}
        for key in METRICS + ERRORS:
            row[f"first_{key}"] = stats(r["first"].get(key) for r in rows)["mean"]
            row[f"final_{key}"] = stats(r["final"].get(key) for r in rows)["mean"]
        rq2_desc.append(row)
    report["rq2"]["per_description"] = rq2_desc
    report["tables"] = {"test_per_fold": rows_fold, "rq2_per_fold": rows_rq2,
                        "guidelines_per_fold": rows_guid, "levels": rows_levels}
    return report


def cv_report(generator: str, baseline: str | None = None, out_root: Path | None = None) -> Path:
    try:
        report = build_cv(generator, baseline)
    except NoBaseline as exc:
        raise SystemExit(str(exc))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = generator.replace(":", "-").replace("/", "-")
    out = (out_root or RUNS_DIR / "_cv_reports") / f"{slug}_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    tables = report["tables"]
    rows_fold, rows_rq2 = tables["test_per_fold"], tables["rq2_per_fold"]
    rows_guid, rows_levels = tables["guidelines_per_fold"], tables["levels"]
    rq2_desc = report["rq2"]["per_description"]
    (out / "cv_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")

    def table(name, header, rows):
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
    head = ["fold", "metric", "before mean (SD) [min–max]", "after mean (SD) [min–max]",
            "mean change", "better", "worse", "wilcoxon p"]
    table("test_per_fold.csv", head, rows_fold)
    table("rq2_per_fold.csv", head, rows_rq2)
    table("test_over_folds.csv", ["metric", "baseline (fold means)", "B (fold means)", "change (fold means)"],
          [[k, _fmt(v["baseline"]), _fmt(v["B"]), _fmt(v["change"])]
           for k, v in report["over_folds"].items()])
    if report["pooled"]:
        table("test_pooled.csv", head[1:], [[k, _fmt(c["before"]), _fmt(c["after"]), c["change"]["mean"],
                                             c["better"], c["worse"], c["wilcoxon_p"]]
                                            for k, c in report["pooled"]["comparison"].items()])
    table("guidelines_per_fold.csv", ["fold", "in catalogue", "general (promoted)", "general confirmed",
                                      "example-specific", "given to the test", "agent outcomes",
                                      "descriptions run again", "outcomes of their first attempts (history)",
                                      "confirmation tests moved to history"], rows_guid)
    table("levels.csv", ["set", "configuration", "level", "accuracy", "correct", "incorrect",
                         "accuracy per model mean (SD) [min–max]", "models failing"], rows_levels)
    if rq2_desc:
        table("rq2_per_description.csv", list(rq2_desc[0]), [list(r.values()) for r in rq2_desc])
    lines = [f"# Cross-validation report: {generator}", "",
             f"Baseline (documentation guidelines only): {report['baseline_run']}", ""]
    for fold, e in report["folds"].items():
        lines.append(f"- fold {fold}: training {report['train_runs'].get(fold, 'missing')}, "
                     f"test {report['test_runs'].get(fold, 'missing')}")
    if report["pooled"]:
        lines += ["", f"## Test, the {report['pooled']['descriptions']} test descriptions pooled "
                  "(baseline vs B)", "", "| metric | baseline | B | better | worse | p |", "|---|---|---|---|---|---|"]
        for k, c in report["pooled"]["comparison"].items():
            lines.append(f"| {k} | {_fmt(c['before'])} | {_fmt(c['after'])} | {c['better']} | "
                         f"{c['worse']} | {c['wilcoxon_p']} |")
    (out / "cv_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--generator", help="provider:model, e.g. openai:gpt-6-luna")
    parser.add_argument("--baseline", default=None, help="baseline run folder (default: the latest)")
    parser.add_argument("--run", default=None, help="only (re)write the summary of this run folder")
    args = parser.parse_args()
    if args.run:
        write_run_summary(RUNS_DIR / args.run)
        print(f"written: {RUNS_DIR / args.run / 'metrics_summary.json'}")
        return
    if not args.generator:
        parser.error("--generator is required")
    print(f"written: {cv_report(args.generator, args.baseline)}")


if __name__ == "__main__":
    main()
