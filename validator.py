import json
import statistics
import sys
from pathlib import Path

from lxml import etree

GENERATED_FILE = "generated_bpmn_gpt.json"   # input file to validate (standalone use)
OUTPUT_DIR = "validator_output"                 # base folder (standalone use only): one subfolder per example + performance_summary.json
XSD_DIR = "xsd"                                  # folder containing the 5 .xsd files

MODEL_USED = "gpt"   # which model generated the XML being validated: "gpt" / "claude"
                         # controls the output field name "generated_bpmn_xml_<MODEL_USED>"

PERFORMANCE_OUTPUT = "validator_performance_summary.json" # the one dataset-wide file, saved directly in OUTPUT_DIR

# WHY every output file is prefixed "validator_": the Similarity Evaluator writes
# its own combined.json / performance.json into ITS own per-example folders. Even
# though the two live in different directories, having two files with identical
# names describing different things is a real source of confusion -- and the
# Failure Classifier reads BOTH, so an ambiguous filename there would be a source of
# errors. Prefixing makes it impossible to mix them up.
FILE_PREFIX = "validator_"

# Cumulative failure history, one per example, appended to at every inner-loop
# attempt. WHY this file exists: the inner loop (Generator <-> Validator) FIXES
# failures. Without a history, an example that failed L1 twice and then passed on
# the third attempt looks, at the end, like it never failed at all -- so the
# Failure Classifier would never see it, and the Guideline Base would never learn
# that this error type exists. This file is what lets the Guideline Learner learn
# from ALL failures encountered, not only the ones the generator never managed to
# fix on its own.
HISTORY_OUTPUT = "validator_history.json"
# ─────────────────────────────────────────────────────────────────

LEVELS = ("L1", "L2", "L3", "L4")

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
NS = {"bpmn": BPMN_NS}

AUTHORIZED_GATEWAYS = {
    "exclusiveGateway",
    "parallelGateway",
    "inclusiveGateway",
    "eventBasedGateway",  
    "complexGateway",     
}

# Tags recognized as "flow nodes" (can have incoming/outgoing,
# can be referenced by a messageFlow)
FLOW_NODE_TAGS = {
    "task", "userTask", "serviceTask", "scriptTask", "manualTask",
    "businessRuleTask", "sendTask", "receiveTask", "subProcess",
    "transaction", "adHocSubProcess",
    "callActivity",
    "startEvent", "endEvent", "intermediateCatchEvent", "intermediateThrowEvent",
    "boundaryEvent",
    "exclusiveGateway", "parallelGateway", "inclusiveGateway",
    "eventBasedGateway", "complexGateway",
}

# ─────────────────────────────────────────────────────────────────
# CHECKLIST_REFERENCE — for each level, what rule/standard/reference was
# actually used to judge it. Included in every output file so a reader can
# see, per level, exactly what was checked against, not just the result.
# ─────────────────────────────────────────────────────────────────
SUBPROCESS_TAGS = {"subProcess", "transaction", "adHocSubProcess"}
from soundness import analyze_scope  # noqa: E402  (C8, behavioural soundness)
# Flow nodes that are not activities (a boundary event cannot be attached to them).
ACTIVITY_EXCLUDED_TAGS = {"startEvent", "endEvent", "intermediateCatchEvent",
                          "intermediateThrowEvent", "boundaryEvent", "exclusiveGateway",
                          "parallelGateway", "inclusiveGateway", "eventBasedGateway",
                          "complexGateway"}

CHECKLIST_REFERENCE = {
    "L1": {
        "name": "Syntax and Schema Conformance",
        "standard": "BPMN 2.0 official XSD schema, published by the OMG",
        "files_used": ["BPMN20.xsd", "Semantic.xsd", "BPMNDI.xsd", "DC.xsd", "DI.xsd"],
        "xsd_dir": XSD_DIR,
        "note": "Children are reordered to the schema's canonical xsd:sequence order "
                "before validation, since ordering alone is not semantically meaningful "
                "(confirmed on the gold corpus and on real BPMN tooling).",
    },
    "L2": {
        "name": "Gateway Types and Event-Based Gateway Rules",
        "standard": "BPMN 2.0 standard gateway vocabulary; BPMN 2.0.2 section 10.6.6",
        "authorized_types": sorted(AUTHORIZED_GATEWAYS),
        "note": "Any element with 'Gateway' in its tag name, including inside "
                "sub-processes, must be one of these 5 types. An eventBasedGateway "
                "has at least two outgoing sequence flows, none with a condition, and "
                "each leads directly to an intermediate catch event (message, timer, "
                "signal or conditional) or a receive task.",
        "division_of_labour": "The type-vocabulary branch overlaps the XSD on purpose "
                "(defence in depth if L1 is ever skipped); a non-BPMN gateway tag is "
                "first a grammar error, reported by L1. The event-based gateway rules "
                "are the part the XSD cannot express: they relate a gateway to its "
                "outgoing flows and to the TARGETS of those flows, and XSD validates "
                "each element in isolation. Gateway in/out DEGREES are checked in L3 "
                "(C4) because degree rules apply uniformly to every flow node.",
    },
    "L3": {
        "name": "Flow Integrity and Connectivity",
        "standard": "Graph-theoretic properties applied to BPMN's sequenceFlow semantics",
        "conditions_checked": [
            "C1: every flow scope (process or expanded sub-process) has a startEvent and an endEvent "
            "(a GuideBPMN modelling rule: BPMN allows implicit start/end in some cases)",
            "C2: every sequenceFlow connects two existing nodes of the same scope",
            "C3: every node has an incoming flow (except start/boundary events and catch links) "
            "and an outgoing flow (except end events and throw links); start events have no "
            "incoming flow and end events no outgoing flow",
            "C4: every gateway splits or merges the flow",
            "C5: every node is reachable from a startEvent and can reach an endEvent (directed)",
            "C6: the same rules apply inside every expanded sub-process; event sub-processes "
            "have no sequence flow; ad-hoc sub-processes are exempt from flow rules",
            "C7: the flow of each scope forms one connected block (no separate start-to-end chain)",
            "C8: behaviour (token game, soundness.py), run on scopes that pass C1-C7: no deadlock "
            "(tokens left that can never move) and the process can always complete; a flow that "
            "can carry two tokens (lack of synchronisation) is reported as a warning",
        ],
        "note": "Each <process> and each expanded sub-process is a separate flow scope. "
                "boundaryEvent elements are entered through attachedToRef; link events "
                "connect a throw to the catch with the same name. The verdict and the "
                "per-element overview come from one shared analysis.",
    },
    "L4": {
        "name": "Pool, Lane and Message Consistency",
        "standard": "BPMN 2.0 collaboration, messageFlow and laneSet semantics",
        "note": "Applies if the document contains a <collaboration> or a <laneSet>. Every "
                "messageFlow must connect two elements belonging to two DIFFERENT pools; "
                "gateways and lanes never send or receive messages, start/catch/boundary "
                "events are never sources, end/throw events are never targets. Every lane's "
                "flowNodeRef must name a flow node of the process (or sub-process) that "
                "owns the laneSet, and a flow node belongs to at most one lane of a laneSet. "
                "Flow nodes left outside every lane are reported as a warning, not a failure.",
    },
}


