"""GuideBPMN web API: runs the pipeline behind the project website.

The website (static pages) is the user interface; this service executes the
pipeline of bpmn_pipeline/ (run_batch.run_arm) and serves past runs:

  * /api/orchestrator/*   launch a run, follow it live, open past runs and the learned guidelines
  * /api/validate  validator.validate_bpmn (no LLM call)

Start it from the repository root:

  python -m uvicorn webapi.app:app --host 127.0.0.1 --port 8765

Configuration (environment variables):
  GUIDEBPMN_ALLOWED_ORIGINS   extra comma-separated origins allowed to call the API
  GUIDEBPMN_API_TOKEN         if set, every call except /api/health needs the header X-API-Token
  OPENAI_API_KEY / ANTHROPIC_API_KEY   needed by the chosen LLMs (never sent to the browser)
"""
from __future__ import annotations

import json
import os
import re
import secrets
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import validator  # noqa: E402  (repository root)
from webapi.display_layout import prepare_display_xml  # noqa: E402

API_VERSION = "2.0"
MAX_UPLOAD = 5_000_000
XSD = validator.load_xsd(ROOT / "xsd" / "BPMN20.xsd")

app = FastAPI(title="GuideBPMN API", version=API_VERSION,
              description="Executes the GuideBPMN pipeline for the project website.")

