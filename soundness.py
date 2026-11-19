"""Behavioural soundness of one BPMN flow scope (L3, condition C8).

The validator's structural rules (C1-C7) can all hold while the process still gets
stuck: an exclusive split joined by a parallel gateway waits forever for a token that
never comes (a deadlock). This module plays the BPMN token game on one scope (a
process or an expanded sub-process) and explores every reachable state:

  * deadlock: a reachable state with tokens left in which no element can fire;
  * no completion: a reachable state from which no final state can be reached
    (e.g. a parallel join waiting for a branch that loops forever);
  * lack of synchronisation: a sequence flow holds two tokens at the same time,
    i.e. the following elements run twice (e.g. a parallel split merged by an
    exclusive gateway). Reported separately; the validator treats it as a warning.

Token semantics (BPMN 2.0.2, chapter 13), restricted to what the scope contains:
  * start event: the analysis is run once per start event (each start event
    begins its own instance);
  * activities and intermediate events: fire with one token on any incoming flow
    (implicit exclusive merge); produce a token on every unconditional outgoing
    flow, and on any non-empty subset of conditional ones (or the default flow);
  * interrupting boundary events replace the normal completion of their host;
    non-interrupting ones may add their path to it;
  * exclusive and event-based gateways: one incoming token, one outgoing flow;
  * parallel gateways: one token on every incoming flow, one on every outgoing;
  * inclusive (and complex) gateways: fire when no further token can still reach
    one of their empty incoming flows; produce on any non-empty subset of outgoing;
  * end events consume a token; a terminate end event ends the whole instance;
  * a throwing link event continues at the catching link with the same name;
  * sub-processes are single activities here (their bodies are separate scopes);
    event sub-processes and ad-hoc sub-processes are not part of the token flow.

The exploration is bounded (max_states); a scope that exceeds it is reported as
"not analysed" and never fails.
"""
from __future__ import annotations

from itertools import combinations

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
NS = {"bpmn": BPMN_NS}
MAX_STATES = 20000
TOKEN_CAP = 2          # counts are capped at 2: two tokens on one flow already shows the problem
MAX_SUBSET_BRANCHES = 6


def _tag(elem) -> str:
    t = elem.tag
    return t.split("}", 1)[1] if isinstance(t, str) and "}" in t else (t if isinstance(t, str) else "")


def _has(elem, name: str) -> bool:
    return elem.find(f"bpmn:{name}", NS) is not None


def _subsets(items):
    items = list(items)
    if len(items) > MAX_SUBSET_BRANCHES:          # keep the analysis bounded: all, or each alone
        return [tuple(items)] + [(i,) for i in items]
    out = []
    for k in range(1, len(items) + 1):
        out.extend(combinations(items, k))
    return out


GATEWAY_XOR = {"exclusiveGateway", "eventBasedGateway"}
GATEWAY_OR = {"inclusiveGateway", "complexGateway"}