def local_tag(elem) -> str:
    """Return an element's local tag, ignoring XML comments/instructions.

    lxml represents comments and processing instructions with callable ``tag``
    objects rather than strings.  They are valid XML nodes but are not BPMN
    elements and therefore must be skipped by the semantic validation levels.
    """
    if not isinstance(getattr(elem, "tag", None), str):
        return ""
    return etree.QName(elem).localname


def build_line_lookup(xml_doc):
    """Maps every element id in the document to the line number it was
    written on in the generated XML file, so a failure can point to an
    exact location, not just an abstract element id."""
    lookup = {}
    for elem in xml_doc.iter():
        elem_id = elem.get("id")
        if elem_id:
            lookup[elem_id] = elem.sourceline
    return lookup


def locate(elem_id, line_lookup):
    """Formats an element id together with its source line, e.g. 'Task_3 (line 6)'.
    Falls back gracefully if the id isn't found in the lookup."""
    if elem_id in line_lookup:
        return f"{elem_id} (line {line_lookup[elem_id]})"
    return f"{elem_id} (line unknown)"


def load_xsd(xsd_path: Path) -> etree.XMLSchema:
    xsd_doc = etree.parse(str(xsd_path))
    return etree.XMLSchema(xsd_doc)


# ─────────────────────────────────────────────────────────────────
# Canonical child order, extracted directly from the xsd:sequence
# definitions of the official schema (Semantic.xsd: tFlowNode, tActivity,
# tCatchEvent/tThrowEvent, tSequenceFlow). We reorder according to this
# list before XSD validation, to neutralize order differences that carry
# no semantic meaning (even the gold set does not always follow the strict
# order, and real BPMN tools like bpmn.io are themselves order-tolerant).
# ─────────────────────────────────────────────────────────────────
CANONICAL_CHILD_ORDER = [
    # tBaseElement: documentation and extensionElements come FIRST in every BPMN element.
    # (Missing here, they were pushed to the end and a correctly ordered model failed L1.)
    "documentation", "extensionElements",
    "incoming", "outgoing",
    "ioSpecification", "property",
    "dataInputAssociation", "dataOutputAssociation",
    "resourceRole",
    "dataOutput", "outputSet",
    "conditionExpression",
    "messageEventDefinition", "timerEventDefinition", "signalEventDefinition",
    "errorEventDefinition", "escalationEventDefinition", "conditionalEventDefinition",
    "multiInstanceLoopCharacteristics", "standardLoopCharacteristics", "loopCharacteristics",
]


def reorder_children(xml_doc):
    """Reorders the direct children of every element according to the XSD's
    canonical order, without adding/removing/modifying any content. Tags not
    found in the list keep their relative position, pushed after known tags."""
    for elem in xml_doc.iter():
        children = list(elem)
        if len(children) < 2:
            continue

        def sort_key(child):
            # lxml comments and processing instructions are children too, but
            # their ``tag`` is a Cython callable rather than an XML QName.
            # Preserve them and place them after sortable BPMN elements.
            if not isinstance(child.tag, str):
                return len(CANONICAL_CHILD_ORDER) + 1
            tag = etree.QName(child).localname
            return CANONICAL_CHILD_ORDER.index(tag) if tag in CANONICAL_CHILD_ORDER else len(CANONICAL_CHILD_ORDER)

        sorted_children = sorted(children, key=sort_key)
        if sorted_children != children:
            for child in children:
                elem.remove(child)
            for child in sorted_children:
                elem.append(child)
    return xml_doc


def check_l1(xml_str: str, xsd: etree.XMLSchema):
    """L1: well-formed + conforms to the official BPMN20.xsd schema.
    Returns (ok, message, xml_doc, error_locations). xml_doc is None ONLY if
    the XML is truly impossible to parse (technical failure, not a
    short-circuit); if the XML parses but fails XSD conformance, xml_doc is
    still returned so that L2/L3/L4 can run independently."""
    try:
        xml_doc = etree.fromstring(xml_str.encode("utf-8"))
    except etree.XMLSyntaxError as e:
        location = f"line {e.lineno}, column {e.offset}" if hasattr(e, "lineno") else "unknown location"
        return False, f"malformed XML (cannot be parsed) -> {e}", None, [location]

    xml_doc = reorder_children(xml_doc)

    if not xsd.validate(xml_doc):
        errors = "; ".join(str(e) for e in xsd.error_log)
        error_locations = [f"line {e.line}" for e in xsd.error_log]
        return False, f"does not conform to the BPMN20.xsd schema -> {errors}", xml_doc, error_locations

    return True, "OK", xml_doc, []


def _all_gateways(xml_doc):
    """Every gateway element, including those nested inside sub-processes."""
    for process in xml_doc.findall("bpmn:process", NS):
        for child in process.iterdescendants():
            tag = local_tag(child)
            if "Gateway" in tag:
                yield child, tag


EVENT_GATEWAY_TARGET_DEFS = ("messageEventDefinition", "timerEventDefinition",
                             "signalEventDefinition", "conditionalEventDefinition")


def _event_gateway_problems(gateway):
    """BPMN 2.0.2 (10.6.6): an event-based gateway waits for one of several events.
    Returns the reasons why this eventBasedGateway breaks those rules."""
    scope = gateway.getparent()
    gid = gateway.get("id")
    by_id = {c.get("id"): c for c in scope if isinstance(c.tag, str) and c.get("id")}
    outgoing = [c for c in scope if isinstance(c.tag, str) and local_tag(c) == "sequenceFlow"
                and c.get("sourceRef") == gid]
    reasons = []
    if len(outgoing) < 2:
        reasons.append(f"event-based gateway needs at least two outgoing sequence flows "
                       f"(found {len(outgoing)})")
    for flow in outgoing:
        if flow.find("bpmn:conditionExpression", NS) is not None:
            reasons.append(f"sequenceFlow '{flow.get('id')}' after an event-based gateway "
                           f"must not have a condition")
        target = by_id.get(flow.get("targetRef"))
        if target is None:
            continue                       # missing targets are reported by L3
        ttag = local_tag(target)
        ok = ttag == "receiveTask" or (ttag == "intermediateCatchEvent" and any(
            target.find(f"bpmn:{d}", NS) is not None for d in EVENT_GATEWAY_TARGET_DEFS))
        if not ok:
            reasons.append(f"event-based gateway leads directly to {ttag} "
                           f"'{target.get('id')}'; each branch must first reach an "
                           f"intermediate catch event (message, timer, signal, conditional) "
                           f"or a receive task")
    return reasons


def check_l2(xml_doc, line_lookup):
    """L2: every gateway must be of a type authorized by the BPMN 2.0 standard.
    Scans ALL <process> elements (multi-pool included) and every nested
    sub-process."""
    processes = xml_doc.findall("bpmn:process", NS)
    if not processes:
        return False, "no <process> found", []

    unauthorized_elements = []
    for child, tag in _all_gateways(xml_doc):
        if tag not in AUTHORIZED_GATEWAYS:
            elem_id = child.get("id", "?")
            unauthorized_elements.append(f"{locate(elem_id, line_lookup)} ({tag})")

    if unauthorized_elements:
        return False, f"unauthorized gateway type(s) -> {unauthorized_elements}", unauthorized_elements

    for child, tag in _all_gateways(xml_doc):
        if tag == "eventBasedGateway":
            reasons = _event_gateway_problems(child)
            if reasons:
                located = [locate(child.get("id", "?"), line_lookup)]
                return False, f"{reasons[0]} -> {located}", located

    return True, "OK", []