_origins = [o.strip() for o in os.getenv("GUIDEBPMN_ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    # the website served locally or from any GitHub Pages site
    allow_origin_regex=r"^(https://[a-z0-9-]+\.github\.io|http://(localhost|127\.0\.0\.1)(:\d+)?|null)$",
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Token"],
)


@app.middleware("http")
async def _private_network_access(request, call_next):
    """A page served from the internet (GitHub Pages) may call this API on the
    reviewer's own machine: answer the browser's private-network preflight."""
    response = await call_next(request)
    if request.headers.get("access-control-request-private-network") == "true":
        response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response


def require_token(x_api_token: Optional[str] = Header(default=None)):
    expected = os.getenv("GUIDEBPMN_API_TOKEN", "")
    if expected and not (x_api_token and secrets.compare_digest(x_api_token, expected)):
        raise HTTPException(401, "Missing or wrong X-API-Token")


# ------------------------------------------------------------------ helpers --
def _json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


# ---------------------------------------------------------------------------
# Plain-language explanations of validator failures, served next to the
# technical message. L2-L4 failures are a FINITE set: every entry below mirrors
# one explicit branch in validator.py / soundness.py. L1 messages come from the
# XSD engine (libxml2), an open set, so they are classified by family with a
# generic fallback per level -- no failure is ever left unexplained.
# NOTE these texts exist only in web responses (_clean_profile); the prompts
# of the generator read the validator results directly and are unchanged.
_PLAIN_FALLBACK = {
    "L1": "The XML breaks the official BPMN 2.0 grammar: the message names the exact element, attribute and line that the schema refuses.",
    "L2": "A gateway in the diagram breaks the BPMN gateway rules named in the message.",
    "L3": "The flow of the diagram is broken at the named element: following the arrows, a case could not run from start to end correctly.",
    "L4": "A pool, lane or message flow breaks the BPMN collaboration rules named in the message.",
}
_PLAIN_RULES = [
    # L1: families of schema errors (open set, most specific first)
    ("malformed XML", "The file is not well-formed XML, so nothing else can be checked: fix the syntax error shown (unclosed tag, stray character) and validate again."),
    ("attribute 'isExecutable'", "The attribute isExecutable is allowed on <process> but not here (e.g. not on <subProcess>). Remove it from this element."),
    ("}gateway':", "BPMN has no generic <gateway> element. Use one of the five real types: exclusiveGateway, parallelGateway, inclusiveGateway, eventBasedGateway or complexGateway."),
    ("This element is not expected", "The named element is not valid BPMN at that position: either the tag does not exist in BPMN, or it sits inside the wrong parent."),
    ("attribute 'conditionExpression'", "A condition is a child element of the flow (<conditionExpression xsi:type=\"bpmn:tFormalExpression\">...</conditionExpression>), not an attribute on it."),
    ("attribute 'default'", "The default path is declared on the GATEWAY (default=\"Flow_X\"), not as an attribute of the sequence flow itself."),
    ("The QName value", "The xsi:type must carry the bpmn namespace prefix: write xsi:type=\"bpmn:tFormalExpression\", not plain \"tFormalExpression\"."),
    ("The type definition is abstract", "This tag is an abstract placeholder in the BPMN schema: write the concrete element instead (a task, event or gateway for flowElement; standardLoopCharacteristics or multiInstanceLoopCharacteristics for loopCharacteristics)."),
    ("is not allowed.", "The named attribute does not exist on this element in BPMN. Remove it, or move the information where the schema expects it."),
    ("Missing child element", "The named element is incomplete: BPMN requires a child element that is missing here."),
    ("Duplicate key-sequence", "Two elements share the same id. Every id must be unique in the whole file."),
    ("is not a valid value", "The named attribute has a value of the wrong kind (for example text where BPMN expects true/false or a number)."),
    ("No match found for key", "Something references an id that does not exist in the file. Fix the reference or add the missing element."),
    # L2: all branches of check_l2
    ("no <process> found", "The file contains no <process> element, so there is no process to check."),
    ("unauthorized gateway type", "This gateway type does not exist in BPMN. Use one of the five standard types: exclusive, parallel, inclusive, event-based or complex."),
    ("needs at least two outgoing", "An event-based gateway offers a choice between events, so it needs at least two outgoing flows."),
    ("must not have a condition", "Branches after an event-based gateway carry no conditions: the first event that occurs picks the path."),
    ("leads directly to", "After an event-based gateway, each branch must begin with what it waits for: an intermediate catch event (message, timer, signal or conditional) or a receive task."),
    # L3: all branches of _l3_analyze_scope + soundness.py
    ("missing sourceRef/targetRef", "This flow must name both the element it leaves and the element it reaches."),
    ("has no id", "Every BPMN element needs an id, so that flows and lanes can reference it."),
    ("missing attachedToRef", "A boundary event must say which activity it is attached to (attachedToRef)."),
    ("no startEvent found", "This process has no start event. Add one and connect it to the first step."),
    ("no endEvent found", "This process has no end event: every path should finish in one. Add an end event after the last step."),
    ("is in another process", "A sequence flow (solid arrow) can only connect elements of the same process or sub-process. To cross between pools, use a message flow (dashed arrow) declared in the <collaboration>."),
    ("does not exist", "A flow references an element that is not in the file. Fix the sourceRef/targetRef, or add the missing element."),
    ("which is not an", "A boundary event can only be attached to an activity, a task or a sub-process, never to a gateway or an event."),
    ("detached from the main flow", "These elements form an island, disconnected from the start-to-end flow, so they would never run. Connect them, or delete them."),
    ("event sub-process must not", "An event sub-process is triggered by its own start event, never by arrows: remove the sequence flows entering or leaving it."),
    ("startEvent must not have an incoming", "A start event only begins flow: no arrow may enter it. Move that arrow to another element."),
    ("boundaryEvent must not have an incoming", "A boundary event is entered through the activity it is attached to; it cannot receive a sequence flow."),
    ("endEvent must not have an outgoing", "An end event only terminates flow: no arrow may leave it. Move that arrow to another element."),
    ("no incoming connection", "The named element can never be reached: nothing flows into it. Connect a previous step to it, or remove it."),
    ("no outgoing connection", "The named element is a dead end: flow enters it but never leaves. Connect it to the next step or to an end event."),
    ("no branching/merging role", "This gateway has one flow in and one flow out, so it decides nothing. Remove it, or give it a real split or merge."),
    ("not reachable from a startEvent", "No path leads from a start event to the named element, so it would never run."),
    ("cannot reach an endEvent", "From the named element no path reaches an end event, so a case passing there could never finish."),
    ("deadlock:", "The process can get stuck: the named element waits for a flow that can no longer receive a token, usually a parallel join whose branch cannot arrive. Check the split/join gateway pairs."),
    ("can never complete", "The process can reach a state where nothing can ever move again. Check that every parallel split is matched by a parallel join on the same branches."),
    ("lack of synchronisation", "One flow can receive two tokens at once (a split re-enters a path), so steps may run twice. Add a proper join before the shared path."),
    # L4: all branches of check_l4
    ("a lane cannot be the source", "Messages travel between pools or flow nodes, never lanes. Connect the message flow to the pool itself or to a task or event inside it."),
    ("a lane cannot be the target", "Messages travel between pools or flow nodes, never lanes. Connect the message flow to the pool itself or to a task or event inside it."),
    ("cannot send a message flow", "Gateways route flow inside a process; they never exchange messages. Start the message flow from a task or a throw/end event instead."),
    ("cannot receive a message flow", "Gateways route flow inside a process; they never exchange messages. Point the message flow at a task or a catch/start event instead."),
    ("cannot be the source of a message flow", "This element type cannot send messages. Message sources are activities and throwing/end events."),
    ("cannot be the target of a message flow", "This element type cannot receive messages. Message targets are activities and catching/start events."),
    ("is not an element of", "Each lane may only list flow nodes of the process that owns it. The named element belongs elsewhere."),
    ("not a flow node", "Lanes contain flow nodes (tasks, events, gateways). The named element is not one, so it cannot be listed in a lane."),
    ("is in two lanes", "A flow node belongs to at most one lane of a lane set. Remove it from one of the two lanes."),
    ("references a non-existent element", "The message flow points at an id that does not exist. Fix its sourceRef/targetRef."),
    ("SAME pool", "A message flow may only connect two different pools. Inside one pool, connect the elements with a sequence flow instead."),
    ("does not resolve to any pool", "Each end of a message flow must belong to a pool declared in the <collaboration>."),
]


def _plain(level: str, message) -> str:
    text = str(message or "")
    for needle, explanation in _PLAIN_RULES:
        if needle in text:
            return explanation
    return _PLAIN_FALLBACK.get(level, "")


def _clean_profile(profile: dict) -> dict:
    out = {}
    for level in ("L1", "L2", "L3", "L4"):
        v = profile.get(level) or {}
        out[level] = {"result": v.get("result"), "message": v.get("message"),
                      "error_elements": (v.get("error_elements") or [])[:20]}
        if v.get("result") is False:
            out[level]["plain"] = _plain(level, v.get("message"))
    return out


# ------------------------------------------------------------------- models --
class ValidateRequest(BaseModel):
    xml: str = Field(..., min_length=1, max_length=MAX_UPLOAD)


# ------------------------------------------------------------------- routes --
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root():
    """Landing text for people who open the API address in a browser."""
    return ("<!doctype html><meta charset='utf-8'><title>GuideBPMN API</title>"
            "<body style='font-family:sans-serif;max-width:40rem;margin:3rem auto;line-height:1.5'>"
            "<h2>GuideBPMN API is running</h2>"
            "<p>This address is the service, not the website. Open the <em>Run</em> page of the website "
            "and click <strong>Connect</strong>.</p>"
            "<p>Health check: <a href='/api/health'>/api/health</a> &middot; "
            "API documentation: <a href='/docs'>/docs</a></p></body>")


@app.get("/api/health")
def health():
    return {"status": "ok", "api_version": API_VERSION,
            "openai_key": bool(os.getenv("OPENAI_API_KEY", "").strip()),
            "anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY", "").strip()),
            "token_required": bool(os.getenv("GUIDEBPMN_API_TOKEN"))}


