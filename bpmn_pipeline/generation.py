"""Draw the BPMN XML, guided by the documentation guidelines and, in the
Reuse tests, the confirmed generic error-driven guidelines of the round. Each draft is
generated once; the validator's errors are learned from, not sent back for correction.

The similarity against the reference model is never consulted while
generating; it is measured once, afterwards, so the outcome measure cannot
leak into generation.
"""
import json
import tempfile
import importlib.util
from functools import lru_cache
from pathlib import Path

from pipeline_config import DOCUMENTATION_GUIDELINES, REPO_ROOT
from guideline_store import load_store

GENERATOR_DIR = REPO_ROOT / "bpmn_generator_catalogue"


@lru_cache(maxsize=1)
def load_generator_module():
    """Import bpmn_generator_catalogue/generator.py by file path."""
    path = GENERATOR_DIR / "generator.py"
    spec = importlib.util.spec_from_file_location("bpmn_generator", path)
    module = importlib.util.module_from_spec(spec)
    import sys as _sys
    _sys.modules[spec.name] = module   # dataclasses resolve annotations via sys.modules
    spec.loader.exec_module(module)
    return module


def held_out(guidelines: list[dict], example_id) -> list[dict]:
    """Leave-one-out: the guidelines this example took no part in. A guideline is
    withheld from every example it was learned from, also when other examples
    support it: its wording may come from this example's own reference."""
    eid = str(example_id)
    return [g for g in guidelines
            if eid not in set(map(str, (g.get("support") or {}).get("learned_from") or []))]


def combined_catalogue(arm: str, workdir: Path | None = None,
                       example_id=None) -> Path:
    """Catalogue file for one setting (arm).

    documentation -> the documentation catalogue as-is (First, Revised, Reuse
    training); documentation+learned (Reuse test) appends one extra section
    holding the PROMOTED learned guidelines, in the same {id, instruction} rule
    format. With example_id, leave-one-out: guidelines learned from that example
    are withheld, so each example is generated with what was learned elsewhere.
    """
    if "learned" not in arm:
        return DOCUMENTATION_GUIDELINES
    doc = json.loads(DOCUMENTATION_GUIDELINES.read_text(encoding="utf-8"))
    snapshot = None
    for folder in ([workdir, workdir.parent] if workdir else []):
        if (folder / "learned_guidelines_used.json").is_file():
            snapshot = folder / "learned_guidelines_used.json"
            break
    if snapshot:                     # the catalogue frozen at the start of the run
        promoted = json.loads(snapshot.read_text(encoding="utf-8"))["guidelines"]
    else:
        promoted = [g for g in load_store()["guidelines"] if g.get("status") == "promoted"]
    withheld = []
    if example_id is not None:
        kept = held_out(promoted, example_id)
        withheld = [g["id"] for g in promoted if g not in kept]
        promoted = kept
    doc["sections"].append({
        "category": "Learned guidelines (promoted on evidence)",
        "rules": [{"id": g["id"],
                   "instruction": (f"When {g['trigger']}: {g['instruction']}"
                                    if g.get("trigger") else g["instruction"])}
                  for g in promoted],
    })
    workdir = workdir or Path(tempfile.mkdtemp(prefix="guidebpmn_catalogue_"))
    workdir.mkdir(parents=True, exist_ok=True)
    path = workdir / f"catalogue_{arm.replace('+', '_')}.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    if example_id is not None:      # what this example received, for the paper
        (workdir / "learned_guidelines_given.json").write_text(json.dumps(
            {"example_id": str(example_id), "leave_one_out": True,
             "given": [g["id"] for g in promoted], "withheld_own": withheld},
            indent=1), encoding="utf-8")
    return path


def generate_once(example_id: str, provider: str, catalogue: Path, output_dir: Path,
                  model: str | None = None,
                  correction_feedback: dict | None = None) -> dict:
    """One generator call for one example; returns the result row."""
    gen = load_generator_module()
    rows = gen.run(
        dataset_path=REPO_ROOT / "bpmn_generator_catalogue" / "dataset.json",
        output_dir=output_dir,
        provider=provider,
        selectors=(str(example_id),),
        limit=None,
        model_override=model,
        baseline_catalogue=catalogue,
        correction_feedback=correction_feedback,
    )
    return rows[0]