def _has_definition(elem, name):
    return elem.find(f"bpmn:{name}", NS) is not None


def _is_event_subprocess(elem):
    return (local_tag(elem) in SUBPROCESS_TAGS
            and str(elem.get("triggeredByEvent", "false")).lower() == "true")


def _l3_analyze_scope(container, process_id, line_lookup, nodes_out, problems_out):
    """Analyzes ONE flow scope (a <process> or a sub-process body) and recurses
    into nested sub-processes. The SAME analysis feeds both the verdict
    (check_l3) and the per-element overview (overview_l3), so the two can
    never disagree.

    nodes_out:    one dict per flow node {id, tag, line, process, reasons}
    problems_out: scope-level problems {id, tag, line, process, reason, located}
    """
    scope_tag = local_tag(container)
    scope_id = container.get("id", "?")
    scope_key = f"process:{scope_id}" if scope_tag == "process" else f"{scope_tag}:{scope_id}"
    adhoc = scope_tag == "adHocSubProcess"

    nodes, edges, starts, ends, boundaries = {}, [], [], [], []

    for child in container:
        tag = local_tag(child)
        if not tag:
            continue
        elem_id = child.get("id")
        if tag == "sequenceFlow":
            src, tgt = child.get("sourceRef"), child.get("targetRef")
            if not src or not tgt:
                problems_out.append({
                    "id": elem_id or "?", "tag": tag, "line": child.sourceline, "process": process_id,
                    "reason": f"sequenceFlow '{elem_id}' missing sourceRef/targetRef",
                    "located": [locate(elem_id or "?", line_lookup)]})
            else:
                edges.append((src, tgt, elem_id))
        elif tag in FLOW_NODE_TAGS:
            if not elem_id:
                problems_out.append({
                    "id": f"<{tag}>", "tag": tag, "line": child.sourceline, "process": process_id,
                    "reason": f"element '{tag}' has no id",
                    "located": [f"<{tag}> (no id, line {child.sourceline})"]})
                continue
            nodes[elem_id] = child
            if tag == "startEvent":
                starts.append(elem_id)
            elif tag == "endEvent":
                ends.append(elem_id)
            elif tag == "boundaryEvent":
                host = child.get("attachedToRef")
                if not host:
                    problems_out.append({
                        "id": elem_id, "tag": tag, "line": child.sourceline, "process": process_id,
                        "reason": f"boundaryEvent '{elem_id}' missing attachedToRef",
                        "located": [locate(elem_id, line_lookup)]})
                else:
                    boundaries.append((elem_id, host))

    event_subs = {n for n, e in nodes.items() if _is_event_subprocess(e)}
    flow_nodes = [n for n in nodes if n not in event_subs]
    problems_before = len(problems_out)
    own_entries = []

    # C1: a scope that contains a flow must start and end explicitly
    # (an ad-hoc sub-process has no sequence flow by definition).
    if flow_nodes and not adhoc:
        if not starts:
            problems_out.append({
                "id": scope_key, "tag": scope_tag, "line": container.sourceline, "process": process_id,
                "reason": f"no startEvent found in {scope_key} (GuideBPMN requires explicit "
                          f"start and end events; BPMN allows implicit ones in some cases)",
                "located": [f"{scope_key} (line {container.sourceline})"]})
        if not ends:
            problems_out.append({
                "id": scope_key, "tag": scope_tag, "line": container.sourceline, "process": process_id,
                "reason": f"no endEvent found in {scope_key} (GuideBPMN requires explicit "
                          f"start and end events; BPMN allows implicit ones in some cases)",
                "located": [f"{scope_key} (line {container.sourceline})"]})

    # C2: a sequenceFlow must connect two nodes of the SAME scope
    for src, tgt, flow_id in edges:
        for role, ref in (("source", src), ("target", tgt)):
            if ref not in nodes:
                where = ("is in another process/sub-process" if ref in line_lookup
                         else "does not exist anywhere in the document")
                flow_loc = locate(flow_id or "?", line_lookup)
                problems_out.append({
                    "id": flow_id or "?", "tag": "sequenceFlow",
                    "line": line_lookup.get(flow_id), "process": process_id,
                    "reason": f"sequenceFlow {flow_loc} references a {role} '{ref}' that {where}",
                    "located": [f"{flow_loc} -> {role}Ref '{ref}' {where}"]})

    valid_edges = [(s, t) for s, t, _ in edges if s in nodes and t in nodes]
    indeg, outdeg = {}, {}
    succ = {n: set() for n in nodes}
    pred = {n: set() for n in nodes}
    for s, t in valid_edges:
        outdeg[s] = outdeg.get(s, 0) + 1
        indeg[t] = indeg.get(t, 0) + 1
        succ[s].add(t)
        pred[t].add(s)
    # A boundary event is entered through its host activity, which must be an
    # activity of the same scope.
    for b_id, host in boundaries:
        host_tag = local_tag(nodes[host]) if host in nodes else None
        if host_tag is None or host_tag in ACTIVITY_EXCLUDED_TAGS:
            problems_out.append({
                "id": b_id, "tag": "boundaryEvent", "line": nodes[b_id].sourceline, "process": process_id,
                "reason": f"boundaryEvent '{b_id}' is attached to '{host}', which is not an "
                          f"activity of {scope_key}",
                "located": [locate(b_id, line_lookup)]})
            continue
        succ[host].add(b_id)
        pred[b_id].add(host)
    # Link events: a throw link continues at the catch link with the same name.
    link_throws = [n for n, e in nodes.items() if local_tag(e) == "intermediateThrowEvent"
                   and _has_definition(e, "linkEventDefinition")]
    link_catches = [n for n, e in nodes.items() if local_tag(e) == "intermediateCatchEvent"
                    and _has_definition(e, "linkEventDefinition")]
    for t_id in link_throws:
        for c_id in link_catches:
            if (nodes[t_id].get("name") or "") == (nodes[c_id].get("name") or ""):
                succ[t_id].add(c_id)
                pred[c_id].add(t_id)

    def _walk(roots, graph):
        seen, stack = set(), list(roots)
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(graph.get(cur, ()) - seen)
        return seen

    forward = _walk(starts, succ)
    backward = _walk(ends, pred)

    # C7: the flow of a scope forms ONE connected block (undirected); separate
    # start-to-end chains are detached. Event sub-processes are exempt.
    main_block = set()
    if starts and not adhoc:
        undirected = {n: set() for n in flow_nodes}
        for a, nbrs in succ.items():
            for b in nbrs:
                if a in undirected and b in undirected:
                    undirected[a].add(b)
                    undirected[b].add(a)
        main_block = _walk([starts[0]], undirected)

    own_scope_problems = len(problems_out) - problems_before
    for node_id, elem in nodes.items():
        tag = local_tag(elem)
        reasons = []
        if main_block and node_id not in event_subs and not adhoc and node_id not in main_block:
            reasons.append("detached from the main flow (separate start-to-end chain)")
        in_n, out_n = indeg.get(node_id, 0), outdeg.get(node_id, 0)

        if node_id in event_subs:
            if in_n or out_n:
                reasons.append("event sub-process must not have incoming or outgoing sequence flows")
        elif not adhoc:
            is_link_catch = node_id in link_catches
            is_link_throw = node_id in link_throws
            # C3: incoming / outgoing connections
            if tag == "startEvent":
                if in_n:
                    reasons.append("startEvent must not have an incoming sequence flow")
            elif tag == "boundaryEvent":
                if in_n:
                    reasons.append("boundaryEvent must not have an incoming sequence flow")
            elif not in_n and not is_link_catch:
                reasons.append("no incoming connection")
            if tag == "endEvent":
                if out_n:
                    reasons.append("endEvent must not have an outgoing sequence flow")
            elif not out_n and not is_link_throw:
                reasons.append("no outgoing connection")
            # C4: gateways must split or merge
            if "Gateway" in tag and in_n <= 1 and out_n <= 1:
                reasons.append(f"gateway has no branching/merging role ({in_n} incoming, {out_n} outgoing)")
            # C5: directed reachability (only meaningful once C1 holds)
            if starts and node_id not in forward and "no incoming connection" not in reasons:
                reasons.append("not reachable from a startEvent")
            if ends and node_id not in backward and "no outgoing connection" not in reasons:
                reasons.append("cannot reach an endEvent")

        entry = {"id": node_id, "tag": tag, "line": elem.sourceline,
                 "process": process_id, "reasons": reasons}
        nodes_out.append(entry)
        own_entries.append(entry)

        # C6: recurse into the body of every (expanded) sub-process
        if tag in SUBPROCESS_TAGS:
            _l3_analyze_scope(elem, process_id, line_lookup, nodes_out, problems_out)

    # C8: behaviour, only when the structure of this scope is sound (C1-C7)
    if flow_nodes and not adhoc and not own_scope_problems and not any(e["reasons"] for e in own_entries):
        behaviour = analyze_scope(container, FLOW_NODE_TAGS, SUBPROCESS_TAGS)
        for finding in behaviour["deadlocks"] + behaviour["no_completion"]:
            problems_out.append({
                "id": finding["element"], "tag": local_tag(nodes[finding["element"]]) if finding["element"] in nodes else scope_tag,
                "line": nodes[finding["element"]].sourceline if finding["element"] in nodes else container.sourceline,
                "process": process_id, "reason": finding["reason"],
                "located": [locate(finding["element"], line_lookup)]})
        for finding in behaviour["unsynchronised"]:
            for e in own_entries:
                if e["id"] == finding["element"]:
                    e["warning"] = finding["reason"]
        if behaviour["status"] == "not_analysed" and own_entries:
            own_entries[0]["warning"] = "behaviour not analysed (state space too large)"


