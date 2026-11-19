"""Bonuses and penalties: the work of the orchestrator, error by error.

Every single error counts: each error that a step finds costs one point at
that step, each error that a later step shows to be gone earns one point back.

    utility of a step = bonuses - penalties

What one error is, in each type:
  T1-T4   one incorrect element of a validator level (L1-L4)    found by validate
  T5      one sequence flow missing or additional                found by detect_failures
  T6      one activity without a partner in the other model      found by detect_failures
  T7      one pool, lane, membership or message flow missing
          or additional                                          found by detect_failures
Errors are counted per type at each step: the step is charged the increase and
credited the decrease.

The ledger is computed from the files of a finished (or running) example, so
it exists for every run, old or new. The orchestrator sees the same counts
(open errors per type, after the first pass and after each next iteration) in
its observation, and uses them to decide whether to learn and iterate again.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

LEVEL_TO_TYPE = {"L1": "T1", "L2": "T2", "L3": "T3", "L4": "T4"}
MEANING = {"T1": "invalid XML or schema", "T2": "gateway use", "T3": "sequence flows",
           "T4": "pools, lanes, messages", "T5": "structure differs from the reference",
           "T6": "labels differ from the reference",
           "T7": "collaboration differs from the reference"}


def _step(action: str, draft, before: dict, now: dict) -> dict:
    """before, now: number of open errors per kind ({"T3": 2, "O1": 1, ...}).
    An error found costs one point; an error that is gone earns one point."""
    kinds = sorted(set(before) | set(now))
    detected = {k: now.get(k, 0) - before.get(k, 0) for k in kinds if now.get(k, 0) > before.get(k, 0)}
    resolved = {k: before.get(k, 0) - now.get(k, 0) for k in kinds if before.get(k, 0) > now.get(k, 0)}
    penalty, bonus = float(sum(detected.values())), float(sum(resolved.values()))
    return {"action": action, "draft": draft,
            "penalties": {f"detected_{k}": float(n) for k, n in detected.items()},
            "bonuses": {f"resolved_{k}": float(n) for k, n in resolved.items()},
            "total_penalty": penalty, "total_bonus": bonus, "utility": bonus - penalty,
            "detected": sorted(detected), "resolved": sorted(resolved),
            "detected_counts": detected, "resolved_counts": resolved,
            "still_open": {k: now[k] for k in kinds if now.get(k, 0) > 0}}


def ledger(doc: dict, decisions: Optional[dict] = None) -> dict:
    """doc: iterations.json (or live_iterations.json); decisions: decisions.json.

    Every single error counts: each incorrect element of a validator level
    (T1-T4), each difference from the reference
    (T5: flows, T6: activities without a partner, T7: collaboration relations).
    A step is charged the errors that appear at it and credited the errors
    that are gone at it. Runs saved before the individual counts existed hold
    only the detected types: each type then counts as one error."""
    decisions = decisions or {}
    steps, levels, similarity = [], {}, {}
    revision = (doc.get("rule_feedback") or {}).get("round")
    first_detected = decisions.get("first_pass_detected_failures")
    final_detected = decisions.get("detected_failures")
    first_counts = (decisions.get("first_pass_error_counts")
                    or (doc.get("first_pass") or {}).get("error_counts"))
    final_counts = decisions.get("error_counts")
    if first_detected is None:
        first_detected, final_detected = final_detected, None
        first_counts, final_counts = final_counts, None

    def late(found, counts):
        counts = counts or {}
        return {t: max(1, int(counts.get(t) or 1)) for t in (found or [])
                if t in ("T5", "T6", "T7")}

    def level_errors(it):
        marks = it.get("validator_levels") or {}
        return {LEVEL_TO_TYPE.get(level, level):
                max(1, int((marks.get(level) or {}).get("incorrect") or 0))
                for level in it.get("failed_levels") or []}

    drafts = doc.get("iterations") or []
    # every next iteration starts from a model on which failures were detected:
    # that detection is one step of the record, placed before the iteration
    effects = doc.get("next_iterations") or []
    starts = {e.get("round"): n for n, e in enumerate(effects)}
    if not effects and revision is not None:           # runs saved before the effects existed
        starts = {revision: 0}

    def detected_before(n):
        if n == 0:
            return first_detected, first_counts, doc.get("first_pass", {}).get("kept_round")
        previous = effects[n - 1]
        return previous.get("detected_after"), previous.get("errors_after"), previous.get("kept_round")

    for it in drafts:
        if it.get("valid") is None:
            continue
        if it["round"] in starts:
            found, counts, kept = detected_before(starts[it["round"]])
            if found is not None:
                now = late(found, counts)
                steps.append(_step("detect_failures", kept, similarity, now))
                similarity = now
        now = level_errors(it)
        steps.append(_step("validate", it["round"], levels, now))
        levels = now
    finished = bool(decisions.get("stopped"))
    if finished:
        last, counts = ((final_detected, final_counts) if revision is not None
                        else (first_detected, first_counts))
        if effects and effects[-1].get("detected_after") is not None:
            last, counts = effects[-1]["detected_after"], effects[-1].get("errors_after")
        if last is not None:
            now = late(last, counts)
            steps.append(_step("detect_failures", doc.get("kept_round"), similarity, now))
            similarity = now
    running = 0.0
    for number, step in enumerate(steps, 1):
        running += step["utility"]
        step["step"], step["cumulative_utility"] = number, running
    bonus = sum(s["total_bonus"] for s in steps)
    penalty = sum(s["total_penalty"] for s in steps)
    still = {**levels, **similarity}
    return {"scoring_mode": "individual_errors", "steps": steps,
            "total_bonus": bonus, "total_penalty": penalty, "utility": bonus - penalty,
            "open_errors": sorted(still), "open_error_counts": still, "finished": finished}


def example_ledger(example_dir: Path) -> Optional[dict]:
    path = example_dir / "iterations.json"
    if not path.is_file():
        path = example_dir / "live_iterations.json"
    if not path.is_file():
        return None
    decisions = example_dir / "decisions.json"
    return ledger(json.loads(path.read_text(encoding="utf-8")),
                  json.loads(decisions.read_text(encoding="utf-8")) if decisions.is_file() else {})


def run_summary(run_dir: Path, ids) -> dict:
    """Bonuses and penalties of a whole run, by error type and by example."""
    rows, detected, resolved = [], {}, {}
    for eid in ids:
        book = example_ledger(run_dir / f"id_{eid}")
        if book is None:
            continue
        for step in book["steps"]:
            for e, n in step["detected_counts"].items():
                detected[e] = detected.get(e, 0) + n
            for e, n in step["resolved_counts"].items():
                resolved[e] = resolved.get(e, 0) + n
        rows.append({"id": eid, "total_bonus": book["total_bonus"],
                     "total_penalty": book["total_penalty"], "utility": book["utility"],
                     "open_errors": book["open_errors"]})
    return {"scoring_mode": "individual_errors", "examples": len(rows),
            "total_bonus": sum(r["total_bonus"] for r in rows),
            "total_penalty": sum(r["total_penalty"] for r in rows),
            "utility": sum(r["utility"] for r in rows),
            "detected_by_type": dict(sorted(detected.items())),
            "resolved_by_type": dict(sorted(resolved.items())), "per_example": rows}
