"""Similarity evaluation of one generated diagram against its gold reference.

Wraps the similarity_evaluator package. Returns one compact dict per pair;
the detailed CSV exports stay in the component's own runner.

Collaboration rule of the pipeline: when the reference has no pool,
lane or message flow, it is a single-process convention of the dataset, not a
requirement of the description. The pools, lanes and message flows that the
generator adds are then not counted: the comparison uses a copy of the
generated model without them (every task, event and gateway inside stays and
is compared as usual). The strict values, computed on the model as generated,
are kept alongside (`*_strict`). When the reference has a collaboration,
nothing changes.
"""
import io
import contextlib
import re
import xml.etree.ElementTree as ET
from functools import lru_cache

from pipeline_config import add_shared_paths
add_shared_paths()

import trace as _trace
_trace.TRACE_ENABLED = False

from graph_loader import load_bpmn_graph_from_string
from type_matching import compute_type_precision_recall_grouped
from semantic_family_similarity import (
    compute_semantic_family_similarity, load_embedding_model,
)
from semantic_contextual_alignment import (
    compute_semantic_contextual_alignment, mapping_dict,
)
from connection_matching import compute_connection_matching
from workflow_order_similarity import compute_workflow_order_similarity
from collaboration_similarity import compute_collaboration_similarity


@lru_cache(maxsize=1)
def embedding_model():
    """BAAI/bge-base-en-v1.5, loaded once per process."""
    return load_embedding_model()


MODEL_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
COLLABORATION_TAGS = ("participant", "lane", "messageFlow")


def has_collaboration(xml: str) -> bool:
    """True when the model declares a pool, a lane or a message flow."""
    return bool(re.search(r"<(?:[\w-]+:)?(?:%s)[\s>/]" % "|".join(COLLABORATION_TAGS), xml or ""))


def without_collaboration(xml: str) -> str:
    """A copy of the model without collaboration, lane sets and their diagram
    shapes; processes and everything inside them are kept."""
    root = ET.fromstring(xml)
    removed = set()
    for parent in list(root.iter()):
        for child in list(parent):
            local = child.tag.rsplit("}", 1)[-1]
            if child.tag.startswith("{%s}" % MODEL_NS) and local in ("collaboration", "laneSet"):
                removed.update(e.get("id") for e in child.iter() if e.get("id"))
                parent.remove(child)
    for parent in list(root.iter()):                # diagram shapes of what was removed
        for child in list(parent):
            if child.get("bpmnElement") in removed:
                parent.remove(child)
    return ET.tostring(root, encoding="unicode")


def comparable_generated(gold_xml: str, generated_xml: str) -> tuple[str, bool]:
    """The generated model as compared with this reference, and whether its
    collaboration was set aside (reference without any collaboration)."""
    if generated_xml and not has_collaboration(gold_xml) and has_collaboration(generated_xml):
        try:
            return without_collaboration(generated_xml), True
        except ET.ParseError:
            return generated_xml, False
    return generated_xml, False


STRICT_KEYS = ("semantic_similarity", "activity_semantic_similarity",
               "alignment_coverage", "connection_precision",
               "connection_recall", "connection_f1", "workflow_order_similarity",
               "collaboration_similarity", "collaboration_applicable")


def evaluate_pair(gold_xml: str, generated_xml: str, model=None) -> dict:
    """All retained metrics for one pair (collaboration rule in the module
    docstring). `model` lets tests inject a fake."""
    model = model or embedding_model()
    compared, ignored = comparable_generated(gold_xml, generated_xml)
    result = _evaluate(gold_xml, compared, model)
    result["collaboration_ignored"] = ignored
    strict = _evaluate(gold_xml, generated_xml, model) if ignored else result
    result.update({f"{k}_strict": strict[k] for k in STRICT_KEYS})
    return result