def _l3_analyze(xml_doc, line_lookup):
    nodes_out, problems_out = [], []
    for process in xml_doc.findall("bpmn:process", NS):
        _l3_analyze_scope(process, process.get("id", "?"), line_lookup, nodes_out, problems_out)
    return nodes_out, problems_out


def check_l3(xml_doc, line_lookup):
    """L3: flow integrity and consistency. Each <process> (one per pool) and
    each expanded sub-process body is an independent flow scope. Returns the
    FIRST problem found; overview_l3 reports all of them from the same analysis."""
    if not xml_doc.findall("bpmn:process", NS):
        return False, "no <process> found", []
    nodes_out, problems_out = _l3_analyze(xml_doc, line_lookup)
    if problems_out:
        p = problems_out[0]
        return False, f"{p['reason']} (process '{p['process']}')", p["located"]
    for n in nodes_out:
        if n["reasons"]:
            located = [locate(n["id"], line_lookup)]
            return False, f"{n['reasons'][0]} -> {located} (process '{n['process']}')", located
    return True, "OK", []


FORBIDDEN_MESSAGE_SOURCES = {"startEvent", "intermediateCatchEvent", "boundaryEvent"}
FORBIDDEN_MESSAGE_TARGETS = {"endEvent", "intermediateThrowEvent"}


def _l4_endpoint_problems(src_tag, tgt_tag):
    reasons = []
    if src_tag == "lane":
        reasons.append("a lane cannot be the source of a message flow (use the pool or a flow node)")
    if tgt_tag == "lane":
        reasons.append("a lane cannot be the target of a message flow (use the pool or a flow node)")
    if "Gateway" in (src_tag or ""):
        reasons.append(f"a gateway ('{src_tag}') cannot send a message flow")
    if "Gateway" in (tgt_tag or ""):
        reasons.append(f"a gateway ('{tgt_tag}') cannot receive a message flow")
    if src_tag in FORBIDDEN_MESSAGE_SOURCES:
        reasons.append(f"a {src_tag} cannot be the source of a message flow")
    if tgt_tag in FORBIDDEN_MESSAGE_TARGETS:
        reasons.append(f"a {tgt_tag} cannot be the target of a message flow")
    return reasons


def _l4_context(xml_doc, collaboration):
    participant_process = {}
    for participant in collaboration.findall("bpmn:participant", NS):
        pid = participant.get("id")
        if pid:
            participant_process[pid] = participant.get("processRef") or pid
    node_owner, node_tag = {}, {}
    for process in xml_doc.findall("bpmn:process", NS):
        process_id = process.get("id")
        for child in process.iterdescendants():
            elem_id = child.get("id")
            if elem_id:
                node_owner[elem_id] = process_id
                node_tag[elem_id] = local_tag(child)

    def resolve_owner(ref):
        if ref in node_owner:
            return node_owner[ref]
        return participant_process.get(ref)

    return resolve_owner, node_tag


def _lane_scope(lane_set):
    """The process or sub-process whose flow nodes a (child) laneSet partitions."""
    scope = lane_set.getparent()
    while scope is not None and local_tag(scope) in ("lane", "laneSet", "childLaneSet"):
        scope = scope.getparent()
    return scope


def _l4_lanes(xml_doc, line_lookup):
    """Lane checks shared by check_l4 and overview_l4 (one analysis, so they agree).

    Returns one item per lane: {id, line, scope, reasons, warning}. A lane is
    incorrect when a flowNodeRef does not name a flow node of the scope that owns
    its laneSet, or when a flow node is listed in two lanes of the same laneSet.
    Flow nodes outside every lane only add a warning (BPMN does not require it)."""
    items = []
    lane_sets = [e for e in xml_doc.iter() if isinstance(e.tag, str)
                 and local_tag(e) in ("laneSet", "childLaneSet")]
    for lane_set in lane_sets:
        scope = _lane_scope(lane_set)
        if scope is None:
            continue
        scope_nodes = {c.get("id"): local_tag(c) for c in scope
                       if isinstance(c.tag, str) and c.get("id")}
        owner_of = {}
        set_items = []
        for lane in lane_set.findall("bpmn:lane", NS):
            lane_id = lane.get("id", "?")
            reasons = []
            for ref in lane.findall("bpmn:flowNodeRef", NS):
                node = (ref.text or "").strip()
                tag = scope_nodes.get(node)
                if tag is None:
                    reasons.append(f"flowNodeRef '{node}' is not an element of "
                                   f"{local_tag(scope)} '{scope.get('id')}'")
                elif tag not in FLOW_NODE_TAGS:
                    reasons.append(f"flowNodeRef '{node}' is a {tag}, not a flow node")
                elif node in owner_of and owner_of[node] != lane_id:
                    reasons.append(f"flow node '{node}' is in two lanes "
                                   f"('{owner_of[node]}' and '{lane_id}')")
                else:
                    owner_of[node] = lane_id
            set_items.append({"id": lane_id, "line": lane.sourceline,
                              "scope": scope.get("id"), "reasons": reasons, "warning": None})
        if lane_set.getparent() is not None and local_tag(lane_set.getparent()) != "lane" and owner_of:
            outside = sorted(n for n, t in scope_nodes.items()
                             if t in FLOW_NODE_TAGS and n not in owner_of)
            if outside and set_items:
                set_items[0]["warning"] = (f"{len(outside)} flow node(s) of '{scope.get('id')}' "
                                           f"are in no lane: {', '.join(outside[:5])}"
                                           + (" ..." if len(outside) > 5 else ""))
        items.extend(set_items)
    return items


