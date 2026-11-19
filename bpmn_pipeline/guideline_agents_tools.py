"""Tool-using Retriever and Expert agents (the guideline agents of GuideBPMN).

Each agent runs a ReAct-style loop: at every step it either calls ONE tool
(name + arguments) or gives its final answer, within a budget of tool calls.
The code runs the tool and returns its result; every step (tool, arguments,
reason, result) is kept in a trace that is saved with the run.

The loop is provider-independent: it uses the same `complete_json` call as the
other components, so Luna and Haiku are treated the same way.

Retriever tools   list_evidence(kind), search_evidence(words), find_counterparts(record_id)
Expert tools      read_description(), find_closest_documented_guidelines(text),
                  find_closest_learned_guidelines(text), check_wording(text)

The hard checks of guideline_agents.py (citations, no reference-only label,
the named guideline must be one the agent retrieved, duplicate thresholds)
stay in the code, as guards, exactly like the orchestrator's allowed actions.
"""
from __future__ import annotations

import json
import re
from typing import Callable, Optional

import guideline_agents as ga
import guideline_store as store_module

RETRIEVER_MAX_TOOL_CALLS = 4
EXPERT_MAX_TOOL_CALLS = 6
MAX_LISTED = 40            # records returned by one list/search call
MAX_RESULT_CHARS = 12000   # a tool result is cut beyond this, and says so

LOOP_RULES = (
    "At each step reply with ONE JSON object, either a tool call "
    "{\"action\": \"tool\", \"tool\": \"<name>\", \"args\": {...}, \"reason\": \"...\"} "
    "or your final answer {\"action\": \"final\", ...}. Use only the tools listed, with their "
    "arguments. When tool_calls_left is 0 you must give the final answer."
)


class ToolAgent:
    """One agent: an LLM, a role prompt, tools, a budget. run(task) -> (final, trace)."""

    def __init__(self, name: str, llm, system: str,
                 tools: dict[str, tuple[str, Callable]], max_calls: int,
                 before_final: Optional[Callable[[dict, list], Optional[str]]] = None):
        """before_final(final, trace) -> a message when the final answer is not
        acceptable yet (for example a tool that had to be consulted first): the
        agent is told so and asked again, while tool calls are left."""
        self.name, self.llm, self.system = name, llm, system
        self.tools, self.max_calls = tools, max_calls
        self.before_final = before_final

    def _call(self, name: str, args: dict):
        if name not in self.tools:
            return {"error": f"unknown tool {name!r}; tools: {sorted(self.tools)}"}
        try:
            result = self.tools[name][1](**(args if isinstance(args, dict) else {}))
        except TypeError as exc:
            return {"error": f"bad arguments for {name}: {exc}"}
        text = json.dumps(result, ensure_ascii=False)
        if len(text) > MAX_RESULT_CHARS:
            return {"truncated": True, "result_start": text[:MAX_RESULT_CHARS]}
        return result

    def run(self, task: dict) -> tuple[dict, list[dict]]:
        trace: list[dict] = []
        must_answer, sent_back = False, None
        for _ in range(self.max_calls + 4):
            left = self.max_calls - len(trace)
            request = {"task": task,
                       "tools": [{"name": n, "description": d} for n, (d, _) in self.tools.items()],
                       "steps_so_far": [{k: s[k] for k in ("tool", "args", "result")} for s in trace],
                       "tool_calls_left": max(left, 0),
                       "rules": LOOP_RULES}
            if must_answer:
                request["must_answer"] = "No tool call is left: give the final answer now."
            if sent_back:
                request["before_final"] = sent_back
                sent_back = None
            try:
                reply = self.llm.complete_json(system=self.system,
                                               user=json.dumps(request, ensure_ascii=False))
            except RuntimeError as exc:
                if "truncated at max_tokens" not in str(exc):
                    raise
                # the answer was cut at the output limit: asked once more, briefly
                request["answer_briefly"] = ("Your previous answer was cut at the output limit. "
                                             "Reply with the JSON object only, with a short reason.")
                trace.append({"step": len(trace) + 1, "tool": None, "args": None,
                              "reason": "answer cut at the output limit", "result": "asked again"})
                try:
                    reply = self.llm.complete_json(system=self.system,
                                                   user=json.dumps(request, ensure_ascii=False))
                except RuntimeError as exc2:
                    if "truncated at max_tokens" not in str(exc2):
                        raise
                    # cut twice: a last attempt with the tool results shortened
                    request["steps_so_far"] = [{"tool": s["tool"], "args": s["args"],
                                                "result": str(s["result"])[:600]} for s in trace]
                    trace.append({"step": len(trace) + 1, "tool": None, "args": None,
                                  "reason": "answer cut again", "result": "asked a last time with shortened context"})
                    reply = self.llm.complete_json(system=self.system,
                                                   user=json.dumps(request, ensure_ascii=False))
            action = str(reply.get("action", "")).lower()
            if action == "tool" and left > 0:
                name, args = str(reply.get("tool", "")), reply.get("args") or {}
                trace.append({"step": len(trace) + 1, "tool": name, "args": args,
                              "reason": str(reply.get("reason", ""))[:300],
                              "result": self._call(name, args)})
                continue
            if action == "tool":            # budget reached: one more turn to answer
                if must_answer:
                    break
                must_answer = True
                continue
            if self.before_final and left > 0:
                message = self.before_final(reply, trace)
                if message:                 # not acceptable yet: told why, asked again
                    trace.append({"step": len(trace) + 1, "tool": None, "args": None,
                                  "reason": "final answer sent back", "result": message})
                    sent_back = message
                    continue
            return reply, trace
        return {"action": "final", "decision": "abstain",
                "reason": "tool-call budget reached without a final answer"}, trace