@app.post("/api/validate", dependencies=[Depends(require_token)])
def validate(req: ValidateRequest):
    """Validate a BPMN 2.0 document (L1-L4, including the deadlock check). No LLM call."""
    result = validator.validate_bpmn(req.xml, XSD)
    display, warnings = None, []
    try:
        display, warnings = prepare_display_xml(req.xml)
    except Exception as exc:
        warnings = [f"Diagram not displayable: {exc}"]
    return {"overall_valid": result["overall_valid"], "profile": _clean_profile(result["profile"]),
            "display_xml": display, "display_warnings": warnings}


@app.post("/api/validate/upload", dependencies=[Depends(require_token)])
async def validate_upload(file: UploadFile = File(...)):
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "File larger than 5 MB")
    return validate(ValidateRequest(xml=data.decode("utf-8", errors="replace")))


# ---------------------------------------------------------------------------
# GuideBPMN experiment endpoints (the launcher on docs/run.html).
# One run at a time; a dry run exercises the whole circuit without any LLM.

ORCHESTRATOR: dict[str, Any] = {"state": "idle", "label": None, "progress": [],
                         "report": None, "report_after_rule_feedback": None,
                         "error": None, "started": None,
                         "ids": [], "examples": {}, "run_dir": None}
_ORCHESTRATOR_ARMS = ("documentation", "documentation+learned")


class OrchestratorRunRequest(BaseModel):
    arm: str = "documentation"
    dry_run: bool = True
    limit: Optional[int] = Field(default=None, ge=1, le=55)       # the first N
    ids: Optional[str] = None                                     # "24, 38, 41-45"
    sample: Optional[int] = Field(default=None, ge=1, le=55)      # N drawn at random
    seed: int = 42
    resume: Optional[str] = None      # folder of an interrupted run: continue it
    confirmed_only: bool = False      # reuse only guidelines confirmed by a next iteration
    fresh_catalogue: bool = True      # learning runs: start from an empty learned catalogue
    next_iterations: int = Field(default=3, ge=0, le=10)  # learning runs: maximum per description
    # the other budgets of one description; None = the default of the pipeline
    max_agent_decisions: Optional[int] = Field(default=None, ge=10, le=400)
    max_tool_calls: Optional[int] = Field(default=None, ge=10, le=400)
    # how T5-T7 are detected: any difference found by the evaluator (no threshold)
    failure_rule: str = Field(default="any_difference", pattern="^any_difference$")
    promote_confirmed: bool = False   # learning runs: confirmed example-specific -> generic guideline
    learn: bool = True                # False with 0 next iterations = First
    # stratified k-fold cross-validation: the training learns on the 44 training
    # descriptions of the fold, the test runs on its 11 test descriptions
    fold: Optional[int] = Field(default=None, ge=1, le=5)
    force_iterations: bool = False    # Revised and Reuse training: every description does all next iterations
    replicate: Optional[int] = Field(default=None, ge=1, le=10)   # First / Revised: run number (own catalogue)
    # a learning run on a few chosen descriptions (a reviewer's test): its own
    # catalogue under trials/, so the catalogues of the study are never touched.
    # None = decided here: any learning run that is not a fold and not the whole dataset
    trial: Optional[bool] = None
    # one "provider:model" per component: generator, orchestrator,
    # retriever, expert (openai:... or anthropic:...). Missing ones use llm.DEFAULT_MODELS.
    models: dict[str, str] = Field(default_factory=dict)


def _orchestrator_llm():
    pipeline_dir = ROOT / "bpmn_pipeline"
    if str(pipeline_dir) not in sys.path:
        sys.path.insert(0, str(pipeline_dir))
    import llm
    return llm


def _orchestrator_run_batch():
    """Import the pipeline lazily so the API starts without it."""
    pipeline_dir = ROOT / "bpmn_pipeline"
    if str(pipeline_dir) not in sys.path:
        sys.path.insert(0, str(pipeline_dir))
    import pipeline_config
    pipeline_config.add_shared_paths()
    import run_batch
    return run_batch


@app.get("/api/orchestrator/status", dependencies=[Depends(require_token)])
def orchestrator_status():
    out = {k: ORCHESTRATOR[k] for k in ("state", "label", "report", "report_after_rule_feedback",
                                  "error", "started", "ids", "run_dir")}
    out["limits"] = ORCHESTRATOR.get("limits")
    out["failure_rule"] = ORCHESTRATOR.get("failure_rule")
    out["promote_confirmed"] = ORCHESTRATOR.get("promote_confirmed")
    out["validator_performance"] = ORCHESTRATOR.get("validator_performance")
    out["metrics_summary"] = ORCHESTRATOR.get("metrics_summary")
    out["progress"] = list(ORCHESTRATOR["progress"])[-120:]
    out["examples"] = {eid: {k: v for k, v in ex.items()}
                       for eid, ex in ORCHESTRATOR["examples"].items()}
    return out


_ORCHESTRATOR_RUNS = ROOT / "bpmn_pipeline" / "runs"


def _orchestrator_run_dir(run: Optional[str]) -> Path:
    """The folder of a past run (by name) or of the run of this server session."""
    if run:
        import re
        if not re.fullmatch(r"batch_[A-Za-z0-9_.\-]+", run) or not (_ORCHESTRATOR_RUNS / run).is_dir():
            raise HTTPException(404, f"Unknown run {run!r}")
        return _ORCHESTRATOR_RUNS / run
    if not ORCHESTRATOR.get("run_dir"):
        raise HTTPException(404, "No GuideBPMN run in this server session yet")
    return Path(ORCHESTRATOR["run_dir"])


def _display_copy(xml: str) -> tuple[str, bool]:
    """A copy the browser can draw. Generated models often carry no positions:
    a layout is added for display only (never used by the validator or the metrics)."""
    try:
        laid_out, notes = prepare_display_xml(xml)
        return laid_out, bool(notes)
    except Exception:
        return xml, False


_NEW_SCORES = ("activity_semantic_similarity", "activity_label_precision",
               "activity_label_recall", "activity_label_f1")


def _rescored(run_dir: Path) -> dict:
    path = run_dir / "rescored_drafts.json"
    return _json(path) if path.is_file() else {}