def check_l4(xml_doc, line_lookup):
    """L4: pools and messages. Only applies if the document describes a
    multi-participant collaboration. Every messageFlow must connect two
    DIFFERENT pools, and its endpoints must be allowed to send/receive
    messages (no gateways, no start event as source, no end event as target).
    Returns (ok, message, error_elements)."""
    collaboration = xml_doc.find("bpmn:collaboration", NS)
    lanes = _l4_lanes(xml_doc, line_lookup)
    if collaboration is None and not lanes:
        return None, "not applicable (no <collaboration> and no lanes)", []

    for lane in lanes:
        if lane["reasons"]:
            return False, f"lane '{lane['id']}': {lane['reasons'][0]}", [locate(lane["id"], line_lookup)]
    if collaboration is None:
        return True, "OK", []

    resolve_owner, node_tag = _l4_context(xml_doc, collaboration)

    for mf in collaboration.findall("bpmn:messageFlow", NS):
        mf_id = mf.get("id", "?")
        src = mf.get("sourceRef")
        tgt = mf.get("targetRef")
        if not src or not tgt:
            return False, f"messageFlow '{mf_id}' missing sourceRef/targetRef", [locate(mf_id, line_lookup)]

        owner_src = resolve_owner(src)
        owner_tgt = resolve_owner(tgt)
        if owner_src is None or owner_tgt is None:
            return False, f"messageFlow '{mf_id}' references a non-existent element (source='{src}', target='{tgt}')", [locate(mf_id, line_lookup), src, tgt]
        if owner_src == owner_tgt:
            return False, f"messageFlow '{mf_id}' connects two elements of the SAME pool ('{owner_src}') -> not allowed", [locate(mf_id, line_lookup), locate(src, line_lookup), locate(tgt, line_lookup)]
        endpoint = _l4_endpoint_problems(node_tag.get(src), node_tag.get(tgt))
        if endpoint:
            return False, f"messageFlow '{mf_id}': {endpoint[0]}", [locate(mf_id, line_lookup), locate(src, line_lookup), locate(tgt, line_lookup)]

    return True, "OK", []


def individual_schema_errors(xml_doc, errors, fallback):
    """Expose each schema diagnostic without changing validator verdicts."""
    records = []
    tree = xml_doc.getroottree() if xml_doc is not None else None
    for error in errors:
        path = error.path or ""
        namespaces = {**NS, **{k: v for k, v in (xml_doc.nsmap if xml_doc is not None else {}).items() if k}}
        try:
            nodes = tree.xpath(path, namespaces=namespaces) if tree is not None and path else []
        except etree.XPathError:
            nodes = []
        node = nodes[0] if nodes and isinstance(nodes[0], etree._Element) else None
        owner = node
        while owner is not None and not owner.get("id"):
            owner = owner.getparent()
        owner_id = owner.get("id") if owner is not None else None
        owner_path = tree.getpath(owner) if owner is not None else ""
        suffix = path[len(owner_path):] if owner_path and path.startswith(owner_path) else path
        records.append({"subject_key": (owner_id + suffix) if owner_id else (path or "document"),
                        "element_id": owner_id, "element_path": path,
                        "line": error.line, "column": error.column,
                        "code": error.type_name, "message": error.message})
    if not records:
        records.append({"subject_key": "document", "element_id": None, "element_path": "",
                        "code": "XML_INPUT", "message": fallback})
    return records


def validate_bpmn(xml_str: str, xsd: etree.XMLSchema) -> dict:
    """Runs L1, L2, L3, L4 INDEPENDENTLY (no short-circuit).
    Returns a full profile: the result of each level separately, plus an
    overall status. L2/L3/L4 are only marked 'N/A' if the XML is truly
    impossible to parse (technical constraint, not a design choice)."""
    profile = {
        "L1": {"result": None, "message": None, "error_elements": []},
        "L2": {"result": None, "message": None, "error_elements": []},
        "L3": {"result": None, "message": None, "error_elements": []},
        "L4": {"result": None, "message": None, "error_elements": []},
    }

    if not xml_str or not xml_str.strip():
        profile["L1"] = {"result": False, "message": "empty XML", "error_elements": [],
                         "diagnostics": individual_schema_errors(None, [], "empty XML")}
        profile["L2"] = {"result": None, "message": "N/A (empty XML)", "error_elements": []}
        profile["L3"] = {"result": None, "message": "N/A (empty XML)", "error_elements": []}
        profile["L4"] = {"result": None, "message": "N/A (empty XML)", "error_elements": []}
        return {"profile": profile, "overall_valid": False}

    ok1, msg1, xml_doc, err1 = check_l1(xml_str, xsd)
    profile["L1"] = {"result": ok1, "message": msg1, "error_elements": err1,
                     "diagnostics": individual_schema_errors(xml_doc, list(xsd.error_log) if xml_doc is not None else [], msg1) if not ok1 else []}

    if xml_doc is None:
        profile["L2"] = {"result": None, "message": "N/A (XML not parsable)", "error_elements": []}
        profile["L3"] = {"result": None, "message": "N/A (XML not parsable)", "error_elements": []}
        profile["L4"] = {"result": None, "message": "N/A (XML not parsable)", "error_elements": []}
        return {"profile": profile, "overall_valid": False}

    line_lookup = build_line_lookup(xml_doc)

    ok2, msg2, err2 = check_l2(xml_doc, line_lookup)
    profile["L2"] = {"result": ok2, "message": msg2, "error_elements": err2}

    ok3, msg3, err3 = check_l3(xml_doc, line_lookup)
    profile["L3"] = {"result": ok3, "message": msg3, "error_elements": err3}

    ok4, msg4, err4 = check_l4(xml_doc, line_lookup)
    profile["L4"] = {"result": ok4, "message": msg4, "error_elements": err4}

    applicable_results = [profile[level]["result"] for level in ("L1", "L2", "L3", "L4")
                           if profile[level]["result"] is not None]
    overall_valid = all(applicable_results)

    return {"profile": profile, "overall_valid": overall_valid}


