"""Thin wrapper around the repository-root validator (L1-L4).

The pipeline deliberately has NO validator of its own: the single validator
used by the website, the tests and the paper is the one at the repo root.
"""
from functools import lru_cache

from pipeline_config import XSD_DIR, add_shared_paths
add_shared_paths()

import validator  # repo root, L1-L4 checklist


@lru_cache(maxsize=1)
def _xsd():
    return validator.load_xsd(XSD_DIR / "BPMN20.xsd")


def validate(xml_str: str) -> dict:
    """Full L1-L4 result for one BPMN XML string (no LLM involved).

    Returns validator.validate_bpmn's dict: {"profile": {L1..L4: {result,
    message, error_elements, ...}}, "overall_valid": bool}.
    """
    return validator.validate_bpmn(xml_str, _xsd())


def is_valid(result: dict) -> bool:
    return bool(result.get("overall_valid"))


def failed_levels(result: dict) -> dict:
    """Only the levels whose result is False, for feedback prompts."""
    profile = result.get("profile", {})
    return {name: level for name, level in profile.items()
            if level.get("result") is False}


# ------------------------------------------------- element-level performance --
# For each level, every element the level inspects is classified correct or
# incorrect (the validator's own overview functions), so that a model that is
# right in nine places and wrong in one is not reduced to a single pass/fail.
#   accuracy of a level = correct elements / (correct + incorrect elements)
# A level that does not apply (L4 without pools or lanes; L2-L4 when the XML
# cannot be parsed) is reported as not applicable, never as incorrect.
LEVELS = ("L1", "L2", "L3", "L4")


def element_performance(xml_str: str, result: dict | None = None) -> dict:
    """Per level: result, numbers of correct and incorrect elements, accuracy,
    and the incorrect elements with their reason."""
    from lxml import etree
    result = result or validate(xml_str)
    profile = result.get("profile", {})
    xml_doc, lines = None, {}
    try:
        if xml_str and xml_str.strip():
            xml_doc = validator.reorder_children(etree.fromstring(xml_str.encode("utf-8")))
            lines = validator.build_line_lookup(xml_doc)
    except etree.XMLSyntaxError:
        xml_doc = None
    overviews = {
        "L1": validator.overview_l1(xml_doc, (profile.get("L1") or {}).get("error_elements", []), lines),
        "L2": validator.overview_l2(xml_doc, lines) if xml_doc is not None else [],
        "L3": validator.overview_l3(xml_doc, lines) if xml_doc is not None else [],
        "L4": validator.overview_l4(xml_doc, lines) if xml_doc is not None else [],
    }
    out = {}
    for level in LEVELS:
        verdict = (profile.get(level) or {}).get("result")
        correct, incorrect = validator.split_correct_incorrect(overviews[level])
        applicable = verdict is not None
        total = len(correct) + len(incorrect)
        out[level] = {
            "result": verdict,                       # True, False, or None = not applicable
            "correct": len(correct) if applicable else 0,
            "incorrect": len(incorrect) if applicable else 0,
            "accuracy": round(len(correct) / total, 4) if applicable and total else None,
            "incorrect_elements": [
                {"id": e.get("id"), "tag": e.get("tag"), "line": e.get("line"),
                 "reason": e.get("reason")} for e in incorrect[:40]] if applicable else [],
        }
    return out


def _level_block(rows: list[dict]) -> dict:
    """Aggregate of one level over the drafts of a run."""
    import statistics
    done = [r for r in rows if r is not None]
    applicable = [r for r in done if r["result"] is not None]
    correct = sum(r["correct"] for r in applicable)
    incorrect = sum(r["incorrect"] for r in applicable)
    per_example = [r["accuracy"] for r in applicable if r["accuracy"] is not None]
    block = {"examples_pass": sum(r["result"] is True for r in done),
             "examples_fail": sum(r["result"] is False for r in done),
             "examples_not_applicable": sum(r["result"] is None for r in done),
             "elements_correct": correct, "elements_incorrect": incorrect,
             "accuracy": round(correct / (correct + incorrect), 4) if correct + incorrect else None}
    if per_example:
        block["per_example_accuracy"] = {
            "n": len(per_example), "mean": round(statistics.fmean(per_example), 4),
            "median": round(statistics.median(per_example), 4),
            "std": round(statistics.pstdev(per_example), 4) if len(per_example) > 1 else 0.0,
            "min": round(min(per_example), 4), "max": round(max(per_example), 4)}
    return block


def run_performance(run_dir, write: bool = True) -> dict:
    """Validator performance of a run, level by level, for the first draft and
    for the draft kept in the first pass. Computed from the saved drafts, so it
    exists for any run, old or new."""
    import json
    from pathlib import Path
    run_dir = Path(run_dir)
    first, kept, incorrect = {l: [] for l in LEVELS}, {l: [] for l in LEVELS}, []
    examples = 0
    for path in sorted(run_dir.glob("id_*/iterations.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        drafts = doc.get("iterations") or []
        if not drafts:
            continue
        examples += 1
        wanted = (doc.get("first_pass") or {}).get("kept_round", doc.get("kept_round"))
        chosen = next((d for d in drafts if d["round"] == wanted), drafts[-1])
        for target, draft in ((first, drafts[0]), (kept, chosen)):
            levels = draft.get("validator_levels") or element_performance(draft.get("xml") or "")
            for level in LEVELS:
                target[level].append(levels[level])
            if target is first:
                for level in LEVELS:
                    for e in levels[level]["incorrect_elements"]:
                        incorrect.append({"example_id": doc["id"], "level": level, **e})
    out = {"run": run_dir.name, "examples": examples,
           "accuracy_definition": "correct elements / (correct + incorrect elements), per level, "
                                  "over the examples where the level applies",
           "first_draft": {l: _level_block(first[l]) for l in LEVELS},
           "kept_draft": {l: _level_block(kept[l]) for l in LEVELS},
           "first_draft_incorrect_elements": incorrect}
    if write:
        (run_dir / "validator_performance.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out
