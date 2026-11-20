"""Save the learned-guideline catalogues of the study next to the website
(docs/data/saved/guidelines/), so the Guidelines page can show them online without
the local API. Same content as /api/orchestrator/guidelines?catalogue=<id>.

    python docs/_build/export_saved_guidelines.py        (from the repository root)
"""
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEARNED = ROOT / "guidelines" / "learned"
OUT = ROOT / "docs" / "data" / "saved" / "guidelines"


def catalogues() -> list[dict]:
    out = []
    for model_dir in sorted(p for p in LEARNED.iterdir() if p.is_dir()):
        model = model_dir.name
        for pattern, kind in (("agents/replicates/r*/learned_guidelines.json", "replicate"),
                              ("agents/folds/fold_*/learned_guidelines.json", "fold")):
            for path in sorted(model_dir.glob(pattern), key=lambda p: (len(p.parent.name), p.parent.name)):
                items = json.loads(path.read_text(encoding="utf-8")).get("guidelines", [])
                part = path.parent.name
                label = (f"{model} · Revised run {part[1:]}" if kind == "replicate"
                         else f"{model} · Reuse round {part.split('_')[-1]} (training)")
                general = [g for g in items if g.get("status") == "promoted"]
                out.append({"id": f"{model}/agents/{path.parent.parent.name}/{part}", "label": label, "file": path,
                            "count": len(items), "general": len(general),
                            "confirmed": sum(bool((g.get("confirmation") or {}).get("confirmed")) for g in general)})
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cats = catalogues()
    listing = [{k: c[k] for k in ("id", "label", "count", "general", "confirmed")} for c in cats]
    for c in cats:
        data = json.loads(c["file"].read_text(encoding="utf-8"))
        data.update(catalogue=c["id"], label=c["label"], catalogues=listing)
        name = c["id"].replace("/", "__") + ".json.gz"
        (OUT / name).write_bytes(gzip.compress(json.dumps(data, separators=(",", ":")).encode("utf-8"), 9))
    (OUT / "index.json").write_text(json.dumps({"catalogues": listing}, indent=1), encoding="utf-8")
    print(f"{len(cats)} catalogues saved in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
