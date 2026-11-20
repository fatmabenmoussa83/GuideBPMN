/* Compare page: every model the study kept for one description (First r1-r3, Revised r1-r3 with
   draft 0 / after each iteration / Learned, Reuse test), with its measures, and any of them drawn next
   to the reference. Reads the saved runs of the study (docs/data/saved/, see _build/export_compare.py);
   no API is needed. */
(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  if (!$("cmpGenerator")) return;
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (ch) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]; }); }
  function pct(x) { return x == null ? "&mdash;" : (100 * x).toFixed(1); }
  function num(x, d) { return x == null ? "&mdash;" : Number(x).toFixed(d == null ? 1 : d); }
  var SHORT = { "openai:gpt-6-luna": "Luna", "anthropic:claude-haiku-5-5": "Haiku" };
  var GH = "https://github.com/fatmabenmoussa83/GuideBPMN/tree/main/bpmn_pipeline/runs/";
  var MEASURES = [["activity_label_f1", "Activities F1"], ["connection_f1", "Connections F1"],
                  ["workflow_order_similarity", "Flow order"], ["alignment_coverage", "Coverage"],
                  ["collaboration_similarity", "Participants"]];

  function gz(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error(url + ": HTTP " + r.status);
      if (!/\.gz$/.test(url)) return r.json();
      if (typeof DecompressionStream === "undefined") throw new Error("this browser cannot open the saved runs; use a recent Chrome, Edge, Firefox or Safari");
      return new Response(r.body.pipeThrough(new DecompressionStream("gzip"))).json();
    });
  }

  /* ------------------------------------------------------------ state --- */
  var DATA = {}, data = null, generator = null, id = null;
  var examples = {};                       // run -> id -> example document (lazy)
  var drawn = [];                          // [{key, run, draft, label}]
  var viewers = {};

  function loadGenerator(g) {
    generator = g;
    if (DATA[g]) { data = DATA[g]; return Promise.resolve(data); }
    $("cmpNote").textContent = "";
    return gz("data/saved/compare/" + g.replace(":", "-") + ".json.gz").then(function (d) {
      DATA[g] = d; data = d; return d;
    });
  }

  function ids() { return Object.keys(data.descriptions).sort(); }

  function fillSelect() {
    var sel = $("cmpId"), keep = id;
    sel.innerHTML = ids().map(function (i) {
      var t = data.titles[i] || {}, pools = t.pools ? " · pools or lanes" : "";
      return '<option value="' + i + '">' + i + " · " + esc(t.start || "") + "… (" + esc(t.words || "?") + " words" + pools + ")</option>";
    }).join("");
    if (keep && data.descriptions[keep]) sel.value = keep;
    id = sel.value;
  }

  /* --------------------------------------------------- the main table --- */
  function model(m) { return m || {}; }
  function validCell(m) {
    if (m.valid == null) return "&mdash;";
    return m.valid ? '<span class="text-success">valid</span>'
                   : '<span class="text-danger">invalid ' + esc((m.failed_levels || []).join(",")) + "</span>";
  }
  function errorsCell(m) {
    var e = m.errors || {}, parts = Object.keys(e).filter(function (t) { return e[t]; }).map(function (t) { return t + " " + e[t]; });
    return '<span title="' + esc(parts.join(", ") || "no open error") + '">' + (m.errors_total == null ? "&mdash;" : m.errors_total) + "</span>";
  }
  function measureCells(m) {
    return MEASURES.map(function (p) { return '<td class="text-right">' + pct(m[p[0]]) + "</td>"; }).join("");
  }
  function drawCell(key, run, draft, label) {
    var on = drawn.some(function (d) { return d.key === key; });
    return '<td class="text-center"><input type="checkbox" class="cmp-draw" data-key="' + esc(key) + '" data-run="' + esc(run) +
      '" data-draft="' + draft + '" data-label="' + esc(label) + '"' + (on ? " checked" : "") + "></td>";
  }
  function guidelineCell(step, rv) {
    if (step.iteration === 0) {
      var l = rv.learned || [];
      return l.length ? "learned " + l.length + " of " + rv.proposals + " proposals: " + l.map(function (g) { return esc(g.id) + " (" + esc(g.type) + ")"; }).join(", ")
                      : (rv.proposals ? rv.proposals + " proposals, none kept" : "&mdash;");
    }
    var sent = step.sent || [], ok = step.confirmed_ids || [], tr = step.type_results || {};
    if (!sent.length) return "nothing sent";
    return "sent " + sent.map(function (g) {
      var r = tr[g], tip = r ? g + " (" + r.type + "): " + r.before + " → " + r.after + " errors" : g;
      return '<span title="' + esc(tip) + '" class="' + (ok.indexOf(g) >= 0 ? "text-success font-weight-bold" : "") + '">' + esc(g) + "</span>";
    }).join(", ") + (step.reverted ? ' <span class="badge badge-warning">not kept</span>' : "") +
      (step.not_run ? ' <span class="text-muted">(not run)</span>' : "");
  }
  function meanRow(label, models) {
    if (!models.length) return "";
    function mean(k) { var v = models.map(function (m) { return m[k]; }).filter(function (x) { return x != null; });
      return v.length ? v.reduce(function (a, b) { return a + b; }, 0) / v.length : null; }
    var valid = models.filter(function (m) { return m.valid; }).length;
    return '<tr class="table-light font-weight-bold"><td colspan="3">' + label + "</td><td>" + valid + " of " + models.length + ' valid</td>' +
      '<td class="text-right">' + num(mean("errors_total")) + "</td>" +
      MEASURES.map(function (p) { return '<td class="text-right">' + pct(mean(p[0])) + "</td>"; }).join("") + "<td></td><td></td></tr>";
  }

  function renderTable() {
    var row = data.descriptions[id];
    if (!row) { $("cmpCard").style.display = "none"; return; }
    $("cmpCard").style.display = "";
    $("cmpTitle").textContent = "Description " + id + " — " + (SHORT[generator] || generator);
    $("cmpText").textContent = row.description || "";
    var head = "<tr><th>Configuration</th><th>Run</th><th>Model</th><th>Validator</th><th class=\"text-right\">Errors</th>" +
      MEASURES.map(function (p) { return '<th class="text-right">' + p[1] + "</th>"; }).join("") + "<th>Guidelines</th><th>Draw</th></tr>";
    var body = "";
    var firsts = row.First || [];
    firsts.forEach(function (f, i) {
      var m = model(f.model), label = "First r" + (i + 1);
      body += "<tr>" + (i === 0 ? '<td rowspan="' + firsts.length + '"><strong>First</strong><br><span class="text-muted">documentation guidelines only, no learning</span></td>' : "") +
        "<td>" + runLink(f.run, "r" + (i + 1)) + "</td><td>draft " + esc(m.draft) + "</td><td>" + validCell(m) + '</td><td class="text-right">' + errorsCell(m) + "</td>" +
        measureCells(m) + "<td>&mdash;</td>" + drawCell(f.run + "#" + m.draft, f.run, m.draft, label) + "</tr>";
    });
    body += meanRow("First, mean of " + firsts.length + " runs", firsts.map(function (f) { return f.model; }));
    var revs = row.Revised || [], learnedModels = [];
    revs.forEach(function (rv, i) {
      var steps = rv.steps || [], n = steps.length;
      steps.forEach(function (s, j) {
        var last = j === n - 1, name = j === 0 ? "draft 0" : (last ? "Learned" : "Revised i" + s.iteration);
        if (last) learnedModels.push(s);
        body += "<tr" + (last ? ' class="font-weight-bold"' : "") + ">" +
          (i === 0 && j === 0 ? '<td rowspan="' + revs.reduce(function (a, r) { return a + (r.steps || []).length; }, 0) + '"><strong>Revised</strong><br><span class="text-muted font-weight-normal">learns from its own errors, 3 next iterations</span></td>' : "") +
          (j === 0 ? '<td rowspan="' + n + '">' + runLink(rv.run, "r" + (i + 1)) + "</td>" : "") +
          "<td>" + name + (j > 0 ? ' <span class="text-muted font-weight-normal">(draft ' + esc(s.draft) + ")</span>" : "") + "</td><td>" + validCell(s) +
          '</td><td class="text-right">' + errorsCell(s) + "</td>" + measureCells(s) +
          '<td class="font-weight-normal" style="max-width:22rem">' + guidelineCell(s, rv) + "</td>" +
          drawCell(rv.run + "#" + s.draft, rv.run, s.draft, "Revised r" + (i + 1) + " · " + name) + "</tr>";
      });
    });
    body += meanRow("Learned, mean of " + revs.length + " runs", learnedModels);
    if (row.Reuse) {
      var m = model(row.Reuse.model);
      body += "<tr><td><strong>Reuse</strong><br><span class='text-muted'>fold " + row.Reuse.fold + " held out; generated with the confirmed generic guidelines learned on the other 44 descriptions</span></td>" +
        "<td>" + runLink(row.Reuse.run, "fold " + row.Reuse.fold) + "</td><td>draft " + esc(m.draft) + "</td><td>" + validCell(m) + '</td><td class="text-right">' + errorsCell(m) + "</td>" +
        measureCells(m) + "<td>&mdash;</td>" + drawCell(row.Reuse.run + "#" + m.draft, row.Reuse.run, m.draft, "Reuse · fold " + row.Reuse.fold) + "</tr>";
    }
    var train = row.ReuseTrain || [];
    if (train.length) {
      body += '<tr><td colspan="' + (7 + MEASURES.length) + '" class="pt-2"><a href="#" id="cmpTrainToggle" class="small">' +
        (showTrain ? "Hide" : "Show") + " the " + train.length + " Reuse training runs in which this description was one of the 44 (its Learned model there)</a></td></tr>";
      if (showTrain) train.forEach(function (t, i) {
        var tm = model(t.model);
        body += '<tr class="text-muted">' + (i === 0 ? '<td rowspan="' + train.length + '">Reuse training<br><span class="small">learned on this description, among 44</span></td>' : "") +
          "<td>" + runLink(t.run, "fold " + t.fold) + "</td><td>Learned (draft " + esc(tm.draft) + ")</td><td>" + validCell(tm) + '</td><td class="text-right">' + errorsCell(tm) + "</td>" +
          measureCells(tm) + "<td>learned " + (t.learned || []).map(function (g) { return esc(g.id); }).join(", ") + "</td>" +
          drawCell(t.run + "#" + tm.draft, t.run, tm.draft, "Reuse training fold " + t.fold + " · Learned") + "</tr>";
      });
    }
    $("cmpTable").querySelector("thead").innerHTML = head;
    $("cmpTable").querySelector("tbody").innerHTML = body;
  }
  var showTrain = false;
  function runLink(run, text) {
    return '<a href="run.html#run=' + encodeURIComponent(run) + "&id=" + encodeURIComponent(id) + '" title="' + esc(run) + '">' + esc(text) + "</a>";
  }

  /* ---------------------------------------------------------- diagrams -- */
  function example(run, i) {
    examples[run] = examples[run] || {};
    if (examples[run][i]) return examples[run][i];
    examples[run][i] = gz("data/saved/runs/" + run + "/example_" + i + ".json.gz");
    return examples[run][i];
  }
  function pane(key, title) {
    var safe = key.replace(/[^a-zA-Z0-9]/g, "_");
    return '<div class="cmp-pane" id="pane_' + safe + '" data-key="' + esc(key) + '"><div class="d-flex align-items-center mb-1"><span class="small font-weight-bold mr-auto">' + esc(title) + "</span>" +
      '<button class="btn btn-xs btn-light border mr-1" data-zoom="out" data-target="cv_' + safe + '">&minus;</button>' +
      '<button class="btn btn-xs btn-light border mr-1" data-zoom="in" data-target="cv_' + safe + '">+</button>' +
      '<button class="btn btn-xs btn-light border mr-1" data-zoom="fit" data-target="cv_' + safe + '">Fit</button>' +
      '<button class="btn btn-xs btn-light border mr-1" data-edit="cv_' + safe + '" title="Switch this diagram between read-only and editable">Edit</button>' +
      '<button class="btn btn-xs btn-light border" data-full="pane_' + safe + '" title="This diagram on the whole screen (Esc to leave)"><i class="fas fa-expand"></i></button></div>' +
      '<div id="cv_' + safe + '" class="cmp-canvas"></div><p class="small text-muted mt-1 mb-0 cmp-note"></p></div>';
  }
  function fit(cid) {
    var v = viewers[cid]; if (!v) return;
    try { var c = v.get("canvas"); c.resized(); c.zoom("fit-viewport", "auto"); } catch (e) { /* empty */ }
  }
  function show(cid, xml, note) {
    var box = document.getElementById(cid), noteBox = box && box.parentNode.querySelector(".cmp-note");
    if (!box || !window.BpmnJS) return;
    if (!viewers[cid]) viewers[cid] = new BpmnJS({ container: "#" + cid });
    if (noteBox) noteBox.textContent = note || "";
    if (!xml) { if (noteBox) noteBox.textContent = "No XML for this model."; return; }
    viewers[cid].importXML(xml).then(function () { fit(cid); })
      .catch(function (err) { if (noteBox) noteBox.textContent = "This XML cannot be drawn: " + (err && err.message ? err.message : err); });
  }
  function renderDiagrams() {
    var card = $("cmpDiagramsCard"), grid = $("cmpDiagrams");
    if (!drawn.length) { card.style.display = "none"; grid.innerHTML = ""; viewers = {}; return; }
    card.style.display = "";
    var keep = {};
    var html = pane("ref", "Reference model (description " + id + ")");
    drawn.forEach(function (d) { html += pane(d.key, d.label); keep[d.key] = true; });
    grid.innerHTML = html;
    grid.setAttribute("data-count", String(drawn.length + 1));
    viewers = {};
    var first = drawn[0];
    example(first.run, id).then(function (doc) { show("cv_ref", doc.gold_display_xml || doc.gold_xml, ""); });
    drawn.forEach(function (d) {
      example(d.run, id).then(function (doc) {
        var it = (doc.iterations || [])[d.draft] || {};
        var note = (it.valid ? "valid" : "invalid " + (it.failed_levels || []).join(",")) +
          (it.layout_added ? " · layout added for display" : "");
        show("cv_" + d.key.replace(/[^a-zA-Z0-9]/g, "_"), it.display_xml || it.xml, note);
      }).catch(function (e) { var n = grid.querySelector('[data-key="' + d.key + '"] .cmp-note'); if (n) n.textContent = e.message; });
    });
  }

  /* -------------------------------------------------- all descriptions -- */
  var sortKey = "id", sortDir = 1;
  function mean(v) { v = v.filter(function (x) { return x != null; }); return v.length ? v.reduce(function (a, b) { return a + b; }, 0) / v.length : null; }
  function summary(i) {
    var r = data.descriptions[i], revs = r.Revised || [];
    function step(k) { return mean(revs.map(function (v) { var s = v.steps || []; return k < s.length ? s[k].errors_total : null; })); }
    var first = (r.First || []).map(function (f) { return f.model; });
    var learned = revs.map(function (v) { var s = v.steps || []; return s[s.length - 1]; });
    var o = { id: i, start: (data.titles[i] || {}).start || "", pools: !!(data.titles[i] || {}).pools,
      first: mean(first.map(function (m) { return m.errors_total; })), i1: step(1), i2: step(2),
      learned: mean(learned.map(function (m) { return m.errors_total; })),
      reuse: r.Reuse ? r.Reuse.model.errors_total : null,
      validFirst: first.filter(function (m) { return m.valid; }).length, validLearned: learned.filter(function (m) { return m.valid; }).length,
      validReuse: r.Reuse ? r.Reuse.model.valid : null,
      connFirst: mean(first.map(function (m) { return m.connection_f1; })), connLearned: mean(learned.map(function (m) { return m.connection_f1; })),
      connReuse: r.Reuse ? r.Reuse.model.connection_f1 : null,
      orderFirst: mean(first.map(function (m) { return m.workflow_order_similarity; })), orderLearned: mean(learned.map(function (m) { return m.workflow_order_similarity; })),
      orderReuse: r.Reuse ? r.Reuse.model.workflow_order_similarity : null };
    o.dLearned = o.learned != null && o.first != null ? o.learned - o.first : null;
    o.dReuse = o.reuse != null && o.first != null ? o.reuse - o.first : null;
    return o;
  }
  function delta(x) {
    if (x == null) return "&mdash;";
    var cls = x < 0 ? "text-success" : x > 0 ? "text-danger" : "text-muted";
    return '<span class="' + cls + ' font-weight-bold">' + (x > 0 ? "+" : "") + x.toFixed(1) + "</span>";
  }
  function renderAll() {
    var rows = ids().map(summary);
    rows.sort(function (a, b) { var x = a[sortKey], y = b[sortKey]; if (x == null) return 1; if (y == null) return -1; return (x < y ? -1 : x > y ? 1 : 0) * sortDir; });
    var better = rows.filter(function (r) { return r.dLearned < 0; }).length, worse = rows.filter(function (r) { return r.dLearned > 0; }).length;
    var rb = rows.filter(function (r) { return r.dReuse < 0; }).length, rw = rows.filter(function (r) { return r.dReuse > 0; }).length;
    $("cmpAllTitle").textContent = "Open errors per description — " + (SHORT[generator] || generator);
    $("cmpAllSummary").innerHTML = "Mean open errors over the 55 descriptions: First " + num(mean(rows.map(function (r) { return r.first; }))) +
      ", Learned " + num(mean(rows.map(function (r) { return r.learned; }))) + ", Reuse " + num(mean(rows.map(function (r) { return r.reuse; }))) +
      ". <strong>Learned vs First</strong>: errors decrease for " + better + " descriptions, increase for " + worse + ", unchanged for " + (rows.length - better - worse) +
      ". <strong>Reuse vs First</strong>: decrease for " + rb + ", increase for " + rw + ", unchanged for " + (rows.length - rb - rw) + ".";
    var cols = [["id", "Description"], ["first", "First"], ["i1", "Revised i1"], ["i2", "Revised i2"], ["learned", "Learned"], ["dLearned", "Learned − First"],
                ["reuse", "Reuse"], ["dReuse", "Reuse − First"], ["validFirst", "Valid First / Learned / Reuse"], ["connFirst", "Connections F1 First / Learned / Reuse"],
                ["orderFirst", "Flow order First / Learned / Reuse"]];
    $("cmpAll").querySelector("thead").innerHTML = "<tr>" + cols.map(function (c) {
      return '<th class="cmp-sort' + (c[0] === "id" ? "" : " text-right") + '" data-key="' + c[0] + '" style="cursor:pointer">' + c[1] + (sortKey === c[0] ? (sortDir > 0 ? " ▲" : " ▼") : "") + "</th>";
    }).join("") + "</tr>";
    $("cmpAll").querySelector("tbody").innerHTML = rows.map(function (r) {
      return '<tr class="cmp-all-row' + (r.id === id ? " table-active" : "") + '" data-id="' + r.id + '" style="cursor:pointer"><td><strong>' + r.id + "</strong> " +
        '<span class="text-muted">' + esc(r.start) + "…</span>" + (r.pools ? ' <span class="badge badge-light border">pools/lanes</span>' : "") + "</td>" +
        '<td class="text-right">' + num(r.first) + '</td><td class="text-right">' + num(r.i1) + '</td><td class="text-right">' + num(r.i2) + "</td>" +
        '<td class="text-right font-weight-bold">' + num(r.learned) + '</td><td class="text-right">' + delta(r.dLearned) + "</td>" +
        '<td class="text-right">' + num(r.reuse, 0) + '</td><td class="text-right">' + delta(r.dReuse) + "</td>" +
        '<td class="text-right">' + r.validFirst + "/3 · " + r.validLearned + "/3 · " + (r.validReuse == null ? "—" : r.validReuse ? "✓" : "✗") + "</td>" +
        '<td class="text-right">' + pct(r.connFirst) + " · " + pct(r.connLearned) + " · " + pct(r.connReuse) + "</td>" +
        '<td class="text-right">' + pct(r.orderFirst) + " · " + pct(r.orderLearned) + " · " + pct(r.orderReuse) + "</td></tr>";
    }).join("");
  }

  /* ------------------------------------------------------------ wiring -- */
  function hash() {
    var m = (location.hash || "").match(/#(luna|haiku)\/(\d{2})/i);
    return m ? { g: m[1].toLowerCase() === "luna" ? "openai:gpt-6-luna" : "anthropic:claude-haiku-5-5", id: m[2] } : null;
  }
  function setHash() {
    var h = "#" + (SHORT[generator] || "").toLowerCase() + "/" + id;
    if (location.hash !== h) history.replaceState(null, "", h);
  }
  function select(newId, resetDrawn) {
    id = newId; $("cmpId").value = id;
    if (resetDrawn !== false) drawn = [];
    renderTable(); renderDiagrams(); renderAll(); setHash();
  }
  function start(g, i) {
    loadGenerator(g).then(function () {
      $("cmpGenerator").value = g;
      fillSelect();
      select(i && data.descriptions[i] ? i : (data.descriptions[id] ? id : ids()[0]));
    }).catch(function (e) { $("cmpNote").textContent = "The saved runs could not be read: " + e.message; });
  }

  $("cmpGenerator").addEventListener("change", function () { start($("cmpGenerator").value, id); });
  $("cmpId").addEventListener("change", function () { select($("cmpId").value); });
  $("cmpPrev").addEventListener("click", function () { var a = ids(), k = a.indexOf(id); if (k > 0) select(a[k - 1]); });
  $("cmpNext").addEventListener("click", function () { var a = ids(), k = a.indexOf(id); if (k >= 0 && k < a.length - 1) select(a[k + 1]); });
  document.addEventListener("change", function (ev) {
    var cb = ev.target.closest(".cmp-draw");
    if (!cb) return;
    var key = cb.getAttribute("data-key");
    drawn = drawn.filter(function (d) { return d.key !== key; });
    if (cb.checked) {
      if (drawn.length >= 3) { cb.checked = false; alert("Three models at most next to the reference: untick one first."); return; }
      drawn.push({ key: key, run: cb.getAttribute("data-run"), draft: Number(cb.getAttribute("data-draft")), label: cb.getAttribute("data-label") });
    }
    renderDiagrams();
  });
  document.addEventListener("click", function (ev) {
    var z = ev.target.closest("[data-zoom]");
    if (z) {
      var cid = z.getAttribute("data-target"), v = viewers[cid];
      if (!v) return;
      var c = v.get("canvas"), how = z.getAttribute("data-zoom");
      if (how === "fit") fit(cid); else c.zoom(c.zoom() * (how === "in" ? 1.25 : 0.8));
      return;
    }
    var ed = ev.target.closest("[data-edit]");
    if (ed) {
      var pane = document.getElementById(ed.getAttribute("data-edit"));
      if (pane) { var on = pane.classList.toggle("editing"); ed.textContent = on ? "Stop editing" : "Edit"; ed.classList.toggle("btn-warning", on); ed.classList.toggle("btn-light", !on); }
      return;
    }
    var fs = ev.target.closest("[data-full]");
    if (fs) { fullScreen(document.getElementById(fs.getAttribute("data-full"))); return; }
    if (ev.target.closest("#cmpStack")) {
      var stacked = $("cmpDiagrams").classList.toggle("cmp-stacked");
      $("cmpStack").textContent = stacked ? "Two per row" : "One per row";
      setTimeout(function () { Object.keys(viewers).forEach(fit); }, 50);
      return;
    }
    if (ev.target.closest("#cmpTrainToggle")) { ev.preventDefault(); showTrain = !showTrain; renderTable(); return; }
    var th = ev.target.closest(".cmp-sort");
    if (th) { var k = th.getAttribute("data-key"); if (sortKey === k) sortDir = -sortDir; else { sortKey = k; sortDir = 1; } renderAll(); return; }
    var row = ev.target.closest(".cmp-all-row");
    if (row) { select(row.getAttribute("data-id")); window.scrollTo({ top: 0, behavior: "smooth" }); }
  });
  function fullScreen(el) {
    if (!el) return;
    if (document.fullscreenElement) { document.exitFullscreen(); if (document.fullscreenElement === el) return; }
    var ask = el.requestFullscreen || el.webkitRequestFullscreen;
    if (ask) ask.call(el); else alert("Full screen is not available in this browser.");
  }
  document.addEventListener("fullscreenchange", function () { window.setTimeout(function () { Object.keys(viewers).forEach(fit); }, 150); });
  window.addEventListener("resize", function () { Object.keys(viewers).forEach(fit); });
  window.addEventListener("hashchange", function () { var h = hash(); if (h && (h.g !== generator || h.id !== id)) start(h.g, h.id); });

  var h = hash();
  start(h ? h.g : $("cmpGenerator").value, h ? h.id : null);
})();