def _add_scores(metrics, again) -> None:
    """Scores added since a run was made, taken from its re-scoring (never overwrites)."""
    if isinstance(metrics, dict) and again:
        for key in _NEW_SCORES:
            if metrics.get(key) is None:
                metrics[key] = again.get(key)


def _validator_performance(folder: Path):
    """Validator performance of a run, level by level (computed once, then read)."""
    path = folder / "validator_performance.json"
    try:
        if path.is_file():
            return _json(path)
        _orchestrator_run_batch()
        import validation
        return validation.run_performance(folder)
    except Exception:
        return None


def _validator_levels(xml: str):
    try:
        _orchestrator_run_batch()
        import validation
        return validation.element_performance(xml or "")
    except Exception:
        return None


def _with_rescored(report: dict, folder: Path) -> dict:
    """The first-pass report of a run, completed with the scores added since
    (activity labels), taken from its re-scoring. Existing values are kept."""
    path = folder / "rescored_summary.json"
    if path.is_file() and isinstance(report.get("metrics"), dict):
        again = _json(path).get("metrics", {})
        added = {k: again[k] for k in _NEW_SCORES if k in again and not (report["metrics"].get(k) or {}).get("n")}
        report["metrics"] = {**added, **{k: v for k, v in report["metrics"].items() if k not in added}}
    return report


RESCORE = {"state": "idle", "progress": [], "error": None, "runs": []}


class RescoreRequest(BaseModel):
    run: Optional[str] = None          # one run folder; none = every finished run of 50+ examples


@app.post("/api/orchestrator/rescore", dependencies=[Depends(require_token)])
def orchestrator_rescore(req: RescoreRequest):
    """Compare the saved drafts of past runs with their references again, with the
    current evaluator. Nothing is generated; run files are not changed."""
    if RESCORE["state"] == "running":
        raise HTTPException(409, "A re-scoring is already in progress")
    names = [_orchestrator_run_dir(req.run).name] if req.run else None
    RESCORE.update(state="running", progress=[], error=None, runs=[])

    def work():
        try:
            _orchestrator_run_batch()
            import rescore
            done = rescore.rescore_runs(names, progress=lambda line: RESCORE["progress"].append(str(line)))
            RESCORE.update(state="done", runs=[{"run": s["run"], "examples": s["examples"],
                                                "activities": s["metrics"]["activity_semantic_similarity"].get("mean"),
                                                "semantic": s["metrics"]["semantic_similarity"].get("mean")}
                                               for s in done])
        except Exception as exc:
            RESCORE.update(state="error", error=f"{type(exc).__name__}: {exc}")

    threading.Thread(target=work, daemon=True, name="guidebpmn-rescore").start()
    return {"started": True}


@app.get("/api/orchestrator/rescore", dependencies=[Depends(require_token)])
def orchestrator_rescore_status():
    return {"state": RESCORE["state"], "error": RESCORE["error"], "runs": RESCORE["runs"],
            "progress": RESCORE["progress"][-5:]}


def _ledger(folder: Path):
    """Bonuses and penalties of one example (None if it has no draft yet)."""
    try:
        _orchestrator_run_batch()
        import utility
        return utility.example_ledger(folder)
    except Exception:
        return None


def _score(folder: Path):
    book = _ledger(folder)
    return ({k: book[k] for k in ("total_bonus", "total_penalty", "utility")} if book else None)


def _version(models: dict) -> dict:
    """The setting of a run (First, Revised, Reuse training / test), from its saved settings."""
    arm, fold, rep = models.get("arm"), models.get("fold"), models.get("replicate")
    if arm == "documentation" and models.get("learn") is False and not models.get("trial"):
        name, meaning = "First", "documentation guidelines only, no learning"
    elif arm == "documentation" and models.get("trial"):
        name = "Trial"
        meaning = ("learns on a few chosen descriptions, own catalogue" if models.get("learn", True)
                   else "one pass on a few chosen descriptions, no learning") + " (not part of the study)"
        rep = None
    elif arm == "documentation" and fold:
        name, meaning = "Reuse training", f"round {fold}, learns on 44 descriptions"
    elif arm == "documentation+learned" and fold:
        name, meaning = "Reuse test", f"round {fold}, confirmed guidelines of the round, 11 unseen descriptions"
    elif arm == "documentation":
        name, meaning = "Revised", "learns" + (", forced next iterations" if models.get("force_iterations") else "")
    else:
        name, meaning = "other", arm or "unknown"
    if rep:
        meaning += f", run {rep}"
    return {"version": name, "version_meaning": meaning}


