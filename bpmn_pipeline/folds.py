"""Stratified k-fold cross-validation folds over the 55-description dataset."""
import json

from pipeline_config import DATASET_PATH, N_FOLDS


# Stratified k-fold cross-validation by complexity.
# Complexity of a description = number of elements of its reference model
# (activities, events, gateways) + its pools + its lanes. The models with pools
# or lanes are spread over the folds first, then the others are dealt in order
# of complexity (snake order), so every fold gets the same mix from simple to
# complex. The folds are computed once and saved in folds_complexity.json.
import re as _re
from pathlib import Path as _Path

COMPLEXITY_FOLDS_FILE = _Path(__file__).resolve().parent / "folds_complexity.json"
_FLOW_ELEMENTS = ("task", "userTask", "serviceTask", "manualTask", "scriptTask", "sendTask",
                  "receiveTask", "businessRuleTask", "callActivity", "subProcess",
                  "exclusiveGateway", "parallelGateway", "inclusiveGateway",
                  "eventBasedGateway", "complexGateway", "startEvent", "endEvent",
                  "intermediateCatchEvent", "intermediateThrowEvent", "boundaryEvent")


def _count(xml: str, tags) -> int:
    pattern = r"<(?:\w+:)?(?:%s)[\s/>]" % "|".join(tags)
    return len(_re.findall(pattern, xml))


def complexity(xml: str) -> dict:
    """Elements, pools and lanes of a reference model, and their sum."""
    elements = _count(xml, _FLOW_ELEMENTS)
    pools = _count(xml, ("participant",))
    lanes = _count(xml, ("lane",))
    return {"elements": elements, "pools": pools, "lanes": lanes,
            "complexity": elements + pools + lanes}


def stratified_folds(data: list[dict] | None = None, k: int = N_FOLDS) -> dict:
    """k folds stratified by complexity; folds are numbered 1..k."""
    data = data or json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    measure = {str(e["id"]): complexity(e["bpmn_xml"]) for e in data}
    size = len(data) // k
    capacity = [size + (1 if f < len(data) % k else 0) for f in range(k)]
    test = [[] for _ in range(k)]
    rank = lambda i: (measure[i]["complexity"], i)
    collab = sorted((i for i, m in measure.items() if m["pools"] or m["lanes"]), key=rank)
    others = sorted((i for i, m in measure.items() if not (m["pools"] or m["lanes"])), key=rank)

    def deal(ids, start):
        f, step = start, 1
        for i in ids:
            # snake order over the folds that still have room
            tries = 0
            while len(test[f]) >= capacity[f] and tries < 2 * k:
                f, step = _next(f, step, k); tries += 1
            test[f].append(i)
            f, step = _next(f, step, k)
        return f, step

    def _next(f, step, k):
        if 0 <= f + step < k:
            return f + step, step
        return f, -step

    deal(collab, 0)
    # the remaining elements are dealt so that the folds with fewer models with
    # pools or lanes receive the next ones first
    deal(others, k - 1)
    folds_out = []
    all_ids = [str(e["id"]) for e in data]
    for f in range(k):
        ids = sorted(test[f], key=lambda i: all_ids.index(i))
        values = [measure[i]["complexity"] for i in ids]
        folds_out.append({"fold": f + 1, "test_ids": ids,
                          "train_ids": [i for i in all_ids if i not in ids],
                          "test_complexity": {"mean": round(sum(values) / len(values), 2),
                                              "min": min(values), "max": max(values)},
                          "test_with_pools_or_lanes": [i for i in ids if i in collab]})
    return {"method": ("stratified k-fold cross-validation by complexity: elements "
                       "(activities, events, gateways) + pools + lanes of the reference model; "
                       "models with pools or lanes spread first, then snake order by complexity"),
            "k": k, "complexity": measure, "folds": folds_out}


def load_complexity_folds() -> dict:
    """The saved folds (computed and saved the first time)."""
    if not COMPLEXITY_FOLDS_FILE.is_file():
        COMPLEXITY_FOLDS_FILE.write_text(json.dumps(stratified_folds(), indent=1), encoding="utf-8")
    return json.loads(COMPLEXITY_FOLDS_FILE.read_text(encoding="utf-8"))


def fold_ids(fold: int, role: str) -> list[str]:
    """role 'train' -> the 44 training descriptions, 'test' -> the 11 test ones."""
    doc = load_complexity_folds()
    match = next((f for f in doc["folds"] if f["fold"] == int(fold)), None)
    if match is None:
        raise ValueError(f"fold must be between 1 and {doc['k']}")
    return list(match["train_ids" if role == "train" else "test_ids"])
