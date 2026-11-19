"""Learned-guidelines store: candidate -> promoted, with abstraction checks.

Schema (one entry):
{
  "id": "LRN-003",
  "category": "Events",                  # same taxonomy as the documentation catalogue
  "family": "missing-timer",             # fidelity error family from the diagnosis step
  "trigger": "...testable condition on a description...",
  "instruction": "...BPMN-only wording, no domain vocabulary...",
  "status": "candidate" | "promoted" | "rejected",
  "support": {"learned_from": [ids], "fires_on": [ids], "gain": {id: delta}},
  "baseline_relation": {"type": "new" | "refines", "ref": "EVT-04" | null},
  "provenance": {"created_at": ..., "fold": ..., "run": ...}
}

Promotion rule: a candidate proposed by the Expert agent is promoted when it
passes the automatic checks (its citations exist, it contains no label that
exists only in the reference, and it is not already a documentation guideline
or an already learned one). One supporting example is enough; the number of
supporting examples is recorded in `support.learned_from`.
"""
import json
import re
import datetime
from collections import Counter
from pathlib import Path

import os
import pipeline_config
from pipeline_config import (DATASET_PATH, DOCUMENTATION_GUIDELINES, LEARNED_GUIDELINES,
                    PROMOTION_MIN_SUPPORT)

_SET_BY_RUN = None          # the catalogue a run chose (see use_catalogue)


def catalogue_for_model(spec: str) -> Path:
    """The learned catalogue of one generator model: each model learns into, and
    reuses, its own file, so two models can run side by side without mixing."""
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(spec)).strip("-") or "default"
    # the tree of the tool-using agents: guidelines/learned/<model>/agents/
    return pipeline_config.LEARNED_BY_MODEL / slug / "agents" / "learned_guidelines.json"


def choose_catalogue_for_run(generator_spec: str, saved: str | None = None) -> Path:
    """Point the store at the catalogue of this run and return it. A resumed run
    keeps the file it started with; an API started with GUIDEBPMN_CATALOGUE (or
    a test that replaced the file) keeps its own; otherwise the generator model's."""
    global LEARNED_GUIDELINES, _SET_BY_RUN
    if saved:
        target = pipeline_config.resolve_path(saved)
    elif os.environ.get("GUIDEBPMN_CATALOGUE", "").strip():
        target = pipeline_config.LEARNED_GUIDELINES
    elif LEARNED_GUIDELINES in (pipeline_config.DEFAULT_LEARNED_GUIDELINES, _SET_BY_RUN):
        target = catalogue_for_model(generator_spec)
    else:
        return LEARNED_GUIDELINES                       # replaced by a test: leave it
    LEARNED_GUIDELINES = _SET_BY_RUN = target
    return target


def current_catalogue() -> Path:
    return LEARNED_GUIDELINES


def model_catalogues() -> list[dict]:
    """Every per-model catalogue on disk, most recently changed first."""
    out = []
    root = pipeline_config.LEARNED_BY_MODEL
    for path in sorted(root.glob("*/agents/learned_guidelines.json")) if root.is_dir() else []:
        try:
            items = json.loads(path.read_text(encoding="utf-8")).get("guidelines", [])
        except (OSError, ValueError):
            items = []
        out.append({"model": path.parent.parent.name, "file": str(path), "count": len(items),
                    "general": sum(g.get("status") == "promoted" for g in items),
                    "changed": path.stat().st_mtime})
    return sorted(out, key=lambda c: -c["changed"])