# --------------------------------------------------------------- Retriever --
RETRIEVER_SYSTEM = (
    "You are the Retriever agent of GuideBPMN. A failure was detected on a generated BPMN "
    "model. Your job: select the evidence records needed to understand this failure: the "
    "findings that show it and the description sentences that state what the model should "
    "contain at that point. You do not see the records at first: use the tools to list or "
    "search them. When you select a reference element without counterpart (missing_element), "
    "use find_counterparts to see generated elements that could be the same element modeled "
    "differently, and select them too. Select at most 12 records, by id. "
    "Final answer: {\"action\": \"final\", \"selected\": [ids], \"reason\": \"...\"}. "
    + LOOP_RULES
)


def retrieve_with_tools(failure: dict, records: list[dict], llm) -> dict:
    pool = ga.records_for(failure["failure_type"], records)
    by_id = {r["id"]: r for r in pool}
    kinds = sorted({r["kind"] for r in pool})

    def list_evidence(kind: str = ""):
        found = [r for r in pool if r["kind"] == kind]
        if not found:
            return {"error": f"no record of kind {kind!r}; kinds: {kinds}"}
        return [{"id": r["id"], "text": r["text"]} for r in found[:MAX_LISTED]]

    def search_evidence(words: str = ""):
        wanted = [w.lower() for w in re.findall(r"[a-zA-Z][a-zA-Z\-']+", str(words)) if len(w) > 2]
        found = [r for r in pool if any(w in r["text"].lower() for w in wanted)] if wanted else []
        return [{"id": r["id"], "kind": r["kind"], "text": r["text"]} for r in found[:MAX_LISTED]]

    def find_counterparts(record_id: str = ""):
        rec = by_id.get(str(record_id))
        if rec is None or rec["kind"] != "missing_element":
            return {"error": "record_id must be the id of a missing_element record"}
        return [{"id": r["id"], "text": r["text"]} for r in ga.possible_counterparts([rec], pool)]

    agent = ToolAgent("retriever", llm, RETRIEVER_SYSTEM, {
        "list_evidence": ("Records of one kind. args: {\"kind\": one of %s}" % kinds, list_evidence),
        "search_evidence": ("Records whose text contains any of the given words. args: {\"words\": \"...\"}",
                            search_evidence),
        "find_counterparts": ("Generated elements that may be a missing reference element modeled "
                              "differently. args: {\"record_id\": id of a missing_element record}",
                              find_counterparts),
    }, RETRIEVER_MAX_TOOL_CALLS)
    final, trace = agent.run({
        "failure_type": failure["failure_type"],
        "meaning": ga.FAILURE_MEANING[failure["failure_type"]],
        "summary": failure.get("summary_evidence", {}),
        "evidence_counts_by_kind": {k: sum(r["kind"] == k for r in pool) for k in kinds},
    })
    asked = [str(i) for i in (final.get("selected") or [])]
    selected = [i for i in dict.fromkeys(asked) if i in by_id][:ga.MAX_SELECTED]
    chosen = [by_id[i] for i in selected]
    added = ga.possible_counterparts(chosen, pool)      # completeness guard (code)
    return {"selected": chosen + added,
            "added_counterparts": [r["id"] for r in added],
            "ignored_unknown_ids": [i for i in asked if i not in by_id],
            "reason": str(final.get("reason", ""))[:500],
            "trace": trace}


