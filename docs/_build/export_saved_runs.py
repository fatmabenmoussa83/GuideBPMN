"""Save, next to the website, what the local API answers for the saved runs, so that the
Run page can show them online without an API (docs/data/saved/).

    python docs/_build/export_saved_runs.py        (from the repository root)

Run it again after adding runs to bpmn_pipeline/runs/. The large answers are gzip-compressed;
the page decompresses them in the browser."""
import gzip
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "webapi"))
from fastapi.testclient import TestClient   # noqa: E402
import webapi.app as appmod                  # noqa: E402

OUT = ROOT / "docs" / "data" / "saved"
GENERATORS = ("openai:gpt-6-luna", "anthropic:claude-haiku-5-5")


def main():
    client = TestClient(appmod.app)
    if OUT.exists():
        shutil.rmtree(OUT)

    def get(path):
        r = client.get(path)
        if r.status_code != 200:
            raise SystemExit(f"{path}: HTTP {r.status_code} {r.text[:200]}")
        return r

    def save(rel, path, compress=False):
        r = get(path)
        target = OUT / (rel + (".gz" if compress else ""))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(gzip.compress(r.content, 9) if compress else r.content)
        return r.json()

    runs = save("runs.json", "/api/orchestrator/runs")["runs"]
    for g in GENERATORS:
        save(f"study/{g.replace(':', '-')}.json", f"/api/orchestrator/study?generator={g}")
    for name in ("dataset", "folds", "models"):
        save(f"{name}.json", f"/api/orchestrator/{name}")
    examples = 0
    for run in runs:
        name = run["run"]
        save(f"runs/{name}/run.json", f"/api/orchestrator/runs/{name}", compress=True)
        for folder in sorted((ROOT / "bpmn_pipeline" / "runs" / name).glob("id_*")):
            i = folder.name[3:]
            r = client.get(f"/api/orchestrator/example/{i}?run={name}")
            if r.status_code == 200:
                (OUT / "runs" / name / f"example_{i}.json.gz").write_bytes(gzip.compress(r.content, 9))
                examples += 1
    print(f"{len(runs)} runs, {examples} descriptions saved in {OUT}")


if __name__ == "__main__":
    main()
