"""GuideBPMN orchestrator agent (LLM + LangGraph).

A `decide` node where the agent chooses ONE action among the currently allowed
ones, then a tool node that runs it and returns to `decide`, until a stop
action ends the graph.

    START -> decide -> {generate | validate | evaluate |
                        detect_failures | learn | revise} -> decide -> ... -> stop_* -> END

`allowed_actions(state)` only holds the guardrails: data dependencies (a draft
must be validated before it is measured), budgets and the no-leak rule.
Wherever a real choice exists, the agent decides and gives its reason:
  * after failure detection: learn from the failures, or stop;
  * after learning, when a documentation rule was not applied: send it back
    to the generator for a second iteration, or stop;
The agent cannot break the rules:
  * the gold diagram never guides generation: each validated draft goes to the
    similarity evaluation, valid or not (the validator's errors are learned from);
  * once evaluated, the example moves to failure detection and learning;
  * second iteration (`revise`), at most once per example: the documentation
    rules the generator did not apply and the guidelines just learned from this
    example are sent back to the generator, and the new draft is validated and
    measured again. This iteration is informed by the comparison
    with the reference, so its metrics are stored and reported separately from
    the first pass (`first_pass`);
  * safety limits (decisions, tool calls) force a stop.
"""
from __future__ import annotations

import json
from enum import Enum
from typing import Callable, Optional, TypedDict

from pydantic import BaseModel, ConfigDict, Field


class OrchestratorAction(str, Enum):
    GENERATE = "generate"
    VALIDATE = "validate"
    EVALUATE = "evaluate"
    DETECT_FAILURES = "detect_failures"
    LEARN = "learn"
    REVISE = "revise"
    STOP_SUCCESS = "stop_success"
    STOP_FAILURE = "stop_failure"


TOOL_ACTIONS = [OrchestratorAction.GENERATE, OrchestratorAction.VALIDATE,
                OrchestratorAction.EVALUATE, OrchestratorAction.DETECT_FAILURES, OrchestratorAction.LEARN,
                OrchestratorAction.REVISE]
TERMINAL_ACTIONS = [OrchestratorAction.STOP_SUCCESS, OrchestratorAction.STOP_FAILURE]

# Budgets of one example. These are the defaults; a run may choose its own
# values (launcher of the site, or the command line) and saves them in models.json.
SAFETY_LIMITS = {"max_agent_decisions": 48, "max_tool_calls": 40, "next_iterations": 3}
# lowest and highest value accepted for each budget
LIMIT_BOUNDS = {"max_agent_decisions": (10, 400), "max_tool_calls": (10, 400),
                "next_iterations": (0, 10)}


def resolve_limits(chosen: Optional[dict] = None) -> dict:
    """The budgets of a run: the defaults, replaced by the chosen values that
    are given, each kept inside its bounds."""
    out = dict(SAFETY_LIMITS)
    for name, value in (chosen or {}).items():
        if name in out and value is not None:
            low, high = LIMIT_BOUNDS[name]
            out[name] = max(low, min(high, int(value)))
    return out


