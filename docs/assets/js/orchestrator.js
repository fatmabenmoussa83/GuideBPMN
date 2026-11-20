/* GuideBPMN launcher and live view: drives /api/orchestrator/* on the local API.
   - launcher: version, examples, one model per component
   - results table: one row per example, filled while the run goes on
   - example view: every draft as a diagram next to the gold reference,
     the metrics of every draft, the orchestrator's decisions, the guideline agents
   - past runs: any run kept on disk can be reopened */
(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  if (!$("orchestratorStart")) return;
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (ch) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]; }); }
  function fmt(x) { return (x === null || x === undefined || x === "") ? "&mdash;" : (typeof x === "number" ? x.toFixed(3) : esc(x)); }

  /* ------------------------------------------------------------ API ---- */
  function remember(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* private mode */ } }
  function recall(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  if (recall("guidebpmn.api")) $("orchestratorApi").value = recall("guidebpmn.api");
  $("orchestratorApi").addEventListener("change", function () { remember("guidebpmn.api", $("orchestratorApi").value.trim()); });

  /* Saved runs: when no local API answers, the page reads the answers it would have given for the
     32 runs of the study, saved with the website (data/saved/, made by docs/_build/export_saved_runs.py). */
  var SAVED = false;
  var REPO = "https://github.com/fatmabenmoussa83/GuideBPMN/tree/main/bpmn_pipeline/runs/";
  var LIVE_ONLY = "This needs GuideBPMN running on your computer: start the API with .\\start_webapi.ps1, then reload the page.";
  function savedFile(path) {
    var q = path.split("?"), p = q[0], params = {};
    (q[1] || "").split("&").forEach(function (kv) { var a = kv.split("="); if (a[0]) params[a[0]] = decodeURIComponent(a[1] || ""); });
    var m;
    if (p === "/api/orchestrator/runs") return "data/saved/runs.json";
    if ((m = p.match(/^\/api\/orchestrator\/runs\/(.+)$/))) return "data/saved/runs/" + decodeURIComponent(m[1]) + "/run.json.gz";
    if ((m = p.match(/^\/api\/orchestrator\/example\/(.+)$/)) && params.run)
      return "data/saved/runs/" + params.run + "/example_" + String(decodeURIComponent(m[1])).padStart(2, "0") + ".json.gz";
    if (p === "/api/orchestrator/study" && params.generator) return "data/saved/study/" + params.generator.replace(":", "-") + ".json";
    if (p === "/api/orchestrator/dataset" || p === "/api/orchestrator/folds" || p === "/api/orchestrator/models")
      return "data/saved/" + p.split("/").pop() + ".json";
    return null;
  }
  function savedApi(path, opts) {
    if (opts.method && opts.method !== "GET") return Promise.reject(new Error(LIVE_ONLY));
    if (path.indexOf("/api/orchestrator/status") === 0)
      return Promise.resolve({ state: "saved runs", label: "no local API: choose one of the study's runs under \u201cOpen a past run\u201d", examples: {} });
    var file = savedFile(path);
    if (!file) return Promise.reject(new Error(LIVE_ONLY));
    return fetch(file).then(function (r) {
      if (!r.ok) throw new Error("not in the saved runs (" + r.status + ")");
      if (!/\.gz$/.test(file)) return r.json();
      if (typeof DecompressionStream === "undefined") throw new Error("this browser cannot open the saved runs; use a recent Chrome, Edge, Firefox or Safari");
      return new Response(r.body.pipeThrough(new DecompressionStream("gzip"))).json();
    });
  }
  function useSaved() {
    if (SAVED) return;
    SAVED = true;
    var note = $("orchestratorSavedNote");
    if (note) note.style.display = "";
    ["orchestratorStart", "orchestratorResume", "orchestratorRescore", "cvSave", "oneStart"].forEach(function (id) {
      var b = $(id);
      if (b) { b.disabled = true; b.title = LIVE_ONLY; }
    });
    var dl = $("orchestratorDownloadRun");
    if (dl) dl.innerHTML = '<i class="fab fa-github mr-1"></i>Open the run\u2019s files';
    var dx = $("orchestratorDownloadExample");
    if (dx) dx.innerHTML = '<i class="fab fa-github mr-1"></i>Open this description\u2019s files';
    window.setTimeout(function () { var s = $("cvShow"); if (s && $("cvGenerator").value) s.click(); }, 1500);
  }
  function api(path, opts) {
    opts = opts || {};
    if (SAVED) return savedApi(path, opts);
    var base = ($("orchestratorApi").value.trim() || "http://127.0.0.1:8765").replace(/\/$/, "");
    var headers = { "Content-Type": "application/json" };
    var token = $("orchestratorToken").value.trim();
    if (token) headers["X-API-Token"] = token;
    return fetch(base + path, { method: opts.method || "GET", headers: headers, body: opts.body })
      .then(function (r) {
        if (!r.ok) return r.json().catch(function () { return {}; }).then(function (d) {
          throw new Error(d.detail || ("HTTP " + r.status));
        });
        return r.json();
      }, function (e) {                       // no API answered: show the saved runs of the study
        if (opts.method && opts.method !== "GET") throw new Error(LIVE_ONLY);
        useSaved();
        return savedApi(path, opts);
      });
  }

  /* ------------------------------------------------------- vocabulary -- */
  var METRICS = [
    ["activity_semantic_similarity", "Activities"], ["semantic_similarity", "All labels"], ["workflow_order_similarity", "Flow order"],
    ["connection_f1", "Connections F1"], ["collaboration_similarity", "Participants"],
    ["alignment_coverage", "Coverage"]];
  var KIND = { draft: "first draft", rule_feedback: "next iteration (guidelines sent back)" };
  var OTHER_KIND = "draft from the validator report";
  var OUTCOME = { promoted: "promoted", merged_with_learned: "merged", existing_documentation_rule: "rule not applied",
                  abstained: "abstained", no_evidence_selected: "no evidence", agent_error: "agent error",
                  rejected_bad_citation: "rejected", rejected_incomplete: "rejected", rejected_reference_label: "rejected",
                  rejected_too_specific: "too specific", rejected_contradicts_documentation: "contradicts documentation", example_specific: "example-specific",
                  generalized: "generalized" };

  /* ---------------------------------------------------- run summaries -- */
  var LEVEL_NAME = { L1: "L1 · Syntax & schema", L2: "L2 · Gateways", L3: "L3 · Sequence flows", L4: "L4 · Collaboration (pools, lanes, message flows)" };

  /* validator performance of a run: per level, examples and elements, first draft and kept draft */
  function renderValidator(perf) {
    var box = $("orchestratorValidator");
    if (!perf || !perf.first_draft) { box.style.display = "none"; return; }
    function rows(part) {
      return ["L1", "L2", "L3", "L4"].map(function (l) {
        var b = part[l] || {}, pe = b.per_example_accuracy || {};
        return "<tr><td>" + LEVEL_NAME[l] + "</td><td class=\"text-right\">" + b.examples_pass + "</td><td class=\"text-right\">" + b.examples_fail +
          "</td><td class=\"text-right\">" + b.examples_not_applicable + "</td><td class=\"text-right\">" + b.elements_correct +
          "</td><td class=\"text-right\">" + b.elements_incorrect + "</td><td class=\"text-right font-weight-bold\">" + fmt(b.accuracy) +
          "</td><td class=\"text-right\">" + fmt(pe.mean) + "</td><td class=\"text-right\">" + fmt(pe.min) + "</td><td class=\"text-right\">" + fmt(pe.max) + "</td></tr>";
      }).join("");
    }
    var head = '<thead><tr><th>level</th><th class="text-right">examples pass</th><th class="text-right">fail</th><th class="text-right">not applicable</th>' +
      '<th class="text-right">elements correct</th><th class="text-right">incorrect</th><th class="text-right">precision</th>' +
      '<th class="text-right">per example: mean</th><th class="text-right">min</th><th class="text-right">max</th></tr></thead>';
    function table(title, part) {
      return '<p class="small font-weight-bold mb-1">' + title + '</p><div class="table-responsive"><table class="table table-sm table-striped small mb-2">' +
        head + "<tbody>" + rows(part) + "</tbody></table></div>";
    }
    box.innerHTML = table("Structural validator, element by element — first draft", perf.first_draft) +
      table("Structural validator, element by element — kept draft", perf.kept_draft) +
      '<p class="small text-muted mb-0">Precision = correct elements (TP) ÷ (correct + incorrect elements, TP + FP) of the level, over the examples where it applies. ' +
      "The full list of incorrect elements, with their reason, is in validator_performance.json in the run folder.</p>";
    box.style.display = "";
  }

  /* validator levels of one draft, with the incorrect elements and why */
  function draftValidator(it) {
    var v = it && it.validator_levels;
    if (!v) { $("orchestratorDraftValidator").innerHTML = '<p class="small text-muted mb-0">Not available for this draft.</p>'; return; }
    $("orchestratorDraftValidator").innerHTML = '<table class="table table-sm small mb-0"><thead><tr><th>level</th><th>result</th>' +
      '<th class="text-right">correct</th><th class="text-right">incorrect</th><th class="text-right">precision</th><th>incorrect elements (why)</th></tr></thead><tbody>' +
      ["L1", "L2", "L3", "L4"].map(function (l) {
        var b = v[l] || {};
        var result = b.result === true ? '<span class="text-success">pass</span>' : b.result === false ? '<span class="text-danger">fail</span>' : '<span class="text-muted">not applicable</span>';
        var bad = (b.incorrect_elements || []).map(function (e) {
          return esc((e.tag || "") + " " + (e.id || "")) + (e.reason ? ' <span class="text-muted">(' + esc(e.reason) + ")</span>" : "");
        }).join("; ");
        return "<tr><td>" + LEVEL_NAME[l] + "</td><td>" + result + '</td><td class="text-right">' + (b.result == null ? "&mdash;" : b.correct) +
          '</td><td class="text-right">' + (b.result == null ? "&mdash;" : b.incorrect) + '</td><td class="text-right">' + fmt(b.accuracy) + "</td><td>" + (bad || "&mdash;") + "</td></tr>";
      }).join("") + "</tbody></table>";
  }

  function reportTable(report, title) {
    var m = report.metrics || {};
    var v = report.validator || {};
    var rows = Object.keys(m).filter(function (k) { return m[k] && m[k].n; }).map(function (k) {
      var s = m[k];
      return "<tr><td>" + esc(k) + "</td><td>" + s.n + "</td><td>" + fmt(s.mean) + "</td><td>" + fmt(s.std) +
             "</td><td>" + fmt(s.min) + "</td><td>" + fmt(s.median) + "</td><td>" + fmt(s.max) + "</td></tr>";
    }).join("");
    return '<p class="small font-weight-bold mb-1">' + esc(title) + "</p>" +
      '<p class="small mb-2"><strong>Structural validator:</strong> ' + v.valid_count + "/" + v.total +
      " valid (" + fmt(v.overall_valid_rate) + ") &middot; pass rates L1 " + fmt(v.L1_pass_rate) +
      " &middot; L2 " + fmt(v.L2_pass_rate) + " &middot; L3 " + fmt(v.L3_pass_rate) + " &middot; L4 " + fmt(v.L4_pass_rate) + "</p>" +
      '<div class="table-responsive"><table class="table table-sm table-striped small mb-0"><thead><tr><th>metric</th><th>n</th><th>mean</th>' +
      "<th>std</th><th>min</th><th>median</th><th>max</th></tr></thead><tbody>" + rows + "</tbody></table></div>";
  }

  /* First pass = before any documentation guideline was sent back. The second
     table appears only when a second iteration ran on at least one example. */
  function renderReport(report, after) {
    if (!report) { $("orchestratorReport").style.display = "none"; return; }
    var html = reportTable(report, after ? "First pass (before any guideline was sent back)" : "Aggregate over the run");
    if (after) {
      html += '<div class="mt-3">' + reportTable(after,
        "After the next iterations (guidelines sent back) — examples revised: " +
        (after.revised_examples || []).join(", ")) + "</div>";
    }
    $("orchestratorReport").innerHTML = html;
    $("orchestratorReport").style.display = "";
  }

  /* ---------------------------------------------- example-by-example -- */
  var lastStatus = null;
  function isDone(e) { return !!e && (!!e.stopped || e.valid === true || e.valid === false); }
  function runningId(status) {
    var ids = status.ids || [], ex = status.examples || {};
    if (status.state !== "running") return null;
    for (var i = 0; i < ids.length; i++) { if (!isDone(ex[ids[i]])) return ids[i]; }
    return null;
  }

  function guidelineSummary(list) {
    if (!list || !list.length) return "&mdash;";
    var count = {};
    list.forEach(function (g) { var k = OUTCOME[g.status] || g.status; count[k] = (count[k] || 0) + 1; });
    return Object.keys(count).map(function (k) {
      var cls = k === "promoted" || k === "merged" || k === "generalized" ? "text-success"
              : k === "rule not applied" ? "text-warning" : k === "example-specific" ? "text-info" : "text-muted";
      return '<span class="' + cls + '">' + count[k] + " " + esc(k) + "</span>";
    }).join(" &middot; ");
  }

  function scoreCell(e) {
    var s = e.score;
    if (!s) return "&mdash;";
    return '<span class="text-success">+' + s.total_bonus + '</span> / <span class="text-danger">&minus;' + s.total_penalty +
      "</span> = <strong>" + (s.utility > 0 ? "+" : "") + s.utility + "</strong>";
  }

  /* bonuses and penalties of one example: one row per step that detected or resolved errors */
  function utilityTable(doc) {
    var u = doc.utility;
    if (!u || !u.steps || !u.steps.length) return '<p class="small text-muted mb-0">No step scored yet.</p>';
    var names = function (list, counts) {
      if (!list || !list.length) return "&mdash;";
      return esc(list.map(function (k) { var n = counts && counts[k]; return n > 1 ? k + " ×" + n : k; }).join(", "));
    };
    var open = u.open_error_counts || {};
    var rows = u.steps.map(function (s) {
      return "<tr><td>" + esc(s.step) + "</td><td>" + esc(s.action) + (s.draft != null ? " (draft " + esc(s.draft) + ")" : "") + "</td>" +
        '<td class="text-danger">' + names(s.detected, s.detected_counts) + '</td><td class="text-success">' + names(s.resolved, s.resolved_counts) + "</td>" +
        '<td class="text-right">' + (s.utility > 0 ? "+" : "") + esc(s.utility) + '</td><td class="text-right">' +
        (s.cumulative_utility > 0 ? "+" : "") + esc(s.cumulative_utility) + "</td></tr>";
    }).join("");
    return '<div class="table-responsive"><table class="table table-sm small mb-1"><thead><tr><th>#</th><th>step</th>' +
      "<th>errors found (penalty &minus;1 each)</th><th>errors gone (bonus +1 each)</th>" +
      '<th class="text-right">utility</th><th class="text-right">total</th></tr></thead><tbody>' + rows + "</tbody></table></div>" +
      '<p class="small mb-0">Bonuses <span class="text-success">+' + esc(u.total_bonus) + '</span>, penalties <span class="text-danger">&minus;' +
      esc(u.total_penalty) + "</span>, utility <strong>" + (u.utility > 0 ? "+" : "") + esc(u.utility) + "</strong>" +
      (u.open_errors && u.open_errors.length ? " &middot; still open: " + names(u.open_errors, open) : " &middot; nothing left open") +
      '.<br><span class="text-muted">Every single error counts; &ldquo;T3 ×2&rdquo; means two errors of type T3. T1&ndash;T4: one incorrect element of a validator level; ' +
      "O: one unmet requirement; T5: one sequence flow missing or additional; T6: one activity without a partner; T7: one pool, lane or message flow missing or additional. " +
      "The orchestrator sees the number of errors still open, per type, and uses it to decide whether to learn and iterate again.</span></p>";
  }

  /* what each next iteration changed, and whether it confirms the guidelines sent in it */
  function effectsList(doc) {
    var list = doc.next_iterations;
    if (!list || !list.length) return "";
    return '<p class="small font-weight-bold mt-3 mb-1">Effect of each next iteration</p><ul class="small mb-0">' +
      list.map(function (e) {
        if (e.mean_change == null) return "<li>Next iteration " + esc(e.iteration) + ": running</li>";
        return "<li>Next iteration " + esc(e.iteration) + " &mdash; sent " + esc((e.sent || []).join(", ") || "nothing new") +
          "; errors of each guideline's type " + Object.keys(e.type_results || {}).map(function (id) {
            var r = e.type_results[id]; return esc(id) + " " + esc(r.failure_type) + " " + r.errors_before + "&rarr;" + r.errors_after;
          }).join(", ") + " &rarr; " +
          (e.confirmed ? '<span class="text-success font-weight-bold">confirmed</span>'
                       : '<span class="text-muted">not confirmed</span>') +
          (e.reverted ? ' <span class="text-warning font-weight-bold">not kept</span>: draft ' + esc(e.reverted.draft) + " had more errors than before (" +
            Object.keys(e.reverted.errors).reduce(function (n, k) { return n + e.reverted.errors[k]; }, 0) + " against " +
            Object.keys(e.reverted.errors_before).reduce(function (n, k) { return n + e.reverted.errors_before[k]; }, 0) +
            "), so the previous model was kept" : "") +
          (e.detected_after ? "; still detected after it: " + esc(e.detected_after.join(", ") || "nothing") : "") +
          (e.promoted || []).map(function (p) {
            return "<br>" + esc(p.specific_id) + (p.status === "promoted_after_confirmation"
              ? ' <span class="text-success">written in general terms as ' + esc(p.guideline_id) + "</span>"
              : p.status === "merged_with_learned" ? " same as " + esc(p.guideline_id) + " in general terms"
              : ' <span class="text-muted">kept for this example only (' + esc(p.detail || p.status) + ")</span>");
          }).join("") + "</li>";
      }).join("") + '</ul><p class="small text-muted mb-0">Confirmed = the errors of the guideline&rsquo;s own type decreased and the new model was kept.</p>';
  }

  function renderTable(status) {
    var ids = status.ids || [], ex = status.examples || {};
    if (!ids.length) { $("orchestratorResults").style.display = "none"; return; }
    $("orchestratorResults").style.display = "";
    var running = runningId(status);
    var done = ids.filter(function (id) { return isDone(ex[id]); }).length;
    $("orchestratorResultsTitle").textContent = "Results, example by example — " + done + " of " + ids.length + " done" +
      (status.label ? " · " + status.label : "");
    var lim = status.limits;
    $("orchestratorBudgets").style.display = lim ? "" : "none";
    if (lim) $("orchestratorBudgets").textContent = "Budgets of this run, per example: " + lim.next_iterations +
      " next iteration" + (lim.next_iterations === 1 ? "" : "s") +
      ", " + lim.max_tool_calls + " tool calls, " + lim.max_agent_decisions + " orchestrator decisions." +
      (status.promote_confirmed ? " Confirmed example-specific guidelines are turned into generic ones." : "");
    $("orchestratorTableBody").innerHTML = ids.map(function (id) {
      var e = ex[id] || {}, its = e.iterations || [], last = its[its.length - 1];
      var state;
      if (isDone(e)) state = e.valid ? '<span class="text-success font-weight-bold">valid</span>'
                                     : '<span class="text-danger font-weight-bold">invalid</span>';
      else if (id === running) state = '<span class="text-primary"><i class="fas fa-spinner fa-spin mr-1"></i>running</span>';
      else state = status.state === "running" ? '<span class="text-muted">waiting</span>' : '<span class="text-muted">not run</span>';
      var m = isDone(e) ? (e.metrics || (last || {}).metrics || {}) : ((last || {}).metrics || {});
      var cells = METRICS.map(function (pair) {
        return '<td class="text-right' + (isDone(e) ? "" : " font-italic text-muted") + '">' + fmt(m[pair[0]]) + "</td>";
      }).join("");
      var second = e.revised
        ? "yes" + (e.first_pass_metrics ? ": " + fmt(e.first_pass_metrics.semantic_similarity) + " &rarr; " + fmt(m.semantic_similarity) : "")
        : (isDone(e) ? "no" : "&mdash;");
      var drafts = its.map(function (it) {
        return '<span class="' + (it.valid ? "text-success" : "text-danger") + '">' + it.round + (it.valid ? "✓" : "✗") + "</span>";
      }).join(" ");
      return '<tr class="orchestrator-row' + (id === shownId ? " table-active" : "") + '" data-id="' + esc(id) + '" style="cursor:pointer">' +
        "<td><strong>" + esc(id) + "</strong></td><td>" + state + "</td><td>" + (drafts || "&mdash;") + "</td>" + cells +
        "<td>" + esc((e.detected || []).join(", ") || (isDone(e) ? "none" : "")) + "</td>" +
        "<td>" + guidelineSummary(e.guidelines) + "</td><td>" + second + "</td>" + '<td class="text-right text-nowrap">' + scoreCell(e) + "</td>" +
        '<td class="text-right">' + (last && last.seconds != null ? Math.round(last.seconds) + " s" : "&mdash;") + "</td></tr>";
    }).join("");
  }

  /* ------------------------------------------------------- diagrams ---- */
  var viewers = {};
  function viewer(which) {
    if (!window.BpmnJS) return null;
    if (!viewers[which]) viewers[which] = new BpmnJS({ container: which });
    return viewers[which];
  }
  function fit(which) {
    var v = viewers[which];
    if (!v) return;
    try { var c = v.get("canvas"); c.resized(); c.zoom("fit-viewport", "auto"); } catch (e) { /* empty diagram */ }
  }
  function showXml(which, xml, note) {
    var v = viewer(which);
    var box = document.querySelector(which + "Note");
    if (box) box.textContent = note || "";
    if (!v) return;
    if (!xml) { v.clear(); if (box) box.textContent = "No XML for this draft."; return; }
    v.importXML(xml).then(function () { fit(which); })
      .catch(function (err) { if (box) box.textContent = "This XML cannot be drawn: " + (err && err.message ? err.message : err); });
  }
  window.addEventListener("resize", function () { fit("#orchestratorCanvasGen"); fit("#orchestratorCanvasGold"); });
  document.addEventListener("fullscreenchange", function () { window.setTimeout(function () { fit("#orchestratorCanvasGen"); fit("#orchestratorCanvasGold"); }, 150); });

  /* ------------------------------------------------------ example view -- */
  var shownId = null, shownSignature = null, current = null, shownDraft = null;

  function signature(e) {
    if (!e) return "";
    return (e.iterations || []).length + "|" + (e.stopped || "") + "|" + (e.guidelines || []).length +
           "|" + ((e.decisions || []).length);
  }

  function openExample(id, keepDraft) {
    var run = viewRun ? "?run=" + encodeURIComponent(viewRun) : "";
    return api("/api/orchestrator/example/" + encodeURIComponent(id) + run).then(function (doc) {
      var previous = shownId === id && keepDraft ? shownDraft : null;
      shownId = id;
      shownSignature = lastStatus ? signature((lastStatus.examples || {})[id]) : null;
      renderDetail(doc, previous);
      document.querySelectorAll(".orchestrator-row").forEach(function (row) {
        row.classList.toggle("table-active", row.getAttribute("data-id") === id);
      });
    }).catch(function (e) {
      shownId = id;
      shownSignature = lastStatus ? signature((lastStatus.examples || {})[id]) : null;
      $("orchestratorDetail").style.display = "";
      $("orchestratorDetailTitle").textContent = "Example " + id;
      $("orchestratorDetailBody").style.display = "none";
      $("orchestratorDetailWait").style.display = "";
      $("orchestratorDetailWait").textContent = e.message.indexOf("no validated draft") >= 0
        ? "Example " + id + " is running: its first draft appears here as soon as the validator has checked it."
        : e.message;
    });
  }

  /* ------------------------------------------- step-by-step timeline -- */
  var TOOL_WORDS = { list_evidence: "lists the evidence records of one kind", search_evidence: "searches the evidence by words",
    find_counterparts: "looks for a generated element that may be the missing one modeled differently",
    read_description: "reads the full process description", find_closest_documented_guidelines: "retrieves the 6 closest documentation guidelines (embedding cosine)",
    find_closest_learned_guidelines: "retrieves the 4 closest error-driven guidelines (embedding cosine)", check_wording: "checks whether a wording is tied to this one process" };
  function argText(args) {
    if (!args || typeof args !== "object") return "";
    return Object.keys(args).map(function (k) { return k + ": " + JSON.stringify(args[k]); }).join(", ");
  }
  function resultText(r) {
    if (r == null) return "";
    if (Array.isArray(r)) return r.length + " record" + (r.length === 1 ? "" : "s") + (r.length ? " (" + r.slice(0, 8).map(function (x) { return x.id || x; }).join(", ") + (r.length > 8 ? ", …" : "") + ")" : "");
    if (typeof r === "object") {
      if (r.error) return "error: " + r.error;
      if (r.process_description) return "the description (" + r.process_description.length + " characters)";
      if (r.tied_to_this_process != null) return r.tied_to_this_process ? "tied to this process by: " + (r.words || []).join(", ") : "not tied to this process";
      if (r.truncated) return "long result (cut for the agent)";
      return JSON.stringify(r).slice(0, 120);
    }
    return String(r).slice(0, 160);
  }
  function agentSteps(trace, who) {
    if (!trace || !trace.length) return '<li class="text-muted">' + who + ": no tool call</li>";
    return trace.map(function (s) {
      if (!s.tool) return '<li><span class="badge badge-warning">' + esc(who) + " answer sent back</span> " + esc(String(s.result || s.reason)) + "</li>";
      return "<li><strong>" + esc(who) + "</strong> calls <code>" + esc(s.tool) + "</code>(" + esc(argText(s.args)) + ")" +
        (TOOL_WORDS[s.tool] ? ' <span class="text-muted">— ' + TOOL_WORDS[s.tool] + "</span>" : "") +
        " &rarr; " + esc(resultText(s.result)) + (s.reason ? ' <span class="text-muted">· why: ' + esc(s.reason) + "</span>" : "") + "</li>";
    }).join("");
  }
  function learnBlock(outcomes) {
    if (!outcomes || !outcomes.length) return '<div class="small text-muted">No failure type was handed to the agents.</div>';
    return outcomes.map(function (o) {
      var tr = o.agent_trace || {}, cand = o.candidate || {}, rel = cand.relation_answered || {};
      var judged = o.relation_judgement;
      var html = '<details class="mb-2"><summary class="small"><strong>' + esc(o.failure_type) + "</strong> &rarr; " +
        esc(OUTCOME[o.status] || o.status) + (o.guideline_id ? " (" + esc(o.guideline_id) + ")" : o.ref ? " (" + esc(o.ref) + ")" : "") +
        (cand.trigger ? ' <span class="text-muted">· when ' + esc(cand.trigger.slice(0, 90)) + (cand.trigger.length > 90 ? "…" : "") + "</span>" : "") + "</summary>" +
        '<div class="pl-3 small">';
      if (o.learning_mode === "tools" || tr.retriever) {
        html += '<p class="mb-1 font-weight-bold">Retriever agent (ReAct loop, budget 4 tool calls)</p><ol class="mb-1">' + agentSteps(tr.retriever, "Retriever") + "</ol>" +
          "<p class=\"mb-2\">Final answer: selected " + esc((o.retrieved || []).join(", ") || "nothing") +
          (o.added_counterparts && o.added_counterparts.length ? ' <span class="text-muted">(+ counterparts added by code: ' + esc(o.added_counterparts.join(", ")) + ")</span>" : "") +
          (o.retriever_reason ? ' <span class="text-muted">· why: ' + esc(o.retriever_reason) + "</span>" : "") + "</p>";
        (tr.expert || []).forEach(function (run, i) {
          html += '<p class="mb-1 font-weight-bold">Expert agent' + ((tr.expert || []).length > 1 ? ", run " + (i + 1) + (i === 0 ? "" : " (asked again)") : "") +
            " (ReAct loop, budget 6 tool calls)</p><ol class=\"mb-1\">" + agentSteps(run.trace, "Expert") + "</ol>";
        });
      } else {
        html += '<p class="mb-1">Retriever selected ' + esc((o.retrieved || []).join(", ") || "nothing") + (o.retriever_reason ? ' <span class="text-muted">· ' + esc(o.retriever_reason) + "</span>" : "") + "</p>";
      }
      html += '<p class="mb-1"><strong>Expert final answer:</strong> ' + (cand.decision === "propose" || cand.trigger
        ? "propose — <em>when " + esc(cand.trigger || "") + ":</em> " + esc(cand.instruction || "") +
          (cand.cited && cand.cited.length ? ' <span class="text-muted">· cites ' + esc(cand.cited.join(", ")) + "</span>" : "") +
          (rel.relation ? ' <span class="text-muted">· relation answered: ' + esc(String(rel.relation)) + (rel.rule_id ? " " + esc(String(rel.rule_id)) : "") + "</span>" : "")
        : "abstain" + (cand.reason ? " — " + esc(cand.reason) : "")) + "</p>";
      if (o.first_answer) html += '<p class="mb-1 text-muted">First answer: abstain (' + esc(o.first_answer.reason || "") + "); asked once more because the failure remained.</p>";
      if (o.first_wording) html += '<p class="mb-1 text-muted">First wording tied to this process by ' + esc((o.words_to_avoid || []).join(", ")) + ": rewritten once.</p>";
      if (o.contradicted) html += '<p class="mb-1 text-muted">Contradicted ' + esc(o.contradicted.rule_id) + ": returned once to the Expert to be rewritten.</p>";
      html += '<p class="mb-1"><strong>Code guards:</strong> ' + esc(OUTCOME[o.status] || o.status) +
        (judged ? " · relation decided by the Expert: " + esc(judged.relation) + (judged.rule_id ? " " + esc(judged.rule_id) : "") : (o.judged_by === "similarity" ? ' · <span class="text-warning">relation decided by the similarity thresholds (the Expert gave none)</span>' : "")) +
        (o.detail ? ' <span class="text-muted">— ' + esc(o.detail) + "</span>" : "") + "</p>";
      html += '<p class="mb-0"><strong>Catalogue:</strong> ' + (o.status === "promoted" ? "stored as " + esc(o.guideline_id) + (o.relation && o.relation.type ? " (" + esc(o.relation.type) + (o.relation.ref ? " " + esc(o.relation.ref) : "") + ")" : "")
        : o.status === "example_specific" ? "stored as example-specific " + esc(o.guideline_id)
        : o.status === "merged_with_learned" ? "consolidated with " + esc(o.guideline_id || o.ref)
        : o.status === "generalized" ? "one generic guideline " + esc(o.guideline_id)
        : o.status === "existing_documentation_rule" ? "nothing stored; documentation guideline " + esc(o.ref) + " is sent back"
        : "nothing stored") + "</p></div></details>";
      return html;
    }).join("");
  }
  function timeline(doc) {
    var ag = doc.agent || {}, decisions = ag.decisions || [];
    if (!decisions.length) return '<p class="small text-muted mb-0">No decision yet.</p>';
    var its = doc.iterations || [], nexts = doc.next_iterations || [], fp = doc.first_pass || {};
    var history = doc.guideline_learning_history || null;
    var draft = -1, learnCalls = 0, reviseCalls = 0, html = '<ol class="small mb-0">';
    decisions.forEach(function (d) {
      var what = "";
      var it = its[draft] || {};
      if (d.action === "generate") { draft = 0; it = its[0] || {}; what = "draft 0 written by the generator" + (it.seconds != null ? " (" + Math.round(it.seconds) + " s)" : ""); }
      else if (d.action === "validate") {
        var lv = it.validator_levels || {};
        what = (it.valid ? '<span class="text-success">valid</span>' : '<span class="text-danger">invalid: ' + esc((it.failed_levels || []).join(", ")) + "</span>") +
          " · " + ["L1", "L2", "L3", "L4"].map(function (L) { var b = lv[L] || {}; return L + " " + (b.result == null ? "n/a" : (b.result ? "pass" : "fail") + " (" + (b.correct || 0) + " correct, " + (b.incorrect || 0) + " incorrect)"); }).join("; ");
      }
      else if (d.action === "evaluate") {
        var m = it.metrics || {};
        what = "activities F1 " + fmt(m.activity_label_f1) + " · connections F1 " + fmt(m.connection_f1) + " · flow order " + fmt(m.workflow_order_similarity) +
          " · element coverage " + fmt(m.alignment_coverage) + " · participants " + (m.collaboration_similarity == null ? "n/a" : fmt(m.collaboration_similarity));
      }
      else if (d.action === "detect_failures") {
        var det, err;
        if (draft === 0) { det = fp.detected || ag.first_pass_detected_failures || []; err = fp.error_counts || ag.first_pass_error_counts || {}; }
        else { var e = nexts[draft - 1] || {}; det = e.detected_after || []; err = e.errors_after || {}; }
        what = "failure types " + esc(det.join(", ") || "none") + " · errors " + esc(Object.keys(err).map(function (k) { return k + " " + err[k]; }).join(", ") || "0");
      }
      else if (d.action === "learn") {
        var outcomes = history ? ((history[learnCalls] || {}).outcomes || []) : (learnCalls === 0 && !nexts.length ? doc.guideline_learning : null);
        learnCalls += 1;
        what = "the guideline agents run on the detected failure types" +
          (outcomes ? ':<div class="mt-1">' + learnBlock(outcomes) + "</div>" : ' <span class="text-muted">(the trace of this learn call was not kept: only the last one, shown in the guidelines panel)</span>');
      }
      else if (d.action === "revise") {
        var n = nexts[reviseCalls] || {}; reviseCalls += 1; draft += 1;
        what = "next iteration " + (n.iteration || reviseCalls) + ": sent back " + esc((n.sent || []).join(", ") || "the documentation guidelines not applied") + " &rarr; draft " + draft +
          (n.valid_kept != null ? " · kept model: " + (n.kept_round != null ? "draft " + n.kept_round : "") + (n.confirmed ? ', <span class="text-success">confirmed</span>' : ", not confirmed") : "");
      }
      else if (d.action.indexOf("stop") === 0) what = esc(ag.stop_reason || d.reason || "");
      html += "<li><strong>" + esc(d.action) + "</strong>" + (d.allowed && d.allowed.length > 1 ? ' <span class="badge badge-primary">chose among ' + esc(d.allowed.join(" / ")) + "</span>" : "") +
        (d.reason && d.action.indexOf("stop") !== 0 ? ' <span class="text-muted">— ' + esc(d.reason) + "</span>" : "") + "<br>" + what + "</li>";
    });
    return html + "</ol>";
  }

  function renderDetail(doc, keepDraft) {
    current = doc;
    $("orchestratorDetail").style.display = "";
    $("orchestratorDetailWait").style.display = "none";
    $("orchestratorDetailBody").style.display = "";
    var ag = doc.agent || {};
    var stateText = doc.live ? "running" : (ag.stopped || "done");
    $("orchestratorDetailTitle").textContent = "Example " + doc.id + " — " + stateText +
      (doc.kept_round != null && !doc.live ? " · kept draft " + doc.kept_round : "") +
      (ag.agent && ag.agent !== "running" ? " · orchestrator: " + ag.agent : "");
    $("orchestratorDescription").textContent = doc.description || "";

    /* draft buttons */
    $("orchestratorIterTabs").innerHTML = doc.iterations.map(function (it, i) {
      return '<button class="btn btn-sm ' + (it.valid ? "btn-outline-success" : "btn-outline-danger") +
        ' mr-1 mb-1 orchestrator-iter" data-i="' + i + '">' +
        (it.kind === "rule_feedback" ? "next iteration · draft " : "draft ") + it.round +
        (it.valid ? " ✓" : " ✗ " + (it.failed_levels || []).join(",")) +
        (it.unmet && it.unmet.length ? " · " + it.unmet.length + " unmet" : "") +
        (it.round === doc.kept_round && !doc.live ? " · kept" : "") + "</button>";
    }).join("");

    /* metrics of every draft */
    var head = "<tr><th>metric</th>" + doc.iterations.map(function (it) {
      return '<th class="text-right">draft ' + it.round + (it.kind === "rule_feedback" ? " (next it.)" : it.kind !== "draft" ? " (validator report)" : "") + "</th>";
    }).join("") + "</tr>";
    var rows = METRICS.map(function (pair) {
      return "<tr><td>" + esc(pair[0]) + "</td>" + doc.iterations.map(function (it) {
        return '<td class="text-right">' + fmt((it.metrics || {})[pair[0]]) + "</td>";
      }).join("") + "</tr>";
    }).join("");
    var validity = "<tr><td>validator</td>" + doc.iterations.map(function (it) {
      return '<td class="text-right ' + (it.valid ? "text-success" : "text-danger") + '">' +
        (it.valid ? "valid" : "invalid " + esc((it.failed_levels || []).join(","))) + "</td>";
    }).join("") + "</tr>";
    $("orchestratorDraftMetrics").innerHTML = '<table class="table table-sm small mb-0"><thead>' + head +
      "</thead><tbody>" + validity + rows + "</tbody></table>";
    var fp = doc.first_pass;
    $("orchestratorFirstPass").innerHTML = fp && fp.metrics
      ? "First pass (before the guidelines were sent back): draft " + esc(fp.kept_round) + ", " +
        (fp.valid ? "valid" : "invalid") + ", semantic " + fmt(fp.metrics.semantic_similarity) +
        ", failures " + esc((fp.detected || []).join(", ") || "none") + "."
      : "";

    /* orchestrator decisions */
    var steps = (ag.decisions || []).map(function (d) {
      var choice = d.allowed && d.allowed.length > 1;
      return "<li" + (choice ? ' class="font-weight-bold"' : "") + ">" + esc(d.action) +
        (choice ? ' <span class="badge badge-primary">agent chose among ' + esc(d.allowed.join(" / ")) + "</span>" : "") +
        (d.fallback ? ' <span class="badge badge-warning">default</span>' : "") +
        ' <span class="font-weight-normal text-muted">&mdash; ' + esc(d.reason) + "</span></li>";
    }).join("");
    $("orchestratorAgentSteps").innerHTML = steps ? '<ol class="small mb-0">' + steps + "</ol>"
      : '<p class="small text-muted mb-0">No decision yet.</p>';
    $("orchestratorTimeline").innerHTML = timeline(doc);
    $("orchestratorUtility").innerHTML = utilityTable(doc);
    $("orchestratorDetected").textContent = (ag.detected_failures && ag.detected_failures.length)
      ? "Detected failures: " + ag.detected_failures.join(", ") : "";

    /* guideline agents */
    var learned = doc.guideline_learning || [];
    var fb = doc.rule_feedback;
    $("orchestratorGuidelines").innerHTML = (learned.length
      ? '<div class="table-responsive"><table class="table table-sm small mb-2"><thead><tr><th>failure</th>' +
        "<th>outcome</th><th>guideline (when &hellip; : do &hellip;)</th><th>why</th></tr></thead><tbody>" +
        learned.map(function (o) {
          var cand = o.candidate || {};
          var ok = o.status === "promoted" || o.status === "merged_with_learned" || o.status === "generalized";
          return "<tr><td>" + esc(o.failure_type) + '</td><td class="' + (ok ? "text-success" : o.status === "existing_documentation_rule" ? "text-warning" : "text-muted") +
            '">' + esc(OUTCOME[o.status] || o.status) + (o.guideline_id ? " (" + esc(o.guideline_id) + ")" : o.ref ? " (" + esc(o.ref) + ")" : "") + "</td><td>" +
            (cand.trigger ? "<em>When " + esc(cand.trigger) + ":</em> " + esc(cand.instruction) : "&mdash;") +
            "</td><td>" + esc(o.detail || "") + "</td></tr>";
        }).join("") + "</tbody></table></div>"
      : '<p class="small text-muted mb-2">' + (doc.live ? "The guideline agents have not run yet." : "No failure was handed to the guideline agents.") + "</p>") +
      (fb && fb.rules && fb.rules.length
        ? '<p class="small font-weight-bold mb-1">Next iteration &mdash; guidelines sent back to the generator</p>' +
          '<ul class="small mb-0">' + fb.rules.map(function (r) {
            return "<li><strong>" + esc(r.rule_id) + "</strong> " +
              '<span class="badge badge-light border">' + esc(r.source || "documentation guideline not applied") + "</span> &mdash; " + esc(r.instruction) +
              (r.situation ? ' <span class="text-muted">(where: ' + esc(r.situation) + ")</span>" : "") + "</li>";
          }).join("") + "</ul>" + effectsList(doc)
        : "");

    var index = keepDraft != null && keepDraft < doc.iterations.length ? keepDraft : doc.iterations.length - 1;
    showDraft(index);
    showXml("#orchestratorCanvasGold", doc.gold_display_xml || doc.gold_xml, "");
  }

  function showDraft(i) {
    var it = current && current.iterations[i];
    if (!it) return;
    shownDraft = Number(i);
    document.querySelectorAll(".orchestrator-iter").forEach(function (n, j) { n.classList.toggle("active", j === Number(i)); });
    $("orchestratorDraftInfo").innerHTML = "<strong>Draft " + esc(it.round) + "</strong> &mdash; " + esc(KIND[it.kind] || (it.kind ? OTHER_KIND : "draft")) +
      " &middot; " + (it.valid ? '<span class="text-success">valid (L1–L4)</span>'
                               : '<span class="text-danger">invalid: ' + esc((it.failed_levels || []).join(", ")) + "</span>") +
      (it.seconds != null ? " &middot; " + Math.round(it.seconds) + " s after the start of the example" : "") +
      ((it.metrics || {}).collaboration_ignored
        ? '<br><span class="text-muted">The reference has no pool, lane or message flow: those added by the generator are not counted ' +
          "(strict semantic score, counting them: " + fmt(it.metrics.semantic_similarity_strict) + ").</span>" : "");
    draftValidator(it);
    showXml("#orchestratorCanvasGen", it.display_xml || it.xml,
      it.layout_added ? "The generator gave no diagram positions: a layout was added for display only (the validator and the metrics use the XML as generated)." : "");
  }

  document.addEventListener("click", function (ev) {
    var row = ev.target.closest(".orchestrator-row");
    if (row) { follow(false); openExample(row.getAttribute("data-id")); }
    var tab = ev.target.closest(".orchestrator-iter");
    if (tab) showDraft(tab.getAttribute("data-i"));
    var zoom = ev.target.closest("[data-zoom]");
    if (zoom) {
      var which = zoom.getAttribute("data-target"), v = viewers[which];
      if (!v) return;
      var canvas = v.get("canvas"), how = zoom.getAttribute("data-zoom");
      if (how === "fit") fit(which); else canvas.zoom(canvas.zoom() * (how === "in" ? 1.25 : 0.8));
    }
    var ed = ev.target.closest("[data-edit]");
    if (ed) {
      var pane = document.querySelector(ed.getAttribute("data-target"));
      if (pane) { var on = pane.classList.toggle("editing"); ed.textContent = on ? "Stop editing" : "Edit"; ed.classList.toggle("btn-warning", on); ed.classList.toggle("btn-light", !on); }
      return;
    }
    var fs = ev.target.closest("[data-full]");
    if (fs) {
      var target = document.querySelector(fs.getAttribute("data-full"));
      if (!target) return;
      if (document.fullscreenElement) { document.exitFullscreen(); if (document.fullscreenElement === target) return; }
      var ask = target.requestFullscreen || target.webkitRequestFullscreen;
      if (ask) ask.call(target); else alert("Full screen is not available in this browser.");
      return;
    }
    if (ev.target.closest("#orchestratorStack")) {
      var stacked = $("orchestratorDiagrams").classList.toggle("orchestrator-stacked");
      $("orchestratorStack").textContent = stacked ? "Side by side" : "One above the other";
      setTimeout(function () { fit("#orchestratorCanvasGen"); fit("#orchestratorCanvasGold"); }, 50);
    }
  });

  function follow(on) { if (on !== undefined) $("orchestratorFollow").checked = on; return $("orchestratorFollow").checked; }

  /* ---------------------------------------------------- live polling --- */
  var timer = null, viewRun = null;

  function applyStatus(s) {
    lastStatus = s;
    renderTable(s);
    var ex = s.examples || {};
    if (!viewRun && s.state === "running" && follow()) {
      var id = runningId(s);
      if (id && (id !== shownId || signature(ex[id]) !== shownSignature)) openExample(id, false);
    } else if (shownId && signature(ex[shownId]) !== shownSignature) {
      openExample(shownId, true);
    }
  }

  function poll() {
    if (viewRun) return;
    api("/api/orchestrator/status").then(function (s) {
      $("orchestratorConn").textContent = s.state + (s.label ? " · " + s.label : "");
      if (s.progress && s.progress.length) {
        $("orchestratorLog").style.display = "";
        $("orchestratorLog").textContent = s.progress.join("\n");
        $("orchestratorLog").scrollTop = $("orchestratorLog").scrollHeight;
      }
      applyStatus(s);
      if (s.state === "running") { timer = setTimeout(poll, 2500); return; }
      $("orchestratorStart").disabled = SAVED;
      if (s.state === "error") $("orchestratorConn").innerHTML = '<span class="text-danger">' + esc(s.error || "failed") + "</span>";
      if (s.state === "done") { renderValidator(s.validator_performance); renderReport(s.report, s.report_after_rule_feedback); renderSummary(s.metrics_summary); loadRuns(); }
    }).catch(function (e) {
      $("orchestratorStart").disabled = SAVED;
      $("orchestratorConn").innerHTML = '<span class="text-danger">' + esc(e.message) +
        '</span> &mdash; is the API running? Start it with <code>.\\start_webapi.ps1</code>';
    });
  }

  /* --------------------------------------------------------- past runs - */
  /* run.html#run=<run>&id=<description> opens that run and that description (links of the Compare page). */
  var deepLink = (function () {
    var h = location.hash || "", m = h.match(/run=([^&]+)/), i = h.match(/[#&]id=(\d+)/);
    return m ? { run: decodeURIComponent(m[1]), id: i ? i[1] : null } : null;
  })();
  var pendingId = null;
  function loadRuns() {
    api("/api/orchestrator/runs").then(function (data) {
      var keep = $("orchestratorRuns").value;
      function when(run) {                         // folder names carry the start time in UTC
        var m = run.match(/^batch_(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})/);
        if (!m) return "";
        var d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]));
        return d.toLocaleString([], { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
      }
      function option(r) {
        var state = r.finished ? "finished" : ((r.unfinished || []).length
          ? r.unfinished.length + " to redo: " + r.unfinished.join(", ") : "interrupted");
        var text = r.dry_run
          ? "dry run · " + when(r.run) + " · " + r.examples + " example(s)"
          : r.version + " — " + r.version_meaning + " · " + r.examples + " example" + (r.examples > 1 ? "s" : "") +
            " · " + when(r.run) + " · " + (r.generator || "?") + " · " + state + (r.rescored ? " · re-scored" : "");
        return '<option value="' + esc(r.run) + '" data-finished="' + (r.finished ? "1" : "0") + '">' + esc(text) + "</option>";
      }
      var runs = data.runs || [];
      function is(name) { return function (r) { return !r.dry_run && r.version === name; }; }
      var first = runs.filter(is("First")), revised = runs.filter(is("Revised"));
      var reuse = runs.filter(function (r) { return !r.dry_run && (r.version === "Reuse training" || r.version === "Reuse test"); });
      var trials = runs.filter(function (r) { return !r.dry_run && r.version === "Trial"; });
      var others = runs.filter(function (r) { return !r.dry_run && ["First", "Revised", "Reuse training", "Reuse test", "Trial"].indexOf(r.version) < 0; });
      var dry = runs.filter(function (r) { return r.dry_run; });
      function group(title, list) {
        return list.length ? '<optgroup label="' + esc(title) + '">' + list.map(option).join("") + "</optgroup>" : "";
      }
      $("orchestratorRuns").innerHTML = '<option value="">— this session (live) —</option>' +
        group("First", first) + group("Revised", revised) + group("Reuse (rounds: training and test)", reuse) + group("Trials (a few descriptions, own catalogue)", trials) + group("Other", others) +
        group("Dry runs (no model call)", dry);
      $("orchestratorRuns").value = keep;
      runChoiceChanged();
      fillCvGenerators(runs);
      if (deepLink) {
        var want = deepLink; deepLink = null;
        $("orchestratorRuns").value = want.run;
        if ($("orchestratorRuns").value) { pendingId = want.id; $("orchestratorOpenRun").click(); }
      }
    }).catch(function () { /* API not started yet */ });
  }

  /* Resume is offered for an interrupted run only. */
  function runChoiceChanged() {
    var option = $("orchestratorRuns").options[$("orchestratorRuns").selectedIndex];
    $("orchestratorResume").disabled = !option || !option.value || option.getAttribute("data-finished") === "1";
  }
  $("orchestratorRuns").addEventListener("change", runChoiceChanged);

  $("orchestratorResume").addEventListener("click", function () {
    var run = $("orchestratorRuns").value;
    if (!run) return;
    if (timer) clearTimeout(timer);
    viewRun = null;
    $("orchestratorStart").disabled = true; $("orchestratorResume").disabled = true;
    $("orchestratorReport").style.display = "none"; $("orchestratorDetail").style.display = "none";
    shownId = null; $("orchestratorLog").textContent = "";
    follow(true);
    api("/api/orchestrator/run", { method: "POST", body: JSON.stringify({ resume: run }) })
      .then(function () { $("orchestratorConn").textContent = "resuming " + run; $("orchestratorRuns").value = ""; poll(); })
      .catch(function (e) {
        $("orchestratorStart").disabled = SAVED; runChoiceChanged();
        $("orchestratorConn").innerHTML = '<span class="text-danger">' + esc(e.message) + "</span>";
      });
  });

  /* re-score past runs: the chosen one, or every finished run when none is chosen */
  function followRescore() {
    api("/api/orchestrator/rescore").then(function (s) {
      var last = (s.progress || []).slice(-1)[0] || "";
      if (s.state === "running") {
        $("orchestratorRescoreNote").textContent = "Re-scoring… " + last;
        setTimeout(followRescore, 2000);
      } else if (s.state === "error") {
        $("orchestratorRescoreNote").innerHTML = '<span class="text-danger">' + esc(s.error) + "</span>";
        $("orchestratorRescore").disabled = false;
      } else if (s.state === "done") {
        $("orchestratorRescoreNote").textContent = "Re-scored " + (s.runs || []).length + " run(s). Open a run to see the activities column.";
        $("orchestratorRescore").disabled = false;
        if ($("orchestratorRuns").value) $("orchestratorOpenRun").click();
      }
    }).catch(function (e) { $("orchestratorRescoreNote").textContent = e.message; $("orchestratorRescore").disabled = false; });
  }
  $("orchestratorRescore").addEventListener("click", function () {
    var run = $("orchestratorRuns").value;
    $("orchestratorRescore").disabled = true;
    $("orchestratorRescoreNote").textContent = run ? "Re-scoring " + run + "…" : "Re-scoring every finished run…";
    api("/api/orchestrator/rescore", { method: "POST", body: JSON.stringify(run ? { run: run } : {}) })
      .then(followRescore)
      .catch(function (e) { $("orchestratorRescoreNote").innerHTML = '<span class="text-danger">' + esc(e.message) + "</span>"; $("orchestratorRescore").disabled = false; });
  });

  $("orchestratorOpenRun").addEventListener("click", function () {
    var run = $("orchestratorRuns").value;
    if (timer) clearTimeout(timer);
    shownId = null; $("orchestratorDetail").style.display = "none";
    if (!run) { viewRun = null; poll(); return; }
    viewRun = run;
    api("/api/orchestrator/runs/" + encodeURIComponent(run)).then(function (s) {
      $("orchestratorConn").textContent = "past run · " + s.label;
      $("orchestratorLog").style.display = "none";
      applyStatus(s);
      renderValidator(s.validator_performance);
      renderReport(s.report, s.report_after_rule_feedback);
      renderSummary(s.metrics_summary);
      var want = pendingId; pendingId = null;
      var ids = s.ids || [];
      if (ids.length) openExample(want && ids.indexOf(want) >= 0 ? want : ids[0]);
      if (want) window.setTimeout(function () { $("orchestratorDetail").scrollIntoView({ behavior: "smooth" }); }, 400);
    }).catch(function (e) { $("orchestratorConn").innerHTML = '<span class="text-danger">' + esc(e.message) + "</span>"; });
  });

  /* ---------------------------------------------------------- launcher - */
  /* Which examples: all, the first N, chosen ids, or N drawn at random. */
  function pickChanged() {
    var pick = $("orchestratorPick").value, input = $("orchestratorPickValue");
    $("orchestratorPickValueBox").style.display = pick === "all" ? "none" : "";
    $("orchestratorSeedBox").style.display = pick === "random" ? "" : "none";
    $("orchestratorPickLabel").textContent = pick === "chosen" ? "Example numbers" : "How many";
    input.placeholder = pick === "chosen" ? "24, 38, 41-45" : "3";
    if (pick === "chosen" && /^\d+$/.test(input.value.trim())) input.value = "";
    if (pick !== "chosen" && !/^\d+$/.test(input.value.trim())) input.value = "3";
  }
  $("orchestratorPick").addEventListener("change", pickChanged);
  pickChanged();

  // ---- budgets of one example: read the five fields, and say what they allow
  function budget(id, low, high, fallback) {
    var n = parseInt($(id).value, 10);
    if (isNaN(n)) n = fallback;
    return Math.max(low, Math.min(high, n));
  }
  function budgets() {
    return { next_iterations: budget("orchestratorNext", 0, 10, 3),
             max_tool_calls: budget("orchestratorToolCalls", 10, 400, 40),
             max_agent_decisions: budget("orchestratorDecisions", 10, 400, 48) };
  }
  function budgetNote() {
    var b = budgets(), arm = $("orchestratorArm").value;
    var learns = arm === "revised" || arm === "reuse_train";
    // first pass: generate, validate, evaluate, detect failures (+ learn when the run learns)
    var first = 4 + (learns ? 1 : 0);
    var each = 4;                                        // revise, validate, evaluate, detect
    var between = Math.max(0, b.next_iterations - 1);    // one learn between two next iterations
    var need = first + (learns ? b.next_iterations * each + between : 0);
    var text = "With these values, one description uses at most " + need + " tool calls (" + first +
      " for the first pass" + (learns && b.next_iterations ? " + " + b.next_iterations + " × " + each + " for the next iterations + " + between + " to learn between them" : "") +
      ") and " + (need + 1) + " orchestrator decisions.";
    var short = [];
    if (b.max_tool_calls < need) short.push("tool calls (" + b.max_tool_calls + ")");
    if (b.max_agent_decisions < need + 1) short.push("orchestrator decisions (" + b.max_agent_decisions + ")");
    $("orchestratorBudgetNote").innerHTML = esc(text) + (short.length
      ? ' <span class="text-danger font-weight-bold">The budget of ' + esc(short.join(" and ")) +
        " is lower: an example could be stopped before it finishes. Raise it or lower the iterations.</span>"
      : ' <span class="text-success">The budgets are sufficient.</span>');
  }
  document.querySelectorAll(".orchestrator-budget").forEach(function (input) { input.addEventListener("input", budgetNote); });
  $("orchestratorArm").addEventListener("change", budgetNote);
  budgetNote();

  var oneTrial = false;              // set by "Test one description from zero"
  $("orchestratorStart").addEventListener("click", function () {
    if (timer) clearTimeout(timer);
    viewRun = null; $("orchestratorRuns").value = "";
    $("orchestratorStart").disabled = true;
    $("orchestratorReport").style.display = "none";
    $("orchestratorSummary").style.display = "none";
    $("orchestratorDetail").style.display = "none";
    shownId = null;
    $("orchestratorLog").textContent = "";
    var models = {};
    document.querySelectorAll(".orchestrator-model").forEach(function (select) {
      var name = select.getAttribute("data-component");
      var value = select.value === "__other__" ? $("orchestratorO_" + name).value.trim() : select.value;
      if (value) models[name] = value;
    });
    var version = $("orchestratorArm").value;
    var body = { arm: version === "reuse_test" ? "documentation+learned" : "documentation",
                 dry_run: $("orchestratorDry").checked, models: models, fresh_catalogue: true };
    var chosen = budgets();
    Object.keys(chosen).forEach(function (name) { body[name] = chosen[name]; });
    if (version === "first" || version === "reuse_test") body.next_iterations = 0;
    if (version === "first") body.learn = false;
    if (version === "revised" || version === "reuse_train") { body.force_iterations = true; body.promote_confirmed = true; }
    // a learning run on a few descriptions learns into a trial catalogue of its own
    if (oneTrial || (version === "revised" && $("orchestratorPick").value !== "all")) body.trial = true;
    oneTrial = false;
    if (version === "first" || version === "revised") body.replicate = parseInt($("orchestratorReplicate").value, 10);
    if ((version === "reuse_train" || version === "reuse_test") && !$("orchestratorFold").value) {
      $("orchestratorConn").innerHTML = '<span class="text-danger">Choose the Reuse round (fold).</span>';
      $("orchestratorStart").disabled = SAVED; return;
    }
    var pick = $("orchestratorPick").value, value = $("orchestratorPickValue").value.trim();
    if ((version === "reuse_train" || version === "reuse_test") && $("orchestratorFold").value) {
      body.fold = parseInt($("orchestratorFold").value, 10);           // the fold decides the descriptions
    } else {
      if (pick === "first") body.limit = parseInt(value, 10) || 3;
      if (pick === "chosen") body.ids = value;
      if (pick === "random") {
        body.sample = parseInt(value, 10) || 3;
        body.seed = parseInt($("orchestratorSeed").value, 10) || 42;
      }
    }
    follow(true);
    api("/api/orchestrator/run", { method: "POST", body: JSON.stringify(body) })
      .then(function () { $("orchestratorConn").textContent = "started"; poll(); })
      .catch(function (e) {
        $("orchestratorStart").disabled = SAVED;
        $("orchestratorConn").innerHTML = '<span class="text-danger">' + esc(e.message) + "</span>";
      });
  });

  var modelsLoaded = false;
  document.addEventListener("change", function (ev) {
    var select = ev.target.closest && ev.target.closest(".orchestrator-model");
    if (!select) return;
    var other = $("orchestratorO_" + select.getAttribute("data-component"));
    other.style.display = select.value === "__other__" ? "" : "none";
    if (select.value === "__other__") other.focus();
  });

  function loadModels() {
    api("/api/orchestrator/models").then(function (m) {
      function label(s) {
        var provider = s.split(":")[0];
        return s + (m.keys && m.keys[provider] === false ? " — key not set" : "");
      }
      (m.components || []).forEach(function (name) {
        var select = $("orchestratorM_" + name);
        if (!select) return;
        var previous = select.value;
        var list = (m.suggestions || []).slice();
        if (list.indexOf(m.defaults[name]) < 0) list.unshift(m.defaults[name]);
        select.innerHTML = list.map(function (s) {
          return '<option value="' + esc(s) + '">' + esc(label(s)) + "</option>";
        }).join("") + '<option value="__other__">Other… (type a model)</option>';
        select.value = modelsLoaded && (list.indexOf(previous) >= 0 || previous === "__other__")
          ? previous : m.defaults[name];
      });
      modelsLoaded = true;
      var notes = [];
      notes.push("OpenAI key: " + (m.keys.openai ? "set" : "not set"));
      notes.push("Anthropic key: " + (m.keys.anthropic ? "set" : "not set"));
      $("orchestratorModelNote").textContent = notes.join(" · ");
    }).catch(function () {
      $("orchestratorModelNote").textContent = "Start the API to load the available models.";
    });
  }

  /* ------------------------------ study: folds and results ------------ */
  var LABELS = {
    activity_label_precision: "Activities precision", activity_label_recall: "Activities recall",
    activity_label_f1: "Activities F1", connection_precision: "Connections precision",
    connection_recall: "Connections recall", connection_f1: "Connections F1",
    workflow_order_similarity: "Flow order", alignment_coverage: "Element coverage",
    semantic_similarity: "Label meaning (all labels)", activity_semantic_similarity: "Label meaning (activities)",
    collaboration_similarity: "Participants", errors_total: "Errors, total",
    errors_T1: "Errors T1 (L1)", errors_T2: "Errors T2 (L2)", errors_T3: "Errors T3 (L3)",
    errors_T4: "Errors T4 (L4)", errors_T5: "Errors T5 (connections)", errors_T6: "Errors T6 (activities)",
    errors_T7: "Errors T7 (participants)" };
  function stat(s, key) {
    if (!s || s.mean === null || s.mean === undefined) return "&mdash;";
    var d = key && key.indexOf("errors") === 0 ? 1 : 3;     // errors are counts
    return s.mean.toFixed(d) + " (" + s.sd.toFixed(d) + ")" +
      ' <span class="text-muted">[' + s.min.toFixed(d) + "&ndash;" + s.max.toFixed(d) + "]</span>";
  }
  function signed(x) { return (x === null || x === undefined) ? "&mdash;" : (x > 0 ? "+" : "") + x.toFixed(3); }
  function pval(p) { return (p === null || p === undefined) ? "&mdash;" : (p < 0.05 ? "<strong>" + p.toFixed(4) + "</strong>" : p.toFixed(4)); }
  function table(head, rows) {
    return '<div class="table-responsive"><table class="table table-sm table-striped small mb-2"><thead><tr>' +
      head.map(function (h) { return "<th>" + h + "</th>"; }).join("") + "</tr></thead><tbody>" +
      rows.map(function (r) { return "<tr>" + r.map(function (c) { return "<td>" + c + "</td>"; }).join("") + "</tr>"; }).join("") +
      "</tbody></table></div>";
  }
  function levelRows(block, name) {
    return ["L1", "L2", "L3", "L4"].map(function (l) {
      var b = (block.levels || {})[l] || {};
      return [name || "", l, fmt(b.accuracy), (b.elements_correct || 0) + " / " + ((b.elements_correct || 0) + (b.elements_incorrect || 0)),
              stat(b.accuracy_per_model), (b.models_fail || 0) + " fail, " + (b.models_not_applicable || 0) + " n/a"];
    });
  }
  var LEVEL_HEAD = ["", "level", "precision", "correct / (correct + incorrect)", "precision per model", "models"];

  /* Every metric of a run: mean, SD, min, max; precision per level. */
  function renderSummary(ms) {
    if (!ms) { $("orchestratorSummary").style.display = "none"; return; }
    var two = ms.descriptions_with_next_iterations > 0;
    var keys = Object.keys(ms.final.metrics);
    var head = ["metric", two ? "first model" : "mean (SD) [min&ndash;max]"].concat(two ? ["final model (after the next iterations)"] : []);
    var rows = keys.map(function (k) {
      return [esc(LABELS[k] || k), stat(ms.first.metrics[k], k)].concat(two ? [stat(ms.final.metrics[k], k)] : []);
    });
    var html = '<p class="small font-weight-bold mb-1">Every metric over the ' + ms.final.descriptions +
      " description(s): mean (SD between the descriptions) [min&ndash;max] &middot; valid models: " +
      (two ? ms.first.valid_models + " &rarr; " : "") + ms.final.valid_models + "</p>" + table(head, rows) +
      '<p class="small font-weight-bold mb-1">Precision per level of the structural validator = correct &divide; (correct + incorrect elements)</p>' +
      table(LEVEL_HEAD, (two ? levelRows(ms.first, "first") : []).concat(levelRows(ms.final, two ? "final" : "")));
    $("orchestratorSummary").innerHTML = html;
    $("orchestratorSummary").style.display = "";
  }

  /* The folds, and what the chosen fold will run. */
  function foldNote() {
    var fold = $("orchestratorFold").value, arm = $("orchestratorArm").value;
    var reuse = arm === "reuse_train" || arm === "reuse_test";
    $("orchestratorFold").disabled = !reuse;
    $("orchestratorReplicateBox").style.display = reuse ? "none" : "";
    [$("orchestratorPick"), $("orchestratorPickValue"), $("orchestratorSeed")].forEach(function (b) { b.disabled = reuse; });
    var text = "";
    if (arm === "first") text = "First: documentation guidelines only, no learning, no next iteration. Run it 3 times (runs 1, 2, 3) on all 55 descriptions.";
    else if (arm === "revised") text = "Revised: learns from an empty catalogue of its own (one per run number), with 3 forced next iterations. Run it 3 times on all 55 descriptions.";
    else if (!fold) text = '<span class="text-danger">Choose the round.</span>';
    else if (arm === "reuse_train") text = "Round " + fold + ", training: learns from the 44 training descriptions, into the round's own empty catalogue, with 3 forced next iterations.";
    else text = "Round " + fold + ", test: first pass on the 11 test descriptions of fold " + fold + ", with the confirmed generic guidelines of round " + fold + " only. Start it after the training of the same round.";
    $("orchestratorFoldNote").innerHTML = text;
    $("orchestratorNext").disabled = arm === "first" || arm === "reuse_test";
  }
  $("orchestratorFold").addEventListener("change", foldNote);
  $("orchestratorArm").addEventListener("change", foldNote);
  foldNote();

  function loadFolds() {
    api("/api/orchestrator/folds").then(function (d) {
      $("orchestratorFoldsTable").innerHTML = table(["fold", "test descriptions (11)", "complexity of the test descriptions", "with pools or lanes"],
        d.folds.map(function (f) {
          return [f.fold, f.test_ids.join(", "), "mean " + f.test_complexity.mean + " (" + f.test_complexity.min + "&ndash;" + f.test_complexity.max + ")",
                  f.test_with_pools_or_lanes.join(", ")];
        }));
    }).catch(function () { $("orchestratorFoldsTable").innerHTML = '<p class="text-muted">Start the API to see the folds.</p>'; });
  }

  function fillCvGenerators(runs) {
    var keep = $("cvGenerator").value, seen = [];
    runs.forEach(function (r) { if (!r.dry_run && r.generator && seen.indexOf(r.generator) < 0) seen.push(r.generator); });
    var withFolds = seen.filter(function (g) { return runs.some(function (r) { return r.generator === g && r.fold; }); });
    var order = withFolds.concat(seen.filter(function (g) { return withFolds.indexOf(g) < 0; }));
    $("cvGenerator").innerHTML = order.map(function (g) {
      return '<option value="' + esc(g) + '">' + esc(g) + (withFolds.indexOf(g) >= 0 ? " — has fold runs" : "") + "</option>";
    }).join("");
    if (keep && order.indexOf(keep) >= 0) $("cvGenerator").value = keep;
  }

  var STUDY_LABELS = { precision_L1: "Structural validator precision L1", precision_L2: "Structural validator precision L2", precision_L3: "Structural validator precision L3",
    precision_L4: "Structural validator precision L4", precision_levels_average: "Structural validator precision, average of the levels",
    activity_label_precision: "Activities P", activity_label_recall: "Activities R", activity_label_f1: "Activities F1",
    connection_precision: "Connections P", connection_recall: "Connections R", connection_f1: "Connections F1",
    workflow_order_similarity: "Flow order", alignment_coverage: "Element coverage", errors_total: "Errors (T1–T7)", valid: "Valid models (share)" };
  var STUDY_CONFIGS = ["First", "Revised i1", "Revised i2", "Learned", "Reuse"];
  function renderStudy(r) {
    var cols = STUDY_CONFIGS.filter(function (c) { return r.table[c]; });
    var keys = Object.keys(STUDY_LABELS);
    var html = "<h6 class='font-weight-bold small text-uppercase text-muted mt-2'>Runs found</h6>" +
      table(["setting", "runs", "descriptions per run"], [
        ["First", esc((r.runs.First || []).join(", ") || "none yet"), esc((r.descriptions.First || []).join(", "))],
        ["Revised", esc((r.runs.Revised || []).join(", ") || "none yet"), esc((r.descriptions.Learned || []).join(", "))],
        ["Reuse training", esc(Object.keys(r.runs.Reuse_train || {}).map(function (k) { return "round " + k + ": " + r.runs.Reuse_train[k]; }).join(", ") || "none yet"), ""],
        ["Reuse test", esc(Object.keys(r.runs.Reuse_tests || {}).map(function (k) { return "round " + k + ": " + r.runs.Reuse_tests[k]; }).join(", ") || "none yet"),
          esc((r.descriptions.Reuse || []).join(", "))]]);
    if (!cols.length) { $("cvBody").innerHTML = html; return; }
    html += "<h6 class='font-weight-bold small text-uppercase text-muted mt-3'>Results</h6>" +
      table(["measure"].concat(cols), keys.map(function (k) {
        return [esc(STUDY_LABELS[k])].concat(cols.map(function (c) {
          var t = r.table[c][k], v = (r.versus_first[c] || {})[k] || {};
          if (!t || t.mean == null) return "&mdash;";
          return fmt(t.mean) + " (" + fmt(t.sd) + ")" + (v.p != null && v.p < 0.05 ? " *" : "");
        }));
      }));
    var others = cols.filter(function (c) { return c !== "First"; });
    if (others.length) html += "<details class='mb-2'><summary class='small font-weight-bold'>Compared with First (change, better / worse descriptions, p)</summary>" +
      table(["measure"].concat(others), keys.map(function (k) {
        return [esc(STUDY_LABELS[k])].concat(others.map(function (c) {
          var v = (r.versus_first[c] || {})[k];
          if (!v || v.change == null) return "&mdash;";
          return signed(v.change) + " &middot; " + v.better + " / " + v.worse + " &middot; " + pval(v.p);
        }));
      })) + "<p class='small text-muted'>For errors, fewer is better.</p></details>";
    html += "<details class='mb-2'><summary class='small font-weight-bold'>Each run (First, Revised) and each round (Reuse)</summary>" +
      table(["measure"].concat(cols), keys.map(function (k) {
        return [esc(STUDY_LABELS[k])].concat(cols.map(function (c) {
          var t = r.table[c][k];
          return t && t.per_run && t.per_run.length ? t.per_run.map(fmt).join(" | ") : "&mdash;";
        }));
      })) + "</details>";
    $("cvBody").innerHTML = html;
  }
  $("cvShow").addEventListener("click", function () {
    var g = $("cvGenerator").value;
    if (!g) { $("cvNote").textContent = "No generator model with runs yet."; return; }
    $("cvNote").textContent = "computing…";
    api("/api/orchestrator/study?generator=" + encodeURIComponent(g)).then(function (r) {
      $("cvNote").textContent = "";
      renderStudy(r);
    }).catch(function (e) { $("cvNote").innerHTML = '<span class="text-danger">' + esc(e.message) + "</span>"; $("cvBody").innerHTML = ""; });
  });
  $("cvSave").addEventListener("click", function () {
    var g = $("cvGenerator").value;
    if (!g) return;
    api("/api/orchestrator/study/save?generator=" + encodeURIComponent(g), { method: "POST" }).then(function (r) {
      $("cvNote").innerHTML = "saved in <code>" + esc(r.folder) + "</code>";
    }).catch(function (e) { $("cvNote").innerHTML = '<span class="text-danger">' + esc(e.message) + "</span>"; });
  });

  /* ------------------------------------ test one description from zero -- */
  var DATASET = [];
  function oneText() {
    var id = $("oneId").value, entry = null;
    DATASET.forEach(function (d) { if (d.id === id) entry = d; });
    $("oneText").textContent = entry ? entry.description : "Choose a description above.";
  }
  function loadDataset() {
    api("/api/orchestrator/dataset").then(function (d) {
      DATASET = d.descriptions || [];
      $("oneId").innerHTML = '<option value="">— choose —</option>' + DATASET.map(function (e) {
        return '<option value="' + esc(e.id) + '">' + esc(e.id) + " · " + e.words + " words" + (e.with_pools_or_lanes ? " · pools or lanes" : "") +
          " · " + esc(e.excerpt) + "</option>";
      }).join("");
      oneText();
    }).catch(function () { /* API not started yet */ });
  }
  $("oneId").addEventListener("change", oneText);
  $("oneStart").addEventListener("click", function () {
    var id = $("oneId").value;
    if (!id) { $("oneText").textContent = DATASET.length ? "Choose a description first." : "Start the local API first, then reload this page."; return; }
    // the launcher below does the work: one chosen description, trial catalogue
    $("orchestratorArm").value = $("oneArm").value;
    $("orchestratorDry").checked = $("oneDry").checked;
    $("orchestratorFold").value = "";
    $("orchestratorPick").value = "chosen"; pickChanged();
    $("orchestratorPickValue").value = id;
    var model = $("oneModel").value;
    if (model !== "__launcher__") {
      document.querySelectorAll(".orchestrator-model").forEach(function (select) {
        var known = Array.prototype.some.call(select.options, function (o) { return o.value === model; });
        if (known) select.value = model;
        else { select.value = "__other__"; $("orchestratorO_" + select.getAttribute("data-component")).value = model; }
        select.dispatchEvent(new Event("change"));
      });
    }
    foldNote();
    oneTrial = true;
    $("orchestratorStart").click();
    var card = $("orchestratorResults");
    if (card) window.setTimeout(function () { card.scrollIntoView({ behavior: "smooth", block: "start" }); }, 400);
  });

  /* --------------------------------------------- download the files ---- */
  function download(path, filename, note) {
    if (SAVED) {                               // saved runs: the files are in the repository
      var m = path.match(/run=([^&]+)/), e = path.match(/example=([^&]+)/);
      var run = m ? decodeURIComponent(m[1]) : $("orchestratorRuns").value;
      if (!run) { if (note) note.textContent = "choose a run first"; return Promise.resolve(); }
      window.open(REPO + run + (e ? "/id_" + String(decodeURIComponent(e[1])).padStart(2, "0") : ""), "_blank", "noopener");
      if (note) note.textContent = "opened the run's files on GitHub";
      return Promise.resolve();
    }
    var base = ($("orchestratorApi").value.trim() || "http://127.0.0.1:8765").replace(/\/$/, "");
    var headers = {}, token = $("orchestratorToken").value.trim();
    if (token) headers["X-API-Token"] = token;
    if (note) note.textContent = "preparing the zip…";
    return fetch(base + path, { headers: headers }).then(function (r) {
      if (!r.ok) return r.json().catch(function () { return {}; }).then(function (d) { throw new Error(d.detail || ("HTTP " + r.status)); });
      return r.blob();
    }).then(function (blob) {
      var url = URL.createObjectURL(blob), a = document.createElement("a");
      a.href = url; a.download = filename; document.body.appendChild(a); a.click();
      window.setTimeout(function () { URL.revokeObjectURL(url); a.remove(); }, 1000);
      if (note) note.textContent = "downloaded " + filename + " (" + (blob.size / 1048576).toFixed(1) + " MB)";
    }).catch(function (e) { if (note) note.textContent = "download failed: " + e.message; else alert("Download failed: " + e.message); });
  }
  function runQuery() { return viewRun ? "run=" + encodeURIComponent(viewRun) : ""; }
  $("orchestratorDownloadRun").addEventListener("click", function () {
    var chosen = $("orchestratorRuns").value, q = chosen ? "run=" + encodeURIComponent(chosen) : runQuery();
    download("/api/orchestrator/download" + (q ? "?" + q : ""), (chosen || viewRun || "guidebpmn_run") + ".zip", $("orchestratorRescoreNote"));
  });
  $("orchestratorDownloadExample").addEventListener("click", function () {
    if (!shownId) return;
    var q = runQuery();
    download("/api/orchestrator/download?example=" + encodeURIComponent(shownId) + (q ? "&" + q : ""),
             (viewRun || "guidebpmn_run") + "_id_" + String(shownId).padStart(2, "0") + ".zip", $("orchestratorDownloadNote"));
  });

  loadModels();
  loadRuns();
  loadFolds();
  loadDataset();
  poll();
})();
