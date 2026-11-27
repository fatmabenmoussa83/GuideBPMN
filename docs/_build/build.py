"""Assemble the static pages: one shared skeleton + one content file per page.

  python _build/build.py

The output (*.html next to assets/) is plain static HTML for GitHub Pages; this
script is only needed when the page content changes.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent

PAGES = [
    # file, page id, title, description
    ("index.html", "home", "Overview",
     "GuideBPMN generates BPMN from text and learns reusable modeling guidelines from the OMG documentation and from its own verified mistakes."),
    ("run.html", "run", "Run GuideBPMN",
     "Test one description from zero, download everything the tool did, or launch the study on the 55-description dataset and watch the orchestrator, the agents, the metrics and the diagrams in real time."),
    ("compare.html", "compare", "Compare the runs",
     "Every model the study kept for one description, side by side: First, Revised (draft 0, each iteration, Learned) and Reuse, with their measures and their diagrams next to the reference."),
    ("guidelines.html", "guidelines", "Guidelines",
     "The documentation guidelines (OMG BPMN 2.0.2) and the guidelines GuideBPMN has learned from verified mistakes."),
    ("guideline_learning.html", "learning", "Guideline learning (agents)",
     "How the Retriever and Expert agents learn error-driven guidelines: their ReAct loops, their tools, the code guards and the catalogue."),
    ("orchestrator.html", "orchestrator", "Orchestrator and budgets",
     "The orchestrator's actions, the budgets of one description, the stop rules, the failure types T1-T7 and the bonuses and penalties."),
    ("validator.html", "validator", "Structural validator L1-L4",
     "The four levels of the structural validator (L1-L4), how its results are measured and the deadlock check."),
    ("similarity.html", "similarity", "Similarity evaluator",
     "Every score of the similarity evaluator with its equation: pairing, activities, connections, coverage, workflow order, swimlanes and messages."),
    ("documentation.html", "docs", "Documentation",
     "Installation, configuration, usage and outputs of GuideBPMN."),
    ("404.html", "none", "Page not found", "This page does not exist."),
]

SKELETON = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
<meta name="description" content="{desc}">
<title>{title} | GuideBPMN</title>
<link rel="icon" href="assets/img/favicon.svg" type="image/svg+xml">
<link href="assets/vendor/fontawesome/css/all.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css?family=Nunito:400,600,700,800,900&display=swap" rel="stylesheet">
<link href="assets/css/sb-admin-2.min.css" rel="stylesheet">
<link href="assets/css/guidebpmn.css" rel="stylesheet">
</head>
<body id="page-top" data-page="{pid}" data-title="{title}">
<div id="wrapper">
<div id="sidebar-slot"></div>
<div id="content-wrapper" class="d-flex flex-column">
<div id="content">
<div id="topbar-slot"></div>
<main class="container-fluid">
{content}
</main>
</div>
<div id="footer-slot"></div>
</div>
</div>
<a class="scroll-to-top rounded" href="#page-top" aria-label="Back to top"><i class="fas fa-angle-up"></i></a>
<script src="assets/vendor/jquery/jquery.min.js"></script>
<script src="assets/vendor/bootstrap/bootstrap.bundle.min.js"></script>
<script src="assets/vendor/jquery-easing/jquery.easing.min.js"></script>
<script src="assets/js/layout.js"></script>
<script src="assets/js/sb-admin-2.min.js"></script>
{scripts}
</body>
</html>
"""


NUMBERS = SITE.parent / "paper" / "numbers.tex"


def paper_numbers() -> dict:
    """The macros of paper/numbers.tex (tools/paper_numbers.py), so the site shows the paper's numbers."""
    import re
    if not NUMBERS.is_file():
        return {}
    found = re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}", NUMBERS.read_text(encoding="utf-8"))
    return {k: ("TBD" if "TBD" in v else v) for k, v in found}


def fill(text: str, numbers: dict) -> str:
    import re
    return re.sub(r"\{\{(\w+)\}\}", lambda m: numbers.get(m.group(1), m.group(0)), text)


def bust(html: str, version: str) -> str:
    """Add ?v=<build> to local scripts and stylesheets, so browsers never keep an old copy."""
    import re
    return re.sub(r'((?:src|href)="assets/[^"?]+\.(?:js|css))"', lambda m: f'{m.group(1)}?v={version}"', html)


def main():
    import time
    ASSET_VERSION = time.strftime("%Y%m%d%H%M")
    numbers = paper_numbers()
    for fname, pid, title, desc in PAGES:
        src = HERE / "pages" / fname
        text = src.read_text(encoding="utf-8")
        content, _, scripts = fill(text, numbers).partition("<!--SCRIPTS-->")
        html = SKELETON.format(desc=desc, title=title, pid=pid, content=content.strip(),
                               scripts=scripts.strip())
        (SITE / fname).write_text(bust(html, ASSET_VERSION), encoding="utf-8")
        print("wrote", fname)
    write_documentation_guidelines()


def write_documentation_guidelines():
    """The read-only documentation catalogue, as a script the Guidelines page loads
    (works from GitHub Pages, a local server or a file opened directly)."""
    import json
    source = SITE.parent / "guidelines" / "bpmn_documentation_guidelines.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    target = SITE / "assets" / "data" / "documentation_guidelines.js"
    target.write_text("/* generated by _build/build.py from guidelines/bpmn_documentation_guidelines.json */\n"
                      "window.DOC_GUIDELINES = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n",
                      encoding="utf-8")
    print("wrote", target.relative_to(SITE))


if __name__ == "__main__":
    main()