def run_catalogues() -> list[dict]:
    """The catalogues of the final study, most recently changed first: one per
    repetition of the learning run (replicates/r1..r3) and one per round of the
    cross-validation (folds/fold_1..5), for every generator model."""
    out = []
    root = pipeline_config.LEARNED_BY_MODEL
    if not root.is_dir():
        return out
    for pattern, kind in (("*/agents/replicates/r*/learned_guidelines.json", "replicate"),
                          ("*/agents/folds/fold_*/learned_guidelines.json", "fold"),
                          ("*/agents/trials/trial_*/learned_guidelines.json", "trial")):
        for path in sorted(root.glob(pattern)):
            try:
                items = json.loads(path.read_text(encoding="utf-8")).get("guidelines", [])
            except (OSError, ValueError):
                items = []
            agents = True                             # learned by the tool-using agents
            model = path.parents[3].name
            part = path.parent.name
            label = (f"{model} \u00b7 Revised run {part[1:]}" if kind == "replicate"
                     else f"{model} \u00b7 trial of {part.split('_', 1)[-1]} (a few descriptions)" if kind == "trial"
                     else f"{model} \u00b7 Reuse round {part.split('_')[-1]} (training)")
            general = [g for g in items if g.get("status") == "promoted"]
            out.append({"id": f"{model}/{'agents/' if agents else ''}{path.parent.parent.name}/{part}",
                        "model": model, "learning_agents": "tools" if agents else "roles",
                        "label": label, "file": str(path), "count": len(items),
                        "general": len(general),
                        "confirmed": sum(bool((g.get("confirmation") or {}).get("confirmed"))
                                         for g in general),
                        "changed": path.stat().st_mtime})
    return sorted(out, key=lambda c: -c["changed"])


_WORD = re.compile(r"[a-zA-Z][a-zA-Z\-']+")

# Vocabulary that is always allowed, besides BPMN terms.
_GENERIC = {
    "process", "task", "activity", "event", "gateway", "flow", "sequence",
    "message", "pool", "lane", "participant", "subprocess", "start", "end",
    "intermediate", "boundary", "timer", "condition", "conditional", "error",
    "signal", "escalation", "parallel", "exclusive", "inclusive", "branch",
    "path", "loop", "decision", "outcome", "trigger", "label", "model",
    "diagram", "description", "element", "node", "catch", "throw", "default",
    "split", "join", "merge", "deadline", "delay", "duration", "actor", "role",
    "sender", "receiver", "notify", "notification", "request", "approval",
    "approve", "reject", "alternative", "stated", "describe", "described",
    "when", "then", "never", "always", "only", "each", "every", "must", "use",
    "add", "remove", "keep", "between", "after", "before", "with", "without",
    "the", "and", "that", "this", "its", "their", "not", "for", "from", "into",
}


_DESCRIPTION_SCOPE = None   # ids of the descriptions a learning run may read (k-fold: training only)


def set_description_scope(ids) -> None:
    """Restrict the word counts of the abstraction filter to these descriptions
    (in k-fold cross-validation, the training descriptions of the fold), so that
    nothing of the test descriptions is read while learning. None = all."""
    global _DESCRIPTION_SCOPE
    _DESCRIPTION_SCOPE = None if ids is None else {str(i) for i in ids}


def _description_df() -> Counter:
    """In how many dataset descriptions (of the scope) does each word appear?"""
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    if _DESCRIPTION_SCOPE is not None:
        data = [e for e in data if str(e["id"]) in _DESCRIPTION_SCOPE]
    df = Counter()
    for entry in data:
        words = {w.lower() for w in _WORD.findall(entry["description"])}
        df.update(words)
    return df


def abstraction_violations(instruction: str, source_description: str,
                           df: Counter | None = None,
                           rare_below: int = 3) -> list[str]:
    """Words that tie the instruction to its source example.

    A word is a violation when it appears in the source description, is NOT
    generic/BPMN vocabulary, and occurs in fewer than `rare_below` of the descriptions
    in scope (all 55, or the training descriptions of a fold) (i.e., it is domain-specific, like 'dish' or 'invoice').
    An empty list means the wording passes the abstraction filter.
    """
    df = df or _description_df()
    source_words = {w.lower() for w in _WORD.findall(source_description)}
    out = []
    for word in {w.lower() for w in _WORD.findall(instruction)}:
        if word in _GENERIC or len(word) <= 3:
            continue
        if word in source_words and df.get(word, 0) < rare_below:
            out.append(word)
    return sorted(out)


def load_store() -> dict:
    if LEARNED_GUIDELINES.exists():
        return json.loads(LEARNED_GUIDELINES.read_text(encoding="utf-8"))
    return {"version": "2.0", "schema": "trigger-based, promotion on evidence",
            "guidelines": []}


