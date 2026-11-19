"""XML -> NetworkX graph. The single source of truth for how a BPMN document
becomes something comparable."""

import xml.etree.ElementTree as ET
import networkx as nx

from config import FLOW_NODE_TAGS
from trace import trace, section, trace_table


def load_bpmn_graph_from_string(xml_str: str, label: str = "") -> nx.DiGraph:
    """Parses BPMN 2.0 XML into a DiGraph.

    Nodes carry (id, name, type, has_name, process_id); edges come from
    sequenceFlow. Pools / lanes / message flows are stored on graph.graph
    instead of as nodes -- they are organisational containers, not flow
    elements, and mixing them in would change what the structure metrics measure.
    """
    section("graph", f"parsing {label or 'graph'}")
    root = ET.fromstring(xml_str)
    prefix = ""
    if '}' in root.tag:
        prefix = f"{{{root.tag.split('}')[0].strip('{')}}}"

    graph = nx.DiGraph()
    processes = root.findall(f".//{prefix}process")
    process_details = []
    for process in processes:
        raw_name = process.attrib.get("name")
        process_details.append({
            "id": process.attrib.get("id"),
            "name": raw_name.strip() if raw_name and raw_name.strip() else "",
            "has_name": bool(raw_name and raw_name.strip()),
            "is_executable": process.attrib.get("isExecutable", ""),
        })

    # PASS 1 -- declare every real flow node and preserve subprocess hierarchy.
    # ElementTree does not expose a parent pointer, so the recursive walker
    # explicitly carries the current parent subprocess ID.
    subprocess_memberships = []

    def visit(element, process_id, parent_subprocess_id=None):
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        next_parent = parent_subprocess_id
        if tag in FLOW_NODE_TAGS:
            node_id = element.attrib.get("id")
            raw_name = element.attrib.get("name")
            has_name = raw_name is not None and raw_name.strip() != ""
            graph.add_node(
                node_id,
                name=raw_name if has_name else node_id,
                type=tag,
                has_name=has_name,
                xml_excerpt=ET.tostring(element, encoding="unicode")[:4000],
                process_id=process_id,
                parent_subprocess_id=parent_subprocess_id,
            )
            if parent_subprocess_id:
                subprocess_memberships.append({
                    "subprocess_id": parent_subprocess_id,
                    "member_id": node_id,
                    "member_type": tag,
                })
            # Children of this subprocess belong to it. The subprocess node
            # itself still belongs to the outer subprocess, if one exists.
            if tag == "subProcess":
                next_parent = node_id
        for child in list(element):
            visit(child, process_id, next_parent)

    for process in processes:
        process_id = process.attrib.get("id")
        visit(process, process_id)

    # PASS 2 -- add edges, but only between endpoints that actually exist.
    known = set(graph.nodes())
    skipped = []
    for process in processes:
        for flow in process.findall(f".//{prefix}sequenceFlow"):
            src, tgt = flow.attrib.get("sourceRef"), flow.attrib.get("targetRef")
            if not src or not tgt:
                skipped.append({
                    "flow_id": flow.attrib.get("id"),
                    "source_ref": src or "",
                    "target_ref": tgt or "",
                    "reason": "MISSING_ENDPOINT_REFERENCE",
                })
                continue
            if src not in known or tgt not in known:
                # A generated model can hold a sequenceFlow pointing at an id
                # never declared anywhere. A dangling reference is not
                # a traversable connection, so skipping it is correct -- not
                # merely a way to avoid the crash.
                skipped.append({
                    "flow_id": flow.attrib.get("id"),
                    "source_ref": src,
                    "target_ref": tgt,
                    "reason": "DANGLING_ENDPOINT_REFERENCE",
                })
                continue
            raw_name = flow.attrib.get("name")
            condition = flow.find(f"{prefix}conditionExpression")
            condition_text = "" if condition is None else " ".join(condition.itertext()).strip()
            graph.add_edge(
                src, tgt,
                id=flow.attrib.get("id"),
                name=raw_name.strip() if raw_name and raw_name.strip() else "",
                condition=condition_text,
            )

    # --- collaboration: pools, lanes, message flows ---
    participants, message_flows, lanes = {}, [], {}
    for collab in root.findall(f".//{prefix}collaboration"):
        for part in collab.findall(f"{prefix}participant"):
            raw = part.attrib.get("name")
            participants[part.attrib.get("id")] = {
                "name": raw if raw and raw.strip() else part.attrib.get("id"),
                "has_name": bool(raw and raw.strip()),
                "process_ref": part.attrib.get("processRef"),
            }
        for mf in collab.findall(f"{prefix}messageFlow"):
            s, t = mf.attrib.get("sourceRef"), mf.attrib.get("targetRef")
            if s and t:
                raw = mf.attrib.get("name")
                message_flows.append({
                    "id": mf.attrib.get("id"), "source": s, "target": t,
                    "name": raw.strip() if raw and raw.strip() else "",
                    "has_name": bool(raw and raw.strip()),
                })

    for process in processes:
        for lane_set in process.findall(f"{prefix}laneSet"):
            for lane in lane_set.findall(f"{prefix}lane"):
                raw = lane.attrib.get("name")
                lanes[lane.attrib.get("id")] = {
                    "name": raw if raw and raw.strip() else lane.attrib.get("id"),
                    "has_name": bool(raw and raw.strip()),
                    "process_id": process.attrib.get("id"),
                    "flow_node_refs": [r.text.strip()
                                       for r in lane.findall(f"{prefix}flowNodeRef")
                                       if r.text and r.text.strip()],
                }

    graph.graph["processes"] = process_details
    graph.graph["xml_namespace"] = prefix.strip("{}")
    graph.graph["participants"] = participants
    graph.graph["lanes"] = lanes
    graph.graph["message_flows"] = message_flows
    graph.graph["subprocess_memberships"] = subprocess_memberships
    graph.graph["skipped_sequence_flows"] = skipped

    # ---- traces ----
    trace("graph", f"nodes={graph.number_of_nodes()}  edges={graph.number_of_edges()}")
    unnamed = [n for n, d in graph.nodes(data=True) if not d["has_name"]]
    trace("graph", f"unnamed nodes: {len(unnamed)}  {unnamed[:6]}")
    trace("graph", f"pools={len(participants)}  lanes={len(lanes)}  messageFlows={len(message_flows)}")
    trace("graph", f"subprocess memberships={len(subprocess_memberships)}")
    if subprocess_memberships:
        trace_table(
            "graph",
            [(x["subprocess_id"], x["member_id"], x["member_type"])
             for x in subprocess_memberships],
            headers=["subprocess", "member", "member_type"],
            max_rows=30,
        )
    if skipped:
        trace("graph", f"!! skipped {len(skipped)} dangling sequenceFlow(s):")
        trace_table(
            "graph",
            [(row["flow_id"], row["source_ref"], row["target_ref"], row["reason"])
             for row in skipped],
            headers=["flow_id", "sourceRef", "targetRef", "reason"],
            max_rows=5,
        )
    return graph