def _run_summary(folder: Path) -> dict:
    """A finished (or interrupted) run read back from disk, shaped like /status."""
    models = _json(folder / "models.json") if (folder / "models.json").is_file() else {}
    folders = sorted(p for p in folder.glob("id_*") if p.is_dir())
    ids = (models.get("examples") or {}).get("ids") or [p.name[3:] for p in folders]
    examples = {}
    for sub in folders:
        final = sub / "iterations.json"
        source = final if final.is_file() else sub / "live_iterations.json"
        if not source.is_file():
            continue
        doc = _json(source)
        decisions = _json(sub / "decisions.json") if (sub / "decisions.json").is_file() else {}
        kept = next((i for i in doc["iterations"] if i["round"] == doc.get("kept_round")), None)
        first = doc.get("first_pass") or {}
        examples[sub.name[3:]] = {
            "iterations": [{k: i.get(k) for k in ("round", "kind", "valid", "failed_levels",
                                                  "metrics", "seconds")}
                           for i in doc["iterations"]],
            "valid": kept["valid"] if kept and final.is_file() else None,
            "kept_round": doc.get("kept_round"),
            "revised": bool(doc.get("rule_feedback")),
            "metrics": (kept or {}).get("metrics") if final.is_file() else None,
            "first_pass_metrics": first.get("metrics"),
            "stopped": decisions.get("stopped"),
            "detected": decisions.get("detected_failures", []),
            "guidelines": decisions.get("guidelines", []),
            "score": _score(sub),
        }
    rescored = _rescored(folder)                       # written by rescore.py
    for eid, ex in examples.items():
        for it in ex["iterations"]:
            _add_scores(it.get("metrics"), rescored.get(eid, {}).get(str(it["round"])))
        if ex.get("kept_round") is not None:
            _add_scores(ex.get("metrics"), rescored.get(eid, {}).get(str(ex["kept_round"])))
    reports = sorted(folder.glob("report_*.json"))
    first = next((p for p in reports if not p.stem.endswith("_after_rule_feedback")), None)
    after = next((p for p in reports if p.stem.endswith("_after_rule_feedback")), None)
    used = models.get("models") or {}
    return {"run": folder.name, "state": "done" if first else "interrupted",
            "label": ("dry run" if models.get("dry_run") else
                      "Version %(version)s (%(version_meaning)s)" % _version(models)
                      + " / " + used.get("generator", "?"))
                     + f" / {len(ids)} example(s)",
            "ids": ids, "examples": examples, "models": used, "arm": models.get("arm"),
            "dry_run": models.get("dry_run"), "progress": [], "error": None,
            "limits": models.get("limits"),
            "failure_rule": models.get("failure_rule") or "any_difference",
            "promote_confirmed": models.get("promote_confirmed"),
            "validator_performance": _validator_performance(folder) if first else None,
            "report": _with_rescored(_json(first), folder) if first else None,
            "report_after_rule_feedback": _json(after) if after else None,
            "fold": models.get("fold"), "fold_role": models.get("fold_role"),
            "metrics_summary": _metrics_summary(folder) if examples else None}


def _unfinished_examples(folder: Path) -> list[str]:
    """Examples of a run that did not finish, or stopped on an infrastructure error."""
    ids = (_json(folder / "models.json").get("examples") or {}).get("ids") or []
    out = []
    for eid in ids:
        sub = folder / f"id_{eid}"
        if not (sub / "iterations.json").is_file():
            out.append(str(eid))
            continue
        decisions = _json(sub / "decisions.json")
        if decisions.get("error") or _orchestrator_run_batch().lost_agent_step(decisions):
            out.append(str(eid))
    return out


def _fold_report():
    _orchestrator_run_batch()                       # puts bpmn_pipeline on the path
    import fold_report
    return fold_report


def _metrics_summary(folder: Path) -> Optional[dict]:
    """Mean, SD, min and max of every metric, and the accuracy per level."""
    try:
        fr = _fold_report()
        rows = fr.example_rows(folder)
        return fr.summarize(rows) if rows else None
    except Exception:
        return None


@app.get("/api/orchestrator/folds", dependencies=[Depends(require_token)])
def orchestrator_folds():
    """The folds of the stratified k-fold cross-validation."""
    _orchestrator_run_batch()
    import folds
    doc = folds.load_complexity_folds()
    return {"method": doc["method"], "k": doc["k"],
            "folds": [{k: f[k] for k in ("fold", "test_ids", "test_complexity",
                                         "test_with_pools_or_lanes")} for f in doc["folds"]]}


@app.get("/api/orchestrator/cv", dependencies=[Depends(require_token)])
def orchestrator_cv(generator: str, baseline: Optional[str] = None):
    """Cross-validation results of one generator model (baseline vs B per fold,
    pooled over the test descriptions, RQ2 per fold, levels, guidelines)."""
    fr = _fold_report()
    try:
        return fr.build_cv(generator, baseline)
    except fr.NoBaseline as exc:
        raise HTTPException(404, str(exc))


@app.post("/api/orchestrator/cv/save", dependencies=[Depends(require_token)])
def orchestrator_cv_save(generator: str, baseline: Optional[str] = None):
    """Write the cross-validation report files (CSV, JSON, Markdown)."""
    fr = _fold_report()
    try:
        fr.build_cv(generator, baseline)
    except fr.NoBaseline as exc:
        raise HTTPException(404, str(exc))
    return {"folder": str(fr.cv_report(generator, baseline))}


def _study_report():
    _orchestrator_run_batch()                       # puts bpmn_pipeline on the path
    import study_report
    return study_report


@app.get("/api/orchestrator/study", dependencies=[Depends(require_token)])
def orchestrator_study(generator: str):
    """Results of the study for one generator: First, Revised i1, i2, Learned, Reuse.
    """
    return _study_report().build(generator)


@app.post("/api/orchestrator/study/save", dependencies=[Depends(require_token)])
def orchestrator_study_save(generator: str):
    """Write the study report files (JSON, CSV, Markdown)."""
    sr = _study_report()
    return {"folder": str(sr.write(sr.build(generator)))}


@app.get("/api/orchestrator/runs", dependencies=[Depends(require_token)])
def orchestrator_runs():
    """Runs kept on disk, most recent first (the site can reopen any of them)."""
    out = []
    folders = sorted((p for p in _ORCHESTRATOR_RUNS.glob("batch_*") if p.is_dir()),
                     key=lambda p: p.name, reverse=True) if _ORCHESTRATOR_RUNS.is_dir() else []
    real = dry = 0
    for folder in folders:
        models = _json(folder / "models.json") if (folder / "models.json").is_file() else {}
        used = models.get("models") or {}
        is_dry = bool(models.get("dry_run")) or not models
        if (dry >= 5) if is_dry else (real >= 80):      # every real run, only the latest dry runs
            continue
        dry, real = dry + is_dry, real + (not is_dry)
        out.append({"run": folder.name, "dry_run": bool(models.get("dry_run")),
                    **_version(models), "rescored": (folder / "rescored_drafts.json").is_file(),
                    "arm": models.get("arm"), "generator": used.get("generator"),
                    "fold": models.get("fold"), "fold_role": models.get("fold_role"),
                    "examples": len((models.get("examples") or {}).get("ids")
                                    or list(folder.glob("id_*"))),
                    "finished": any(folder.glob("report_*.json")) and not _unfinished_examples(folder),
                    "unfinished": _unfinished_examples(folder),
                    "current": str(folder) == str(ORCHESTRATOR.get("run_dir") or "")})
    return {"runs": out}


