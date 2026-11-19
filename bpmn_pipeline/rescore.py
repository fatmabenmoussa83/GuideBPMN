"""Score the saved drafts of finished runs again with the current evaluator.

Nothing is generated and no run file is changed: for each run, the draft every
example kept in its first pass is compared with its reference again, and the
result is written next to the run as rescored_first_pass.json (all metrics,
including the activities-only label scores) and rescored_summary.json.

    python rescore.py                       # every finished run of 50+ examples
    python rescore.py batch_2026..._documentation_r1 batch_2026..._forced_r1_agents
"""
import json
import sys
from pathlib import Path
from typing import Optional

from pipeline_config import DATASET_PATH, RUNS_DIR
from evaluation import embedding_model, evaluate_pair
from reporting import _stats

KEYS = ("activity_semantic_similarity", "activity_label_precision", "activity_label_recall",
        "activity_label_f1", "semantic_similarity", "alignment_coverage",
        "connection_precision", "connection_recall", "connection_f1",
        "workflow_order_similarity", "collaboration_similarity")


def first_pass_draft(example_dir: Path) -> Optional[str]:
    """The draft an example kept in its first pass (before any guideline was sent back)."""
    path = example_dir / "iterations.json"
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    wanted = (doc.get("first_pass") or {}).get("kept_round", doc.get("kept_round"))
    draft = next((i for i in doc["iterations"] if i["round"] == wanted), None)
    return (draft or {}).get("xml") or None


def rescore(run: Path, gold: dict, model, progress=lambda line: None) -> dict:
    rows, drafts = {}, {}
    for folder in sorted(run.glob("id_*")):
        eid, path = folder.name[3:], folder / "iterations.json"
        if eid not in gold or not path.is_file():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        first = (doc.get("first_pass") or {}).get("kept_round", doc.get("kept_round"))
        for it in doc["iterations"]:                 # every draft, so the site can show them
            if not it.get("xml"):
                continue
            metrics = evaluate_pair(gold[eid], it["xml"], model=model)
            clean = {k: v for k, v in metrics.items() if k not in ("node_mapping", "counts")}
            drafts.setdefault(eid, {})[str(it["round"])] = {k: clean.get(k) for k in KEYS}
            if it["round"] == first:
                rows[eid] = clean
        progress(f"{run.name}: example {eid} scored again")
    (run / "rescored_drafts.json").write_text(json.dumps(drafts, indent=1), encoding="utf-8")
    (run / "rescored_first_pass.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    summary = {"run": run.name, "examples": len(rows),
               "metrics": {k: _stats([r.get(k) for r in rows.values()]) for k in KEYS}}
    (run / "rescored_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def finished_runs(minimum: int = 50) -> list[Path]:
    return [p for p in sorted(RUNS_DIR.glob("batch_*"))
            if (p / "models.json").is_file()
            and not json.loads((p / "models.json").read_text(encoding="utf-8")).get("dry_run")
            and sum(1 for _ in p.glob("id_*/iterations.json")) >= minimum]


def rescore_runs(names: list[str] | None = None, progress=print) -> list[dict]:
    """Score again the named runs (or every finished run of 50+ examples)."""
    gold = {str(e["id"]): e["bpmn_xml"]
            for e in json.loads(DATASET_PATH.read_text(encoding="utf-8"))}
    wanted = [RUNS_DIR / name for name in names] if names else finished_runs()
    model = embedding_model()
    out = []
    for run in wanted:
        summary = rescore(run, gold, model, progress)
        m = summary["metrics"]
        progress(f"{run.name}: {summary['examples']} examples | activities-only semantic "
                 f"{m['activity_semantic_similarity'].get('mean')} | semantic "
                 f"{m['semantic_similarity'].get('mean')}")
        out.append(summary)
    return out


def main() -> None:
    rescore_runs(sys.argv[1:] or None, progress=lambda line: print(line, flush=True))


if __name__ == "__main__":
    main()
