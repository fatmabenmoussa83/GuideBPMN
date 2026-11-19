"""Run GuideBPMN over the dataset. For every description the orchestrator agent
drives: generate -> validate -> evaluate -> detect_failures ->
learn (Retriever agent -> Expert agent -> code guards -> catalogue) -> revise (next
iteration) ... -> stop.

The three settings of the study (run_kfold.ps1 starts them, each in its own window):

    First     --arm documentation --no-learn --next-iterations 0 --replicate N
    Revised   --arm documentation --next-iterations 3 --force-iterations --promote-confirmed --replicate N
    Reuse     training: --arm documentation --fold k --next-iterations 3 --force-iterations --promote-confirmed
              test:     --arm documentation+learned --fold k

Two reports are written: report_<label>.json holds the first pass (before any
guideline was sent back) and report_<label>_after_rule_feedback.json the result
after the next iterations. A next iteration is informed by the comparison with
the reference of the same description, so it is reported separately.

Each component has its own model, named "provider:model" (openai or anthropic):

    python run_batch.py --dry-run                      # no LLM at all (circuit test)
    python run_batch.py --arm documentation --generator openai:gpt-6-luna \
        --orchestrator openai:gpt-6-luna --retriever openai:gpt-6-luna --expert openai:gpt-6-luna

Resume an interrupted run (same folder, same settings; finished descriptions are
kept, the description that was running starts again):
    python run_batch.py --resume batch_20261117T232222Z_openai-gpt-6-luna_documentation_forced_r1_agents

Which descriptions: all 55 by default, in dataset order;
    --limit 3              the first three
    --ids "24,38,41-45"    chosen descriptions
    --sample 5 --seed 42   five drawn at random (same seed -> same draw)
A learning run on a few chosen descriptions is a trial (--trial): it learns into a
catalogue of its own and is not part of the study.
"""
import argparse
import json
import random
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from pipeline_config import DATASET_PATH, RUNS_DIR, portable_path
from evaluation import ExactLabelModel, embedding_model
from reporting import write_report
from orchestrator_agent import (OrchestratorState, FirstAllowedAgent, LLMOrchestratorAgent, resolve_limits,
                         run_example)
from orchestrator_tools import make_tools
from llm import COMPONENTS, GENERATOR_PROVIDER, LLM, parse_spec, resolve_models

LEARNING_AGENTS = "tools"        # the tool-using Retriever and Expert (labels *_agents, catalogues under agents/)


def _key(example_id) -> str:
    text = str(example_id).strip()
    return str(int(text)) if text.isdigit() else text


def parse_ids(text: str) -> list[str]:
    """'24, 38, 41-45' -> ['24', '38', '41', '42', '43', '44', '45']."""
    wanted = []
    for part in re.split(r"[,;\s]+", str(text).strip()):
        if not part:
            continue
        span = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if span:
            low, high = int(span.group(1)), int(span.group(2))
            if low > high:
                raise ValueError(f"Range {part!r} goes backwards")
            wanted += [str(n) for n in range(low, high + 1)]
        elif part.isdigit():
            wanted.append(str(int(part)))
        else:
            raise ValueError(f"Cannot read example id {part!r}; write e.g. 24, 38, 41-45")
    return wanted


def select_examples(data: list[dict], limit: int | None = None, ids=None,
                    sample: int | None = None, seed: int = 42) -> tuple[list[dict], dict]:
    """The examples of one run, always returned in dataset order, plus a
    record of how they were chosen (saved with the run)."""
    if ids:
        wanted = parse_ids(ids) if isinstance(ids, str) else [_key(i) for i in ids]
        known = {_key(e["id"]) for e in data}
        unknown = [i for i in wanted if i not in known]
        if unknown:
            raise ValueError(f"Unknown example id(s): {', '.join(unknown)}")
        chosen = [e for e in data if _key(e["id"]) in set(wanted)]
        how = {"mode": "chosen"}
    elif sample:
        if not 1 <= int(sample) <= len(data):
            raise ValueError(f"Random sample must be between 1 and {len(data)}")
        picked = {id(e) for e in random.Random(int(seed)).sample(data, int(sample))}
        chosen = [e for e in data if id(e) in picked]
        how = {"mode": "random", "seed": int(seed)}
    elif limit:
        chosen = data[:int(limit)]
        how = {"mode": "first"}
    else:
        chosen, how = list(data), {"mode": "all"}
    how["ids"] = [e["id"] for e in chosen]
    return chosen, how


