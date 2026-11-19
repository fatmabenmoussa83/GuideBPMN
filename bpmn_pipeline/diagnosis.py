"""The Failure detector: deterministic failure classifier (T1-T7) + the evidence files.

Maps the validator profile and the similarity metrics of one evaluated pair
onto the failure taxonomy, then writes the two files the guideline agents' evidence
is built from (bpmn_learner/evidence_registry.py):
  09_agent_input_preview.json    detected failures + summary evidence
  10_evidence_file_registry.json inventory of the sim-eval export folder

The LLM never chooses or changes the failure type.
"""
import json
import importlib.util
from functools import lru_cache
from pathlib import Path

from pipeline_config import REPO_ROOT

LEARNER_DIR = REPO_ROOT / "bpmn_learner"

# T6 is counted on the activities: the label score the paper reports
# (activity_semantic_similarity); it names the score in the summary evidence.
SEMANTIC_METRIC = "activity_semantic_similarity"


@lru_cache(maxsize=1)
def _evidence_registry():
    path = LEARNER_DIR / "evidence_registry.py"
    spec = importlib.util.spec_from_file_location("learner_evidence_registry", path)
    module = importlib.util.module_from_spec(spec)
    import sys as _sys
    _sys.modules[spec.name] = module   # dataclasses resolve annotations via sys.modules
    spec.loader.exec_module(module)
    return module


# How a difference from the reference becomes a failure type (T5-T7): the
# evaluator found at least one difference. No threshold.
FAILURE_RULES = ("any_difference",)


def difference_counts(metrics: dict) -> dict:
    """The individual differences from the reference, per failure type:
      T5  sequence flows missing or additional (if the flows agree: order
          relations missing or additional)
      T6  activities, of either model, without a partner
      T7  pools, lanes, memberships and message flows missing or additional
    A count is None when the saved scores do not hold the figures needed."""
    count = lambda key: metrics.get(key) or 0
    flows = (None if metrics.get("connection_fp") is None and metrics.get("connection_fn") is None
             else count("connection_fp") + count("connection_fn"))
    order = count("order_fp") + count("order_fn")
    reference, generated = metrics.get("activity_reference"), metrics.get("activity_generated")
    unpaired = (None if reference is None or generated is None
                else reference + generated - 2 * count("activity_matched"))
    collaboration = (count("collaboration_fp") + count("collaboration_fn")
                     if metrics.get("collaboration_applicable") else 0)
    return {"T5": flows if flows else (order if flows == 0 or order else flows),
            "T6": unpaired, "T7": collaboration}


VALIDATOR_TYPES = {"L1": "T1", "L2": "T2", "L3": "T3", "L4": "T4"}


def validator_counts(validation_result: dict) -> dict:
    """The individual validator errors, per failure type: for every failed level,
    the number of wrong elements it reports (at least 1)."""
    profile = (validation_result or {}).get("profile", {})
    return {t: max(1, len(profile[level].get("error_elements") or []))
            for level, t in VALIDATOR_TYPES.items()
            if profile.get(level, {}).get("result") is False}


def error_counts(validation_result: dict, metrics: dict) -> dict:
    """All open errors of one model, T1-T7: validator errors and differences
    from the reference."""
    counts = {t: n for t, n in difference_counts(metrics).items() if n}
    counts.update(validator_counts(validation_result))
    return counts


