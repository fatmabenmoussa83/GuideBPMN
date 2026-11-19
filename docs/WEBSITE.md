# GuideBPMN website (GitHub Pages)

Static site, no build server needed. Pages live in `docs/` next to `assets/`.

- **Publish:** GitHub → Settings → Pages → Source: *Deploy from a branch* → Branch `main`, folder `/docs`.
- **Site identity:** title, menu and footer are set in `assets/js/layout.js`.
- **Edit page content:** edit `_build/pages/<page>.html`, then run `python docs/_build/build.py`
  (it rebuilds every page from the shared skeleton).
- **Figure:** `assets/img/guidebpmn_pipeline.png` is rendered from `bpmn_pipeline/figures/pipeline-vf5.pdf`.
- **Live parts** (Run and Guidelines pages) talk to the local API started with `.\start_webapi.ps1`.
- Built on SB Admin 2 (MIT, Start Bootstrap) and Font Awesome Free; licences in `assets/vendor/`.