def lost_agent_step(decisions: dict) -> list[str]:
    """Failure types whose learning step was lost to the network or to an unusable
    reply (the agents did not run as designed for them)."""
    from llm import INFRASTRUCTURE_MARKERS
    return [g.get("failure_type") or "?" for g in decisions.get("guidelines") or []
            if g.get("status") == "agent_error"
            and any(m in (g.get("detail") or "") for m in INFRASTRUCTURE_MARKERS)]


def finished_example(example_dir: Path) -> dict | None:
    """What a finished example contributes to the reports, read back from its
    files (None when the example did not finish)."""
    path = example_dir / "iterations.json"
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    decisions_path = example_dir / "decisions.json"
    decisions = json.loads(decisions_path.read_text(encoding="utf-8")) if decisions_path.is_file() else {}
    if decisions.get("error"):        # stopped by an infrastructure error (e.g. network): run it again
        return None
    if lost_agent_step(decisions):    # a learning step was lost to the network: run it again
        return None
    kept = next((i for i in doc["iterations"] if i["round"] == doc.get("kept_round")), None)
    row = {"id": doc["id"], "valid": bool(kept and kept["valid"]),
           "failed_levels": kept["failed_levels"] if kept else ["L1"], **doc.get("final_metrics", {})}
    first = doc.get("first_pass") or {}
    revised = bool(doc.get("rule_feedback")) and bool(first)
    first_row = ({"id": doc["id"], "valid": bool(first["valid"]),
                  "failed_levels": first["failed_levels"], **first["metrics"]} if revised else row)
    return {"doc": doc, "decisions": decisions, "row": row, "first_row": first_row,
            "revised": revised}


