"""The tools the GuideBPMN orchestrator agent calls, bound to one example.

Each tool reads and updates the OrchestratorState; none of them decides anything.
They reuse the modules validation (root validator), evaluation
(similarity_evaluator), diagnosis (Failure Detector) and generation.

Display-only numbers: after each validation, the similarity of that draft is
computed for the live site view and stored as `display_metrics`. The agent's
observation never includes them (see OrchestratorState.observation), so the gold
diagram cannot steer drafting.

Second iteration (`revise`): when the guideline agents conclude that the
mistake is a documentation rule the generator did not apply, that rule (its
id, its text and the situation where it applies) is sent back to the
generator once. The result of the first pass is saved in `state.first_pass`
before anything is overwritten, so both results are reported.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, Optional

from orchestrator_agent import OrchestratorState, keep_best
from validation import validate, is_valid, failed_levels, element_performance
from evaluation import evaluate_pair
from diagnosis import classify, write_learner_inputs


def _lite(metrics: dict) -> dict:
    keys = ("semantic_similarity", "workflow_order_similarity", "connection_f1",
            "collaboration_similarity", "alignment_coverage", "collaboration_ignored",
            "semantic_similarity_strict", "activity_semantic_similarity",
            "activity_label_precision", "activity_label_recall", "activity_label_f1")
    return {k: metrics.get(k) for k in keys}


def _rules_for_generator(state: OrchestratorState) -> list[dict]:
    return [{"rule_id": r["rule_id"], "source": r.get("source", "documentation rule not applied"),
             "rule": r["instruction"], "where_it_applies": r["situation"]}
            for r in state.rules_to_reapply]


def make_tools(entry: dict, embedding_model,
               catalogue: Optional[Path] = None,
               generate_fn: Optional[Callable[..., str]] = None,
               on_event: Optional[Callable[[dict], None]] = None,
               retriever_llm=None, expert_llm=None,
               learned_guidelines: Optional[list] = None) -> dict:
    """Return {action_name: fn(state)} for one example.

    generate_fn(state, feedback) -> xml lets tests inject a fake generator;
    by default the real generator runs (or the gold XML in a dry run).
    """
    gold_xml = entry["bpmn_xml"]
    started = time.time()

    def emit(event):
        if on_event:
            on_event(event)

    def write_live(state: OrchestratorState):
        """Drafts validated so far, for the live view (replaced by iterations.json at the end)."""
        folder = Path(state.run_dir)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "live_iterations.json").write_text(json.dumps(
            {"id": state.example_id, "live": True, "kept_round": state.kept_round,
             "iterations": [{"round": r["round"], "kind": r.get("kind", "draft"),
                             "valid": r["valid"], "failed_levels": r["failed_levels"],
                             "seconds": r.get("seconds"),
                             "validator_levels": r.get("validator_levels"),
                             "metrics": r.get("display_metrics", {}), "xml": r["xml"]}
                            for r in state.rounds if r["validated"]]},
            ensure_ascii=False, default=str), encoding="utf-8")

    def draft(state: OrchestratorState, feedback: Optional[dict]) -> str:
        if generate_fn is not None:
            return generate_fn(state, feedback)
        if state.dry_run:
            return gold_xml
        from generation import generate_once, combined_catalogue
        out_dir = Path(state.run_dir) / f"round_{len(state.rounds)}"
        out_dir.mkdir(parents=True, exist_ok=True)
        row = generate_once(state.example_id, state.provider,
                            catalogue or combined_catalogue(
                                state.arm, Path(state.run_dir),
                                example_id=state.example_id if "learned" in state.arm else None),
                            out_dir, model=state.model_name,
                            correction_feedback=feedback)
        return row.get("generated_bpmn_xml") or ""

    def generate(state: OrchestratorState):
        xml = draft(state, None)
        state.rounds.append({"round": 0, "kind": "draft", "xml": xml, "validated": False,
                             "valid": None, "failed_levels": []})

    def validate_tool(state: OrchestratorState):
        last = state.rounds[-1]
        result = validate(last["xml"])
        last.update(validated=True, valid=is_valid(result),
                    failed_levels=sorted(failed_levels(result)),
                    validation=result,
                    validator_levels=element_performance(last["xml"], result))
        display = _lite(evaluate_pair(gold_xml, last["xml"], model=embedding_model)) \
            if last["xml"] else {}
        last["display_metrics"] = display            # never shown to the agent
        last["seconds"] = round(time.time() - started, 1)
        write_live(state)
        emit({"type": "iteration", "id": state.example_id, "round": last["round"],
              "kind": last.get("kind", "draft"), "seconds": last["seconds"],
              "valid": last["valid"], "failed_levels": last["failed_levels"],
              "metrics": display})

    def evaluate(state: OrchestratorState):
        state.kept_round = keep_best(state)
        best = next(r for r in state.rounds if r["round"] == state.kept_round)
        metrics = evaluate_pair(gold_xml, best["xml"], model=embedding_model)
        effect = state.iteration_effects[-1] if state.iteration_effects else None
        if (effect is not None and "after" not in effect and effect.get("errors_before") is not None
                and state.previous_kept is not None and state.kept_round != state.previous_kept):
            # A next iteration must not make the example worse: the new model is kept only
            # if its open errors (validator errors T1-T4 and differences from the
            # reference T5-T7) did not increase.
            from diagnosis import error_counts
            from guideline_store import effect_of
            new_errors = error_counts(best.get("validation") or {}, metrics)
            if sum(new_errors.values()) > sum(effect["errors_before"].values()):
                tried = effect_of(effect["before"], metrics, effect["valid_before"], bool(best["valid"]))
                effect["reverted"] = {"draft": best["round"], "errors": new_errors,
                                      "errors_before": effect["errors_before"],
                                      "mean_change": tried["mean_change"]}
                state.kept_round = state.previous_kept
                best = next(r for r in state.rounds if r["round"] == state.kept_round)
                metrics = evaluate_pair(gold_xml, best["xml"], model=embedding_model)
                emit({"type": "progress", "id": state.example_id,
                      "text": f"next iteration {effect['iteration']}: more errors than before "
                              f"({sum(new_errors.values())} > {sum(effect['errors_before'].values())}), "
                              f"the previous model (draft {state.kept_round}) is kept"})
        state.metrics = {k: v for k, v in metrics.items() if k != "node_mapping"}
        state.evaluated = True
        if effect is not None and "after" not in effect:        # result of the next iteration
            from diagnosis import error_counts
            from guideline_store import effect_of, record_type_tests
            effect.update(effect_of(effect["before"], state.metrics,
                                    effect["valid_before"], bool(best["valid"])))
            effect.pop("confirmed", None)        # the score change is reported, it confirms nothing
            effect["kept_round"] = state.kept_round
            # errors of the model kept after this next iteration (T1-T7)
            effect["errors_after"] = error_counts(best.get("validation") or {}, state.metrics)
            # the model kept after this next iteration, in full (per-iteration results)
            effect["metrics_after"] = dict(state.metrics)
            effect["validator_levels_after"] = best.get("validator_levels")
            effect["valid_kept"] = bool(best["valid"])
            effect["failed_levels_kept"] = list(best.get("failed_levels") or [])
            save = state.learn_enabled and not state.dry_run and retriever_llm is not None
            # a guideline is confirmed when the errors of the type it was learned from go down
            effect["type_results"] = record_type_tests(state.example_id, effect, save=save)
            confirmed_ids = [gid for gid, r in effect["type_results"].items() if r["removed"] > 0]
            effect["confirmed"] = bool(confirmed_ids)
            if save:
                if state.promote_confirmed and confirmed_ids and expert_llm is not None:
                    # an example-specific guideline has just removed errors of its type in its
                    # own example: the Expert may now write it in general terms
                    from guideline_agents import promote_confirmed
                    effect["promoted"] = promote_confirmed(entry, confirmed_ids, expert_llm,
                                                           embedding_model)
                    for row in effect["promoted"]:
                        emit({"type": "guideline", "id": state.example_id, "failure_type": None,
                              "status": row["status"], "detail": row.get("detail"),
                              "guideline_id": row.get("guideline_id"), "ref": row["specific_id"],
                              "trigger": row.get("trigger"), "instruction": row.get("instruction")})
            emit({"type": "iteration_effect", "id": state.example_id,
                  "iteration": effect["iteration"], "sent": effect["sent"],
                  "mean_change": effect["mean_change"], "confirmed": effect["confirmed"],
                  "type_results": effect["type_results"]})

    def detect_failures(state: OrchestratorState):
        best = next(r for r in state.rounds if r["round"] == state.kept_round)
        state.failures = classify(best.get("validation") or {}, state.metrics,
                                  rule=state.failure_rule)
        state.detected = [f["failure_type"] for f in state.failures
                          if f["status"] == "detected"]
        state.error_counts = {f["failure_type"]: f["errors"] for f in state.failures
                              if f["status"] == "detected" and f.get("errors")}
        effect = state.iteration_effects[-1] if state.iteration_effects else None
        if effect is not None and "after" in effect and "detected_after" not in effect:
            # what is still detected after this next iteration (bonuses and penalties)
            effect["detected_after"] = list(state.detected)
            effect.setdefault("errors_after", dict(state.error_counts))

    def learn(state: OrchestratorState):
        """Hand the detected failures to the guideline agents: they get the
        Similarity Evaluator's results, never the gold BPMN file itself."""
        from evidence_package import write_evidence_package
        run_dir = Path(state.run_dir)
        best = next(r for r in state.rounds if r["round"] == state.kept_round)
        write_evidence_package(run_dir, entry, best["xml"],
                               best.get("validation") or {}, state.metrics,
                               embedding_model)
        write_learner_inputs(state.example_id, state.provider, state.failures, run_dir)
        if retriever_llm is not None and expert_llm is not None:
            from guideline_agents import learn_from_example
            outcomes = learn_from_example(run_dir, entry, best["xml"], state.failures,
                                          retriever_llm, expert_llm, embedding_model,
                                          on_event=on_event,
                                          after_iteration=state.revisions)
            state.guideline_outcomes += [
                dict({k: o.get(k) for k in ("failure_type", "status", "detail", "guideline_id",
                                            "ref")}, after_iteration=state.revisions)
                for o in outcomes]
            # second iteration: send back to the generator, for this same example,
            # (a) the documentation rules it did not apply and (b) the guidelines
            # the agents have just learned from it (new, refining, or merged)
            from guideline_store import documentation_rules, load_store
            rules = {r["id"]: r for r in documentation_rules()}
            learned = {g["id"]: g for g in load_store()["guidelines"]}
            for o in outcomes:
                status, situation = o.get("status"), (o.get("candidate") or {}).get("trigger", "")
                if status == "existing_documentation_rule" and o.get("ref") in rules:
                    rule_id, text, source = o["ref"], rules[o["ref"]]["instruction"], \
                        "documentation rule not applied"
                elif status in ("promoted", "merged_with_learned", "generalized",
                                "example_specific") and o.get("guideline_id") in learned:
                    g = learned[o["guideline_id"]]
                    rel = g.get("baseline_relation") or {}
                    rule_id, text = g["id"], f"When {g['trigger']}: {g['instruction']}"
                    if status == "example_specific":
                        source = "example-specific guideline"
                    elif rel.get("type") == "refines":
                        source = "learned guideline (refines %s)" % rel.get("ref")
                    else:
                        source = "learned guideline (new)"
                    if status == "generalized":
                        source += ", generalized from " + ", ".join(g.get("generalized_from", []))
                    situation = situation or g.get("trigger", "")
                else:
                    continue
                if rule_id not in {r["rule_id"] for r in state.rules_to_reapply}:
                    state.rules_to_reapply.append({
                        "rule_id": rule_id, "instruction": text, "situation": situation,
                        "source": source, "failure_type": o["failure_type"]})
        state.learned = True

    def revise(state: OrchestratorState):
        """Second iteration: the generator gets back its kept draft, the
        validator report and the documentation rules it did not apply."""
        best = next(r for r in state.rounds if r["round"] == state.kept_round)
        if not state.first_pass:               # the result before any guideline was sent back
            state.first_pass = {"kept_round": best["round"], "valid": best["valid"],
                                "failed_levels": list(best["failed_levels"]),
                                "metrics": dict(state.metrics),
                                "detected": list(state.detected),
                                "error_counts": dict(state.error_counts)}
        new = [r["rule_id"] for r in state.rules_to_reapply if r["rule_id"] not in state.rules_sent]
        feedback = {"source_iteration": best["round"],
                    "validation_profile": (best.get("validation") or {}).get("profile", {}),
                    "previous_generated_bpmn_xml": best["xml"],
                    "guidelines_to_apply": _rules_for_generator(state)}
        xml = draft(state, feedback)
        number = state.rounds[-1]["round"] + 1
        state.rounds.append({"round": number, "kind": "rule_feedback", "xml": xml,
                             "validated": False, "valid": None, "failed_levels": []})
        state.revised, state.revision_round = True, number
        if state.first_revision_round is None:
            state.first_revision_round = number
        state.previous_kept = best["round"]
        state.revisions += 1
        state.rules_sent += new
        state.iteration_effects.append({
            "iteration": state.revisions, "round": number, "sent": new,
            "before": _lite(state.metrics), "valid_before": bool(best["valid"]),
            "errors_before": dict(state.error_counts)})
        state.learned = False                  # the agents may learn again from the new model
        state.evaluated, state.failures, state.detected = False, None, []
        state.error_counts = {}
        emit({"type": "rule_feedback", "id": state.example_id, "round": number,
              "iteration": state.revisions, "rules": new})

    return {"generate": generate, "validate": validate_tool,
            "evaluate": evaluate, "detect_failures": detect_failures, "learn": learn,
            "revise": revise}