def save_store(store: dict) -> None:
    store["updated_at_utc"] = datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    LEARNED_GUIDELINES.parent.mkdir(parents=True, exist_ok=True)
    LEARNED_GUIDELINES.write_text(
        json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def next_id(store: dict, prefix: str = "LRN") -> str:
    used = {g["id"] for g in store["guidelines"]}
    n = 1
    while f"{prefix}-{n:03d}" in used:
        n += 1
    return f"{prefix}-{n:03d}"


def documentation_rules() -> list[dict]:
    doc = json.loads(DOCUMENTATION_GUIDELINES.read_text(encoding="utf-8"))
    return [dict(rule, category=section["category"])
            for section in doc["sections"] for rule in section["rules"]]


def duplicates_documentation(instruction: str, threshold: float = 0.6) -> dict | None:
    """Cheap lexical duplicate check against the documentation catalogue.

    Returns the most-overlapping documentation rule when Jaccard word overlap
    >= threshold, else None. (An embedding check can replace this later; the
    lexical gate alone already catches restatements.)
    """
    cand = {w.lower() for w in _WORD.findall(instruction)} - _GENERIC
    best, best_score = None, 0.0
    for rule in documentation_rules():
        ref = {w.lower() for w in _WORD.findall(rule["instruction"])} - _GENERIC
        if not cand or not ref:
            continue
        score = len(cand & ref) / len(cand | ref)
        if score > best_score:
            best, best_score = rule, score
    return best if best_score >= threshold else None


def promotion_ready(entry: dict) -> bool:
    fires = set(entry.get("support", {}).get("fires_on", []))
    fires -= set(entry.get("support", {}).get("learned_from", []))
    gains = entry.get("support", {}).get("gain", {})
    no_harm = all(v >= 0 for v in gains.values()) if gains else False
    return len(fires) >= PROMOTION_MIN_SUPPORT and no_harm


def add_guideline(store: dict, candidate: dict, failure_type: str, example_id: str,
                  relation: dict, cited_records: list[dict], status: str = "promoted",
                  learned_from: list[str] | None = None,
                  evidence: list[dict] | None = None, generalized_from: list[str] | None = None) -> str:
    """Append one guideline and save the catalogue; returns its id.

    status "promoted": a generic guideline (LRN-xxx), reusable on other descriptions.
    status "example_specific": tied to its description (EXS-xxx); sent back to the
    generator for that description only, never reused on another one."""
    specific = status == "example_specific"
    gid = next_id(store, "EXS" if specific else "LRN")
    entry = {
        "id": gid,
        "category": candidate.get("category") or "Learned",
        "family": failure_type,
        "trigger": candidate["trigger"],
        "instruction": candidate["instruction"],
        "status": status,
        "support": {"learned_from": [str(e) for e in (learned_from or [example_id])]},
        "baseline_relation": relation,
        "evidence": evidence if evidence is not None else [
            {"example_id": str(example_id),
             "records": [{"id": r["id"], "text": r["text"]} for r in cited_records]}],
        "provenance": {"created_at": datetime.datetime.now(datetime.timezone.utc)
                       .strftime("%Y-%m-%dT%H:%M:%SZ")},
    }
    if specific:
        entry["scope"] = {"example_id": str(example_id)}
    if generalized_from:
        entry["generalized_from"] = list(generalized_from)
    store["guidelines"].append(entry)
    save_store(store)
    return gid


def mark_generalized(store: dict, specific_id: str, general_id: str,
                     trace_only: bool = False) -> None:
    """An example-specific guideline was folded into a general one. trace_only:
    it is the Expert's first, context-dependent wording of that general one,
    kept for traceability and never sent to the generator."""
    for g in store["guidelines"]:
        if g["id"] == specific_id:
            g["generalized_into"] = general_id
            if trace_only:
                g["trace_only"] = True
    save_store(store)


def start_empty(stamp: str) -> Path | None:
    """A learning run starts from an empty catalogue: the current one is moved
    (never deleted) to guidelines/archive/. Returns where it went."""
    if not LEARNED_GUIDELINES.exists():
        return None
    current = load_store()
    if not current.get("guidelines"):
        return None
    folder = LEARNED_GUIDELINES.parent / "archive"
    folder.mkdir(parents=True, exist_ok=True)
    kept = folder / f"learned_guidelines_before_{stamp}.json"
    LEARNED_GUIDELINES.replace(kept)
    save_store({"version": current.get("version", "2.0"),
                "schema": current.get("schema", "trigger-based, promotion on evidence"),
                "guidelines": []})
    return kept


# A guideline is confirmed when sending it back improved the model of the example
# by a clear margin. Two generations of the same example already differ by about
# 0.05 on one score, so the margin applies to the mean change of the four scores.
CONFIRMATION_MARGIN = 0.03
EFFECT_KEYS = ("semantic_similarity", "workflow_order_similarity", "connection_f1",
               "alignment_coverage")


def effect_of(before: dict, after: dict, valid_before: bool, valid_after: bool) -> dict:
    """What one next iteration changed: the scores after, the change of each
    score, their mean, and whether it counts as an improvement."""
    changes = {k: round(after[k] - before[k], 6) for k in EFFECT_KEYS
               if before.get(k) is not None and after.get(k) is not None}
    mean_change = round(sum(changes.values()) / len(changes), 6) if changes else 0.0
    return {"after": {k: after.get(k) for k in EFFECT_KEYS}, "valid_after": valid_after,
            "changes": changes, "mean_change": mean_change,
            "confirmed": bool(mean_change >= CONFIRMATION_MARGIN
                              and (valid_after or not valid_before))}


def _apply_test(guideline: dict, example_id, effect: dict) -> None:
    box = guideline.setdefault("confirmation", {"tests": []})
    box["tests"] = [t for t in box["tests"] if not (t["example_id"] == str(example_id)
                                                     and t.get("run") == effect.get("run"))]
    box["tests"].append({"example_id": str(example_id), "run": effect.get("run"),
                         "mean_change": effect["mean_change"], "changes": effect["changes"],
                         "sent_with": [i for i in effect["sent"] if i != guideline["id"]]})
    mean = sum(t["mean_change"] for t in box["tests"]) / len(box["tests"])
    box["mean_change"] = round(mean, 6)
    box["margin"] = CONFIRMATION_MARGIN
    box["confirmed"] = bool(mean >= CONFIRMATION_MARGIN)


def type_test(guideline: dict, effect: dict) -> dict:
    """What one next iteration did to the errors of the type a guideline was
    learned from (its family, T1-T7)."""
    failure_type = guideline.get("family") or guideline.get("failure_type")
    before = (effect.get("errors_before") or {}).get(failure_type, 0) or 0
    after = (effect.get("errors_after") or {}).get(failure_type, 0) or 0
    return {"failure_type": failure_type, "errors_before": before, "errors_after": after,
            "removed": before - after}


CONFIRMATION_RULE = ("confirmed when, after it is sent back, the number of errors of the type it "
                     "was learned from goes down (over its tests) and the new model is kept")


def record_type_tests(example_id, effect: dict, store: dict | None = None,
                      save: bool = True) -> dict:
    """Confirmation of the guidelines sent in one next iteration, each by the
    errors of its own type. Returns {guideline id: type test}; with save, the
    test is written in the guideline's confirmation box."""
    own = store is None
    store = load_store() if own else store
    results = {}
    for g in store["guidelines"]:
        if g["id"] not in effect.get("sent", []):
            continue
        test = type_test(g, effect)
        results[g["id"]] = test
        if save:
            box = g.setdefault("confirmation", {"tests": []})
            box["tests"] = [t for t in box.get("tests", [])
                            if "removed" in t and not (t["example_id"] == str(example_id)
                                                       and t.get("run") == effect.get("run")
                                                       and t.get("iteration") == effect.get("iteration"))]
            box["tests"].append({"example_id": str(example_id), "run": effect.get("run"),
                                 "iteration": effect.get("iteration"), **test,
                                 "sent_with": [i for i in effect["sent"] if i != g["id"]]})
            box["errors_removed"] = sum(t["removed"] for t in box["tests"])
            box["rule"] = CONFIRMATION_RULE
            box.pop("margin", None)
            box.pop("mean_change", None)
            box["confirmed"] = box["errors_removed"] > 0
    if own and save and results:
        save_store(store)
    return results


def supersede_tests(example_id, reason: str, stamp: str, store: dict | None = None) -> list[str]:
    """A description is run again (its first attempt lost a step to an
    infrastructure error): the confirmation tests of its first attempt are moved
    to the history of each guideline (superseded_tests) and the confirmation is
    recomputed from the remaining tests. Nothing is deleted. The guidelines its
    first attempt learned stay in the catalogue: when the description is run
    again, the Expert finds them and merges into them, and they are tested again."""
    own = store is None
    store = load_store() if own else store
    touched = []
    for g in store["guidelines"]:
        box = g.get("confirmation")
        if not box:
            continue
        old = [t for t in box.get("tests", []) if str(t.get("example_id")) == str(example_id)]
        if not old:
            continue
        box.setdefault("superseded_tests", []).extend(
            dict(t, superseded_at=stamp, superseded_because=reason) for t in old)
        box["tests"] = [t for t in box["tests"] if str(t.get("example_id")) != str(example_id)]
        box["errors_removed"] = sum(t.get("removed", 0) for t in box["tests"])
        box["confirmed"] = box["errors_removed"] > 0
        touched.append(g["id"])
    if own and touched:
        save_store(store)
    return touched


def record_tests(example_id, effect: dict, store: dict | None = None) -> list[str]:
    """Write the measured effect of one next iteration on the learned guidelines
    that were sent in it (several guidelines sent together share the result)."""
    own = store is None
    store = load_store() if own else store
    touched = []
    for g in store["guidelines"]:
        if g["id"] in effect["sent"]:
            _apply_test(g, example_id, effect)
            touched.append(g["id"])
    if own and touched:
        save_store(store)
    return touched


def confirm_from_run(run_dir: Path) -> dict:
    """Fill the confirmations from a finished learning run (its saved files)."""
    store = load_store()
    tested = 0
    for folder in sorted(Path(run_dir).glob("id_*")):
        path = folder / "iterations.json"
        if not path.is_file():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        effects = doc.get("next_iterations")
        if not effects:                       # runs made before the effects were saved
            feedback, first = doc.get("rule_feedback"), doc.get("first_pass") or {}
            if not feedback or not first.get("metrics"):
                continue
            kept = next((i for i in doc["iterations"] if i["round"] == doc.get("kept_round")), {})
            effect = {"iteration": 1, "sent": [r["rule_id"] for r in feedback["rules"]],
                      **effect_of(first["metrics"], doc["final_metrics"],
                                  bool(first.get("valid")), bool(kept.get("valid")))}
            effects = [effect]
        for effect in effects:
            if "mean_change" in effect:
                effect = dict(effect, run=Path(run_dir).name)
                tested += bool(record_tests(doc["id"], effect, store))
    save_store(store)
    learned = [g for g in store["guidelines"] if g.get("confirmation")]
    return {"run": Path(run_dir).name, "next_iterations_used": tested,
            "guidelines_tested": len(learned),
            "confirmed": sorted(g["id"] for g in learned if g["confirmation"]["confirmed"])}


def add_support(store: dict, guideline_id: str, example_id: str,
                cited_records: list[dict]) -> None:
    """Another example led to the same guideline: record it as extra support."""
    for g in store["guidelines"]:
        if g["id"] == guideline_id:
            seen = g.setdefault("support", {}).setdefault("learned_from", [])
            if str(example_id) not in seen:
                seen.append(str(example_id))
                g.setdefault("evidence", []).append(
                    {"example_id": str(example_id),
                     "records": [{"id": r["id"], "text": r["text"]} for r in cited_records]})
            save_store(store)
            return
    raise KeyError(guideline_id)
