"""Guideline agents of GuideBPMN: the evidence records, the code guards and the
catalogue update around the Retriever and Expert agents (guideline_agents_tools.py).

For one evaluated example and each failure reported by the Failure Detector:

  1. build_records   (code)  turns the evidence files into numbered records:
                             description sentences, validator findings,
                             Similarity Evaluator results.
  2. Retriever agent (LLM, ReAct loop with tools) selects the records relevant
                             to this failure and explains the error.
  3. Expert agent    (LLM, ReAct loop with tools) reads the description and the
                             selected records, consults the closest documentation
                             and learned guidelines, checks its wording, and
                             proposes one guideline (trigger + instruction) with
                             its relation (contradicts / not applied / refines /
                             new / same as a learned one), or abstains (it is
                             then asked once more, since the failure remains); a
                             wording tied to this process is rewritten once.
  4. check_candidate (code)  citations must exist; no label that exists only
                             in the reference; the Expert's relation must name a
                             guideline it was shown; no near-copy of a learned
                             one. A guideline still tied to its process after one
                             rewrite (rare domain words) is kept as
                             EXAMPLE-SPECIFIC: sent back for its own example,
                             never reused on another description.
  4b. generalization (LLM)   when a guideline resembles an example-specific one
                             learned from ANOTHER example, the Expert may write
                             one general guideline covering both; it then
                             enters the catalogue with both examples as support.
  4c. promotion (LLM, option) an example-specific guideline whose return
                             improved the model of its own example is given to
                             the Expert once more, to be written in general terms.
  5. the catalogue           guidelines/learned_guidelines.json is updated.

The agents never open the gold BPMN file: they work on the Similarity
Evaluator's results (labels included).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

import numpy as np

from evidence_package import GoldLeak, assert_gold_blind
import guideline_store as store_module

MAX_SELECTED = 12
DUPLICATE_COSINE, REFINES_COSINE = 0.88, 0.72
DUPLICATE_LEXICAL = 0.60

FAILURE_MEANING = {
    "T1": "Invalid or unparseable XML (validator L1)",
    "T2": "Incorrect gateway use (validator L2)",
    "T3": "Incorrect control flow (validator L3)",
    "T4": "Malformed pools, lanes or message flows (validator L4)",
    "T5": "Structural divergence from the reference (elements, flows, order)",
    "T6": "Semantic divergence from the reference (labels)",
    "T7": "Collaboration divergence from the reference (pools, lanes, messages)",
}
LEVEL_OF = {"T1": "L1", "T2": "L2", "T3": "L3", "T4": "L4"}


# ------------------------------------------------------------- 1. records --
def _el(e: dict) -> str:
    label = e.get("label") or ""
    return f"{e.get('type')} \"{label}\"" if label else str(e.get("type"))


def build_records(run_dir: Path) -> list[dict]:
    """Numbered, citable evidence records from the four evidence files."""
    run_dir = Path(run_dir)
    description = (run_dir / "validator" / "process_description.txt").read_text(encoding="utf-8")
    profile = json.loads((run_dir / "validator" / "validation_profile.json")
                         .read_text(encoding="utf-8")).get("validation_profile", {})
    sim = json.loads((run_dir / "similarity" / "similarity_results.json")
                     .read_text(encoding="utf-8"))
    records = []

    def add(rid, kind, text, source):
        records.append({"id": rid, "kind": kind, "text": " ".join(str(text).split()),
                        "source": source})

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", description) if s.strip()]
    for i, sentence in enumerate(sentences[:80], 1):
        add(f"S{i}", "description", sentence, "process_description.txt")

    for level, data in profile.items():
        if data.get("result") is False:
            add(f"V-{level}", f"validator_{level}", data.get("message") or "",
                "validation_profile.json")
            for j, element in enumerate((data.get("error_elements") or [])[:10], 1):
                add(f"V-{level}-{j}", f"validator_{level}", f"element in error: {element}",
                    "validation_profile.json")

    src = "similarity_results.json"
    add("METRICS", "metrics", json.dumps(sim.get("metrics", {})), src)
    add("COUNTS", "counts", json.dumps({"by_type": sim.get("element_counts_by_type", {}),
                                        **sim.get("counts", {})}), src)
    for i, e in enumerate(sim.get("reference_elements_without_counterpart", [])[:25], 1):
        where = []
        if e.get("after_generated"):
            where.append("after " + ", ".join(_el(x) for x in e["after_generated"]))
        if e.get("before_generated"):
            where.append("before " + ", ".join(_el(x) for x in e["before_generated"]))
        add(f"M{i}", "missing_element",
            f"reference {_el(e)} has no counterpart in the generated model"
            + (" (" + "; ".join(where) + ")" if where else ""), src)
    for i, e in enumerate(sim.get("generated_elements_without_counterpart", [])[:25], 1):
        add(f"X{i}", "extra_element",
            f"generated {_el(e)} has no counterpart in the reference", src)
    pairs = [p for p in sim.get("matched_elements", [])
             if (p.get("label_similarity") is not None and p["label_similarity"] < 0.999)]
    pairs.sort(key=lambda p: p["label_similarity"])
    for i, p in enumerate(pairs[:15], 1):
        add(f"P{i}", "label_pair",
            f"{p.get('type')}: generated \"{p.get('generated_label')}\" matched to reference "
            f"\"{p.get('reference_label')}\" (label similarity {round(p['label_similarity'], 3)})", src)
    for i, f in enumerate(sim.get("reference_flows_absent_from_generated", [])[:25], 1):
        add(f"F{i}", "missing_flow",
            f"reference flow {_el(f['from'])} -> {_el(f['to'])} is absent from the generated model", src)
    for i, f in enumerate(sim.get("generated_flows_absent_from_reference", [])[:25], 1):
        add(f"G{i}", "extra_flow",
            f"generated flow {_el(f['from'])} -> {_el(f['to'])} is absent from the reference", src)
    # pools, lanes, memberships and message flows on which the two models differ
    for i, c in enumerate(sim.get("collaboration_differences", [])[:30], 1):
        add(f"C{i}", "collaboration", c["text"], src)
    return records


def records_for(failure_type: str, records: list[dict]) -> list[dict]:
    """The records a given failure type may draw on (the Retriever picks among them)."""
    level = LEVEL_OF.get(failure_type)
    if level:
        kinds = {"description", f"validator_{level}"}
    elif failure_type == "T6":
        kinds = {"description", "label_pair", "missing_element", "extra_element", "metrics"}
    elif failure_type == "T7":
        kinds = {"description", "collaboration", "missing_element", "extra_element",
                 "counts", "metrics"}
    else:   # T5
        kinds = {"description", "missing_element", "extra_element", "missing_flow",
                 "extra_flow", "counts", "metrics"}
    return [r for r in records if r["kind"] in kinds]


# ------------------------------------------------------------ 2. Retriever --
# (the Retriever agent itself is in guideline_agents_tools.py; here, its completeness guard)
MAX_COUNTERPARTS = 4


def possible_counterparts(selected: list[dict], pool: list[dict]) -> list[dict]:
    """Generated elements without counterpart that share wording with a selected
    missing reference element: the same element may have been modeled differently
    (other type, other pool). Added so the Expert does not mistake it for a gap."""
    def label(text):
        found = re.findall(r'"([^"]*)"', text)
        return found[0] if found else ""
    missing = [label(r["text"]) for r in selected if r["kind"] == "missing_element"]
    chosen = {r["id"] for r in selected}
    out = []
    for r in pool:
        if r["kind"] != "extra_element" or r["id"] in chosen:
            continue
        if any(m and _lexical(m, label(r["text"])) >= 0.25 for m in missing):
            out.append(r)
    return out[:MAX_COUNTERPARTS]


# --------------------------------------------------------------- 3. Expert --
# (the Expert agent itself is in guideline_agents_tools.py; below, the relation prompt
# used when a confirmed or generalized guideline is classified, and the code guards)
RELATION_SYSTEM = (
    "You are the Expert agent of GuideBPMN. You proposed a modeling guideline. Compare it with "
    "the guidelines already learned from other examples (learned_guidelines) and with the "
    "documentation guidelines (paraphrased from the OMG BPMN 2.0.2 specification), and "
    "classify it:\n"
    "- \"same_as_learned\": a given learned guideline already says essentially the same thing "
    "(same situation, same modeling advice), even in other words. Give its id.\n"
    "- \"not_applied\": a given documentation rule already says the same thing; the generator "
    "simply did not apply it. Give that rule's id.\n"
    "- \"refines\": a given documentation rule covers the topic, and your guideline adds when "
    "or how to apply it (for example the wording of the description that calls for it). Give "
    "that rule's id.\n"
    "- \"new\": no given rule covers it.\n"
    "- \"contradicts\": your guideline asks for a model that a given documentation rule forbids "
    "or advises against (for example a task where the rule asks for an intermediate catch event "
    "when the flow waits for a trigger, or an exclusive gateway where every branch must be "
    "completed before continuing). Give that rule's id. Check this first.\n"
    "Use only ids from the lists. Return JSON: {\"relation\": \"contradicts\" | \"same_as_learned\" | "
    "\"not_applied\" | \"refines\" | \"new\", \"rule_id\": \"...\" or null, \"reason\": \"...\"}."
)
NEAREST_SHOWN = 6
NEAREST_LEARNED_SHOWN = 4


def nearest_rules(text: str, rules: list[dict], embedder, k: int = NEAREST_SHOWN) -> list[dict]:
    """The k documentation rules closest to a text, each with its scores."""
    if not rules:
        return []
    texts = [text] + [r["instruction"] for r in rules]
    vectors = np.asarray(embedder.encode(texts, normalize_embeddings=True,
                                         show_progress_bar=False), dtype=float)
    cosines = vectors[1:] @ vectors[0]
    scored = [dict(r, cosine=float(cosines[i]), lexical=_lexical(text, r["instruction"]))
              for i, r in enumerate(rules)]
    scored.sort(key=lambda r: max(r["cosine"], r["lexical"]), reverse=True)
    return scored[:k]


def classify_relation(candidate: dict, shown: list[dict], llm,
                      learned_shown: Optional[list[dict]] = None) -> dict:
    """The Expert's own judgement of how its guideline relates to the guidelines
    already learned and to the documentation."""
    reply = llm.complete_json(system=RELATION_SYSTEM, user=json.dumps({
        "guideline": {"trigger": candidate["trigger"], "instruction": candidate["instruction"]},
        "learned_guidelines": [{"id": g["id"], "rule": f"When {g['trigger']}: {g['instruction']}"}
                               for g in (learned_shown or [])],
        "documentation_guidelines": [{"id": r["id"], "category": r.get("category"),
                                      "rule": r["instruction"]} for r in shown],
    }, ensure_ascii=False))
    relation = str(reply.get("relation", "")).strip().lower()
    rule_id = reply.get("rule_id")
    return {"relation": relation if relation in ("contradicts", "same_as_learned", "not_applied",
                                                 "refines", "new") else None,
            "rule_id": str(rule_id).strip() if rule_id else None,
            "reason": str(reply.get("reason", ""))[:400]}


# --------------------------------------------------------------- 4. checks --
def _lexical(a: str, b: str) -> float:
    wa = {w for w in re.findall(r"[a-z][a-z\-']+", a.lower()) if len(w) > 3}
    wb = {w for w in re.findall(r"[a-z][a-z\-']+", b.lower()) if len(w) > 3}
    return len(wa & wb) / len(wa | wb) if wa and wb else 0.0


def nearest(text: str, rules: list[dict], embedder) -> tuple[Optional[dict], float, float]:
    """Closest rule: (rule, cosine, lexical overlap)."""
    best = nearest_rules(text, rules, embedder, k=1)
    if not best:
        return None, 0.0, 0.0
    return best[0], best[0]["cosine"], best[0]["lexical"]


def form_problem(candidate: dict, dossier: dict, *, gold_xml: str, generated_xml: str,
                 description: str) -> Optional[dict]:
    """Citations, completeness, labels found only in the reference."""
    given = {r["id"] for r in dossier["selected"]}
    if not candidate["cited"] or not set(candidate["cited"]) <= given:
        return {"status": "rejected_bad_citation",
                "detail": f"cited {candidate['cited']} but was given {sorted(given)}"}
    if len(candidate["instruction"]) < 15 or len(candidate["trigger"]) < 10:
        return {"status": "rejected_incomplete", "detail": "trigger or instruction too short"}
    try:
        assert_gold_blind(candidate["trigger"] + " " + candidate["instruction"],
                          gold_xml, generated_xml, description)
    except GoldLeak as exc:
        return {"status": "rejected_reference_label", "detail": str(exc)}
    return None


def too_specific(candidate: dict, description: str) -> list[str]:
    """Words that tie the guideline to its source process (rare domain words)."""
    return store_module.abstraction_violations(
        candidate["trigger"] + " " + candidate["instruction"], description)


def relation_outcome(candidate: dict, shown: list[dict], judged: Optional[dict]) -> dict:
    """Status from the Expert's classification, checked by code.

    The Expert's choice stands when it names a rule it was shown. A guideline
    called new that is nearly identical to a documentation rule is still
    treated as that rule (safety net). Without a usable classification, the
    similarity thresholds decide."""
    by_id = {r["id"]: r for r in shown}
    top = shown[0] if shown else None
    near_copy = top and (top["cosine"] >= DUPLICATE_COSINE or top["lexical"] >= DUPLICATE_LEXICAL)
    if judged and judged.get("relation") == "contradicts" and judged.get("rule_id") in by_id:
        ref = judged["rule_id"]
        return {"status": "rejected_contradicts_documentation", "ref": ref, "judged_by": "expert",
                "detail": f"contradicts documentation rule {ref} ({judged.get('reason', '')})"}
    if judged and judged.get("relation") in ("not_applied", "refines") and judged.get("rule_id") in by_id:
        ref = judged["rule_id"]
        if judged["relation"] == "not_applied":
            return {"status": "existing_documentation_rule", "ref": ref, "judged_by": "expert",
                    "detail": f"documentation rule {ref} not applied ({judged.get('reason', '')})"}
        return {"status": "promoted", "relation": {"type": "refines", "ref": ref},
                "judged_by": "expert", "detail": f"refines {ref} ({judged.get('reason', '')})"}
    if near_copy:
        return {"status": "existing_documentation_rule", "ref": top["id"], "judged_by": "similarity",
                "detail": f"same as {top['id']} (cosine {top['cosine']:.2f}, overlap {top['lexical']:.2f})"}
    if judged and judged.get("relation") == "new":
        return {"status": "promoted", "relation": {"type": "new", "ref": None},
                "judged_by": "expert", "detail": f"new guideline ({judged.get('reason', '')})"}
    if top and top["cosine"] >= REFINES_COSINE:
        return {"status": "promoted", "relation": {"type": "refines", "ref": top["id"]},
                "judged_by": "similarity", "detail": f"refines {top['id']} (cosine {top['cosine']:.2f})"}
    return {"status": "promoted", "relation": {"type": "new", "ref": None},
            "judged_by": "similarity", "detail": "new guideline"}


def check_candidate(candidate: dict, dossier: dict, *, gold_xml: str, generated_xml: str,
                    description: str, documentation: list[dict], learned: list[dict],
                    embedder, judged: Optional[dict] = None,
                    shown: Optional[list[dict]] = None,
                    learned_shown: Optional[list[dict]] = None) -> dict:
    """Outcome of the automatic checks for one proposed guideline."""
    problem = form_problem(candidate, dossier, gold_xml=gold_xml,
                           generated_xml=generated_xml, description=description)
    if problem:
        return problem
    if (judged and judged.get("relation") == "same_as_learned"
            and judged.get("rule_id") in {g["id"] for g in (learned_shown or [])}):
        return {"status": "merged_with_learned", "ref": judged["rule_id"], "judged_by": "expert",
                "detail": f"same as {judged['rule_id']} ({judged.get('reason', '')})"}
    shown = shown if shown is not None else nearest_rules(candidate["instruction"], documentation, embedder)
    outcome = relation_outcome(candidate, shown, judged)
    if outcome["status"] != "promoted":
        return outcome
    words = too_specific(candidate, description)
    if words:
        return {"status": "example_specific", "relation": outcome["relation"],
                "detail": "kept for this example only, tied to it by: " + ", ".join(words)}
    known, cosine_l, lexical_l = nearest(candidate["instruction"], learned, embedder)
    if known and (cosine_l >= DUPLICATE_COSINE or lexical_l >= DUPLICATE_LEXICAL):
        return {"status": "merged_with_learned", "ref": known["id"],
                "detail": f"same as {known['id']} (cosine {cosine_l:.2f})"}
    return outcome


# ------------------------------------------------------ 4b. generalize ----
GENERALIZE_SYSTEM = (
    "You are the Expert agent of GuideBPMN. Two modeling guidelines were learned from two "
    "different processes; at least one of them is still worded in terms of its own process. "
    "If both describe the same modeling situation, write ONE guideline in general terms that "
    "covers both: trigger = the situation as observable in any process description (start "
    "with 'the description ...'), instruction = what to model in BPMN. Use no domain word of "
    "either process. If they describe different situations, answer no. "
    "Return JSON: {\"decision\": \"generalize\" or \"no\", \"trigger\": \"...\", "
    "\"instruction\": \"...\", \"category\": one of the given categories, \"reason\": \"...\"}."
)
GENERALIZE_COSINE, GENERALIZE_LEXICAL = 0.72, 0.35


def _description_of(example_id: str) -> str:
    from pipeline_config import DATASET_PATH
    for e in json.loads(DATASET_PATH.read_text(encoding="utf-8")):
        if str(e["id"]) == str(example_id):
            return e["description"]
    return ""


def try_generalize(candidate: dict, entry: dict, store: dict, documentation: list[dict],
                   categories: list[str], expert_llm, embedder) -> Optional[dict]:
    """A general guideline covering this candidate and an example-specific one
    from another example, or None. Checked like any guideline."""
    others = [g for g in store["guidelines"]
              if g.get("status") == "example_specific" and not g.get("generalized_into")
              and str(entry["id"]) not in g["support"]["learned_from"]]
    match, cosine, lexical = nearest(candidate["instruction"], others, embedder)
    if not match or (cosine < GENERALIZE_COSINE and lexical < GENERALIZE_LEXICAL):
        return None
    reply = expert_llm.complete_json(system=GENERALIZE_SYSTEM, user=json.dumps({
        "guidelines_to_generalize": [
            {"trigger": candidate["trigger"], "instruction": candidate["instruction"]},
            {"trigger": match["trigger"], "instruction": match["instruction"]}],
        "categories": categories}, ensure_ascii=False))
    if str(reply.get("decision", "")).lower() != "generalize":
        return {"status": "not_generalized", "with": match["id"],
                "reason": str(reply.get("reason", ""))[:300]}
    general = {"decision": "propose", "trigger": " ".join(str(reply.get("trigger", "")).split()),
               "instruction": " ".join(str(reply.get("instruction", "")).split()),
               "category": str(reply.get("category", "")) or candidate.get("category", "")}
    other_example = match["support"]["learned_from"][0]
    words = sorted(set(too_specific(general, entry["description"])
                       + too_specific(general, _description_of(other_example))))
    if len(general["instruction"]) < 15 or len(general["trigger"]) < 10 or words:
        return {"status": "not_generalized", "with": match["id"],
                "reason": "still tied to a process: " + ", ".join(words) if words else "incomplete"}
    shown = nearest_rules(general["instruction"], documentation, embedder)
    outcome = relation_outcome(general, shown, classify_relation(general, shown, expert_llm))
    if outcome["status"] != "promoted":
        return {"status": "not_generalized", "with": match["id"],
                "reason": "the general form is documentation rule " + str(outcome.get("ref"))}
    return {"status": "generalized", "with": match, "guideline": general,
            "relation": outcome["relation"]}


# ------------------------------------- 4c. promotion after confirmation ----
PROMOTE_SYSTEM = (
    "You are the Expert agent of a BPMN generation system. A modeling guideline was learned "
    "from one process and is still worded in terms of that process. It was sent back to the "
    "generator for that process, and the model measurably improved. Rewrite it as ONE "
    "guideline in general terms, usable for any process description: trigger = the situation "
    "as observable in a description (start with 'the description ...'), instruction = what to "
    "model in BPMN. Use none of the words listed in words_to_avoid and no other word of the "
    "business domain of that process. If the guideline only makes sense for that process, "
    "answer no. Return JSON: {\"decision\": \"generalize\" or \"no\", \"trigger\": \"...\", "
    "\"instruction\": \"...\", \"category\": one of the given categories, \"reason\": \"...\"}."
)


def promote_confirmed(entry: dict, sent_ids: list[str], expert_llm, embedder) -> list[dict]:
    """After a next iteration that improved the model: each example-specific
    guideline of this example that was sent in it is given to the Expert once
    more, to be written in general terms. The general form is checked like any
    guideline (no word tied to the process, not a documentation rule, not a
    copy of a learned one) and then enters the learned catalogue; the
    example-specific one keeps a pointer to it. One row per guideline tried."""
    import copy
    store = store_module.load_store()
    documentation = store_module.documentation_rules()
    categories = sorted({r["category"] for r in documentation})
    description, example = entry["description"], str(entry["id"])
    rows = []
    for specific in [g for g in store["guidelines"]
                     if g["id"] in sent_ids and g.get("status") == "example_specific"
                     and not g.get("generalized_into") and not g.get("trace_only")
                     and example in g["support"]["learned_from"]]:
        row = {"specific_id": specific["id"]}
        try:
            words = too_specific(specific, description)
            reply = expert_llm.complete_json(system=PROMOTE_SYSTEM, user=json.dumps({
                "guideline": {"trigger": specific["trigger"], "instruction": specific["instruction"]},
                "words_to_avoid": words, "categories": categories}, ensure_ascii=False))
            general = {"decision": "propose",
                       "trigger": " ".join(str(reply.get("trigger", "")).split()),
                       "instruction": " ".join(str(reply.get("instruction", "")).split()),
                       "category": str(reply.get("category", "")) or specific.get("category", "")}
            left = too_specific(general, description) if general["instruction"] else []
            if str(reply.get("decision", "")).lower() != "generalize":
                row.update(status="not_promoted",
                           detail="the Expert kept it for this example only: "
                                  + str(reply.get("reason", ""))[:300])
            elif len(general["instruction"]) < 15 or len(general["trigger"]) < 10 or left:
                row.update(status="not_promoted",
                           detail=("still tied to its process by: " + ", ".join(left)) if left
                           else "the general wording is incomplete")
            else:
                shown = nearest_rules(general["instruction"], documentation, embedder)
                outcome = relation_outcome(general, shown,
                                           classify_relation(general, shown, expert_llm))
                learned = [g for g in store["guidelines"] if g.get("status") == "promoted"]
                known, cosine, lexical = nearest(general["instruction"], learned, embedder)
                if outcome["status"] != "promoted":
                    row.update(status="not_promoted",
                               detail="its general form is documentation rule "
                                      + str(outcome.get("ref")))
                elif known and (cosine >= DUPLICATE_COSINE or lexical >= DUPLICATE_LEXICAL):
                    store_module.add_support(store, known["id"], example, [])
                    store_module.mark_generalized(store, specific["id"], known["id"])
                    row.update(status="merged_with_learned", guideline_id=known["id"],
                               detail=f"its general form is the same as {known['id']}")
                else:
                    gid = store_module.add_guideline(
                        store, general, specific.get("family"), example, outcome["relation"], [],
                        evidence=specific.get("evidence"), generalized_from=[specific["id"]])
                    added = next(g for g in store["guidelines"] if g["id"] == gid)
                    added["promoted_after_confirmation"] = True
                    if specific.get("confirmation"):
                        added["confirmation"] = copy.deepcopy(specific["confirmation"])
                    store_module.save_store(store)
                    store_module.mark_generalized(store, specific["id"], gid)
                    row.update(status="promoted_after_confirmation", guideline_id=gid,
                               trigger=general["trigger"], instruction=general["instruction"],
                               detail=f"general form of {specific['id']}, written after it "
                                      f"improved the model of example {example}")
        except Exception as exc:                       # an agent failed, not the pipeline
            row.update(status="agent_error", detail=f"{type(exc).__name__}: {exc}"[:300])
        rows.append(row)
    return rows


# ------------------------------------------------------- 5. one example ----
LEARNING_MODE = "tools"      # the tool-using agents (the only mode of the study)


def learn_from_example(run_dir: Path, entry: dict, generated_xml: str, failures: list[dict],
                       retriever_llm, expert_llm, embedder, on_event=None,
                       after_iteration: int = 0) -> list[dict]:
    """Retriever -> Expert -> checks for every detected failure; update the catalogue.

    Each agent runs a tool-using loop (guideline_agents_tools): the Retriever
    lists and searches the evidence itself, the Expert reads the description,
    consults the closest documented and learned guidelines and checks its
    wording through tools, and gives the relation in its final answer.

    Per failure: the Expert proposes; a wording tied to this process gets one
    rewrite; the Expert's classification against the closest documented
    guidelines (contradicts / not applied / refines / new) is checked by code."""
    import guideline_agents_tools as gat
    run_dir = Path(run_dir)
    records = build_records(run_dir)
    documentation = store_module.documentation_rules()
    categories = sorted({r["category"] for r in documentation})
    description = entry["description"]
    outcomes = []
    for failure in [f for f in failures if f["status"] == "detected"]:
        ftype = failure["failure_type"]
        outcome = {"failure_type": ftype, "example_id": entry["id"], "learning_mode": LEARNING_MODE}
        traces = {"retriever": None, "expert": []}
        try:
            store = store_module.load_store()
            learned = [g for g in store["guidelines"] if g.get("status") == "promoted"]

            def ask_expert(**kw):
                """One tool-using run of the Expert."""
                cand = gat.expert_with_tools(failure, dossier, categories, expert_llm,
                                             description=description, documentation=documentation,
                                             learned=learned, embedder=embedder, **kw)
                traces["expert"].append({"tools_used": cand["_tools_used"], "trace": cand["_trace"]})
                return cand

            dossier = gat.retrieve_with_tools(failure, records, retriever_llm)
            traces["retriever"] = dossier.pop("trace")
            outcome["retrieved"] = [r["id"] for r in dossier["selected"]]
            outcome["retriever_reason"] = dossier["reason"]
            if dossier.get("added_counterparts"):
                outcome["added_counterparts"] = dossier["added_counterparts"]
            if not dossier["selected"]:
                outcome.update(status="no_evidence_selected")
            else:
                candidate = ask_expert()
                if candidate["decision"] != "propose":
                    # errors of this type remain on the model: the Expert is asked once more
                    outcome["first_answer"] = {"decision": "abstain", "reason": candidate["reason"]}
                    candidate = ask_expert(
                        second_request="You abstained with this reason: " + candidate["reason"]
                        + " The failure is still detected on this model and nothing was learned "
                          "from it.")
                if candidate["decision"] == "propose":
                    words = too_specific(candidate, description)
                    if words:                       # one rewrite in general terms
                        outcome["first_wording"] = {k: candidate[k] for k in ("trigger", "instruction")}
                        outcome["words_to_avoid"] = words
                        candidate = ask_expert(avoid=words, previous=candidate)
                outcome["candidate"] = {k: v for k, v in candidate.items() if not k.startswith("_")}
                if candidate["decision"] != "propose":
                    outcome.update(status="abstained", detail=candidate["reason"])
                else:
                    def judge(candidate):
                        if form_problem(candidate, dossier, gold_xml=entry["bpmn_xml"],
                                        generated_xml=generated_xml, description=description):
                            return [], None, []
                        # the Expert consulted the guidelines itself and gave the relation;
                        # without that consultation the similarity thresholds decide
                        if candidate.get("_judged") is None:
                            return (nearest_rules(candidate["instruction"], documentation, embedder),
                                    None, [])
                        return candidate["_shown"], candidate["_judged"], candidate["_learned_shown"]

                    shown, judged, learned_shown = judge(candidate)
                    rules = {r["id"]: r for r in shown}
                    if judged and judged.get("relation") == "contradicts" and judged.get("rule_id") in rules:
                        # the documentation follows the BPMN specification: it wins over the
                        # reference; the Expert gets one chance to write a guideline that respects it
                        rule = rules[judged["rule_id"]]
                        outcome["contradicted"] = {"rule_id": rule["id"], "reason": judged.get("reason"),
                                                   "guideline": {k: candidate[k] for k in ("trigger", "instruction")}}
                        again = ask_expert(
                            second_request=f"Your guideline contradicts documentation rule {rule['id']}: "
                                           f"\"{rule['instruction']}\" The documentation guidelines follow the "
                                           "BPMN 2.0.2 specification and take precedence over the reference "
                                           "model. Propose a guideline that respects this rule, or abstain.")
                        if again["decision"] == "propose" and not too_specific(again, description):
                            candidate = again
                            outcome["candidate"] = {k: v for k, v in candidate.items() if not k.startswith("_")}
                            shown, judged, learned_shown = judge(candidate)
                    if judged is not None:
                        outcome["relation_judgement"] = judged
                        outcome["rules_shown"] = [r["id"] for r in shown]
                        outcome["learned_shown"] = [g["id"] for g in learned_shown]
                    check = check_candidate(
                        candidate, dossier, gold_xml=entry["bpmn_xml"],
                        generated_xml=generated_xml, description=description,
                        documentation=documentation, learned=learned, embedder=embedder,
                        judged=judged, shown=shown or None, learned_shown=learned_shown)
                    outcome.update(check)
                    cited = [r for r in dossier["selected"] if r["id"] in candidate["cited"]]
                    general = None
                    if check["status"] in ("promoted", "example_specific"):
                        general = try_generalize(candidate, entry, store, documentation,
                                                 categories, expert_llm, embedder)
                        if general and general["status"] == "not_generalized":
                            outcome["generalization"] = general
                            general = None
                    if general:
                        match = general["with"]
                        evidence = list(match.get("evidence", [])) + [
                            {"example_id": str(entry["id"]),
                             "records": [{"id": r["id"], "text": r["text"]} for r in cited]}]
                        examples = list(match["support"]["learned_from"]) + [str(entry["id"])]
                        gid = store_module.add_guideline(
                            store, general["guideline"], ftype, entry["id"], general["relation"],
                            cited, learned_from=examples, evidence=evidence,
                            generalized_from=[match["id"]])
                        store_module.mark_generalized(store, match["id"], gid)
                        outcome.update(status="generalized", guideline_id=gid,
                                       relation=general["relation"],
                                       detail=f"general guideline covering {match['id']} "
                                              f"(example {match['support']['learned_from'][0]}) and this example")
                        outcome["candidate_before_generalization"] = candidate
                        outcome["candidate"] = dict(candidate, **{k: general["guideline"][k]
                                                                  for k in ("trigger", "instruction")})
                    elif check["status"] == "promoted":
                        outcome["guideline_id"] = store_module.add_guideline(
                            store, candidate, ftype, entry["id"], check["relation"], cited)
                    elif check["status"] == "example_specific":
                        outcome["guideline_id"] = store_module.add_guideline(
                            store, candidate, ftype, entry["id"], check["relation"], cited,
                            status="example_specific")
                    elif check["status"] == "merged_with_learned":
                        store_module.add_support(store, check["ref"], entry["id"], cited)
                        outcome["guideline_id"] = check["ref"]
                    if (outcome.get("first_wording") and outcome.get("guideline_id")
                            and outcome.get("status") in ("promoted", "merged_with_learned",
                                                          "generalized")):
                        # trace of the context-dependent wording the Expert first wrote;
                        # only the general version is sent back and reused on other descriptions
                        store = store_module.load_store()
                        trace_id = store_module.add_guideline(
                            store, dict(candidate, **outcome["first_wording"]), ftype, entry["id"],
                            check.get("relation") or {"type": "new", "ref": None}, cited,
                            status="example_specific")
                        store_module.mark_generalized(store, trace_id, outcome["guideline_id"],
                                                      trace_only=True)
                        outcome["specific_wording_id"] = trace_id
        except Exception as exc:                       # an agent failed, not the pipeline
            outcome.update(status="agent_error", detail=f"{type(exc).__name__}: {exc}"[:300])
        outcome["agent_trace"] = traces
        outcomes.append(outcome)
        if on_event:
            on_event({"type": "guideline", "id": entry["id"], **{
                k: outcome.get(k) for k in ("failure_type", "status", "detail", "guideline_id",
                                            "ref")},
                "trigger": (outcome.get("candidate") or {}).get("trigger"),
                "instruction": (outcome.get("candidate") or {}).get("instruction")})
    (run_dir / "guideline_learning.json").write_text(
        json.dumps({"example_id": entry["id"], "outcomes": outcomes},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    # every learn call of this description is kept, in order (the file above is
    # the latest one): the full trace of the agents, iteration by iteration
    history_file = run_dir / "guideline_learning_history.json"
    try:
        history = json.loads(history_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        history = {"example_id": entry["id"], "learn_calls": []}
    history["learn_calls"].append({"call": len(history["learn_calls"]) + 1,
                                   "after_iteration": after_iteration, "outcomes": outcomes})
    history_file.write_text(json.dumps(history, ensure_ascii=False, indent=1), encoding="utf-8")
    return outcomes