# ------------------------------------------------------------------ Expert --
EXPERT_SYSTEM = (
    "You are the Expert agent of GuideBPMN. You receive one detected failure and the evidence "
    "records selected for it. Decide whether this evidence supports ONE modeling guideline that "
    "would prevent the failure the next time a similar situation is described, and how it "
    "relates to the guidelines that already exist.\n"
    "Work with your tools: read_description to verify what the process really states before "
    "you conclude; find_closest_documented_guidelines to see the documented guidelines closest "
    "to your guideline; find_closest_learned_guidelines to see the error-driven guidelines "
    "already learned; check_wording to verify that your wording is not tied to this one process.\n"
    "A guideline has: trigger = the situation, stated as something observable in a process "
    "description (start with 'the description ...'); instruction = what to model in BPMN when "
    "the trigger holds.\n"
    "Before concluding that an element is missing, check the records of generated elements "
    "without counterpart (extra_element): the generator may have modeled the same element "
    "differently (another element type, another pool, other wording). The element is then not "
    "missing: the mistake is the choice of BPMN element. The reference model is the expected "
    "model: when it agrees with the description and with BPMN 2.0.2, such a difference is a "
    "modeling mistake. Never turn a choice of the reference that breaks BPMN semantics into a "
    "guideline: a wait for a message, a signal, a time or a condition is an intermediate catch "
    "event (or an event-based gateway), not a task, and branches that must all be completed are "
    "joined by a parallel gateway, not an exclusive one.\n"
    "Rules: write the guideline so that it applies beyond this one process; do not restate this "
    "process's steps, names or domain words. If words_to_avoid is given, rewrite without those "
    "words. Never copy an element label that comes from the reference model; wording from the "
    "description is allowed. Cite the ids of the records that support the guideline (only ids "
    "you were given). Abstain only if the records show no difference, or if the reference "
    "contradicts the description or BPMN 2.0.2. If second_request is given, you abstained once "
    "while differences remain: propose the one guideline that the records support best.\n"
    "Relation: after consulting the documented guidelines, classify your guideline as "
    "\"contradicts\" (it asks for a model that a documented guideline forbids or advises against; "
    "check this first), \"not_applied\" (a documented guideline already says the same thing), "
    "\"refines\" (a documented guideline covers the topic and yours adds when or how to apply it), "
    "\"same_as_learned\" (a learned guideline already says essentially the same thing), or "
    "\"new\". Give the id of the guideline concerned (null for new); use only ids your tools "
    "returned.\n"
    "Final answer: {\"action\": \"final\", \"decision\": \"propose\" or \"abstain\", "
    "\"trigger\": \"...\", \"instruction\": \"...\", \"category\": one of the given categories, "
    "\"cited\": [ids], \"relation\": \"...\", \"rule_id\": \"...\" or null, \"reason\": \"...\"}. "
    + LOOP_RULES
)
RELATIONS = ("contradicts", "same_as_learned", "not_applied", "refines", "new")


_RELATION_WORDS = {
    "contradicts": "contradicts", "contradict": "contradicts", "contradiction": "contradicts",
    "contradicting": "contradicts",
    "same_as_learned": "same_as_learned", "same as learned": "same_as_learned",
    "same_as_learned_guideline": "same_as_learned", "duplicate": "same_as_learned",
    "same": "same_as_learned", "repeats_learned": "same_as_learned",
    "not_applied": "not_applied", "not applied": "not_applied", "restates": "not_applied",
    "restate": "not_applied", "restatement": "not_applied", "restating": "not_applied",
    "existing": "not_applied", "same_as_documented": "not_applied",
    "refines": "refines", "refine": "refines", "refinement": "refines", "refining": "refines",
    "new": "new", "new_guideline": "new", "none": "new",
}
_ID = re.compile(r"\b([A-Z]{2,5}-\d{2,3}|LRN-\d+|EXS-\d+)\b")


def normalize_relation(final: dict) -> tuple[Optional[str], Optional[str]]:
    """The relation and guideline id of a final answer, in the forms the LLMs
    write them ("refinement", "same as learned", "ACT-07 (activities)", a
    list, a nested object). Returns (None, None) when no relation is given."""
    rel = final.get("relation")
    if isinstance(rel, dict):
        final = {**final, "rule_id": rel.get("rule_id") or rel.get("id") or final.get("rule_id")}
        rel = rel.get("relation") or rel.get("type")
    text = " ".join(str(rel or "").strip().lower().replace("-", "_").split())
    relation = _RELATION_WORDS.get(text) or _RELATION_WORDS.get(text.replace(" ", "_"))
    if relation is None:
        for key, value in _RELATION_WORDS.items():
            if key in text:
                relation = value
                break
    rid = final.get("rule_id")
    if rid is None:
        rid = final.get("guideline_id") or final.get("ref") or final.get("id_concerned")
    if isinstance(rid, (list, tuple)):
        rid = rid[0] if rid else None
    if isinstance(rid, dict):
        rid = rid.get("id")
    if rid is not None:
        found = _ID.search(str(rid))
        rid = found.group(1) if found else (str(rid).strip() or None)
    if relation == "new":
        rid = None
    return relation, rid