def run_arm(arm: str = "documentation",
            model_name: str | None = None, dry_run: bool = False,
            limit: int | None = None, progress=print, observer=None,
            agent_kind: str | None = None, learn: bool = True,
            models: dict | None = None, rule_feedback: bool = True,
            ids=None, sample: int | None = None, seed: int = 42,
            resume: str | None = None,
            confirmed_only: bool = False, fresh_catalogue: bool = True,
            next_iterations: int = 3, limits: dict | None = None,
            failure_rule: str = "any_difference", promote_confirmed: bool = False,
            fold: int | None = None,
            redo: list | None = None, force_iterations: bool = False,
            replicate: int | None = None,
            trial: bool = False) -> dict:
    """Evaluate one setting (arm) over the dataset; used by the CLI and the site.

    trial: a learning run on a few chosen descriptions (for example a reviewer
    testing one description from zero). It learns into a catalogue of its own,
    guidelines/learned/<model>/[agents/]trials/trial_<stamp>/, so it never
    touches the catalogues of the study (replicates/rN, folds/fold_k).

    fold (stratified k-fold cross-validation, folds.py): with --arm documentation
    the run learns from the training descriptions of that fold only, into the
    fold's own catalogue, which starts empty (Reuse training); with
    --arm documentation+learned it tests on the fold's test descriptions with the
    confirmed generic guidelines of that catalogue (Reuse test).

    models: {"generator"|"orchestrator"|"retriever"|"expert": "provider:model"}
    observer receives live events: start, decision, iteration, guideline,
    rule_feedback, stop, example, error. Each example folder gets iterations.json, decisions.json
    and, when failures were detected, guideline_learning.json.
    """
    def emit(event):
        if observer:
            observer(event)

    settings = None
    if resume:                       # same folder, same settings as the interrupted run
        out = RUNS_DIR / resume
        if not re.fullmatch(r"batch_[A-Za-z0-9_.\-]+", resume) or not (out / "models.json").is_file():
            raise ValueError(f"Cannot resume {resume!r}: no such run")
        settings = json.loads((out / "models.json").read_text(encoding="utf-8"))
        arm, dry_run = settings["arm"], bool(settings.get("dry_run"))
        models = {k: v for k, v in (settings.get("models") or {}).items() if k in COMPONENTS}
        learn = settings.get("learn", learn)
        rule_feedback = settings.get("rule_feedback", rule_feedback)
        confirmed_only = bool(settings.get("confirmed_only", confirmed_only))
        if settings.get("learning_agents", LEARNING_AGENTS) != LEARNING_AGENTS:
            raise ValueError(f"{resume} cannot be resumed: its settings do not match this pipeline")
        next_iterations = int(settings.get("next_iterations", next_iterations))
        limits = settings.get("limits") or limits
        failure_rule = settings.get("failure_rule", failure_rule)
        promote_confirmed = bool(settings.get("promote_confirmed", promote_confirmed))
        fold = settings.get("fold")
        force_iterations = bool(settings.get("force_iterations"))
        replicate = settings.get("replicate")
        trial = bool(settings.get("trial"))
        ids, limit, sample = (settings.get("examples") or {}).get("ids"), None, None

    from diagnosis import FAILURE_RULES
    if failure_rule not in FAILURE_RULES:
        raise ValueError(f"failure rule must be one of {FAILURE_RULES}")
    # the budgets of every example of this run (defaults unless chosen)
    budgets = resolve_limits({**(limits or {}), "next_iterations": next_iterations})
    next_iterations = budgets["next_iterations"]

    if arm not in ("documentation", "documentation+learned"):
        raise ValueError("--arm must be documentation (First, Revised, Reuse training) or "
                         "documentation+learned (Reuse test)")
    # A Reuse test measures the learned guidelines: the catalogue is frozen for the
    # whole run, so all descriptions are generated under the same conditions.
    frozen = "learned" in arm
    if frozen:
        learn = False
    models = resolve_models(dict(models or {}))
    fold_role = None
    if fold is not None:
        from folds import fold_ids
        if learn and arm == "documentation":
            fold_role = "train"
        elif arm == "documentation+learned":
            fold_role = "test"
            confirmed_only = True            # the test receives only confirmed guidelines
        else:
            raise ValueError("--fold works with --arm documentation (learning) for the Reuse "
                             "training and --arm documentation+learned for the Reuse test")
        if not resume:
            ids, limit, sample = fold_ids(fold, fold_role), None, None
    gen_provider, gen_model = parse_spec(models["generator"])
    generator_name = GENERATOR_PROVIDER[gen_provider]
    gen_model = model_name or gen_model

    # each generator model has its own learned catalogues (a learning run writes into
    # one, a Reuse test reuses it), so runs with two models never mix guidelines:
    # guidelines/learned/<model>/agents/{replicates/rN | folds/fold_k | trials/trial_<stamp>}
    import guideline_store
    fold_catalogue = None
    tree = guideline_store.catalogue_for_model("dryrun" if dry_run else models["generator"]).parent
    # (not in a dry run: the circuit test needs no catalogue of its own)
    trial = bool(trial and fold is None and not dry_run and not resume) or bool(trial and resume)
    if trial and learn and not resume:   # a trial on a few descriptions: its own catalogue
        trial_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        fold_catalogue = str(tree / "trials" / f"trial_{trial_stamp}" / "learned_guidelines.json")
    elif fold is not None:               # each fold of each model has its own catalogue
        fold_catalogue = str(tree / "folds" / f"fold_{int(fold)}" / "learned_guidelines.json")
    elif replicate and learn:            # each repetition of a learning run has its own catalogue
        fold_catalogue = str(tree / "replicates" / f"r{int(replicate)}" / "learned_guidelines.json")
    # otherwise the model's own catalogue (guideline_store.choose_catalogue_for_run)
    catalogue = guideline_store.choose_catalogue_for_run(
        "dryrun" if dry_run else models["generator"],
        saved=(settings or {}).get("learned_catalogue") if resume else fold_catalogue)
    progress(f"learned catalogue of this run: {catalogue}")
    if frozen and not dry_run and not resume:
        known = [g for g in guideline_store.load_store()["guidelines"] if g.get("status") == "promoted"]
        if not known:
            raise ValueError(f"No guideline has been learned with {models['generator']} yet "
                             f"({catalogue} is empty): run the training of this round first.")

    data, selection = select_examples(
        json.loads(DATASET_PATH.read_text(encoding="utf-8")), limit, ids, sample, seed)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = models["generator"].replace(":", "-").replace("/", "-")
    label = "dryrun" if dry_run else (f"{safe}_{arm.replace('+', '_')}"
                                      + ("_confirmed" if confirmed_only else "")
                                      + (f"_fold{int(fold)}" if fold is not None else "")
                                      + ("_forced" if force_iterations else "")
                                      + (f"_r{int(replicate)}" if replicate and not trial else "")
                                      + "_agents"
                                      + ("_trial" if trial else ""))
    used = {} if dry_run else models
    if resume and redo:
        # descriptions that finished but lost a step to an infrastructure error
        # (network, cut answer): their first attempt is kept in _redone/ and their
        # confirmation tests go to the history of the guidelines; they run again
        reason = "run again: a step of the first attempt was lost to an infrastructure error"
        known = {_key(i): str(i) for i in (settings.get("examples") or {}).get("ids") or []}
        for eid in [str(i).strip() for i in redo if str(i).strip()]:
            if _key(eid) not in known:
                raise ValueError(f"description {eid} is not part of {resume}")
            eid = known[_key(eid)]                # "7" and "07" are the same description
            folder = out / f"id_{eid}"
            if folder.exists():
                keep = out / "_redone" / f"id_{eid}_{stamp}"
                keep.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(folder), str(keep))
            else:
                keep = None
            touched = [] if dry_run else guideline_store.supersede_tests(eid, reason, stamp)
            settings.setdefault("redone", []).append(
                {"id": eid, "at": stamp, "reason": reason,
                 "first_attempt": str(keep.relative_to(out)) if keep else None,
                 "tests_moved_to_history": touched})
            progress(f"id {eid} | run again (first attempt kept in {keep.name if keep else '-'}; "
                     f"its confirmation tests moved to the history of {len(touched)} guideline(s))")
    if resume:
        settings.setdefault("resumed_at", []).append(stamp)
        (out / "models.json").write_text(json.dumps(settings, indent=1), encoding="utf-8")
        progress(f"resuming {out.name}")
    else:
        out = RUNS_DIR / f"batch_{stamp}_{label}"
        out.mkdir(parents=True, exist_ok=True)
        (out / "models.json").write_text(json.dumps(
            {"dry_run": dry_run, "arm": arm, "models": used, "examples": selection,
             "learn": learn, "rule_feedback": rule_feedback,
             "confirmed_only": confirmed_only,
             "next_iterations": next_iterations,
             "limits": budgets, "failure_rule": failure_rule,
             "learned_catalogue": portable_path(catalogue),
             "promote_confirmed": promote_confirmed,
             "fold": fold, "fold_role": fold_role,
             "force_iterations": force_iterations, "replicate": replicate,
             "learning_agents": LEARNING_AGENTS,
             "trial": trial},
            indent=1), encoding="utf-8")
        if learn and fresh_catalogue and not dry_run:
            # a learning run starts with no learned guideline
            import guideline_store
            kept = guideline_store.start_empty(stamp)
            progress("learned catalogue: starting empty"
                     + (f" (the previous one was moved to {kept})" if kept else ""))
    if fold_role == "train":
        # nothing of the test descriptions is read while learning
        guideline_store.set_description_scope(selection["ids"])
        progress(f"k-fold cross-validation: fold {fold}, training on {len(selection['ids'])} "
                 "descriptions, own catalogue")
    elif fold_role == "test":
        guideline_store.set_description_scope(None)
        progress(f"k-fold cross-validation: fold {fold}, test on {len(selection['ids'])} "
                 "descriptions with the confirmed guidelines of the fold")
    progress(f"examples ({selection['mode']}"
             + (f", seed {selection['seed']}" if "seed" in selection else "")
             + f"): {', '.join(map(str, selection['ids']))}")
    if frozen and not (out / "learned_guidelines_used.json").is_file():
        import guideline_store
        promoted = [g for g in guideline_store.load_store()["guidelines"]
                    if g.get("status") == "promoted"]
        if confirmed_only:           # only those whose return improved a model
            everything = len(promoted)
            promoted = [g for g in promoted if (g.get("confirmation") or {}).get("confirmed")]
            progress(f"confirmed guidelines only: {len(promoted)} of {everything}")
        (out / "learned_guidelines_used.json").write_text(json.dumps(
            {"frozen": True, "leave_one_out": True, "confirmed_only": confirmed_only,
             "count": len(promoted), "guidelines": promoted},
            ensure_ascii=False, indent=1), encoding="utf-8")
        progress(f"learned guidelines frozen: {len(promoted)} in the catalogue; leave-one-out: "
                 "each description receives only those learned from other descriptions")
    emit({"type": "start", "ids": [e["id"] for e in data], "label": label,
          "run_dir": str(out), "models": used, "limits": budgets,
          "failure_rule": failure_rule, "promote_confirmed": promote_confirmed})

    kind = agent_kind or ("deterministic" if dry_run else "llm")
    agent = (FirstAllowedAgent() if kind == "deterministic"
             else LLMOrchestratorAgent(LLM(models["orchestrator"])))
    retriever_llm = expert_llm = None
    if not dry_run:
        if learn:
            retriever_llm, expert_llm = LLM(models["retriever"]), LLM(models["expert"])
        for name in COMPONENTS:
            progress(f"model | {name}: {models[name]}")
    progress(f"orchestrator agent: {getattr(agent, 'name', kind)}")
    model = ExactLabelModel() if dry_run else embedding_model()

    def relay(event):
        kind_, eid = event.get("type"), event.get("id")
        if kind_ == "decision":
            progress(f"id {eid} | agent decides: {event['action']} — {event['reason']}")
        elif kind_ == "iteration":
            verdict = "valid" if event["valid"] else "invalid " + ",".join(event["failed_levels"])
            progress(f"id {eid} | validator, draft {event['round']}: {verdict}")
        elif kind_ == "rule_feedback":
            progress(f"id {eid} | next iteration {event.get('iteration', 1)}: guideline(s) "
                     f"{', '.join(event['rules'])} sent back to the generator")
        elif kind_ == "iteration_effect":
            results = event.get("type_results") or {}
            progress(f"id {eid} | next iteration {event['iteration']}: "
                     + ("; ".join(f"{gid} {r['failure_type']} {r['errors_before']}->{r['errors_after']}"
                                  + (" confirmed" if r["removed"] > 0 else "")
                                  for gid, r in results.items()) or "no learned guideline sent")
                     + f" (mean score change {event['mean_change']:+.3f})")
        elif kind_ == "guideline":
            progress(f"id {eid} | guideline for {event['failure_type']}: {event['status']}"
                     + (f" ({event['guideline_id']})" if event.get("guideline_id") else ""))
        elif kind_ == "error":
            progress(f"id {eid} | ERROR {event['text']}")
        emit(event)

    rows, rows_after, revised_ids = [], [], []
    agent_choices: dict[str, int] = {}        # what the agent chose when it had a choice
    for entry in data:
        eid = entry["id"]
        example_dir = out / f"id_{eid}"
        done = finished_example(example_dir) if resume else None
        if done:                                   # finished before the interruption
            rows.append(done["first_row"]); rows_after.append(done["row"])
            if done["revised"]:
                revised_ids.append(eid)
            for d in done["decisions"].get("decisions", []):
                if len(d.get("allowed", [])) > 1:
                    key = (f"{d['action']} (among {' / '.join(d['allowed'])})"
                           + (" [default: agent reply unusable]" if d.get("fallback") else ""))
                    agent_choices[key] = agent_choices.get(key, 0) + 1
            for it in done["doc"]["iterations"]:
                emit({"type": "iteration", "id": eid, **{k: it.get(k) for k in (
                    "round", "kind", "valid", "failed_levels", "metrics", "seconds")}})
            first = done["doc"].get("first_pass") or {}
            emit({"type": "example", "id": eid, "valid": done["row"]["valid"],
                  "kept_round": done["doc"].get("kept_round"),
                  "metrics": {k: done["row"].get(k) for k in ("activity_semantic_similarity", "semantic_similarity",
                              "workflow_order_similarity", "connection_f1",
                              "collaboration_similarity", "alignment_coverage")},
                  "revised": done["revised"],
                  "first_pass_metrics": first.get("metrics") if done["revised"] else None,
                  "rounds": len(done["doc"]["iterations"]),
                  "stopped": done["decisions"].get("stopped") or "stop_success",
                  "detected": done["decisions"].get("detected_failures", []), "error": None})
            progress(f"id {eid} | already finished before the interruption: kept")
            continue
        if resume and example_dir.exists():       # interrupted mid-way: start it again
            keep = out / "_interrupted" / f"id_{eid}_{stamp}"
            keep.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(example_dir), str(keep))
            progress(f"id {eid} | did not finish (interrupted, infrastructure error, or a "
                     "learning step lost to the network): starting it again "
                     "(previous files kept in _interrupted)")
        example_dir.mkdir(parents=True, exist_ok=True)

        state = OrchestratorState(example_id=eid, provider=generator_name, arm=arm,
                           model_name=gen_model, run_dir=str(example_dir),
                           learn_enabled=learn, dry_run=dry_run,
                           rule_feedback_enabled=rule_feedback and next_iterations > 0,
                           max_revisions=next_iterations, limits=budgets,
                           failure_rule=failure_rule, promote_confirmed=promote_confirmed,
                           force_iterations=force_iterations)
        tools = make_tools(entry, model, on_event=relay,
                           retriever_llm=retriever_llm, expert_llm=expert_llm)
        final = run_example(state, agent, tools, on_event=relay)

        best = next((r for r in final.rounds if r["round"] == final.kept_round), None)
        row = {"id": eid,
               "valid": bool(best and best["valid"]),
               "failed_levels": best["failed_levels"] if best else ["L1"],
               **final.metrics}
        rows_after.append(row)
        for d in final.decisions:
            if len(d.get("allowed", [])) > 1:
                key = (f"{d['action']} (among {' / '.join(d['allowed'])})"
                       + (" [default: agent reply unusable]" if d.get("fallback") else ""))
                agent_choices[key] = agent_choices.get(key, 0) + 1
        first = final.first_pass
        if final.revised and first:
            revised_ids.append(eid)
            rows.append({"id": eid, "valid": bool(first["valid"]),
                         "failed_levels": first["failed_levels"], **first["metrics"]})
        else:
            rows.append(row)
        (example_dir / "iterations.json").write_text(json.dumps(
            {"id": eid, "kept_round": final.kept_round,
             "iterations": [{"round": r["round"], "kind": r.get("kind", "draft"),
                             "valid": r["valid"],
                             "failed_levels": r["failed_levels"],
                             "seconds": r.get("seconds"),
                             "validator_levels": r.get("validator_levels"),
                             "metrics": r.get("display_metrics", {}), "xml": r["xml"]}
                            for r in final.rounds],
             "first_pass": first or None,
             "rule_feedback": ({"round": final.first_revision_round,
                                "rules": final.rules_to_reapply}
                               if final.revised else None),
             "next_iterations": final.iteration_effects or None,
             "final_metrics": final.metrics},
            ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        (example_dir / "decisions.json").write_text(json.dumps(
            {"id": eid, "agent": getattr(agent, "name", kind), "stopped": final.stopped,
             "stop_reason": final.stop_reason, "error": final.error,
             "detected_failures": final.detected,
             "error_counts": final.error_counts,
             "first_pass_error_counts": first.get("error_counts") if first else None,
             "guidelines": final.guideline_outcomes,
             "rules_sent_back": final.rules_to_reapply if final.revised else [],
             "first_pass_detected_failures": first.get("detected") if first else None,
             "decisions": final.decisions},
            ensure_ascii=False, indent=1), encoding="utf-8")
        progress(f"id {eid} | {final.stopped}: valid={row['valid']} "
                 f"semantic={row.get('semantic_similarity')} "
                 f"failures={','.join(final.detected) or 'none'}")
        emit({"type": "example", "id": eid, "valid": row["valid"],
              "kept_round": final.kept_round,
              "metrics": {k: row.get(k) for k in ("activity_semantic_similarity", "semantic_similarity",
                          "workflow_order_similarity", "connection_f1",
                          "collaboration_similarity", "alignment_coverage")},
              "revised": final.revised,
              "first_pass_metrics": ({k: first["metrics"].get(k) for k in (
                                      "semantic_similarity", "workflow_order_similarity",
                                      "connection_f1", "collaboration_similarity",
                                      "alignment_coverage")}
                                     if final.revised and first else None),
              "rounds": len(final.rounds), "stopped": final.stopped,
              "detected": final.detected, "error": final.error})

    (out / "agent_choices.json").write_text(json.dumps(
        {"agent": getattr(agent, "name", kind), "choices": agent_choices}, indent=1),
        encoding="utf-8")
    for key, count in sorted(agent_choices.items()):
        progress(f"orchestrator agent chose {count} time(s): {key}")
    from validation import run_performance                   # validator, element by element
    levels = run_performance(out)
    progress("validator accuracy, first draft: " + " | ".join(
        f"{l} {levels['first_draft'][l]['accuracy']}" for l in ("L1", "L2", "L3", "L4")))
    import utility                                           # bonuses and penalties
    scores = utility.run_summary(out, [e["id"] for e in data])
    (out / "utility_summary.json").write_text(json.dumps(scores, indent=1), encoding="utf-8")
    progress(f"bonuses and penalties: {scores['total_penalty']:.0f} error(s) detected "
             f"(penalties), {scores['total_bonus']:.0f} resolved (bonuses), "
             f"utility {scores['utility']:+.0f} | detected {scores['detected_by_type']} | "
             f"resolved {scores['resolved_by_type']}")
    import fold_report                                       # mean, SD, min, max of every metric
    fold_report.write_run_summary(out)
    report = write_report(rows, out, label)                  # first pass
    report_after = None
    if revised_ids:                                          # after the second iteration
        report_after = write_report(rows_after, out, f"{label}_after_rule_feedback")
        report_after["revised_examples"] = revised_ids
        progress(f"second iteration ran on {len(revised_ids)} example(s): "
                 f"{', '.join(map(str, revised_ids))}")
    return {"run_dir": str(out), "label": label, "report": report,
            "agent_choices": agent_choices, "resumed": bool(resume),
            "utility_summary": scores,
            "report_after_rule_feedback": report_after, "revised_examples": revised_ids,
            "models": used}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--arm", default="documentation")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="the first N examples")
    parser.add_argument("--ids", default=None, help='chosen examples, e.g. "24,38,41-45"')
    parser.add_argument("--sample", type=int, default=None, help="N examples drawn at random")
    parser.add_argument("--seed", type=int, default=42, help="seed of the random draw")
    parser.add_argument("--agent", choices=("llm", "deterministic"), default=None)
    parser.add_argument("--no-learn", action="store_true")
    parser.add_argument("--no-rule-feedback", action="store_true",
                        help="do not send non-applied documentation rules back (no second iteration)")
    parser.add_argument("--next-iterations", type=int, default=3,
                        help="learning runs: maximum number of next iterations per description (0-10)")
    parser.add_argument("--promote-confirmed", action="store_true",
                        help="learning runs: an example-specific guideline that improved its own "
                             "description is rewritten in general terms and added to the catalogue")
    parser.add_argument("--max-decisions", type=int, default=None,
                        help="budget: orchestrator decisions per example (default 48)")
    parser.add_argument("--max-tool-calls", type=int, default=None,
                        help="budget: tool calls per example (default 40)")
    parser.add_argument("--keep-catalogue", action="store_true",
                        help="learning runs: keep learning into the current catalogue instead of "
                             "starting from an empty one")
    parser.add_argument("--confirmed-only", action="store_true",
                        help="reuse only the learned guidelines confirmed by a next iteration "
                             "(always the case in a Reuse test)")
    parser.add_argument("--fold", type=int, default=None, choices=range(1, 6), metavar="1-5",
                        help="stratified k-fold cross-validation: with --arm documentation, learn "
                             "on the 44 training descriptions of the fold; with --arm "
                             "documentation+learned, test on its 11 test descriptions")
    parser.add_argument("--force-iterations", action="store_true",
                        help="learning runs: every description goes through all the next iterations")
    parser.add_argument("--replicate", type=int, default=None, metavar="N",
                        help="number of this repetition of the same configuration (1, 2, 3)")
    parser.add_argument("--trial", action="store_true",
                        help="a learning run on a few chosen descriptions (e.g. --ids 07): learns into "
                             "its own catalogue under trials/, never into those of the study")
    parser.add_argument("--redo", default=None, metavar="IDS",
                        help='with --resume: run these finished descriptions again, e.g. "07,20" '
                             "(their first attempt and its tests are kept as history)")
    parser.add_argument("--resume", default=None, metavar="RUN_FOLDER",
                        help="continue an interrupted run (its folder name under runs/)")
    for name in COMPONENTS:
        parser.add_argument(f"--{name}", default=None, metavar="PROVIDER:MODEL")
    args = parser.parse_args()
    models = {name: getattr(args, name) for name in COMPONENTS if getattr(args, name)}
    info = run_arm(arm=args.arm, dry_run=args.dry_run,
                   limit=args.limit, agent_kind=args.agent, learn=not args.no_learn,
                   models=models, rule_feedback=not args.no_rule_feedback,
                   ids=args.ids, sample=args.sample, seed=args.seed, resume=args.resume,
                   confirmed_only=args.confirmed_only,
                   fresh_catalogue=not args.keep_catalogue,
                   next_iterations=args.next_iterations,
                   promote_confirmed=args.promote_confirmed,
                   fold=args.fold, force_iterations=args.force_iterations,
                   replicate=args.replicate,
                   trial=args.trial,
                   redo=[i for i in (args.redo or "").split(",") if i.strip()] or None,
                   limits={"max_agent_decisions": args.max_decisions,
                           "max_tool_calls": args.max_tool_calls})
    report = info["report"]
    print(json.dumps({"run": info["run_dir"], "models": info["models"],
                      "overall_valid_rate": report["validator"]["overall_valid_rate"],
                      "semantic_mean": report["metrics"]["semantic_similarity"].get("mean"),
                      "second_iteration_examples": info["revised_examples"],
                      "semantic_mean_after_rule_feedback": (
                          info["report_after_rule_feedback"]["metrics"]
                          ["semantic_similarity"].get("mean")
                          if info["report_after_rule_feedback"] else None)},
                     indent=2))


if __name__ == "__main__":
    main()