def classify(validation_result: dict, metrics: dict, rule: str = "any_difference") -> list[dict]:
    """T1-T7 rows in the schema the learner's runner reads."""
    if rule not in FAILURE_RULES:
        raise ValueError(f"failure rule must be one of {FAILURE_RULES}")
    profile = validation_result.get("profile", {})
    failures = []

    def level_row(level: str, failure_type: str, meaning: str):
        data = profile.get(level, {})
        detected = data.get("result") is False
        failures.append({
            "failure_type": failure_type,
            "status": "detected" if detected else "not_detected",
            "source": f"Validator {level}",
            "meaning": meaning,
            # number of individual errors: the wrong elements the level reports (at least 1)
            "errors": max(1, len(data.get("error_elements") or [])) if detected else 0,
            "summary_evidence": {
                "message": data.get("message"),
                "error_elements": data.get("error_elements", [])[:10],
            } if detected else {},
        })

    level_row("L1", "T1", "Invalid or unparseable XML")
    level_row("L2", "T2", "Incorrect gateway use")
    level_row("L3", "T3", "Incorrect control flow")
    level_row("L4", "T4", "Malformed pools, lanes, or message flows")

    differences = difference_counts(metrics)

    def metric_row(failure_type, meaning, detected, evidence):
        failures.append({
            "failure_type": failure_type,
            "status": "detected" if detected else "not_detected",
            "source": "Similarity Evaluator",
            "meaning": meaning,
            # number of individual errors of this type (at least 1 when detected)
            "errors": max(1, differences.get(failure_type) or 0) if detected else 0,
            "summary_evidence": evidence if detected else {},
        })

    conn = metrics.get("connection_f1")
    order = metrics.get("workflow_order_similarity")
    sem = metrics.get(SEMANTIC_METRIC)
    if sem is None:                       # scores saved before the activity score existed
        sem = metrics.get("semantic_similarity")
    collab = metrics.get("collaboration_similarity")
    applicable = bool(metrics.get("collaboration_applicable"))
    # T5: a sequence flow is missing or additional (connection F1 below 1), or an
    # order relation is missing or additional
    # T6: an activity of either model has no partner (two activities whose labels
    #     mean the same are paired, so a different wording alone is not a difference)
    # T7: a pool, lane, membership or message flow is missing or additional
    count = lambda key: metrics.get(key) or 0
    order_differences = count("order_fp") + count("order_fn")
    reference, generated = metrics.get("activity_reference"), metrics.get("activity_generated")
    unpaired = (None if reference is None or generated is None
                else reference + generated - 2 * count("activity_matched"))
    collaboration_differences = count("collaboration_fp") + count("collaboration_fn")
    metric_row(
        "T5", "Structural divergence from the Gold BPMN",
        (conn is not None and conn < 1.0) or order_differences > 0,
        {"connection_f1": conn, "workflow_order_similarity": order,
         "order_relations_missing_or_additional": order_differences,
         "rule": "any difference"},
    )
    metric_row(
        "T6", "Semantic divergence from the Gold BPMN",
        unpaired > 0 if unpaired is not None else (sem is not None and sem < 1.0),
        {SEMANTIC_METRIC: sem, "activities_without_partner": unpaired,
         "rule": "any difference"},
    )
    metric_row(
        "T7", "Collaboration divergence from the Gold BPMN",
        applicable and (collaboration_differences > 0 or (collab is not None and collab < 1.0)),
        {"collaboration_similarity": collab,
         "collaboration_relations_missing_or_additional": collaboration_differences,
         "rule": "any difference"},
    )
    return failures


def write_learner_inputs(example_id: str, generator_name: str,
                         failures: list[dict], evidence_folder: Path) -> dict:
    """Write 09 + 10 next to the sim-eval export of this pair."""
    agent_input = {
        "example_id": str(example_id).zfill(2),
        "generator": generator_name,
        "detected_failures": failures,
        "note": "Deterministic classification; the LLM never changes failure types.",
    }
    out09 = evidence_folder / "09_agent_input_preview.json"
    out09.write_text(json.dumps(agent_input, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    registry_module = _evidence_registry()
    # The registry separates validator evidence from similarity evidence;
    # run_batch.py writes the validator profile into <folder>/validator and the
    # sim-eval export into <folder>/similarity.
    registry = registry_module.build_registry(
        example_id=str(example_id).zfill(2),
        generator=generator_name,
        validator_dir=evidence_folder / "validator",
        similarity_dir=evidence_folder / "similarity",
    )
    registry_module.save_registry(registry, evidence_folder)
    return {"agent_input": out09,
            "registry": evidence_folder / "10_evidence_file_registry.json",
            "detected": [f["failure_type"] for f in failures
                         if f["status"] == "detected"]}
