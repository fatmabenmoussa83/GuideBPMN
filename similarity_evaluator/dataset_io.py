"""Load one reference/generated pair by ID (standalone use of a module: python <module>.py <id> <generated.json>)."""

import json
import csv
from pathlib import Path
from config import DATASET_PATH


def _read(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _by_id(entries, entry_id: str):
    wanted = str(entry_id).zfill(2)
    for entry in entries:
        if str(entry.get("id", "")).zfill(2) == wanted:
            return entry
    raise KeyError(f"ID {wanted!r} not found")


def load_pair(entry_id: str, generator: str = "gpt",
              dataset_path=DATASET_PATH, generated_path=None):
    """generated_path: a JSON list of {id, generated_bpmn_xml} (e.g. a run's
    round_K/generated_bpmn_gpt.json); the pipeline itself passes XML directly."""
    generator = generator.lower()
    if generated_path is None:
        raise ValueError("generated_path is needed: a JSON list of {id, generated_bpmn_xml}")
    generated_path = Path(generated_path)
    gold = _by_id(_read(Path(dataset_path)), entry_id)
    generated = _by_id(_read(generated_path), entry_id)
    gold_xml = gold.get("bpmn_xml") or generated.get("reference_bpmn_xml")
    generated_xml = generated.get("generated_bpmn_xml")
    if not gold_xml:
        raise ValueError(f"No gold XML for id={entry_id}")
    if not generated_xml:
        raise ValueError(f"No generated XML for id={entry_id}")
    return {
        "id": str(entry_id).zfill(2),
        "generator": generator,
        "description": gold.get("description", ""),
        "gold_xml": gold_xml,
        "generated_xml": generated_xml,
    }


def write_json(data, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_rows_csv(rows, path, fieldnames=None):
    """Write a flat, Excel-readable audit table using UTF-8 BOM."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_matrix_csv(values, row_elements, column_elements, path,
                     value_name="value", footer_rows=None):
    """Wide matrix with human-identifiable row and column headers."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    column_headers = [
        f"{e['id']} | {e['category']} | {e.get('label') or '[NO LABEL]'}"
        for e in column_elements
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["gold_id", "gold_type", "gold_category", "gold_label", *column_headers])
        for element, row in zip(row_elements, values):
            writer.writerow([
                element["id"], element["type"], element["category"],
                element.get("label") or "[NO LABEL]", *row,
            ])
        for footer in footer_rows or []:
            writer.writerow([
                footer.get("label", "SUMMARY"), "", "",
                footer.get("formula", ""), footer.get("value", ""),
            ])
    return path
