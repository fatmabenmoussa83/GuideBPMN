"""Create inspectable comparable elements from flow nodes and collaboration data."""

from config import TASK_LIKE_TAGS, GATEWAY_TAGS, EVENT_TAGS


def comparison_category(bpmn_type: str) -> str:
    """Shared type grouping; despite its use by semantics, it reads no labels."""
    if bpmn_type in TASK_LIKE_TAGS:
        return "activity"
    if bpmn_type in GATEWAY_TAGS:
        return bpmn_type  # gateway kinds must remain distinct
    if bpmn_type in EVENT_TAGS:
        return bpmn_type
    return bpmn_type


def semantic_category(bpmn_type: str) -> str:
    """Backward-compatible name used by the semantic matrix module."""
    return comparison_category(bpmn_type)


def compatible(a: dict, b: dict) -> bool:
    return a["category"] == b["category"]


def extract_elements(graph):
    elements = []
    for node_id, data in graph.nodes(data=True):
        elements.append({
            "kind": "flow_node", "id": node_id, "type": data["type"],
            "category": semantic_category(data["type"]),
            "label": data["name"] if data.get("has_name") else "",
            "has_label": bool(data.get("has_name")),
            "process_id": data.get("process_id"),
        })
    for pool_id, data in graph.graph.get("participants", {}).items():
        elements.append({
            "kind": "pool", "id": pool_id, "type": "participant",
            "category": "pool", "label": data["name"] if data.get("has_name") else "",
            "has_label": bool(data.get("has_name")),
            "process_id": data.get("process_ref"),
        })
    for lane_id, data in graph.graph.get("lanes", {}).items():
        elements.append({
            "kind": "lane", "id": lane_id, "type": "lane", "category": "lane",
            "label": data["name"] if data.get("has_name") else "",
            "has_label": bool(data.get("has_name")), "process_id": None,
        })
    for mf in graph.graph.get("message_flows", []):
        label = mf.get("name", "") if mf.get("has_name") else ""
        elements.append({
            "kind": "message_flow", "id": mf["id"], "type": "messageFlow",
            "category": "message_flow", "label": label,
            "has_label": bool(label), "process_id": None,
            "source": mf["source"], "target": mf["target"],
        })
    return elements


def labeled(elements):
    return [e for e in elements if e["has_label"]]
