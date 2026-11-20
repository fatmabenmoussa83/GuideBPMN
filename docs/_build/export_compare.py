"""Build the data of the Compare page (docs/data/saved/compare/<generator>.json.gz)
from the saved runs of the study (docs/data/saved/, made by export_saved_runs.py).

    python docs/_build/export_compare.py        (from the repository root)

For every description and every LLM, the file gives the measures of the model kept
by each run of the study: the three First runs, the three Revised runs (draft 0,
then the model kept after each next iteration, the last one being Learned) and the
Reuse test of the fold that held the description out. The Compare page draws the
diagrams itself from the saved example files."""
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAVED = ROOT / "docs" / "data" / "saved"
OUT = SAVED / "compare"

SIM = ("activity_label_precision", "activity_label_recall", "activity_label_f1",
       "connection_precision", "connection_recall", "connection_f1",
       "workflow_order_similarity", "alignment_coverage", "collaboration_similarity")
LEVELS = ("L1", "L2", "L3", "L4")
TYPES = ("T1", "T2", "T3", "T4", "T5", "T6", "T7")


def load(path: Path):
    data = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
    return json.loads(data)


def levels_precision(levels: dict) -> dict:
    out, values = {}, []
    for level in LEVELS:
        row = (levels or {}).get(level) or {}
        checked = (row.get("correct") or 0) + (row.get("incorrect") or 0)
        value = (row.get("correct") or 0) / checked if row.get("result") is not None and checked else None
        out[f"precision_{level}"] = None if value is None else round(value, 4)
        if value is not None:
            values.append(value)
    out["precision_levels_average"] = round(sum(values) / len(values), 4) if values else None
    return out


def model(metrics: dict, levels: dict, errors: dict, valid, failed, draft) -> dict:
    """The measures of one kept model."""
    errors = {t: int((errors or {}).get(t) or 0) for t in TYPES}
    out = {k: (None if (metrics or {}).get(k) is None else round(metrics[k], 4)) for k in SIM}
    out.update(levels_precision(levels))
    out["errors"] = errors
    out["errors_total"] = sum(errors.values())
    out["valid"] = bool(valid)
    out["failed_levels"] = list(failed or [])
    out["draft"] = draft                      # index of the draft in the example file (its XML)
    return out


def draft_by_round(doc: dict, rnd):
    drafts = doc.get("iterations") or []
    for i, d in enumerate(drafts):
        if d.get("round") == rnd:
            return i, d
    return (len(drafts) - 1, drafts[-1]) if drafts else (None, {})


def final_model(doc: dict) -> dict:
    """The model kept by a run without learning (First, Reuse test)."""
    i, kept = draft_by_round(doc, doc.get("kept_round"))
    agent = doc.get("agent") or {}
    return model(doc.get("final_metrics"), kept.get("validator_levels"), agent.get("error_counts"),
                 kept.get("valid"), kept.get("failed_levels"), i)


def revised_models(doc: dict) -> dict:
    """Draft 0, then the model kept after each next iteration, with the guidelines."""
    first = doc.get("first_pass") or {}
    agent = doc.get("agent") or {}
    i0, kept0 = draft_by_round(doc, first.get("kept_round", 0))
    steps = [dict(model(first.get("metrics") or doc.get("final_metrics"), kept0.get("validator_levels"),
                        agent.get("first_pass_error_counts") or agent.get("error_counts"),
                        kept0.get("valid"), kept0.get("failed_levels"), i0),
                  iteration=0, label="draft 0")]
    last = steps[0]
    for e in doc.get("next_iterations") or []:
        if not e.get("metrics_after"):
            steps.append(dict(last, iteration=e.get("iteration"), label=f"after iteration {e.get('iteration')}",
                              sent=e.get("sent") or [], confirmed_ids=[], reverted=False, not_run=True))
            continue
        i, _ = draft_by_round(doc, e.get("kept_round"))
        m = model(e["metrics_after"], e.get("validator_levels_after"), e.get("errors_after"),
                  e.get("valid_kept"), e.get("failed_levels_kept"), i)
        results = e.get("type_results") or {}
        m.update(iteration=e.get("iteration"), label=f"after iteration {e.get('iteration')}",
                 sent=e.get("sent") or [],
                 confirmed_ids=sorted(g for g, r in results.items() if (r.get("removed") or 0) > 0) if not e.get("reverted") else [],
                 reverted=bool(e.get("reverted")),
                 type_results={g: {"type": r.get("failure_type"), "before": r.get("errors_before"), "after": r.get("errors_after")}
                               for g, r in results.items()})
        steps.append(m)
        last = m
    learned = [g for g in agent.get("guidelines") or [] if g.get("status") in ("promoted", "generalized")]
    return {"steps": steps, "kept_round": doc.get("kept_round"),
            "learned": [{"id": g.get("guideline_id"), "type": g.get("failure_type"), "status": g.get("status")} for g in learned],
            "proposals": len(agent.get("guidelines") or [])}


def main():
    runs_index = load(SAVED / "runs.json")["runs"]
    folds = load(SAVED / "folds.json")
    fold_of = {i: f["fold"] for f in folds.get("folds", []) for i in f.get("test_ids", [])}
    dataset = load(SAVED / "dataset.json")
    titles = {}
    for d in dataset.get("descriptions") or []:
        text = d.get("description") or ""
        titles[str(d.get("id"))] = {"start": " ".join(text.split()[:8]), "words": d.get("words"),
                                    "pools": bool(d.get("with_pools_or_lanes"))}
    OUT.mkdir(parents=True, exist_ok=True)
    generators = sorted({r["generator"] for r in runs_index})
    for g in generators:
        study = load(SAVED / "study" / f"{g.replace(':', '-')}.json")
        names = study["runs"]
        out = {"generator": g, "runs": names, "fold_of": fold_of, "titles": titles, "descriptions": {}}
        per = out["descriptions"]

        def example(run, i):
            p = SAVED / "runs" / run / f"example_{i}.json.gz"
            return load(p) if p.is_file() else None

        ids = sorted(fold_of) or [f"{i:02d}" for i in range(1, 56)]
        for i in ids:
            row = {"First": [], "Revised": [], "Reuse": None, "ReuseTrain": []}
            for run in names["First"]:
                doc = example(run, i)
                if doc:
                    row["First"].append(dict(run=run, model=final_model(doc), description=doc.get("description")))
            for run in names["Revised"]:
                doc = example(run, i)
                if doc:
                    row["Revised"].append(dict(run=run, **revised_models(doc)))
            k = fold_of.get(i)
            if k and str(k) in names.get("Reuse_tests", {}):
                run = names["Reuse_tests"][str(k)]
                doc = example(run, i)
                if doc:
                    row["Reuse"] = dict(run=run, fold=k, model=final_model(doc))
            for kk, run in sorted(names.get("Reuse_train", {}).items()):
                doc = example(run, i)
                if doc:
                    r = revised_models(doc)
                    row["ReuseTrain"].append(dict(run=run, fold=int(kk), learned=r["learned"],
                                                  model=r["steps"][-1], kept_round=r["kept_round"]))
            if row["First"] or row["Revised"]:
                row["description"] = (row["First"] or [{}])[0].get("description") or ""
                for f in row["First"]:
                    f.pop("description", None)
                per[i] = row
        target = OUT / f"{g.replace(':', '-')}.json.gz"
        target.write_bytes(gzip.compress(json.dumps(out, separators=(",", ":")).encode("utf-8"), 9))
        print(f"{g}: {len(per)} descriptions -> {target.relative_to(ROOT)} ({target.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