@app.get("/api/orchestrator/runs/{run}", dependencies=[Depends(require_token)])
def orchestrator_past_run(run: str):
    return _run_summary(_orchestrator_run_dir(run))


@app.get("/api/orchestrator/example/{example_id}", dependencies=[Depends(require_token)])
def orchestrator_example(example_id: str, run: Optional[str] = None):
    """Everything the view needs for one example: the description, the gold
    BPMN, and every draft's XML, validator outcome and metrics. Works while
    the example is still running (drafts validated so far) and for past runs."""
    run_dir = _orchestrator_run_dir(run)
    wanted = str(example_id).zfill(2)
    folder = run_dir / f"id_{wanted}"
    if not folder.is_dir():
        folder = run_dir / f"id_{example_id}"
    path = folder / "iterations.json"
    if not path.is_file():
        path = folder / "live_iterations.json"      # the example is still running
    if not path.is_file():
        raise HTTPException(404, f"Example {example_id} has no validated draft yet")
    document = json.loads(path.read_text(encoding="utf-8"))
    again = _rescored(run_dir).get(str(document["id"]), {})
    for iteration in document["iterations"]:
        iteration["display_xml"], iteration["layout_added"] = _display_copy(iteration["xml"] or "")
        _add_scores(iteration.get("metrics"), again.get(str(iteration["round"])))
        if not iteration.get("validator_levels"):
            iteration["validator_levels"] = _validator_levels(iteration.get("xml"))
    if document.get("live") and not run:
        live = ORCHESTRATOR["examples"].get(document["id"]) or ORCHESTRATOR["examples"].get(wanted) or {}
        document["agent"] = {"agent": "running", "stopped": None,
                             "decisions": live.get("decisions", [])}
        document["guideline_learning"] = [
            {"failure_type": g.get("failure_type"), "status": g.get("status"),
             "guideline_id": g.get("guideline_id"), "detail": g.get("detail"),
             "candidate": {"trigger": g.get("trigger"), "instruction": g.get("instruction")}}
            for g in live.get("guidelines", [])]
    document["utility"] = _ledger(path.parent)
    learning_path = path.parent / "guideline_learning.json"
    if learning_path.is_file():
        document["guideline_learning"] = json.loads(
            learning_path.read_text(encoding="utf-8"))["outcomes"]
    history_path = path.parent / "guideline_learning_history.json"
    if history_path.is_file():          # every learn call, with the agents' tool steps
        document["guideline_learning_history"] = json.loads(
            history_path.read_text(encoding="utf-8")).get("learn_calls", [])
    decisions_path = path.parent / "decisions.json"
    if decisions_path.is_file():
        document["agent"] = json.loads(decisions_path.read_text(encoding="utf-8"))
    dataset = json.loads((ROOT / "bpmn_generator_catalogue" / "dataset.json")
                         .read_text(encoding="utf-8"))
    entry = next((e for e in dataset
                  if str(e["id"]).zfill(2) == wanted), None)
    if entry:
        document["description"] = entry["description"]
        document["gold_xml"] = entry["bpmn_xml"]
        document["gold_display_xml"], _ = _display_copy(entry["bpmn_xml"])
    return document


@app.get("/api/orchestrator/dataset", dependencies=[Depends(require_token)])
def orchestrator_dataset():
    """The 55 descriptions of the dataset, so that one can be chosen and run from
    zero on the site: number, size, whether its reference has pools or lanes,
    and the text."""
    dataset = json.loads((ROOT / "bpmn_generator_catalogue" / "dataset.json")
                         .read_text(encoding="utf-8"))
    out = []
    for entry in dataset:
        text = " ".join(str(entry.get("description", "")).split())
        xml = entry.get("bpmn_xml", "") or ""
        out.append({"id": str(entry["id"]).zfill(2), "words": len(text.split()),
                    "with_pools_or_lanes": ("participant" in xml) or ("<bpmn:lane " in xml) or ("<lane " in xml),
                    "excerpt": text[:120] + ("…" if len(text) > 120 else ""),
                    "description": text})
    return {"descriptions": out}


_DOWNLOAD_README = """GuideBPMN: files of {what}

Everything here was written by the tool while it ran; nothing was edited.

models.json                      the settings of the run: setting (First / Revised / Reuse / Trial),
                                 model of each component, descriptions, budgets, learning agents, catalogue
id_NN/iterations.json            every draft of description NN: BPMN XML, validator verdict per level,
                                 similarity scores against the reference, first pass and next iterations
id_NN/decisions.json             every decision of the orchestrator, in order, with its reason and the
                                 allowed actions, then the outcome
id_NN/guideline_learning.json    the error-driven guidelines learned for this description (last learn call)
id_NN/guideline_learning_history.json
                                 every learn call: for each failure type, every step of the Retriever and
                                 Expert agents (tool called, arguments, result, reason), their final answers,
                                 and what the code guards did with them
id_NN/round_K/                   draft K as the generator returned it (generated_bpmn_*.json) and the
                                 audit of the prompt it received (prompt_audit/)
id_NN/validator/                 the structural validator's files for the latest draft: the model
                                 (generated_model.bpmn), the description, the report (validation_profile.json)
id_NN/similarity/                the similarity evaluator's results for the latest draft (similarity_results.json)
id_NN/09_agent_input_preview.json, id_NN/10_evidence_file_registry.*
                                 the evidence records built for the guideline agents
catalogue/                       the catalogue of error-driven guidelines of this run, as it is now
                                 (learned_guidelines.json: each guideline with the descriptions it was
                                 learned from, its relation to the documentation guidelines and its tests)
"""