class OrchestratorState(BaseModel):
    """Everything the run knows about one example."""
    model_config = ConfigDict(extra="forbid")

    example_id: str
    provider: str = "gpt"
    arm: str = "documentation"
    model_name: Optional[str] = None
    run_dir: str
    learn_enabled: bool = True
    rule_feedback_enabled: bool = True
    dry_run: bool = False

    # {round, xml, valid, failed_levels, validated}
    rounds: list[dict] = Field(default_factory=list)
    kept_round: Optional[int] = None
    evaluated: bool = False
    metrics: dict = Field(default_factory=dict)
    failures: Optional[list] = None
    detected: list[str] = Field(default_factory=list)
    learned: bool = False
    guideline_outcomes: list[dict] = Field(default_factory=list)

    # second iteration: documentation rules found not applied, sent back once
    # {rule_id, instruction, situation, source, failure_type}: documentation rules
    # not applied and guidelines just learned from this example
    rules_to_reapply: list[dict] = Field(default_factory=list)
    revised: bool = False
    revision_round: Optional[int] = None         # first draft of the latest next iteration
    first_revision_round: Optional[int] = None
    revisions: int = 0                           # next iterations run so far
    max_revisions: int = SAFETY_LIMITS["next_iterations"]   # chosen for the run (0 = none)
    limits: dict = Field(default_factory=lambda: dict(SAFETY_LIMITS))   # budgets of the run
    failure_rule: str = "any_difference"         # how T5-T7 are detected (diagnosis.FAILURE_RULES)
    error_counts: dict = Field(default_factory=dict)   # individual errors per detected type T5-T7
    promote_confirmed: bool = False              # confirmed example-specific -> general guideline
    # every description goes through all the next iterations (max_revisions): an
    # iteration with nothing new resends all the guidelines of the description
    force_iterations: bool = False
    rules_sent: list[str] = Field(default_factory=list)     # guideline ids already sent back
    previous_kept: Optional[int] = None          # draft kept before the latest next iteration
    # one record per next iteration: what was sent, the scores before and after
    iteration_effects: list[dict] = Field(default_factory=list)
    first_pass: dict = Field(default_factory=dict)   # result before the second iteration

    decisions: list[dict] = Field(default_factory=list)
    tool_calls: int = 0
    selected_action: Optional[str] = None
    stopped: Optional[str] = None
    stop_reason: Optional[str] = None
    error: Optional[str] = None

    # ---- what the deciding agent may see (no gold-derived numbers before stop)
    def observation(self) -> dict:
        last = self.rounds[-1] if self.rounds else None
        seen = {
            "example_id": self.example_id,
            "drafts_so_far": len(self.rounds),
            "latest_draft": None if not last else {
                "round": last["round"], "validated": last["validated"],
                "valid_L1_L4": last.get("valid"),
                "failed_levels": last.get("failed_levels", []),
            },
            "similarity_measured": self.evaluated,
            "detected_failure_types": self.detected if self.failures is not None else None,
            "detected_failures_meaning": ({t: FAILURE_MEANING.get(t, "") for t in self.detected}
                                          if self.failures is not None else None),
            "learning_done": self.learned,
            "guideline_agents_outcomes": [
                {"failure_type": o.get("failure_type"), "outcome": o.get("status"),
                 "rule": o.get("ref") or o.get("guideline_id")}
                for o in self.guideline_outcomes],
            "guidelines_to_send_back": [{"id": r["rule_id"], "source": r.get("source")}
                                        for r in self.rules_to_reapply
                                        if r["rule_id"] not in self.rules_sent],
            "second_iteration_done": self.revised,
            "next_iterations_done": self.revisions,
            "next_iterations_allowed": self.max_revisions,
            "tool_calls": self.tool_calls,
            "tool_call_budget": self.limits["max_tool_calls"],
        }
        # the agent's own record: every single error still open on the current
        # model, per type, and how the count changed from one iteration to the next
        marks = (last or {}).get("validator_levels") or {}
        errors = {f"T{level[1]}": max(1, int((marks.get(level) or {}).get("incorrect") or 0))
                  for level in ((last or {}).get("failed_levels") or [])}
        if self.failures is not None:
            errors.update(self.error_counts)
            seen["open_errors"] = errors
            seen["open_errors_total"] = sum(errors.values())
        elif errors:
            seen["open_validator_errors"] = errors
        history = []
        if self.first_pass.get("error_counts") is not None:
            history.append({"after": "first pass", "errors": self.first_pass["error_counts"],
                            "total": sum(self.first_pass["error_counts"].values())})
        for effect in self.iteration_effects:
            if effect.get("errors_after") is not None:
                history.append({"after": f"next iteration {effect['iteration']}",
                                "errors": effect["errors_after"],
                                "total": sum(effect["errors_after"].values())})
        if history:
            seen["open_errors_history"] = history
        return seen


FAILURE_MEANING = {
    "T1": "invalid or unparseable XML (validator L1)",
    "T2": "incorrect gateway use (validator L2)",
    "T3": "incorrect control flow (validator L3)",
    "T4": "malformed pools, lanes or message flows (validator L4)",
    "T5": "structure differs from the reference (elements, flows, order)",
    "T6": "labels differ in meaning from the reference",
    "T7": "pools, lanes or messages differ from the reference",
}


# ------------------------------------------------------------ the rules ----
def keep_best(state: OrchestratorState) -> Optional[int]:
    """Valid first, then fewest failed levels, ties: earliest. Validity only.

    After a next iteration the revised draft is kept, unless it is less valid
    than the draft kept before it (a rule reminder must not replace a valid
    model by an invalid one). The evaluate tool then adds one check: if the
    revised draft has more open errors than the previous one, the previous one
    is kept (orchestrator_tools.evaluate).
    """
    done = [r for r in state.rounds if r["validated"]]
    if not done:
        return None
    # a draft without a model (the generator returned nothing usable, e.g. an answer
    # cut at the output limit) is never kept while a draft with a model exists
    empty = lambda r: not (r.get("xml") or "").strip()
    pick = lambda rounds: min(rounds, key=lambda r: (empty(r), not r["valid"],
                                                     len(r["failed_levels"]), r["round"]))
    if state.revision_round is None:
        return pick(done)["round"]
    before = [r for r in done if r["round"] < state.revision_round]
    after = [r for r in done if r["round"] >= state.revision_round]
    if not after or not before:
        return pick(after or before)["round"]
    first, revised = pick(before), pick(after)
    if state.previous_kept is not None:          # what was kept before this next iteration
        first = next((r for r in before if r["round"] == state.previous_kept), first)
    rank = lambda r: (empty(r), not r["valid"], len(r["failed_levels"]))
    return (revised if rank(revised) <= rank(first) else first)["round"]