# ═════════════════════════════════════════════════════════════════
# NEW: per-element overview builders (correct AND incorrect elements),
# one per level. These do NOT short-circuit -- every element gets a
# status, not just the first one that fails -- so the per-level output
# files can show a complete picture, not just the first problem found.
# ═════════════════════════════════════════════════════════════════

def overview_l1(xml_doc, l1_error_locations, line_lookup):
    """Attribute schema errors on ID-less children to their owning element."""
    if xml_doc is None:
        return []
    import re
    error_lines = set()
    for loc in l1_error_locations:
        match = re.search(r"line\s+(\d+)", str(loc))
        if match:
            error_lines.add(int(match.group(1)))

    affected = {}
    for error_line in error_lines:
        matches = [elem for elem in xml_doc.iter()
                   if isinstance(elem.tag, str) and elem.sourceline == error_line]
        if not matches:
            # Preserve an unattributed schema failure instead of marking all
            # identifiable elements correct. The document owns the fallback.
            affected.setdefault(xml_doc, []).append(error_line)
        for elem in matches:
            owner = elem
            while owner is not None and not owner.get("id"):
                owner = owner.getparent()
            if owner is None:
                owner = xml_doc
            affected.setdefault(owner, []).append(error_line)

    overview = []
    for elem in xml_doc.iter():
        if not isinstance(elem.tag, str):
            continue
        elem_id = elem.get("id")
        if not elem_id and elem not in affected:
            continue
        item = {"id": elem_id or "document", "tag": local_tag(elem),
                "line": elem.sourceline,
                "status": "incorrect" if elem in affected else "correct"}
        if elem in affected:
            item["schema_error_lines"] = sorted(set(affected[elem]))
        overview.append(item)
    return overview


def overview_l2(xml_doc, line_lookup):
    """Every gateway element (nested ones included), marked correct/incorrect
    against AUTHORIZED_GATEWAYS."""
    overview = []
    for child, tag in _all_gateways(xml_doc):
        reasons = [] if tag in AUTHORIZED_GATEWAYS else [f"unauthorized gateway type '{tag}'"]
        if tag == "eventBasedGateway":
            reasons += _event_gateway_problems(child)
        item = {"id": child.get("id", "?"), "tag": tag, "line": child.sourceline,
                "status": "incorrect" if reasons else "correct"}
        if reasons:
            item["reason"] = "; ".join(reasons)
        overview.append(item)
    return overview


def overview_l3(xml_doc, line_lookup):
    """Every flow node (sub-process bodies included), marked correct/incorrect
    with a reason, plus scope-level problems. Built from the SAME analysis as
    check_l3, so check_l3 passes if and only if nothing here is incorrect."""
    nodes_out, problems_out = _l3_analyze(xml_doc, line_lookup)
    overview = []
    for n in nodes_out:
        item = {
            "id": n["id"], "tag": n["tag"], "line": n["line"], "process": n["process"],
            "status": "incorrect" if n["reasons"] else "correct",
            "reason": "; ".join(n["reasons"]) if n["reasons"] else None,
        }
        if n.get("warning"):
            item["warning"] = n["warning"]
        overview.append(item)
    for p in problems_out:
        overview.append({
            "id": p["id"], "tag": p["tag"], "line": p["line"], "process": p["process"],
            "status": "incorrect", "reason": p["reason"],
        })
    return overview


def overview_l4(xml_doc, line_lookup):
    """Every messageFlow, marked correct/incorrect, evaluated fully (not
    stopping at the first bad one), with the same rules as check_l4."""
    overview = []
    for lane in _l4_lanes(xml_doc, line_lookup):
        item = {"id": lane["id"], "tag": "lane", "line": lane["line"], "process": lane["scope"],
                "status": "incorrect" if lane["reasons"] else "correct",
                "reason": "; ".join(lane["reasons"]) if lane["reasons"] else None}
        if lane["warning"]:
            item["warning"] = lane["warning"]
        overview.append(item)
    collaboration = xml_doc.find("bpmn:collaboration", NS)
    if collaboration is None:
        return overview

    resolve_owner, node_tag = _l4_context(xml_doc, collaboration)

    for mf in collaboration.findall("bpmn:messageFlow", NS):
        mf_id = mf.get("id", "?")
        src, tgt = mf.get("sourceRef"), mf.get("targetRef")
        owner_src = resolve_owner(src) if src else None
        owner_tgt = resolve_owner(tgt) if tgt else None

        reasons = []
        if not src or not tgt:
            reasons.append("missing sourceRef/targetRef")
        else:
            if owner_src is None:
                reasons.append(f"source '{src}' does not resolve to any pool")
            if owner_tgt is None:
                reasons.append(f"target '{tgt}' does not resolve to any pool")
            if owner_src is not None and owner_tgt is not None and owner_src == owner_tgt:
                reasons.append(f"source and target are in the SAME pool ('{owner_src}')")
            if owner_src is not None and owner_tgt is not None:
                reasons.extend(_l4_endpoint_problems(node_tag.get(src), node_tag.get(tgt)))

        status = "correct" if not reasons else "incorrect"
        overview.append({
            "id": mf_id, "line": mf.sourceline, "sourceRef": src, "targetRef": tgt,
            "source_pool": owner_src, "target_pool": owner_tgt,
            "status": status, "reason": "; ".join(reasons) if reasons else None,
        })

    return overview


def split_correct_incorrect(overview):
    correct = [e for e in overview if e["status"] == "correct"]
    incorrect = [e for e in overview if e["status"] == "incorrect"]
    return correct, incorrect


def extract_error_elements(raw_error_strings, incorrect_list):
    """error_elements should only be the SPECIFIC element(s) that caused the
    reported 'message' (the first problem the short-circuit check_lN found) --
    NOT the full incorrect_elements list. This filters incorrect_list down to
    just those, matched by id (when the id appears in the raw string) or,
    failing that, by line number (for L1, whose raw strings are just line
    numbers with no id at all). Returns structured dicts, same shape as
    incorrect_elements, not plain strings."""
    if not raw_error_strings:
        return []

    matched = []
    matched_ids = set()

    for raw in raw_error_strings:
        # try matching by id first (covers L2/L3/L4, whose raw strings embed the id)
        for entry in incorrect_list:
            entry_id = entry.get("id", "")
            if entry_id and entry_id in raw and entry_id not in matched_ids:
                matched.append(entry)
                matched_ids.add(entry_id)

        # fall back to line-number matching (covers L1, whose raw strings are
        # just "line N", with no id to match against at all)
        digits = "".join(ch for ch in raw if ch.isdigit())
        if digits:
            line_num = int(digits)
            for entry in incorrect_list:
                entry_id = entry.get("id", "")
                if entry.get("line") == line_num and entry_id not in matched_ids:
                    matched.append(entry)
                    matched_ids.add(entry_id)

    return matched


def _accuracy(correct_n, incorrect_n):
    applicable = correct_n + incorrect_n
    return round(correct_n / applicable, 4) if applicable else None


