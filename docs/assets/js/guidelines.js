/* Guidelines page: the documentation guidelines (read-only, from the OMG BPMN
   2.0.2 documentation) and the guidelines GuideBPMN has learned. The
   catalogue of documentation guidelines ships with the site; the catalogue of error-driven guidelines is read
   from the local API because it grows while runs are going on. */
(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  if (!$("glDocTable")) return;
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (ch) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]; }); }
  function recall(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function remember(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* private mode */ } }

  var doc = window.DOC_GUIDELINES || { sections: [] };
  var docRules = [];
  (doc.sections || []).forEach(function (section) {
    (section.rules || []).forEach(function (rule) {
      docRules.push({ id: rule.id, category: section.category, instruction: rule.instruction,
                      clause: rule.source_clause || (doc.source_map || {})[section.category] });
    });
  });
  var byId = {};
  docRules.forEach(function (r) { byId[r.id] = r; });
  var learned = [];

  function matches(text, query) { return !query || text.toLowerCase().indexOf(query) >= 0; }
  function clause(c) { return Array.isArray(c) ? c.join(", ") : (c || ""); }

  function renderDoc() {
    var query = $("glSearch").value.trim().toLowerCase();
    var category = $("glCategory").value;
    var rows = docRules.filter(function (r) {
      return (!category || r.category === category) &&
        matches(r.id + " " + r.category + " " + r.instruction, query);
    });
    $("glDocCount").textContent = rows.length + " of " + docRules.length;
    $("glDocTable").innerHTML = rows.map(function (r) {
      return "<tr><td class=\"text-nowrap\"><strong>" + esc(r.id) + "</strong></td><td>" + esc(r.category) +
        "</td><td>" + esc(r.instruction) + "</td><td class=\"text-nowrap text-muted\">" + esc(clause(r.clause)) + "</td></tr>";
    }).join("") || '<tr><td colspan="4" class="text-muted">No rule matches.</td></tr>';
  }

  function renderLearned() {
    var query = $("glSearch").value.trim().toLowerCase();
    var rows = learned.filter(function (g) {
      return matches([g.id, g.category, g.family, g.trigger, g.instruction,
                      (g.baseline_relation || {}).ref].join(" "), query);
    });
    $("glLearnedCount").textContent = rows.length + " of " + learned.length;
    $("glLearnedTable").innerHTML = rows.map(function (g) {
      var rel = g.baseline_relation || {};
      var refRule = rel.ref && byId[rel.ref];
      var relation = (rel.type === "refines"
        ? '<span class="badge badge-info">refines ' + esc(rel.ref) + "</span>" +
          (refRule ? '<div class="small text-muted mt-1">' + esc(rel.ref) + ": " + esc(refRule.instruction) + "</div>" : "")
        : '<span class="badge badge-success">new</span>') +
        (g.confirmation
          ? '<div class="mt-1"><span class="badge ' + (g.confirmation.confirmed ? "badge-primary" : "badge-light border") + '">' +
            (g.confirmation.confirmed ? "confirmed" : "not confirmed") + "</span> <span class=\"small text-muted\">" +
            (g.confirmation.errors_removed != null
              ? "errors of its type removed: " + g.confirmation.errors_removed
              : "mean change " + (g.confirmation.mean_change > 0 ? "+" : "") + Number(g.confirmation.mean_change).toFixed(3)) + " over " +
            g.confirmation.tests.length + " test" + (g.confirmation.tests.length > 1 ? "s" : "") + "</span></div>"
          : "") +
        (g.status === "example_specific"
          ? '<div class="mt-1"><span class="badge badge-warning">example ' + esc((g.scope || {}).example_id) +
            " only</span></div>" + '<div class="small text-muted">' +
            (g.trace_only ? "first wording of " + esc(g.generalized_into) + ", kept as a trace (never sent to the generator)"
                          : "sent back to its own description only" + (g.generalized_into ? "; generalized into " + esc(g.generalized_into) : "")) +
            "</div>"
          : "") +
        (g.generalized_from ? '<div class="small text-muted mt-1">generalized from ' + esc(g.generalized_from.join(", ")) + "</div>" : "");
      var support = ((g.support || {}).learned_from || []).join(", ");
      var evidence = (g.evidence || []).map(function (e) {
        return "<li>example " + esc(e.example_id) + ": " + (e.records || []).map(function (r) {
          return "<span class=\"text-muted\">[" + esc(r.id) + "]</span> " + esc(r.text);
        }).join(" &middot; ") + "</li>";
      }).join("");
      return "<tr><td class=\"text-nowrap\"><strong>" + esc(g.id) + "</strong></td><td>" + relation + "</td><td>" +
        esc(g.category) + "<div class=\"small text-muted\">from " + esc(g.family) + "</div></td><td><em>When " +
        esc(g.trigger) + ":</em> " + esc(g.instruction) +
        (evidence ? '<details class="small mt-1"><summary>evidence</summary><ul class="mb-0">' + evidence + "</ul></details>" : "") +
        "</td><td>" + esc(support) + "</td></tr>";
    }).join("") || '<tr><td colspan="5" class="text-muted">' +
      (learned.length ? "No guideline matches." : "No error-driven guideline yet: they appear here as runs learn them.") + "</td></tr>";
  }

  function loadLearned() {
    var base = ($("glApi").value.trim() || "http://127.0.0.1:8765").replace(/\/$/, "");
    remember("guidebpmn.api", $("glApi").value.trim());
    $("glLearnedNote").textContent = "Loading…";
    var chosen = $("glModel").value;
    fetch(base + "/api/orchestrator/guidelines" + (chosen ? "?catalogue=" + encodeURIComponent(chosen) : "")).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (data) {
      learned = data.guidelines || [];
      var list = data.catalogues || [];
      $("glModel").innerHTML = (list.length ? "" : '<option value="">no catalogue yet</option>') + list.map(function (c) {
        return '<option value="' + esc(c.id) + '"' + (c.id === data.catalogue ? " selected" : "") + ">" + esc(c.label) +
          " (" + c.general + " generic, " + c.confirmed + " confirmed, " + c.count + " in all)</option>";
      }).join("");
      var general = learned.filter(function (g) { return g.status !== "example_specific"; });
      var news = general.filter(function (g) { return (g.baseline_relation || {}).type !== "refines"; }).length;
      var traces = learned.filter(function (g) { return g.trace_only; }).length;
      var confirmed = general.filter(function (g) { return (g.confirmation || {}).confirmed; }).length;
      $("glLearnedNote").textContent = general.length + " generic guideline(s), " + confirmed + " confirmed: " + news + " new, " +
        (general.length - news) + " refining a documentation guideline; " + (learned.length - general.length - traces) +
        " example-specific (sent back for their own description only, never given to another description); " + traces +
        " first wordings kept for traceability (rewritten in general terms, never sent to the generator).";
      $("glLearnedTab").textContent = "Error-driven guidelines (" + learned.length + ")";
      renderLearned();
    }).catch(function (e) {
      $("glLearnedNote").innerHTML = '<span class="text-danger">' + esc(e.message) +
        "</span> &mdash; the error-driven guidelines are read from the local API: start it with <code>.\\start_webapi.ps1</code>.";
    });
  }

  function showTab(which) {
    $("glDocPane").style.display = which === "doc" ? "" : "none";
    $("glLearnedPane").style.display = which === "learned" ? "" : "none";
    $("glDocTab").classList.toggle("active", which === "doc");
    $("glLearnedTab").classList.toggle("active", which === "learned");
    $("glCategoryBox").style.display = which === "doc" ? "" : "none";
  }

  $("glCategory").innerHTML = '<option value="">All categories</option>' +
    (doc.sections || []).map(function (s) {
      return '<option value="' + esc(s.category) + '">' + esc(s.category) + " (" + (s.rules || []).length + ")</option>";
    }).join("");
  $("glDocTab").textContent = "Documentation guidelines (" + docRules.length + ")";
  $("glSource").textContent = doc.normative_source
    ? "Source: " + doc.normative_source.title + " (OMG " + doc.normative_source.omg_document_number + "), version " + doc.version + "."
    : "";
  if (recall("guidebpmn.api")) $("glApi").value = recall("guidebpmn.api");

  $("glSearch").addEventListener("input", function () { renderDoc(); renderLearned(); });
  $("glCategory").addEventListener("change", renderDoc);
  $("glDocTab").addEventListener("click", function (ev) { ev.preventDefault(); showTab("doc"); });
  $("glLearnedTab").addEventListener("click", function (ev) { ev.preventDefault(); showTab("learned"); });
  $("glReload").addEventListener("click", loadLearned);
  $("glModel").addEventListener("change", loadLearned);

  renderDoc();
  renderLearned();
  showTab(location.hash === "#learned" ? "learned" : "doc");
  loadLearned();
})();