def budget_reached(state: OrchestratorState) -> Optional[str]:
    """Which budget of the example is used up, in words, or None."""
    limits = state.limits
    if state.tool_calls >= limits["max_tool_calls"]:
        return f"budget reached: {state.tool_calls} tool calls of {limits['max_tool_calls']}"
    if len(state.decisions) >= limits["max_agent_decisions"]:
        return (f"budget reached: {len(state.decisions)} orchestrator decisions of "
                f"{limits['max_agent_decisions']}")
    return None


def allowed_actions(state: OrchestratorState) -> list[OrchestratorAction]:
    if budget_reached(state):
        return [OrchestratorAction.STOP_FAILURE]
    if state.error:
        return [OrchestratorAction.STOP_FAILURE]
    if not state.rounds:
        return [OrchestratorAction.GENERATE]
    last = state.rounds[-1]
    if not last["validated"]:
        return [OrchestratorAction.VALIDATE]
    if not state.evaluated:
        return [OrchestratorAction.EVALUATE]
    if state.failures is None:
        return [OrchestratorAction.DETECT_FAILURES]
    best = next(r for r in state.rounds if r["round"] == state.kept_round)
    stop = OrchestratorAction.STOP_SUCCESS if best["valid"] else OrchestratorAction.STOP_FAILURE
    more = state.revisions < state.max_revisions
    if state.force_iterations and state.learn_enabled and state.rule_feedback_enabled:
        # forced iterations: learn, then send back, until the maximum is reached.
        # Without any error left, or without any guideline for this description,
        # there is nothing to send: the kept model is carried forward.
        if more and state.detected:
            if not state.learned:
                return [OrchestratorAction.LEARN]
            if state.rules_to_reapply:
                return [OrchestratorAction.REVISE]
        return [stop]
    if state.detected and state.learn_enabled and not state.learned and (more or not state.revised):
        # the agent decides: learn from these failures, or end the example.
        # After a next iteration the agents may learn again from the new model,
        # as long as another next iteration could still test what they find.
        return [OrchestratorAction.LEARN, stop]
    pending = [r for r in state.rules_to_reapply if r["rule_id"] not in state.rules_sent]
    if state.rule_feedback_enabled and pending and more:
        # guidelines not sent yet: the agent decides whether to send them back
        # to the generator (next iteration; it repeats while something new is found)
        return [OrchestratorAction.REVISE, stop]
    return [stop]


# ------------------------------------------------------------ the agents ---
class OrchestratorDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str
    reason: str = Field(min_length=3, max_length=600)


class FirstAllowedAgent:
    """Deterministic stand-in (no LLM): first allowed action. Tests / dry runs."""
    name = "deterministic"

    def decide(self, *, observation: dict, allowed: list[str]) -> OrchestratorDecision:
        return OrchestratorDecision(action=allowed[0],
                             reason=f"First allowed action ({allowed[0]}).")


SYSTEM_PROMPT = (
    "You are the orchestrator agent of GuideBPMN, which turns a process description into a "
    "BPMN 2.0 model and learns modeling guidelines from verified mistakes. Choose exactly ONE "
    "next action from allowed_actions, based only on the observed state. "
    "generate drafts a model; validate runs the four-level validator (L1-L4); evaluate "
    "measures similarity to the reference once the draft is validated; detect_failures maps "
    "the evidence (validator errors and differences from the reference) to "
    "failure types T1-T7; learn hands the detected failures to the guideline agents; "
    "revise sends back to the generator the guidelines found for this example that it has not "
    "received yet (documentation rules it did not apply, guidelines just learned from its "
    "mistakes), for a next iteration that shows whether they help; after it, the agents may "
    "learn again from the new model; "
    "stop_success / stop_failure end the run. You decide whenever several actions are allowed. "
    "open_errors is your own record: it counts every single error still open on the current "
    "model, per type (T1-T4: incorrect elements found by the validator; T5: sequence flows "
    "missing or additional; T6: activities without a counterpart; T7: pool, lane or message-flow "
    "relations missing or additional). open_errors_history gives the count after the first pass "
    "and after each next iteration. Your goal is to bring open_errors to zero within the "
    "budgets (next_iterations_allowed, tool_call_budget). "
    "learn or stop: learn while open_errors is not zero, so that the guideline agents can find "
    "what to correct; stop when no error is open. "
    "revise or stop: revise when guidelines_to_send_back lists guidelines and errors are still "
    "open; stop when no error is open, or when open_errors_history shows that the last next "
    "iterations no longer reduce the errors. "
    "Give the concrete reason for your choice, citing what you observed in the state. "
    "Return JSON only: {\"action\": ..., \"reason\": ...}."
)