def append_history(example_dir: Path, entry_id, inner_iter: int,
                    profile: dict, overall_valid: bool):
    """Appends this attempt to the example's cumulative history file.

    Called once per example per inner-loop attempt. Reads whatever history
    already exists, adds the current attempt, rewrites the file.

    WHY the full profile is stored and not just a pass/fail flag: the Failure
    Classifier needs the level AND the message to assign T1-T4 and to give the
    Guideline Learner something specific enough to write a real rule from
    (e.g. "gateway with no branching/merging role -> ExclusiveGateway_1") rather
    than a vague "L3 failed".
    """
    history_path = example_dir / HISTORY_OUTPUT
    if history_path.exists():
        history = json.loads(history_path.read_text(encoding="utf-8"))
    else:
        history = {"id": entry_id, "attempts": []}

    # Re-running the same inner_iter (e.g. after a crash) should overwrite that
    # attempt, not silently duplicate it.
    history["attempts"] = [a for a in history["attempts"] if a.get("inner_iter") != inner_iter]
    history["attempts"].append({
        "inner_iter": inner_iter,
        "validation_profile": {
            lvl: {"result": profile[lvl]["result"], "message": profile[lvl]["message"]}
            for lvl in LEVELS
        },
        "failed_levels": [lvl for lvl in LEVELS if profile[lvl]["result"] is False],
        "overall_valid": overall_valid,
    })
    history["attempts"].sort(key=lambda a: a["inner_iter"])
    history["n_attempts"] = len(history["attempts"])
    history["final_valid"] = history["attempts"][-1]["overall_valid"]
    # Every distinct level that failed at ANY point, even if later fixed --
    # this is the part the Failure Classifier consumes.
    all_failed = []
    for a in history["attempts"]:
        for lvl in a["failed_levels"]:
            if lvl not in all_failed:
                all_failed.append(lvl)
    history["levels_failed_at_any_attempt"] = sorted(all_failed)

    history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    return history