@app.get("/api/orchestrator/download", dependencies=[Depends(require_token)])
def orchestrator_download(run: Optional[str] = None, example: Optional[str] = None):
    """A zip of everything the tool wrote for one description (example=NN) or for
    a whole run, plus the run's settings and its catalogue of error-driven
    guidelines, so that a reviewer can keep the traces on their own computer."""
    import tempfile
    import zipfile
    from starlette.background import BackgroundTask
    from fastapi.responses import FileResponse
    run_dir = _orchestrator_run_dir(run)
    folders: list[Path] = []
    if example:
        wanted = str(example).zfill(2)
        folder = run_dir / f"id_{wanted}"
        if not folder.is_dir():
            folder = run_dir / f"id_{example}"
        if not folder.is_dir() or not re.fullmatch(r"[A-Za-z0-9_-]+", str(example)):
            raise HTTPException(404, f"Description {example} has no files in {run_dir.name}")
        folders = [folder]
        what = f"description {wanted} of run {run_dir.name}"
        name = f"{run_dir.name}_id_{wanted}.zip"
    else:
        folders = sorted(p for p in run_dir.glob("id_*") if p.is_dir())
        what = f"run {run_dir.name}"
        name = f"{run_dir.name}.zip"
    models = _json(run_dir / "models.json") if (run_dir / "models.json").is_file() else {}
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    handle.close()
    base = run_dir.name
    with zipfile.ZipFile(handle.name, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr(f"{base}/README.txt", _DOWNLOAD_README.format(what=what))
        for top in run_dir.iterdir():                 # the files of the run itself
            if top.is_file() and (not example or top.name in ("models.json",)):
                bundle.write(top, f"{base}/{top.name}")
        for folder in folders:
            for path in sorted(folder.rglob("*")):
                if path.is_file():
                    bundle.write(path, f"{base}/{folder.name}/{path.relative_to(folder).as_posix()}")
        catalogue = models.get("learned_catalogue")
        if catalogue:
            _orchestrator_run_batch()
            import pipeline_config
            catalogue = pipeline_config.resolve_path(catalogue)
        if catalogue and catalogue.is_file():
            root = catalogue.parent
            for path in sorted(root.rglob("*")):
                if path.is_file() and "archive" not in path.relative_to(root).parts:
                    bundle.write(path, f"{base}/catalogue/{path.relative_to(root).as_posix()}")
    return FileResponse(handle.name, media_type="application/zip", filename=name,
                        background=BackgroundTask(os.remove, handle.name))


@app.get("/api/orchestrator/models", dependencies=[Depends(require_token)])
def orchestrator_models():
    """What the launcher can offer for each component: the two LLMs of the study;
    any other model of the two providers can be typed as provider:model."""
    llm = _orchestrator_llm()
    return {"components": list(llm.COMPONENTS), "defaults": llm.DEFAULT_MODELS,
            "suggestions": ["openai:gpt-6-luna", "anthropic:claude-haiku-5-5"],
            "keys": {"openai": bool(os.getenv("OPENAI_API_KEY", "").strip()),
                     "anthropic": bool(os.getenv("ANTHROPIC_API_KEY", "").strip())}}


@app.get("/api/orchestrator/guidelines", dependencies=[Depends(require_token)])
def orchestrator_guidelines(catalogue: Optional[str] = None):
    """A learned-guidelines catalogue of the final study: one per repetition of the
    learning run and one per round of the cross-validation (the latest by default).
    `catalogues` lists them all."""
    _orchestrator_run_batch()
    import guideline_store
    catalogues = guideline_store.run_catalogues()
    chosen = None
    if catalogue:
        if not re.fullmatch(r"[A-Za-z0-9._-]+/(agents/)?(replicates/r[0-9]+|folds/fold_[0-9]+|trials/trial_[0-9TZ]+)", catalogue):
            raise HTTPException(422, "unknown catalogue")
        chosen = next((c for c in catalogues if c["id"] == catalogue), None)
        if chosen is None:
            raise HTTPException(404, "no such catalogue")
    elif catalogues:
        chosen = catalogues[0]
    data = (json.loads(Path(chosen["file"]).read_text(encoding="utf-8"))
            if chosen else {"guidelines": []})
    data.update(catalogue=chosen["id"] if chosen else None,
                label=chosen["label"] if chosen else None,
                catalogues=[{k: c[k] for k in ("id", "label", "count", "general", "confirmed")}
                            for c in catalogues])
    return data


@app.post("/api/orchestrator/run", dependencies=[Depends(require_token)])
def orchestrator_run(req: OrchestratorRunRequest):
    if ORCHESTRATOR["state"] == "running":
        raise HTTPException(409, "A GuideBPMN run is already in progress")
    if req.resume:                    # same settings as the interrupted run
        folder = _orchestrator_run_dir(req.resume)
        settings = _json(folder / "models.json")
        if not _unfinished_examples(folder):
            raise HTTPException(409, f"{req.resume} is finished: nothing to resume")
        req = req.model_copy(update={
            "arm": settings.get("arm", req.arm), "dry_run": bool(settings.get("dry_run")),
            "fold": settings.get("fold"), "learn": settings.get("learn", True),
            "force_iterations": bool(settings.get("force_iterations")),
            "replicate": settings.get("replicate"),
            "next_iterations": int(settings.get("next_iterations", req.next_iterations) or 0),
            "promote_confirmed": bool(settings.get("promote_confirmed")),
            "models": settings.get("models") or {}, "limit": None, "sample": None,
            "ids": ",".join((settings.get("examples") or {}).get("ids") or [])})
    if req.arm not in _ORCHESTRATOR_ARMS:
        raise HTTPException(422, f"arm must be one of {_ORCHESTRATOR_ARMS}")
    llm = _orchestrator_llm()
    try:
        models = llm.resolve_models(req.models)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    if not req.dry_run:
        used = {"generator", "orchestrator", "retriever", "expert"}
        problems = llm.missing_requirements({k: models[k] for k in used})
        if problems:
            raise HTTPException(503, "; ".join(problems))
    run_batch = _orchestrator_run_batch()
    if req.fold is not None and not req.resume:
        import folds
        if req.arm == "documentation" and req.learn:
            role = "train"
        elif req.arm == "documentation+learned":
            role = "test"
        else:
            raise HTTPException(422, "A round runs as Reuse training (learning) or Reuse test")
        req = req.model_copy(update={"ids": ",".join(folds.fold_ids(req.fold, role)),
                                     "limit": None, "sample": None})
    try:
        _, selection = run_batch.select_examples(
            json.loads(run_batch.DATASET_PATH.read_text(encoding="utf-8")),
            req.limit, req.ids, req.sample, req.seed)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    if not selection["ids"]:
        raise HTTPException(422, "No example selected")
    which = {"all": "all 55", "first": f"first {len(selection['ids'])}",
             "chosen": f"chosen: {', '.join(selection['ids'])}",
             "random": f"random {len(selection['ids'])} (seed {req.seed})"}[selection["mode"]]
    if req.fold is not None:
        which = f"fold {req.fold}, " + ("training" if req.arm == "documentation" else "test") + \
                f" ({len(selection['ids'])} descriptions)"
    # a learning run on a few descriptions is a trial: it learns into a catalogue of
    # its own and never into the catalogues of the study (replicates/rN, folds/fold_k)
    trial = req.trial
    if trial is None:
        trial = bool(req.arm == "documentation" and req.fold is None and not req.dry_run
                     and not req.resume and len(selection["ids"]) < 55)
    if req.resume:
        trial = bool(_json(_orchestrator_run_dir(req.resume) / "models.json").get("trial"))
    version = _version({"arm": req.arm, "learn": req.learn, "fold": req.fold, "replicate": req.replicate,
                        "force_iterations": req.force_iterations, "trial": trial})["version"] + \
        (f" r{req.replicate}" if req.replicate and not trial else "")
    label = ("dry run" if req.dry_run else f"{models['generator']} / {version}") + f" / {which}" + \
            (f" / resumed {req.resume}" if req.resume else "")
    ORCHESTRATOR.update(state="running", label=label, progress=[], report=None, validator_performance=None,
                 report_after_rule_feedback=None, error=None, started=time.time(), ids=[], examples={},
                 run_dir=None, limits=None, failure_rule=None, promote_confirmed=None,
                 metrics_summary=None)

    def observe(event: dict):
        kind = event.get("type")
        if kind == "start":
            ORCHESTRATOR["ids"] = event["ids"]
            ORCHESTRATOR["run_dir"] = event["run_dir"]
            ORCHESTRATOR["limits"] = event.get("limits")
            ORCHESTRATOR["failure_rule"] = event.get("failure_rule")
            ORCHESTRATOR["promote_confirmed"] = event.get("promote_confirmed")
        elif kind == "iteration":
            ex = ORCHESTRATOR["examples"].setdefault(
                event["id"], {"iterations": [], "valid": None})
            ex["iterations"].append({k: event.get(k) for k in
                                      ("round", "kind", "valid", "failed_levels", "metrics",
                                       "seconds")})
        elif kind == "rule_feedback":
            ex = ORCHESTRATOR["examples"].setdefault(
                event["id"], {"iterations": [], "valid": None})
            ex["rules_sent_back"] = event["rules"]
        elif kind == "decision":
            ex = ORCHESTRATOR["examples"].setdefault(
                event["id"], {"iterations": [], "valid": None})
            ex.setdefault("decisions", []).append(
                {"action": event["action"], "reason": event["reason"],
                 "allowed": event.get("allowed", [])})
        elif kind == "guideline":
            ex = ORCHESTRATOR["examples"].setdefault(
                event["id"], {"iterations": [], "valid": None})
            ex.setdefault("guidelines", []).append(
                {k: event.get(k) for k in ("failure_type", "status", "detail",
                                           "guideline_id", "trigger", "instruction")})
        elif kind == "example":
            ex = ORCHESTRATOR["examples"].setdefault(event["id"], {"iterations": []})
            ex.update(valid=event["valid"], kept_round=event["kept_round"],
                      metrics=event["metrics"], rounds=event["rounds"],
                      stopped=event.get("stopped"), detected=event.get("detected", []),
                      revised=event.get("revised", False),
                      first_pass_metrics=event.get("first_pass_metrics"))
            if ORCHESTRATOR.get("run_dir"):
                ex["score"] = _score(Path(ORCHESTRATOR["run_dir"]) / f"id_{event['id']}")

    def work():
        try:
            run_batch = _orchestrator_run_batch()
            info = run_batch.run_arm(
                arm=req.arm, dry_run=req.dry_run, limit=req.limit, models=models,
                ids=req.ids, sample=req.sample, seed=req.seed, resume=req.resume,
                confirmed_only=req.confirmed_only, fresh_catalogue=req.fresh_catalogue,
                next_iterations=req.next_iterations,
                failure_rule=req.failure_rule, promote_confirmed=req.promote_confirmed,
                learn=req.learn, fold=req.fold,
                force_iterations=req.force_iterations, replicate=req.replicate,
                trial=trial,
                limits={"max_agent_decisions": req.max_agent_decisions,
                        "max_tool_calls": req.max_tool_calls},
                progress=lambda line: ORCHESTRATOR["progress"].append(str(line)),
                observer=observe,
            )
            ORCHESTRATOR["progress"].append(f"report: {info['run_dir']}")
            ORCHESTRATOR["validator_performance"] = _validator_performance(Path(info["run_dir"]))
            ORCHESTRATOR["metrics_summary"] = _metrics_summary(Path(info["run_dir"]))
            ORCHESTRATOR.update(state="done", report=info["report"],
                         report_after_rule_feedback=info.get("report_after_rule_feedback"))
        except Exception as exc:  # surfaced verbatim in the launcher
            ORCHESTRATOR.update(state="error", error=f"{type(exc).__name__}: {exc}")

    threading.Thread(target=work, daemon=True, name="guidebpmn-run").start()
    return {"started": True, "label": label}

