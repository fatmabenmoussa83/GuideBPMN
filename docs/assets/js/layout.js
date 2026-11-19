/* Shared sidebar and topbar for every page (no build step, works on GitHub Pages).
   Each page sets <body data-page="..."> and contains #sidebar-slot, #topbar-slot, #footer-slot. */
(function () {
  var SITE = {
    name: "GuideBPMN",
    tagline: "BPMN generation that learns modeling guidelines"
    // anonymous for review: no author name, no repository link, no publication page
  };
  window.GB_SITE = SITE;

  var NAV = [
    { group: null, items: [{ id: "home", href: "index.html", icon: "fa-home", label: "Overview" },
                           { id: "run", href: "run.html", icon: "fa-play-circle", label: "Run GuideBPMN" },
                           { id: "guidelines", href: "guidelines.html", icon: "fa-clipboard-list", label: "Guidelines" }] },
    { group: "Methodology", items: [
      { id: "orchestrator", href: "orchestrator.html", icon: "fa-project-diagram", label: "Orchestrator & budgets" },
      { id: "learning", href: "guideline_learning.html", icon: "fa-robot", label: "Guideline learning (agents)" },
      { id: "validator", href: "validator.html", icon: "fa-check-double", label: "Structural validator L1–L4" },
      { id: "similarity", href: "similarity.html", icon: "fa-balance-scale", label: "Similarity evaluator" }
    ]},
    { group: "Resources", items: [
      { id: "docs", href: "documentation.html", icon: "fa-book", label: "Documentation" }
    ]}
  ];

  var page = document.body.getAttribute("data-page") || "home";
  var title = document.body.getAttribute("data-title") || "";

  var logo =
    '<svg class="brand-mark" viewBox="0 0 40 40" aria-hidden="true">' +
    '<circle cx="7" cy="20" r="5" fill="none" stroke="currentColor" stroke-width="2"/>' +
    '<rect x="14" y="14" width="12" height="12" rx="2" fill="none" stroke="currentColor" stroke-width="2"/>' +
    '<path d="M33 13 L39 20 L33 27 L27 20 Z" fill="currentColor"/>' +
    '<path d="M12 20 H14 M26 20 H27" stroke="currentColor" stroke-width="2"/></svg>';

  var s = '<ul class="navbar-nav sidebar sidebar-light accordion" id="accordionSidebar">' +
    '<a class="sidebar-brand d-flex align-items-center justify-content-center" href="index.html">' +
    '<div class="sidebar-brand-icon">' + logo + '</div>' +
    '<div class="sidebar-brand-text mx-2">' + SITE.name + '<small>' + SITE.tagline + '</small></div></a>';
  NAV.forEach(function (g, gi) {
    s += '<hr class="sidebar-divider' + (gi === 0 ? ' my-0' : '') + '">';
    if (g.group) s += '<div class="sidebar-heading">' + g.group + '</div>';
    g.items.forEach(function (it) {
      s += '<li class="nav-item' + (it.id === page ? ' active' : '') + '"><a class="nav-link" href="' + it.href + '"' +
        (it.id === page ? ' aria-current="page"' : '') + '><i class="fas fa-fw ' + it.icon + '"></i><span>' + it.label + '</span></a></li>';
    });
  });
  s += '<hr class="sidebar-divider d-none d-md-block">' +
    '<div class="text-center d-none d-md-inline"><button class="rounded-circle border-0" id="sidebarToggle" aria-label="Collapse sidebar"></button></div>' +
    '</ul>';
  document.getElementById("sidebar-slot").outerHTML = s;

  var t = '<nav class="navbar navbar-expand navbar-light bg-white topbar mb-4 static-top shadow">' +
    '<button id="sidebarToggleTop" class="btn btn-link d-md-none rounded-circle mr-3" aria-label="Open menu"><i class="fa fa-bars"></i></button>' +
    '<div class="page-crumb d-none d-sm-block">' + SITE.name + ' <i class="fas fa-angle-right mx-1"></i> <strong>' + title + '</strong></div>' +
    '<ul class="navbar-nav ml-auto">' +
    '<li class="nav-item"><a class="nav-link" href="documentation.html"><i class="fas fa-book fa-fw mr-1"></i><span class="d-none d-lg-inline small">Docs</span></a></li>' +
    '</ul></nav>';
  document.getElementById("topbar-slot").outerHTML = t;
  var foot = document.getElementById("footer-slot");        // the site has no footer
  if (foot) foot.parentNode.removeChild(foot);
})();