def describe(graph: nx.DiGraph, label: str = "graph"):
    """Print a full node/edge dump. For use in the notebook, not in a batch run."""
    section("graph", f"describe {label}")
    trace_table("graph",
                [(n, d["type"], d["name"][:40], d["has_name"]) for n, d in graph.nodes(data=True)],
                headers=["id", "type", "name", "named"], max_rows=40)
    trace("graph", f"edges: {list(graph.edges())[:20]}")


# Standalone test: change only these values.
TEST_ID = "01"
TEST_GENERATOR = "gpt"


def run_test(test_id=TEST_ID, generator=TEST_GENERATOR, generated_path=None):
    from config import OUTPUT_DIR
    from dataset_io import load_pair, write_json
    pair = load_pair(test_id, generator, generated_path=generated_path)
    result = {"id": pair["id"], "generator": generator, "graphs": {}}
    for side, xml in (("gold", pair["gold_xml"]), ("generated", pair["generated_xml"])):
        graph = load_bpmn_graph_from_string(xml, f"{side}-{pair['id']}")
        describe(graph, side)
        result["graphs"][side] = {
            "node_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges(),
            "nodes": [{"id": n, **d} for n, d in graph.nodes(data=True)],
            "edges": [{"source": s, "target": t, **d} for s, t, d in graph.edges(data=True)],
            "participants": graph.graph["participants"],
            "lanes": graph.graph["lanes"],
            "message_flows": graph.graph["message_flows"],
            "subprocess_memberships": graph.graph["subprocess_memberships"],
            "processes": graph.graph["processes"],
            "skipped_sequence_flows": graph.graph["skipped_sequence_flows"],
        }
    path = write_json(result, OUTPUT_DIR / f"graph_loader_{generator}_{pair['id']}.json")
    trace("graph", f"written -> {path}")
    return result


if __name__ == "__main__":      # python <module>.py <id> <generated.json>
    import sys
    run_test(*sys.argv[1:2], generated_path=(sys.argv[2] if len(sys.argv) > 2 else None))