def _must_consult_before_proposing(final: dict, trace: list[dict]) -> Optional[str]:
    """A proposal is accepted only after the Expert consulted the documented
    guidelines through its tool: the relation is always its own decision."""
    if str(final.get("decision", "")).lower() != "propose":
        return None
    used = {s["tool"] for s in trace if s["tool"]}
    if "find_closest_documented_guidelines" not in used:
        return ("Before proposing, call find_closest_documented_guidelines with your guideline "
                "text and classify your guideline against the guidelines it returns.")
    return None


def expert_with_tools(failure: dict, dossier: dict, categories: list[str], llm, *,
                      description: str, documentation: list[dict], learned: list[dict],
                      embedder, avoid: Optional[list[str]] = None,
                      previous: Optional[dict] = None,
                      second_request: Optional[str] = None) -> dict:
    """One run of the Expert agent. Returns a candidate {decision, trigger, instruction,
    category, cited, reason, relation_answered}, plus _judged / _shown / _learned_shown / _trace."""
    shown: dict[str, dict] = {}
    learned_shown: dict[str, dict] = {}
    learned_texts = [dict(g, instruction=f"{g['trigger']} {g['instruction']}") for g in learned]

    def read_description():
        return {"process_description": description}

    def find_closest_documented_guidelines(text: str = ""):
        found = ga.nearest_rules(str(text), documentation, embedder)
        for r in found:
            shown[r["id"]] = r
        return [{"id": r["id"], "category": r.get("category"), "rule": r["instruction"]} for r in found]

    def find_closest_learned_guidelines(text: str = ""):
        found = ga.nearest_rules(str(text), learned_texts, embedder, k=ga.NEAREST_LEARNED_SHOWN)
        out = []
        for s in found:
            g = next(x for x in learned if x["id"] == s["id"])
            learned_shown[g["id"]] = g
            out.append({"id": g["id"], "rule": f"When {g['trigger']}: {g['instruction']}"})
        return out

    def check_wording(text: str = ""):
        words = store_module.abstraction_violations(str(text), description)
        return {"tied_to_this_process": bool(words), "words": words}

    agent = ToolAgent("expert", llm, EXPERT_SYSTEM, {
        "read_description": ("The full process description. args: {}", read_description),
        "find_closest_documented_guidelines": (
            "The 6 documented guidelines closest to a text. args: {\"text\": \"...\"}",
            find_closest_documented_guidelines),
        "find_closest_learned_guidelines": (
            "The 4 error-driven guidelines already learned that are closest to a text. "
            "args: {\"text\": \"...\"}", find_closest_learned_guidelines),
        "check_wording": ("Words of a text that tie it to this one process. args: {\"text\": \"...\"}",
                          check_wording),
    }, EXPERT_MAX_TOOL_CALLS, before_final=_must_consult_before_proposing)
    task = {"failure_type": failure["failure_type"],
            "meaning": ga.FAILURE_MEANING[failure["failure_type"]],
            "records": [{"id": r["id"], "kind": r["kind"], "text": r["text"]}
                        for r in dossier["selected"]],
            "categories": categories}
    if second_request:
        task["second_request"] = second_request
    if avoid:
        task["words_to_avoid"] = avoid
        task["previous_guideline"] = {k: (previous or {}).get(k) for k in ("trigger", "instruction")}
    final, trace = agent.run(task)
    relation, rule_id = normalize_relation(final)
    judged = ({"relation": relation, "rule_id": rule_id, "reason": str(final.get("reason", ""))[:400]}
              if relation else None)
    consulted = [s["tool"] for s in trace if s["tool"]]
    if judged and "find_closest_documented_guidelines" not in consulted:
        # only possible when the whole budget was spent before answering: the
        # relation is not used and the similarity thresholds decide (logged)
        judged = None
    return {"decision": str(final.get("decision", "abstain")).lower(),
            "trigger": " ".join(str(final.get("trigger", "")).split()),
            "instruction": " ".join(str(final.get("instruction", "")).split()),
            "category": str(final.get("category", "")),
            "cited": [str(i) for i in (final.get("cited") or [])],
            "reason": str(final.get("reason", ""))[:600],
            "relation_answered": {"relation": final.get("relation"), "rule_id": final.get("rule_id")},
            "_judged": judged, "_shown": list(shown.values()),
            "_learned_shown": list(learned_shown.values()),
            "_tools_used": consulted, "_trace": trace}