def _system_prompt(observation: dict) -> str:
    return SYSTEM_PROMPT


class LLMOrchestratorAgent:
    """The orchestrator agent on a model of llm.LLM (OpenAI or Anthropic)."""

    def __init__(self, llm):
        self.llm, self.name = llm, llm.spec

    def decide(self, *, observation: dict, allowed: list[str]) -> OrchestratorDecision:
        reply = self.llm.complete_json(system=_system_prompt(observation), user=json.dumps(
            {"state": observation, "allowed_actions": allowed}, ensure_ascii=False))
        action = str(reply.get("action", "")).strip()
        if action not in allowed:
            raise RuntimeError(f"Agent chose forbidden action {action!r}; allowed={allowed}")
        reason = str(reply.get("reason") or "no reason given")[:600]
        return OrchestratorDecision(action=action, reason=reason if len(reason) >= 3 else "no reason given")


# ------------------------------------------------------------ the graph ----
class GraphState(TypedDict):
    orchestrator: dict


def build_graph(agent, tools: dict[str, Callable[[OrchestratorState], None]],
                on_event: Optional[Callable[[dict], None]] = None):
    from langgraph.graph import END, START, StateGraph

    def emit(event):
        if on_event:
            on_event(event)

    def decide(data: GraphState) -> GraphState:
        state = OrchestratorState.model_validate(data["orchestrator"])
        allowed = [a.value for a in allowed_actions(state)]
        fallback = False
        if len(allowed) == 1 and allowed[0] in (a.value for a in TERMINAL_ACTIONS):
            decision = OrchestratorDecision(action=allowed[0], reason="Only remaining action.")
        elif len(allowed) == 1:
            decision = OrchestratorDecision(action=allowed[0],
                                     reason=f"Only permitted action ({allowed[0]}).")
        else:
            decision, problem = None, None
            for _ in range(2):                 # one retry, then the default action
                try:
                    decision = agent.decide(observation=state.observation(), allowed=allowed)
                    break
                except Exception as exc:
                    problem = f"{type(exc).__name__}: {exc}"[:200]
            if decision is None:
                fallback = True
                decision = OrchestratorDecision(
                    action=allowed[0],
                    reason=f"Default action: the agent's reply could not be used ({problem})."[:600])
        state.selected_action = decision.action
        state.decisions.append({"action": decision.action, "reason": decision.reason,
                                "allowed": allowed, "agent": getattr(agent, "name", "agent"),
                                "agent_chose": len(allowed) > 1 and not fallback,
                                "fallback": fallback})
        emit({"type": "decision", "id": state.example_id, "action": decision.action,
              "reason": decision.reason, "allowed": allowed})
        return {"orchestrator": state.model_dump(mode="json")}

    def tool_node(action: OrchestratorAction):
        def node(data: GraphState) -> GraphState:
            state = OrchestratorState.model_validate(data["orchestrator"])
            state.tool_calls += 1
            try:
                tools[action.value](state)
            except Exception as exc:                       # infrastructure, not BPMN
                state.error = f"{action.value}: {type(exc).__name__}: {exc}"
                emit({"type": "error", "id": state.example_id, "text": state.error})
            return {"orchestrator": state.model_dump(mode="json")}
        return node

    def stop_node(action: OrchestratorAction):
        def node(data: GraphState) -> GraphState:
            state = OrchestratorState.model_validate(data["orchestrator"])
            state.stopped = action.value
            state.stop_reason = state.decisions[-1]["reason"] if state.decisions else ""
            spent = budget_reached(state)
            if spent and action == OrchestratorAction.STOP_FAILURE:
                state.stop_reason = f"{spent}. {state.stop_reason}".strip()
            emit({"type": "stop", "id": state.example_id, "action": action.value,
                  "reason": state.stop_reason})
            return {"orchestrator": state.model_dump(mode="json")}
        return node

    graph = StateGraph(GraphState)
    graph.add_node("decide", decide)
    for action in TOOL_ACTIONS:
        graph.add_node(action.value, tool_node(action))
        graph.add_edge(action.value, "decide")
    for action in TERMINAL_ACTIONS:
        graph.add_node(action.value, stop_node(action))
        graph.add_edge(action.value, END)
    graph.add_edge(START, "decide")
    graph.add_conditional_edges(
        "decide", lambda data: data["orchestrator"]["selected_action"],
        {a.value: a.value for a in OrchestratorAction})
    return graph.compile()


def run_example(state: OrchestratorState, agent, tools, on_event=None) -> OrchestratorState:
    graph = build_graph(agent, tools, on_event)
    limit = state.limits["max_agent_decisions"] * 2 + 5
    out = graph.invoke({"orchestrator": state.model_dump(mode="json")},
                       config={"recursion_limit": limit})
    return OrchestratorState.model_validate(out["orchestrator"])