def activity_labels(nodes: dict) -> dict:
    """Label agreement on activities only.

    The overall semantic score counts every labelled element, so a model that
    labels its gateways or its start and end events is penalised when the
    reference leaves them unlabelled: a difference of style, not of meaning.
    Activities always carry a label, in the references and in generated models,
    so this score compares what the two models say is done.

      similarity = sum of the accepted label similarities / max(reference, generated)
      precision  = matched activities / generated activities
      recall     = matched activities / reference activities
    """
    ref = sum(1 for x in nodes["gold_items"] if x["category"] == "activity" and x["has_text"])
    gen = sum(1 for x in nodes["generated_items"]
              if x["category"] == "activity" and x["has_text"])
    pairs = [a for a in nodes["assignments"] if a["category"] == "activity" and a["accepted"]]
    total = sum(a["score_contribution"] for a in pairs)
    precision = len(pairs) / gen if gen else None
    recall = len(pairs) / ref if ref else None
    f1 = (2 * precision * recall / (precision + recall)
          if precision and recall else (0.0 if gen and ref else None))
    return {"activity_semantic_similarity": round(total / max(ref, gen), 6) if max(ref, gen) else None,
            "activity_label_precision": None if precision is None else round(precision, 6),
            "activity_label_recall": None if recall is None else round(recall, 6),
            "activity_label_f1": None if f1 is None else round(f1, 6),
            "activity_matched": len(pairs), "activity_reference": ref, "activity_generated": gen}


def _evaluate(gold_xml: str, generated_xml: str, model) -> dict:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        gold = load_bpmn_graph_from_string(gold_xml, "gold")
        generated = load_bpmn_graph_from_string(generated_xml, "generated")
        types = compute_type_precision_recall_grouped(gold, generated)
        semantic = compute_semantic_family_similarity(gold, generated, model=model)
        alignment = compute_semantic_contextual_alignment(
            gold, generated, semantic["families"]["nodes"],
        )
        connection = compute_connection_matching(gold, generated, alignment)
        node_mapping = mapping_dict(alignment)
        order = compute_workflow_order_similarity(gold, generated, node_mapping)
        collaboration = compute_collaboration_similarity(
            gold, generated, node_mapping, model=model,
        )
    return {
        "semantic_similarity": semantic["semantic_similarity"],
        **activity_labels(semantic["families"]["nodes"]),
        "alignment_coverage": alignment["alignment_coverage"],
        "connection_precision": connection.get("precision"),
        "connection_recall": connection.get("recall"),
        "connection_f1": connection["f1_workflow_relation_similarity"],
        "connection_tp": connection.get("tp"), "connection_fp": connection.get("fp"),
        "connection_fn": connection.get("fn"),
        "workflow_order_similarity": order["workflow_order_similarity"],
        "order_consistency": order["order_consistency"],
        "order_coverage": order["coverage"],
        "order_tp": order.get("tp"), "order_fp": order.get("fp"),
        "order_fn": order.get("fn"),
        "collaboration_similarity": collaboration["structural_similarity"],
        "collaboration_applicable": collaboration["applicable"],
        "collaboration_tp": collaboration.get("tp"),
        "collaboration_fp": collaboration.get("fp"),
        "collaboration_fn": collaboration.get("fn"),
        # Composition diagnostics only, never similarity scores:
        "type_precision_diagnostic": types.get("precision"),
        "type_recall_diagnostic": types.get("recall"),
        "type_f1_diagnostic": types["f1"],
        "node_mapping": node_mapping,        # reused by the diagnosis step
        "counts": {
            "gold_nodes": gold.number_of_nodes(),
            "generated_nodes": generated.number_of_nodes(),
            "gold_flows": gold.number_of_edges(),
            "generated_flows": generated.number_of_edges(),
        },
    }


class ExactLabelModel:
    """Deterministic embedding stand-in: identical normalised label -> 1.0,
    anything else -> 0.0. Enough for identity dry-runs without downloads."""
    import numpy as _np

    def __init__(self):
        self._dims = {}

    def encode(self, texts, normalize_embeddings=True, show_progress_bar=False):
        np = self._np
        out = np.zeros((len(texts), 4096))
        for i, t in enumerate(texts):
            key = " ".join(str(t).strip().casefold().split())
            j = self._dims.setdefault(key, len(self._dims))
            out[i, j] = 1.0
        return out