def validate_dataset(data, xsd, out_dir: Path, inner_iter: int = 1,
                      generated_file_path: str = None, quiet: bool = False):
    """Validates a list of generated BPMN entries and writes all output files.

    This is the entry point the inner-loop orchestrator calls, once per attempt.

    Args:
        data: list of {id, description, generated_bpmn_xml} -- may be the FULL
              dataset (attempt 1) or only the still-failing subset (attempts 2+).
        inner_iter: which attempt this is; recorded in the history file.

    Returns a dict the orchestrator uses to decide whether to loop again:
        {
          "accuracy_l1_l4": float,        # overall accuracy across all 4 levels
          "fully_valid_ids": [...],
          "failed_ids": [...],
          "diagnostics": {id: "the message(s) explaining what failed"},
          "per_example": [...]
        }
    The "diagnostics" field is what gets injected back into the Generator's
    prompt so the retry is a correction, not a blind re-roll.
    """
    performance_path = out_dir / PERFORMANCE_OUTPUT
    xml_field_name = f"generated_bpmn_xml_{MODEL_USED}"
    source_file = generated_file_path or GENERATED_FILE

    aggregated = {lvl: {"correct_elements": [], "incorrect_elements": []} for lvl in LEVELS}
    stats = {lvl: {"correct": 0, "incorrect": 0, "not_applicable": 0} for lvl in LEVELS}
    stats["overall"] = {"fully_valid": 0, "not_fully_valid": 0}
    per_example_performance = []
    fully_valid_ids = []
    failed_ids = []
    diagnostics = {}

    for entry in data:
        entry_id = entry.get("id")
        xml_str = entry.get("generated_bpmn_xml")

        validation = validate_bpmn(xml_str, xsd)
        profile = validation["profile"]
        overall_valid = validation["overall_valid"]

        stats["overall"]["fully_valid" if overall_valid else "not_fully_valid"] += 1
        for lvl in LEVELS:
            r = profile[lvl]["result"]
            if r is None:
                stats[lvl]["not_applicable"] += 1
            elif r:
                stats[lvl]["correct"] += 1
            else:
                stats[lvl]["incorrect"] += 1

        # rebuild xml_doc + line_lookup once, reused for every overview below
        xml_doc = None
        line_lookup = {}
        try:
            xml_doc = reorder_children(etree.fromstring(xml_str.encode("utf-8"))) if xml_str and xml_str.strip() else None
            if xml_doc is not None:
                line_lookup = build_line_lookup(xml_doc)
        except etree.XMLSyntaxError:
            xml_doc = None

        ov1 = overview_l1(xml_doc, profile["L1"]["error_elements"], line_lookup)
        ov2 = overview_l2(xml_doc, line_lookup) if xml_doc is not None else []
        ov3 = overview_l3(xml_doc, line_lookup) if xml_doc is not None else []
        ov4 = overview_l4(xml_doc, line_lookup) if xml_doc is not None else []

        correct1, incorrect1 = split_correct_incorrect(ov1)
        correct2, incorrect2 = split_correct_incorrect(ov2)
        correct3, incorrect3 = split_correct_incorrect(ov3)
        correct4, incorrect4 = split_correct_incorrect(ov4)

        per_level_elements = {
            "L1": (correct1, incorrect1), "L2": (correct2, incorrect2),
            "L3": (correct3, incorrect3), "L4": (correct4, incorrect4),
        }

        for lvl, (correct_list, incorrect_list) in per_level_elements.items():
            for e in correct_list:
                aggregated[lvl]["correct_elements"].append({"example_id": entry_id, **e})
            for e in incorrect_list:
                aggregated[lvl]["incorrect_elements"].append({"example_id": entry_id, **e})

        # ---- one folder per example ----
        example_dir = out_dir / str(entry_id)
        example_dir.mkdir(parents=True, exist_ok=True)

        for lvl, (correct_list, incorrect_list) in per_level_elements.items():
            li_path = example_dir / f"{FILE_PREFIX}{lvl}.json"
            li_data = {
                "validation_level": lvl,
                "id": entry_id,
                "inner_iter": inner_iter,
                "description": entry.get("description"),
                "input_file_path": str(Path(source_file).resolve()),
                "output_file_path": str(li_path.resolve()),
                xml_field_name: xml_str,
                "checklist_reference": CHECKLIST_REFERENCE[lvl],
                "result": profile[lvl]["result"],
                "message": profile[lvl]["message"],
                "error_locations": profile[lvl]["error_elements"],
                "individual_errors": profile[lvl].get("diagnostics", []),
                "correct_elements": correct_list,
                "incorrect_elements": incorrect_list,
            }
            li_path.write_text(json.dumps(li_data, ensure_ascii=False, indent=2), encoding="utf-8")

        combined_path = example_dir / f"{FILE_PREFIX}combined.json"
        combined_data = {
            "id": entry_id,
            "inner_iter": inner_iter,
            "description": entry.get("description"),
            xml_field_name: xml_str,
            "validation_profile": {
                lvl: {
                    "accuracy": _accuracy(len(per_level_elements[lvl][0]), len(per_level_elements[lvl][1])),
                    "threshold": "",  # not yet decided -- placeholder, to be filled in later
                    "result": profile[lvl]["result"],
                    "message": profile[lvl]["message"],
                }
                for lvl in LEVELS
            },
            "overall_valid": overall_valid,
        }
        combined_path.write_text(json.dumps(combined_data, ensure_ascii=False, indent=2), encoding="utf-8")

        # ---- cumulative failure history (survives across inner-loop attempts) ----
        append_history(example_dir, entry_id, inner_iter, profile, overall_valid)

        # ---- collect what the orchestrator needs to drive the next attempt ----
        if overall_valid:
            fully_valid_ids.append(entry_id)
        else:
            failed_ids.append(entry_id)
            # The diagnosis fed back into the Generator's prompt. Only the levels
            # that actually failed, with their message -- this is what turns a
            # retry into a correction instead of a blind re-roll.
            diagnostics[entry_id] = "; ".join(
                f"{lvl}: {profile[lvl]['message']}"
                for lvl in LEVELS if profile[lvl]["result"] is False
            )

        # ---- per-example entry for the dataset-wide performance_summary.json ----
        per_example_entry = {"id": entry_id, "overall_valid": overall_valid}
        level_accuracies = []
        level_correct_counts = []
        for lvl in LEVELS:
            correct_list, incorrect_list = per_level_elements[lvl]
            correct_n, incorrect_n = len(correct_list), len(incorrect_list)
            acc = _accuracy(correct_n, incorrect_n)
            if acc is not None:
                level_accuracies.append(acc)
            level_correct_counts.append(correct_n)
            per_example_entry[lvl] = {
                "result": profile[lvl]["result"],
                "message": profile[lvl]["message"],
                "threshold": "",  # not yet decided -- placeholder
                "correct_elements_count": correct_n,
                "incorrect_elements_count": incorrect_n,
                "accuracy": acc,
            }
        # cross-level spread for this one example (how consistent it is across L1-L4)
        if level_accuracies:
            per_example_entry["accuracy_across_levels"] = {
                "mean": round(statistics.mean(level_accuracies), 4),
                "median": round(statistics.median(level_accuracies), 4),
                "min": round(min(level_accuracies), 4),
                "max": round(max(level_accuracies), 4),
                "std": round(statistics.pstdev(level_accuracies), 4) if len(level_accuracies) > 1 else 0.0,
            }
        else:
            per_example_entry["accuracy_across_levels"] = None
        per_example_entry["min_correct_elements"] = min(level_correct_counts) if level_correct_counts else None

        per_example_performance.append(per_example_entry)

        # write THIS example's own performance.json, right here in the loop --
        # contains only this one example's data, not the whole dataset
        performance_path_example = example_dir / f"{FILE_PREFIX}performance.json"
        performance_path_example.write_text(
            json.dumps(per_example_entry, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        failed_levels = [lvl for lvl in LEVELS if profile[lvl]["result"] is False]
        status_str = "valid" if overall_valid else f"invalid ({', '.join(failed_levels)})"
        if not quiet:
            print(f"id={entry_id}: {status_str}  -> {example_dir}")

    # ---- dataset-wide performance_summary.json ----
    total = len(data)
    performance = {
        "input_file": str(Path(source_file).resolve()),
        "output_file": str(performance_path.resolve()),
        "inner_iter": inner_iter,
        "related_files_path": {
            "note": f"each example's {FILE_PREFIX}L1.json / {FILE_PREFIX}L2.json / "
                    f"{FILE_PREFIX}L3.json / {FILE_PREFIX}L4.json / {FILE_PREFIX}combined.json / "
                    f"{HISTORY_OUTPUT} live in their own folder, named after the example's id",
            "example_folder_pattern": str((out_dir / "{example_id}").resolve()),
        },
        "total_examples": total,
        "per_example": per_example_performance,
    }
    for lvl in LEVELS:
        rate = _accuracy(stats[lvl]["correct"], stats[lvl]["incorrect"])
        performance[lvl] = {
            "nb_correct": stats[lvl]["correct"],
            "incorrect": stats[lvl]["incorrect"],
            "not_applicable": stats[lvl]["not_applicable"],
            "accuracy": rate,
            "threshold": "",  # not yet decided -- placeholder
            "correct_elements": aggregated[lvl]["correct_elements"],
            "incorrect_elements": aggregated[lvl]["incorrect_elements"],
        }
    # accuracy(L1-L4): pooled across all four levels, over applicable results only.
    # WHY pooled and not the mean of the four per-level accuracies: the levels have
    # very different element counts (L1 inspects every element, L4 often inspects
    # none), so averaging the four rates would let a level with 2 elements weigh as
    # much as one with 500. This is the number the inner loop's 0.85 stop condition
    # is compared against.
    total_correct = sum(stats[lvl]["correct"] for lvl in LEVELS)
    total_incorrect = sum(stats[lvl]["incorrect"] for lvl in LEVELS)
    accuracy_l1_l4 = _accuracy(total_correct, total_incorrect)

    performance["overall"] = {
        "fully_valid": stats["overall"]["fully_valid"],
        "not_fully_valid": stats["overall"]["not_fully_valid"],
        "fully_valid_rate": round(stats["overall"]["fully_valid"] / total, 4) if total else None,
        "accuracy_l1_l4": accuracy_l1_l4,
        "accuracy_l1_l4_note": ("pooled correct/(correct+incorrect) across all four levels, "
                                 "applicable results only; this is what the inner loop's 0.85 "
                                 "stop condition compares against"),
    }

    performance_path.write_text(json.dumps(performance, ensure_ascii=False, indent=2), encoding="utf-8")

    if not quiet:
        print(f"\n{'='*60}")
        print(f"Summary over {total} examples (inner_iter={inner_iter}):")
        for lvl in LEVELS:
            print(f"  {lvl}: correct={stats[lvl]['correct']}  incorrect={stats[lvl]['incorrect']}  "
                  f"not_applicable={stats[lvl]['not_applicable']}")
        print(f"  Overall fully valid: {stats['overall']['fully_valid']}/{total}")
        print(f"  accuracy(L1-L4) = {accuracy_l1_l4}")
        print(f"\n\u2705 {total} per-example folders written under {out_dir}")
        print(f"   each containing: {FILE_PREFIX}L1.json ... {FILE_PREFIX}L4.json, "
              f"{FILE_PREFIX}combined.json, {FILE_PREFIX}performance.json, {HISTORY_OUTPUT}")
        print(f"\u2705 Dataset-wide summary saved at {performance_path}")

    return {
        "inner_iter": inner_iter,
        "accuracy_l1_l4": accuracy_l1_l4,
        "total_examples": total,
        "fully_valid_ids": fully_valid_ids,
        "failed_ids": failed_ids,
        "diagnostics": diagnostics,
        "per_example": per_example_performance,
    }


def main():
    """Standalone entry point: validates GENERATED_FILE once (inner_iter=1).
    The inner loop uses validate_dataset() directly instead."""
    xsd_path = Path(XSD_DIR) / "BPMN20.xsd"
    if not xsd_path.exists():
        sys.exit(f"Error: {xsd_path} not found. Make sure BPMN20.xsd, Semantic.xsd, "
                  f"BPMNDI.xsd, DC.xsd, DI.xsd are all in the '{XSD_DIR}' folder.")

    xsd = load_xsd(xsd_path)
    data = json.loads(Path(GENERATED_FILE).read_text(encoding="utf-8"))

    out_dir = Path(OUTPUT_DIR)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        sys.exit(f"Could not create OUTPUT_DIR {out_dir}: {e}\n"
                  "Use an absolute path outside any OneDrive-synced folder.")

    validate_dataset(data, xsd, out_dir, inner_iter=1,
                     generated_file_path=GENERATED_FILE)


if __name__ == "__main__":
    main()
