"""Layered display geometry and obstacle-aware orthogonal connection routing.

Only BPMN-DI is created. Business XML is never inferred or rewritten.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from functools import lru_cache
import heapq
import math
import xml.etree.ElementTree as ET

import networkx as nx

MODEL = "http://www.omg.org/spec/BPMN/20100524/MODEL"
DI = "http://www.omg.org/spec/BPMN/20100524/DI"
DC = "http://www.omg.org/spec/DD/20100524/DC"
DD = "http://www.omg.org/spec/DD/20100524/DI"
SUBPROCESSES = {"subProcess", "transaction", "adHocSubProcess"}
ARTIFACTS = {"dataObjectReference", "dataStoreReference", "textAnnotation"}
NODES = {"task", "userTask", "manualTask", "serviceTask", "scriptTask", "sendTask", "receiveTask",
         "businessRuleTask", "callActivity", *SUBPROCESSES, "startEvent", "endEvent",
         "intermediateCatchEvent", "intermediateThrowEvent", "boundaryEvent", "exclusiveGateway",
         "parallelGateway", "inclusiveGateway", "eventBasedGateway", "complexGateway"}


def local(element):
    return element.tag.rsplit("}", 1)[-1]


def children(scope):
    return [e for e in scope if e.tag.startswith("{" + MODEL + "}") and local(e) in NODES | ARTIFACTS]


@dataclass
class Plan:
    width: float
    height: float
    boxes: dict = field(default_factory=dict)
    parents: dict = field(default_factory=dict)

    def add(self, other, x, y, parent=None):
        for key, (bx, by, width, height, tag) in other.boxes.items():
            self.boxes[key] = (bx + x, by + y, width, height, tag)
            self.parents[key] = other.parents.get(key) or parent


def rank_nodes(scope, nodes):
    """Remove DFS feedback edges for placement only; preserve every XML flow."""
    keys = [n.get("id") for n in nodes]
    graph = nx.DiGraph()
    graph.add_nodes_from(keys)
    for flow in scope.findall(f"{{{MODEL}}}sequenceFlow"):
        source, target = flow.get("sourceRef"), flow.get("targetRef")
        if source in graph and target in graph:
            graph.add_edge(source, target)
    for node in nodes:
        if local(node) == "boundaryEvent" and node.get("attachedToRef") in graph:
            graph.add_edge(node.get("attachedToRef"), node.get("id"))
    # Iterative traversal also handles deep linear processes without recursion.
    color, feedback = {}, []
    starts = [n.get("id") for n in nodes if local(n) == "startEvent"]
    for key in starts + keys:
        if color.get(key):
            continue
        color[key] = 1
        stack = [(key, iter(graph.successors(key)))]
        while stack:
            source, targets = stack[-1]
            target = next(targets, None)
            if target is None:
                color[source] = 2
                stack.pop()
            elif color.get(target) == 1:
                feedback.append((source, target))
            elif not color.get(target):
                color[target] = 1
                stack.append((target, iter(graph.successors(target))))
    graph.remove_edges_from(feedback)
    ranks = {key: 0 for key in keys}
    for key in nx.topological_sort(graph):
        ranks[key] = max((ranks[p] + 1 for p in graph.predecessors(key)), default=0)
    return graph, ranks


def scope_plan(scope):
    nodes = children(scope)
    if any(not n.get("id") for n in nodes):
        raise ValueError("A visible BPMN element has no ID")
    graph, ranks = rank_nodes(scope, nodes)
    sizes, nested = {}, {}
    for node in nodes:
        key, tag = node.get("id"), local(node)
        if tag in SUBPROCESSES and children(node):
            nested[key] = scope_plan(node)
            sizes[key] = (max(420, nested[key].width + 40), nested[key].height + 60)
        elif tag.endswith("Event"):
            sizes[key] = (40, 40)
        elif tag.endswith("Gateway"):
            sizes[key] = (54, 54)
        elif tag == "textAnnotation":
            sizes[key] = (220, 110)
        else:
            sizes[key] = (180, min(140, 84 + 14 * (len(node.get("name", "")) // 80)))
    for node in nodes:
        boundary_count = sum(local(other) == "boundaryEvent" and other.get("attachedToRef") == node.get("id")
                             for other in nodes)
        if boundary_count:
            width, height = sizes[node.get("id")]
            sizes[node.get("id")] = (max(width, 55 * boundary_count + 30), height)
    columns = {}
    for key, rank in ranks.items():
        columns[rank] = max(columns.get(rank, 0), sizes[key][0])
    offsets, cursor = {}, 80
    for rank in sorted(columns):
        offsets[rank] = cursor
        cursor += columns[rank] + 130
    plan = Plan(max(600, cursor + 10), 180)
    lane_set = scope.find(f"{{{MODEL}}}laneSet")

    def lane_groups(lane_set, ancestors=()):
        groups = []
        if lane_set is None:
            return groups
        for lane in lane_set.findall(f"{{{MODEL}}}lane"):
            chain = ancestors + (lane.get("id"),)
            nested_set = lane.find(f"{{{MODEL}}}childLaneSet")
            if nested_set is not None:
                groups.extend(lane_groups(nested_set, chain))
            else:
                refs = {(r.text or "").strip() for r in lane.findall(f"{{{MODEL}}}flowNodeRef")}
                groups.append((chain, [n for n in nodes if n.get("id") in refs]))
        return groups

    groups = lane_groups(lane_set)
    assigned = {n.get("id") for _, members in groups for n in members}
    remaining = [n for n in nodes if n.get("id") not in assigned]
    if remaining or not groups:
        groups.append(((), remaining))
    y, lane_bounds = 35, {}
    for chain, members in groups:
        # Boundary events are positioned on their host, not in independent slots.
        members = [n for n in members if local(n) != "boundaryEvent"]
        bands = {}
        for node in members:
            bands.setdefault(ranks[node.get("id")], []).append(node)
        height = max([sum(sizes[n.get("id")][1] + 75 for n in col) + 70 for col in bands.values()] + [180])
        for rank in sorted(bands):
            col = bands[rank]
            # A stable barycenter ordering reduces branch crossings.
            col.sort(key=lambda n: sum(plan.boxes[p][1] for p in graph.predecessors(n.get("id"))
                        if p in plan.boxes) / max(1, sum(p in plan.boxes for p in graph.predecessors(n.get("id")))))
            total = sum(sizes[n.get("id")][1] + 75 for n in col) - 75
            cy = y + (height - total) / 2
            for node in col:
                key, tag = node.get("id"), local(node)
                width, node_height = sizes[key]
                x = offsets[rank] + (columns[rank] - width) / 2
                plan.boxes[key] = (x, cy, width, node_height, tag)
                plan.parents[key] = chain[-1] if chain else None
                if key in nested:
                    plan.add(nested[key], x + 20, cy + 45, key)
                cy += node_height + 75
        for depth, lane in enumerate(chain):
            if lane in lane_bounds:
                top, _ = lane_bounds[lane][1:3]
            else:
                top = y
            lane_bounds[lane] = (35 + depth * 30, top, y + height)
        y += height
    for lane, (x, top, bottom) in lane_bounds.items():
        plan.boxes[lane] = (x, top, plan.width - x, bottom - top, "lane")
    for chain, _ in groups:
        for index, lane in enumerate(chain):
            plan.parents[lane] = chain[index - 1] if index else None
    for node in nodes:
        if local(node) == "boundaryEvent":
            host = plan.boxes.get(node.get("attachedToRef"))
            if host:
                x, by, width, height, _ = host
                siblings = [n for n in nodes if local(n) == "boundaryEvent" and n.get("attachedToRef") == node.get("attachedToRef")]
                index = siblings.index(node)
                plan.boxes[node.get("id")] = (x + 15 + index * 55, by + height - 20, 40, 40, "boundaryEvent")
                plan.parents[node.get("id")] = plan.parents.get(node.get("attachedToRef"))
    plan.height = max(180, y + 45)
    return plan


def ancestors(plan, key):
    result = set()
    while key and key not in result:
        result.add(key)
        key = plan.parents.get(key)
    return result


def crosses(a, b, box, padding=8):
    x, y, width, height = box[:4]
    left, right, top, bottom = x-padding, x+width+padding, y-padding, y+height+padding
    if a[0] == b[0]:
        return left < a[0] < right and max(a[1], b[1]) > top and min(a[1], b[1]) < bottom
    return top < a[1] < bottom and max(a[0], b[0]) > left and min(a[0], b[0]) < right


def simplify(points):
    result = []
    for point in points:
        if result and point == result[-1]:
            continue
        if len(result) >= 2 and ((result[-2][0] == result[-1][0] == point[0]) or
                                 (result[-2][1] == result[-1][1] == point[1])):
            result.pop()
        result.append(point)
    return result


def route(plan, source, target, message=False, occupied=()):
    """Route around expanded node rectangles with a bounded A* search."""
    sx, sy, sw, sh, source_tag = plan.boxes[source]
    tx, ty, tw, th, target_tag = plan.boxes[target]
    if message:
        down = ty + th/2 >= sy + sh/2
        start = (sx+sw/2, sy+sh if down else sy)
        end = (tx+tw/2, ty if down else ty+th)
        a = (start[0], start[1] + (24 if down else -24))
        b = (end[0], end[1] + (-24 if down else 24))
        if source_tag.endswith("Event") or source_tag.endswith("Gateway"):
            start, a = (sx+sw, sy+sh/2), (sx+sw+24, sy+sh/2)
        if target_tag.endswith("Event") or target_tag.endswith("Gateway"):
            end, b = (tx, ty+th/2), (tx-24, ty+th/2)
    elif source == target or tx <= sx:
        start, end = (sx+sw, sy+sh/2), (tx+tw/2, ty)
        a, b = (start[0]+24, start[1]), (end[0], end[1]-24)
    else:
        start, end = (sx+sw, sy+sh/2), (tx, ty+th/2)
        a, b = (start[0]+24, start[1]), (end[0]-24, end[1])
    # Container boundaries are passable for messages and internal connections.
    excluded = (ancestors(plan, source) | ancestors(plan, target)) - {source, target}
    obstacles = [v for k, v in plan.boxes.items() if k not in excluded
                 and v[4] not in {"participant", "lane"}]
    # Reserve space for the external labels rendered by bpmn.io.
    obstacles += [(x+width/2-70, y+height+5, 140, 48, "label")
                  for key, (x, y, width, height, tag) in plan.boxes.items()
                  if tag.endswith("Event") or tag.endswith("Gateway")]
    # Boundary stubs can be adjacent to their attached host.
    obstacles = [v for v in obstacles if not any(v[0]-8 < p[0] < v[0]+v[2]+8 and
                  v[1]-8 < p[1] < v[1]+v[3]+8 for p in (a, b))]
    xs = sorted({a[0], b[0], 10, plan.width+40, *[p for v in obstacles for p in (v[0]-18, v[0]+v[2]+18)]})
    ys = sorted({a[1], b[1], 10, plan.height+40, *[p for v in obstacles for p in (v[1]-35, v[1]+v[3]+35)]})
    if message:
        xs = sorted(set(xs) | {p[0] + delta for segment in occupied for p in segment for delta in (-14, 14)})
    origin, goal = (xs.index(a[0]), ys.index(a[1])), (xs.index(b[0]), ys.index(b[1]))

    @lru_cache(maxsize=20000)
    def clear(first, second):
        return not any(crosses(first, second, rect) for rect in obstacles)

    initial = (*origin, 0)
    best, previous = {initial: 0}, {}
    queue = [(0, initial)]
    found = None
    for _ in range(12000):
        if not queue:
            break
        _, current = heapq.heappop(queue)
        ix, iy, direction = current
        if (ix, iy) == goal:
            found = current
            break
        for dx, dy, axis in ((1, 0, 1), (-1, 0, 1), (0, 1, 2), (0, -1, 2)):
            jx, jy = ix+dx, iy+dy
            if not (0 <= jx < len(xs) and 0 <= jy < len(ys)):
                continue
            first, second = (xs[ix], ys[iy]), (xs[jx], ys[jy])
            if not clear(first, second):
                continue
            cost = best[current] + abs(first[0]-second[0])+abs(first[1]-second[1]) + (30 if direction and axis != direction else 0)
            if message:
                for c, d in occupied:
                    if first[0] == second[0] == c[0] == d[0]:
                        overlap = min(max(first[1], second[1]), max(c[1], d[1])) - max(min(first[1], second[1]), min(c[1], d[1]))
                    elif first[1] == second[1] == c[1] == d[1]:
                        overlap = min(max(first[0], second[0]), max(c[0], d[0])) - max(min(first[0], second[0]), min(c[0], d[0]))
                    else:
                        overlap = 0
                    cost += max(0, overlap) * 4
            successor = (jx, jy, axis)
            if cost < best.get(successor, math.inf):
                best[successor] = cost
                previous[successor] = current
                heuristic = abs(xs[jx]-b[0])+abs(ys[jy]-b[1])
                heapq.heappush(queue, (cost+heuristic, successor))
    if found is None:
        return [], "Routing budget exhausted; no potentially misleading straight connection was drawn."
    path = []
    while found is not None:
        path.append((xs[found[0]], ys[found[1]]))
        found = previous.get(found)
    return simplify([start, *reversed(path), end]), None


def add_flow_diagrams(root, fresh):
    """Create one plane per collaboration or unrepresented process."""
    warnings = []
    processes = {e.get("id"): e for e in root.findall(f"{{{MODEL}}}process")}
    collaborations = root.findall(f"{{{MODEL}}}collaboration")
    represented = {p.get("processRef") for c in collaborations for p in c.findall(f"{{{MODEL}}}participant")}
    targets = collaborations + [p for key, p in processes.items() if key not in represented]
    if not targets:
        raise ValueError("The XML contains no process or collaboration to display")
    for target in targets:
        if not target.get("id"):
            raise ValueError("The diagram root has no ID")
        if local(target) == "collaboration":
            plans = []
            for participant in target.findall(f"{{{MODEL}}}participant"):
                process = processes.get(participant.get("processRef"))
                plans.append((participant, scope_plan(process) if process is not None else Plan(600, 180)))
            width = max([p.width for _, p in plans] + [600]) + 80
            plan, cursor = Plan(width, 0), 50
            for participant, inner in plans:
                key = participant.get("id")
                plan.boxes[key] = (40, cursor, width-80, inner.height, "participant")
                plan.add(inner, 40, cursor, key)
                cursor += inner.height + 140
            plan.height = cursor
        else:
            inner = scope_plan(target)
            plan = Plan(inner.width + 80, inner.height + 80)
            plan.add(inner, 40, 40)
        diagram = ET.SubElement(root, f"{{{DI}}}BPMNDiagram", {"id": fresh("FlowDiagram")})
        plane = ET.SubElement(diagram, f"{{{DI}}}BPMNPlane", {"id": fresh("FlowPlane"), "bpmnElement": target.get("id")})
        # Containers precede their descendants in the diagram.
        for key in sorted(plan.boxes, key=lambda k: len(ancestors(plan, k))):
            if not key:
                raise ValueError("A visible BPMN element has no ID")
            x, y, width, height, tag = plan.boxes[key]
            attrs = {"id": fresh("FlowShape"), "bpmnElement": key}
            if tag in {"participant", "lane"}:
                attrs["isHorizontal"] = "true"
            if tag in SUBPROCESSES:
                attrs["isExpanded"] = "true"
            shape = ET.SubElement(plane, f"{{{DI}}}BPMNShape", attrs)
            ET.SubElement(shape, f"{{{DC}}}Bounds", {k: str(v) for k, v in zip(("x", "y", "width", "height"), (x, y, width, height))})
        flows = [e for e in root.iter() if local(e) in {"sequenceFlow", "messageFlow", "association"}]
        occupied = []
        for flow in flows:
            source, target_id = flow.get("sourceRef"), flow.get("targetRef")
            if source not in plan.boxes or target_id not in plan.boxes:
                if source in plan.boxes or target_id in plan.boxes:
                    warnings.append(f"Cannot draw {flow.get('id')}: an endpoint is absent from this plane.")
                continue
            if not flow.get("id"):
                raise ValueError("A connection has no ID")
            points, warning = route(plan, source, target_id, local(flow) == "messageFlow", occupied)
            if warning:
                warnings.append(f"{flow.get('id')}: {warning}")
                continue
            occupied.extend(zip(points, points[1:]))
            edge = ET.SubElement(plane, f"{{{DI}}}BPMNEdge", {"id": fresh("FlowEdge"), "bpmnElement": flow.get("id")})
            for x, y in points:
                ET.SubElement(edge, f"{{{DD}}}waypoint", {"x": str(x), "y": str(y)})
    return warnings