def analyze_scope(container, flow_node_tags, subprocess_tags, max_states: int = MAX_STATES) -> dict:
    """Return {"status": "sound"|"unsound"|"not_analysed"|"skipped",
               "deadlocks": [...], "no_completion": [...], "unsynchronised": [...], "states": n}.
    Each finding is a dict {"element": id, "reason": text}."""
    nodes, flows = {}, []
    for child in container:
        tag = _tag(child)
        if tag == "sequenceFlow":
            flows.append(child)
        elif tag in flow_node_tags and child.get("id"):
            nodes[child.get("id")] = child
    result = {"status": "sound", "deadlocks": [], "no_completion": [], "unsynchronised": [], "states": 0}
    if _tag(container) == "adHocSubProcess":
        result["status"] = "skipped"
        return result

    def is_event_sub(e):
        return _tag(e) in subprocess_tags and str(e.get("triggeredByEvent", "false")).lower() == "true"

    flow_ids, flow_src, flow_tgt, flow_cond = [], {}, {}, {}
    for f in flows:
        fid, s, t = f.get("id"), f.get("sourceRef"), f.get("targetRef")
        if not fid or s not in nodes or t not in nodes:
            result["status"] = "skipped"          # structural problems are reported by C2
            return result
        flow_ids.append(fid)
        flow_src[fid], flow_tgt[fid] = s, t
        flow_cond[fid] = f.find("bpmn:conditionExpression", NS) is not None
    index = {f: i for i, f in enumerate(flow_ids)}
    incoming = {n: [] for n in nodes}
    outgoing = {n: [] for n in nodes}
    for f in flow_ids:
        outgoing[flow_src[f]].append(f)
        incoming[flow_tgt[f]].append(f)
    defaults = {n: e.get("default") for n, e in nodes.items() if e.get("default")}

    boundaries = {}                                # host id -> [(boundary id, interrupting)]
    for n, e in nodes.items():
        if _tag(e) == "boundaryEvent" and e.get("attachedToRef") in nodes:
            interrupting = str(e.get("cancelActivity", "true")).lower() != "false"
            boundaries.setdefault(e.get("attachedToRef"), []).append((n, interrupting))

    link_catch_by_name = {}
    for n, e in nodes.items():
        if _tag(e) == "intermediateCatchEvent" and _has(e, "linkEventDefinition"):
            link_catch_by_name.setdefault(e.get("name") or "", []).append(n)

    starts = [n for n, e in nodes.items() if _tag(e) == "startEvent"]
    if not starts or not flow_ids:
        result["status"] = "skipped"
        return result

    # Structural reachability between flows, used by inclusive joins: can a token on
    # flow a still reach flow b without passing through the join itself?
    flow_succ = {f: set() for f in flow_ids}
    for f in flow_ids:
        tgt = flow_tgt[f]
        nxt = list(outgoing[tgt])
        for b, _ in boundaries.get(tgt, []):
            nxt.extend(outgoing[b])
        te = nodes[tgt]
        if _tag(te) == "intermediateThrowEvent" and _has(te, "linkEventDefinition"):
            for c in link_catch_by_name.get(te.get("name") or "", []):
                nxt.extend(outgoing[c])
        flow_succ[f].update(nxt)

    def can_reach(src_flow, dst_flow, blocked_node):
        seen, stack = set(), [src_flow]
        while stack:
            f = stack.pop()
            if f == dst_flow:
                return True
            if f in seen:
                continue
            seen.add(f)
            if flow_tgt[f] == blocked_node:
                continue
            stack.extend(flow_succ[f] - seen)
        return False

    def produce(state, flows_out, unsync):
        s = list(state)
        for f in flows_out:
            i = index[f]
            if s[i] >= 1:
                unsync.add(f)
            s[i] = min(TOKEN_CAP, s[i] + 1)
        return s

    def completion_options(n):
        """Sets of outgoing flows produced when activity/event n completes."""
        outs = outgoing[n]
        plain = [f for f in outs if not flow_cond[f] and f != defaults.get(n)]
        cond = [f for f in outs if flow_cond[f]]
        options = []
        if cond:
            for sub in _subsets(cond):
                options.append(tuple(plain) + sub)
            if defaults.get(n) in outs:
                options.append(tuple(plain) + (defaults[n],))
        else:
            base = tuple(plain) + ((defaults[n],) if defaults.get(n) in outs and not plain else ())
            options.append(base)
        e = nodes[n]
        if _tag(e) == "intermediateThrowEvent" and _has(e, "linkEventDefinition"):
            targets = []
            for c in link_catch_by_name.get(e.get("name") or "", []):
                targets.extend(outgoing[c])
            options = [tuple(o) + tuple(targets) for o in options]
        result_opts = list(options)
        for b, interrupting in boundaries.get(n, []):
            if interrupting:
                result_opts.append(tuple(outgoing[b]))
            else:
                result_opts.extend(tuple(o) + tuple(outgoing[b]) for o in options)
        return result_opts

    def successors(state, unsync):
        """Yield (next_state, terminated) for every element that can fire."""
        marked = [f for f in flow_ids if state[index[f]]]
        fired_nodes = set(flow_tgt[f] for f in marked)
        for n in fired_nodes:
            e = nodes[n]
            tag = _tag(e)
            ins = [f for f in incoming[n] if state[index[f]]]
            if tag == "endEvent":
                for f in ins:
                    s = list(state)
                    s[index[f]] -= 1
                    if _has(e, "terminateEventDefinition"):
                        yield [0] * len(state), True
                    else:
                        yield s, False
            elif tag == "parallelGateway":
                if all(state[index[f]] for f in incoming[n]):
                    s = list(state)
                    for f in incoming[n]:
                        s[index[f]] -= 1
                    yield produce(s, outgoing[n], unsync), False
            elif tag in GATEWAY_OR:
                empty = [f for f in incoming[n] if not state[index[f]]]
                waiting = any(can_reach(m, f, n) for f in empty for m in marked if flow_tgt[m] != n)
                if waiting:
                    continue
                s = list(state)
                for f in ins:
                    s[index[f]] -= 1
                outs = outgoing[n]
                if not outs:
                    yield s, False
                for sub in _subsets(outs):
                    yield produce(s, sub, unsync), False
            elif tag in GATEWAY_XOR:
                for f in ins:
                    s = list(state)
                    s[index[f]] -= 1
                    if not outgoing[n]:
                        yield s, False
                    for o in outgoing[n]:
                        yield produce(s, [o], unsync), False
            elif tag == "boundaryEvent" or is_event_sub(e):
                continue                      # reached only through their host / trigger
            else:                             # activities and intermediate events
                for f in ins:
                    s = list(state)
                    s[index[f]] -= 1
                    for opt in completion_options(n) or [()]:
                        yield produce(s, opt, unsync), False

    for start in starts:
        unsync = set()
        init = produce([0] * len(flow_ids), completion_options(start)[0] if outgoing[start] else [], unsync)
        init_t = tuple(init)
        seen = {init_t}
        edges = {}
        frontier = [init_t]
        finals = set()
        overflow = False
        while frontier:
            st = frontier.pop()
            nxt_list = []
            if not any(st):
                finals.add(st)
                edges[st] = nxt_list
                continue
            for nxt, terminated in successors(st, unsync):
                t = tuple(nxt)
                nxt_list.append(t)
                if t not in seen:
                    if len(seen) >= max_states:
                        overflow = True
                        break
                    seen.add(t)
                    frontier.append(t)
            edges[st] = nxt_list
            if overflow:
                break
        result["states"] += len(seen)
        if overflow:
            result["status"] = "not_analysed"
            continue
        # deadlocks: tokens left, nothing can fire
        for st, nxt in edges.items():
            if any(st) and not nxt:
                stuck = sorted({flow_tgt[f] for f in flow_ids if st[index[f]]})
                for n in stuck:
                    waits = [f for f in incoming[n] if not st[index[f]]]
                    reason = (f"deadlock: {_tag(nodes[n])} '{n}' waits for flow(s) "
                              f"{', '.join(waits)} that can no longer receive a token"
                              if waits else f"deadlock: '{n}' can never fire")
                    if not any(d["element"] == n for d in result["deadlocks"]):
                        result["deadlocks"].append({"element": n, "reason": reason, "start": start})
        # no completion: states from which no final state is reachable
        reverse = {}
        for st, nxt in edges.items():
            for t in nxt:
                reverse.setdefault(t, set()).add(st)
        can_finish, stack = set(), list(finals)
        while stack:
            st = stack.pop()
            if st in can_finish:
                continue
            can_finish.add(st)
            stack.extend(reverse.get(st, ()))
        if not result["deadlocks"]:
            for st in edges:
                if st not in can_finish and edges[st]:
                    holders = sorted({flow_tgt[f] for f in flow_ids if st[index[f]]})
                    result["no_completion"].append({
                        "element": holders[0] if holders else start,
                        "reason": "the process can reach a state from which it can never complete "
                                  f"(tokens before: {', '.join(holders)}; e.g. an activity with several "
                                  f"unconditional outgoing flows starts parallel paths and one of them "
                                  f"loops forever)", "start": start})
                    break
        for f in sorted(unsync):
            if not any(u["element"] == flow_tgt[f] for u in result["unsynchronised"]):
                result["unsynchronised"].append({
                    "element": flow_tgt[f],
                    "reason": f"lack of synchronisation: flow '{f}' can carry two tokens, so "
                              f"'{flow_tgt[f]}' may run twice (a parallel split is merged without "
                              f"a parallel join)", "start": start})
    if result["deadlocks"] or result["no_completion"]:
        result["status"] = "unsound"
    return result
